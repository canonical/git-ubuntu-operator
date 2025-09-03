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

import ops

import launchpad as lp
import package_configuration as pkgs
from importer_node import EmptyImporterNode, ImporterNode, PrimaryImporterNode
from user_management import setup_git_ubuntu_user

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)

VALID_LOG_LEVELS = ["info", "debug", "warning", "error", "critical"]


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

        self._git_ubuntu_importer_node: ImporterNode = EmptyImporterNode()

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
    def _data_directory(self) -> str:
        return str(self.config.get("data_directory"))

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
    def _source_directory(self) -> str:
        return str(self.config.get("source_directory"))

    @property
    def _system_username(self) -> str:
        return str(self.config.get("system_user"))

    @property
    def _num_workers(self) -> int:
        num_workers = self.config.get("workers")
        if isinstance(num_workers, int):
            return num_workers
        return 0

    def _init_importer_node(self) -> None:
        """Initialize the git-ubuntu instance manager and install services."""
        self.unit.status = ops.MaintenanceStatus("Setting up git-ubuntu services.")

        if self._is_primary:
            self._git_ubuntu_importer_node = PrimaryImporterNode(
                self._node_id,
                self._num_workers,
                self._system_username,
                self._is_publishing_active,
                self._controller_port,
                self._data_directory,
                self._source_directory,
            )
        else:
            self._git_ubuntu_importer_node = ImporterNode(
                self._node_id,
                self._num_workers,
                self._system_username,
                self._is_publishing_active,
                self._controller_port,
                self._controller_ip,
            )

        if self._git_ubuntu_importer_node.install():
            self.unit.status = ops.ActiveStatus("Ready")
        else:
            self.unit.status = ops.BlockedStatus("Failed to install git-ubuntu services.")

    def _refresh_importer_node(self) -> None:
        """Check existing importer node and re-initialize its services as needed."""
        self.unit.status = ops.MaintenanceStatus("Refreshing git-ubuntu service files.")

        run_install = False
        update_fail = False

        # Initialize the instance manager if it has yet to be.
        if isinstance(self._git_ubuntu_importer_node, EmptyImporterNode):
            run_install = True

        # Update git-ubuntu instances.
        elif self._is_primary:
            # This node is becoming the primary node but is secondary.
            if not isinstance(self._git_ubuntu_importer_node, PrimaryImporterNode):
                if not self._git_ubuntu_importer_node.destroy():
                    self.unit.status = ops.BlockedStatus("Failed to destroy existing services.")
                    return
                run_install = True

            # Update primary node with new values.
            elif isinstance(
                self._git_ubuntu_importer_node, PrimaryImporterNode
            ) and not self._git_ubuntu_importer_node.update(  # pylint: disable=unexpected-keyword-arg
                False,
                self._node_id,
                self._num_workers,
                self._system_username,
                self._is_publishing_active,
                self._controller_port,
                "127.0.0.1",
                data_directory=self._data_directory,
                source_directory=self._source_directory,
            ):
                update_fail = True
        else:
            # This node is becoming secondary but is the primary.
            if isinstance(self._git_ubuntu_importer_node, PrimaryImporterNode):
                if not self._git_ubuntu_importer_node.destroy():
                    self.unit.status = ops.BlockedStatus("Failed to destroy existing services.")
                    return
                run_install = True

            # Update primary node with new values.
            elif not self._git_ubuntu_importer_node.update(
                False,
                self._node_id,
                self._num_workers,
                self._system_username,
                self._is_publishing_active,
                self._controller_port,
                self._controller_ip,
            ):
                update_fail = True

        if run_install:
            # Initialize and install a new node.
            self._init_importer_node()
        elif update_fail:
            # Show that service updates failed.
            self.unit.status = ops.BlockedStatus("Failed to update services.")
        else:
            self.unit.status = ops.ActiveStatus("Ready")

    def _on_start(self, _: ops.StartEvent) -> None:
        """Handle start event."""
        if isinstance(self._git_ubuntu_importer_node, EmptyImporterNode):
            self.unit.status = ops.BlockedStatus("Failed to start, services not yet installed.")
        elif self._git_ubuntu_importer_node.start():
            self.unit.status = ops.ActiveStatus()
        else:
            self.unit.status = ops.BlockedStatus("Failed to start services.")

    def _update_git_user_config(self) -> bool:
        """Attempt to update git config with the default git-ubuntu user name and email."""
        name = "Ubuntu Git Importer"
        email = "usd-importer-do-not-mail@canonical.com"
        if not pkgs.git_update_user_name_config(
            self._system_username, name
        ) or not pkgs.git_update_user_email_config(self._system_username, email):
            self.unit.status = ops.BlockedStatus("Failed to set git user config.")
            return False
        return True

    def _update_lpuser_config(self) -> bool:
        """Attempt to update git config with the new Launchpad User ID."""
        lpuser = self._lp_username
        if lp.is_valid_lp_username(lpuser):
            if not pkgs.git_update_lpuser_config(self._system_username, lpuser):
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
        self.unit.status = ops.MaintenanceStatus("Updating git-ubuntu snap")

        # Confirm the channel is valid.
        channel = self._git_ubuntu_snap_channel
        if channel not in ("beta", "edge", "stable"):
            self.unit.status = ops.BlockedStatus("Invalid channel configured.")
            return False

        # Install or refresh the git-ubuntu snap.
        if not pkgs.git_ubuntu_snap_refresh(channel):
            self.unit.status = ops.BlockedStatus("Failed to install or refresh git-ubuntu snap")
            return False

        return True

    def _on_install(self, _: ops.InstallEvent) -> None:
        """Handle one-time installation of packages during install hook."""
        self.unit.status = ops.MaintenanceStatus("Installing git")

        if not pkgs.git_install():
            self.unit.status = ops.BlockedStatus("Failed to install git")
            return

        self.unit.status = ops.MaintenanceStatus("Installing sqlite3")

        if not pkgs.sqlite3_install():
            self.unit.status = ops.BlockedStatus("Failed to install sqlite3")
            return

        self.unit.status = ops.ActiveStatus("Ready")

    def _on_config_changed(self, _: ops.ConfigChangedEvent) -> None:
        """Handle updates to config items."""
        self.unit.status = ops.MaintenanceStatus("Setting up git-ubuntu user")
        setup_git_ubuntu_user(self._system_username)

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
