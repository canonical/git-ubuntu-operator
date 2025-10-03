#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Charm the service.

Refer to the following tutorial that will help you
develop a new k8s charm using the Operator Framework:

https://juju.is/docs/sdk/create-a-minimal-kubernetes-charm
"""

import logging
from pathlib import Path

import ops

import importer_node as node
import launchpad as lp
import package_installation as pkgs
import user_management as usr

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)

VALID_LOG_LEVELS = ["info", "debug", "warning", "error", "critical"]

# Constant configuration values
GIT_UBUNTU_SYSTEM_USER_USERNAME = "git-ubuntu"
GIT_UBUNTU_GIT_USER_NAME = "Ubuntu Git Importer"
GIT_UBUNTU_GIT_EMAIL = "usd-importer-do-not-mail@canonical.com"
GIT_UBUNTU_USER_HOME_DIR = "/var/local/git-ubuntu"
GIT_UBUNTU_SOURCE_URL = "https://git.launchpad.net/git-ubuntu"
GIT_UBUNTU_KEYRING_FOLDER = Path(__file__).parent.parent / "keyring"


class GitUbuntuCharm(ops.CharmBase):
    """Charm git-ubuntu for package importing."""

    def __init__(self, framework: ops.Framework):
        """Construct charm.

        Args:
            framework: charm framework managed by parent class.
        """
        super().__init__(framework)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.config_changed, self._on_config_changed)

    @property
    def _controller_ip(self) -> str:
        return str(self.config.get("controller_ip"))

    @property
    def _controller_port(self) -> int:
        port = self.config.get("controller_port")
        if isinstance(port, int):
            return port
        return 0

    @property
    def _git_ubuntu_snap_channel(self) -> str:
        return str(self.config.get("channel"))

    @property
    def _lp_username(self) -> str:
        return str(self.config.get("lpuser"))

    @property
    def _node_id(self) -> int:
        node_id = self.config.get("node_id")
        if isinstance(node_id, int):
            return node_id
        return 0

    @property
    def _is_primary(self) -> bool:
        if self.config.get("primary"):
            return True
        return False

    @property
    def _is_publishing_active(self) -> bool:
        if self.config.get("publish"):
            return True
        return False

    @property
    def _num_workers(self) -> int:
        num_workers = self.config.get("workers")
        if isinstance(num_workers, int):
            return num_workers
        return 0

    @property
    def _lpuser_ssh_key(self) -> str | None:
        try:
            secret_id = self.config.get("lpuser-ssh-key")
            ssh_key_secret = self.model.get_secret(id=secret_id)
            return ssh_key_secret.get_content().get("lpuser-ssh-key")
        except (KeyError, ops.SecretNotFoundError, ops.model.ModelError):
            return None

    def _refresh_importer_node(self) -> None:
        """Remove old and install new git-ubuntu services."""
        self.unit.status = ops.MaintenanceStatus("Refreshing git-ubuntu services.")

        if not node.reset(GIT_UBUNTU_USER_HOME_DIR):
            self.unit.status = ops.BlockedStatus("Failed to remove old git-ubuntu services.")
            return

        if self._is_primary:
            if not node.setup_primary_node(
                GIT_UBUNTU_USER_HOME_DIR,
                self._node_id,
                self._num_workers,
                GIT_UBUNTU_SYSTEM_USER_USERNAME,
                self._is_publishing_active,
                self._controller_port,
            ):
                self.unit.status = ops.BlockedStatus("Failed to install git-ubuntu services.")
                return
            logger.info("Initialized importer node as primary.")
        else:
            if not node.setup_secondary_node(
                GIT_UBUNTU_USER_HOME_DIR,
                self._node_id,
                self._num_workers,
                GIT_UBUNTU_SYSTEM_USER_USERNAME,
                self._is_publishing_active,
                self._controller_port,
                self._controller_ip,
            ):
                self.unit.status = ops.BlockedStatus("Failed to install git-ubuntu services.")
                return
            logger.info("Initialized importer node as secondary.")

        self.unit.status = ops.ActiveStatus("Importer node install complete.")

    def _on_start(self, _: ops.StartEvent) -> None:
        """Handle start event."""
        if node.start(GIT_UBUNTU_USER_HOME_DIR):
            node_type_str = "primary" if self._is_primary else "secondary"
            self.unit.status = ops.ActiveStatus(
                f"Running git-ubuntu importer {node_type_str} node."
            )
        else:
            self.unit.status = ops.BlockedStatus("Failed to start services.")

    def _update_git_user_config(self) -> bool:
        """Attempt to update git config with the default git-ubuntu user name and email."""
        self.unit.status = ops.MaintenanceStatus("Updating git config for git-ubuntu user.")

        if not usr.update_git_user_name(
            GIT_UBUNTU_SYSTEM_USER_USERNAME, GIT_UBUNTU_GIT_USER_NAME
        ) or not usr.update_git_email(GIT_UBUNTU_SYSTEM_USER_USERNAME, GIT_UBUNTU_GIT_EMAIL):
            self.unit.status = ops.BlockedStatus("Failed to set git user config.")
            return False
        return True

    def _update_lpuser_config(self) -> bool:
        """Attempt to update git config with the new Launchpad User ID."""
        self.unit.status = ops.MaintenanceStatus("Updating lpuser entry for git-ubuntu user.")
        lpuser = self._lp_username
        if lp.is_valid_lp_username(lpuser):
            if not usr.update_git_ubuntu_lpuser(GIT_UBUNTU_SYSTEM_USER_USERNAME, lpuser):
                self.unit.status = ops.BlockedStatus("Failed to update lpuser config.")
                return False
        else:
            self.unit.status = ops.BlockedStatus(
                "lpuser does not match Launchpad User ID requirements."
            )
            return False
        return True

    def _update_git_ubuntu_snap(self) -> bool:
        """Install or refresh the git-ubuntu snap with the given channel version."""
        self.unit.status = ops.MaintenanceStatus("Updating git-ubuntu snap.")

        # Confirm the channel is valid.
        channel = self._git_ubuntu_snap_channel
        if channel not in ("beta", "edge", "stable"):
            self.unit.status = ops.BlockedStatus("Invalid channel configured.")
            return False

        # Install or refresh the git-ubuntu snap.
        if not pkgs.git_ubuntu_snap_refresh(channel):
            self.unit.status = ops.BlockedStatus("Failed to install or refresh git-ubuntu snap.")
            return False

        return True

    def _on_install(self, _: ops.InstallEvent) -> None:
        """Handle one-time installation of packages during install hook."""
        self.unit.status = ops.MaintenanceStatus("Installing git.")

        if not pkgs.git_install():
            self.unit.status = ops.BlockedStatus("Failed to install git.")
            return

        self.unit.status = ops.MaintenanceStatus("Installing sqlite3.")

        if not pkgs.sqlite3_install():
            self.unit.status = ops.BlockedStatus("Failed to install sqlite3.")
            return

        self.unit.status = ops.MaintenanceStatus("Setting up git-ubuntu user.")
        usr.setup_git_ubuntu_user(GIT_UBUNTU_SYSTEM_USER_USERNAME, GIT_UBUNTU_USER_HOME_DIR)

        self.unit.status = ops.MaintenanceStatus("Setting up git-ubuntu user files.")
        if not usr.setup_git_ubuntu_user_files(
            GIT_UBUNTU_SYSTEM_USER_USERNAME,
            GIT_UBUNTU_USER_HOME_DIR,
            GIT_UBUNTU_SOURCE_URL,
        ):
            self.unit.status = ops.BlockedStatus("Failed to set up git-ubuntu user files.")
            return

        if not usr.set_snap_homedirs(GIT_UBUNTU_USER_HOME_DIR):
            self.unit.status = ops.BlockedStatus(
                "Failed to allow snap to use homedirs outside /home."
            )
            return

        if not pkgs.git_ubuntu_add_debian_archive_keyring(GIT_UBUNTU_KEYRING_FOLDER):
            self.unit.status = ops.BlockedStatus(
                "Failed to copy debian archive keyring to /etc/git-ubuntu."
            )
            return

        self.unit.status = ops.ActiveStatus("Install complete.")

    def _on_config_changed(self, _: ops.ConfigChangedEvent) -> None:
        """Handle updates to config items."""
        # Update user's git and lpuser config, and git-ubuntu snap
        if (
            not self._update_git_user_config()
            or not self._update_lpuser_config()
            or not self._update_git_ubuntu_snap()
        ):
            return

        # Initialize or re-install git-ubuntu services as needed.
        self._refresh_importer_node()


if __name__ == "__main__":  # pragma: nocover
    ops.main(GitUbuntuCharm)
