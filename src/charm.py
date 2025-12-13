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
import socket
from pathlib import Path

import ops

import environment as env
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

        self.framework.observe(self.on.leader_elected, self._on_leader_elected)
        self.framework.observe(
            self.on.replicas_relation_changed, self._on_replicas_relation_changed
        )

    @property
    def _peer_relation(self) -> ops.Relation | None:
        """Get replica peer relation if available."""
        return self.model.get_relation("replicas")

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
        return int(self.unit.name.split("/")[-1])

    @property
    def _is_primary(self) -> bool:
        return self.unit.is_leader()

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
    def _lpuser_secret(self) -> ops.model.Secret | None:
        secret_id: str = ""

        try:
            secret_id = str(self.config["lpuser_secret_id"])
        except KeyError:
            logger.warning("lpuser_secret_id config not available, unable to extract keys.")
            return None

        try:
            return self.model.get_secret(id=secret_id)
        except (ops.SecretNotFoundError, ops.model.ModelError):
            logger.warning("Failed to get lpuser secret with id %s", secret_id)

        return None

    @property
    def _lpuser_ssh_key(self) -> str | None:
        secret = self._lpuser_secret

        if secret is not None:
            try:
                return secret.get_content(refresh=True)["sshkey"]
            except KeyError:
                logger.warning("sshkey secret key not found in lpuser secret.")

        return None

    @property
    def _lpuser_lp_key(self) -> str | None:
        secret = self._lpuser_secret

        if secret is not None:
            try:
                return secret.get_content(refresh=True)["lpkey"]
            except KeyError:
                logger.warning("lpkey secret key not found in lpuser secret.")

        return None

    @property
    def _git_ubuntu_primary_relation(self) -> ops.Relation | None:
        """Get the peer relation that contains the primary node IP.

        Returns:
            The peer relation or None if it does not exist.
        """
        return self.model.get_relation("replicas")

    def _open_controller_port(self) -> bool:
        """Open the configured controller network port.

        Returns:
            True if the port was opened, False otherwise.
        """
        self.unit.status = ops.MaintenanceStatus("Opening controller port.")

        try:
            port = self._controller_port

            if port > 0:
                self.unit.set_ports(port)
                logger.info("Opened controller port %d", port)
            else:
                self.unit.status = ops.BlockedStatus("Invalid controller port configuration.")
                return False
        except ops.ModelError:
            self.unit.status = ops.BlockedStatus("Failed to open controller port.")
            return False

        return True

    def _set_peer_primary_node_address(self) -> bool:
        """Set the primary node's IP to this unit's in the peer relation databag.

        Returns:
            True if the data was updated, False otherwise.
        """
        self.unit.status = ops.MaintenanceStatus("Setting primary node address in peer relation.")

        relation = self._git_ubuntu_primary_relation

        if relation:
            new_primary_address = socket.gethostbyname(socket.gethostname())
            relation.data[self.app]["primary_address"] = new_primary_address
            logger.info("Updated primary node address to %s", new_primary_address)
            return True

        return False

    def _get_primary_node_address(self) -> str | None:
        """Get the primary node's network address - local if primary or juju binding if secondary.

        Returns:
            The primary IP as a string if available, None otherwise.
        """
        if self._is_primary:
            return "127.0.0.1"

        relation = self._git_ubuntu_primary_relation

        if relation:
            primary_address = relation.data[self.app]["primary_address"]

            if primary_address is not None and len(str(primary_address)) > 0:
                logger.info("Found primary node address %s", primary_address)
                return str(primary_address)

        logger.warning("No primary node address found.")
        return None

    def _refresh_secret_keys(self) -> bool:
        """Refresh the SSH and Launchpad keys for the git-ubuntu user from secrets.

        Returns:
            True if the keys were updated successfully, False otherwise.
        """
        self.unit.status = ops.MaintenanceStatus("Refreshing secret keys.")

        ssh_key_data = self._lpuser_ssh_key
        lp_key_data = self._lpuser_lp_key

        if self._is_publishing_active:
            if ssh_key_data is None:
                logger.warning("ssh private key unavailable, Launchpad publishing will fail.")
            elif not usr.update_ssh_private_key(
                GIT_UBUNTU_SYSTEM_USER_USERNAME, GIT_UBUNTU_USER_HOME_DIR, ssh_key_data
            ):
                self.unit.status = ops.BlockedStatus(
                    "Failed to update SSH key for git-ubuntu user."
                )
                return False

        if lp_key_data is None:
            logger.warning("Launchpad credentials unavailable, unable to gather package updates.")
        elif not usr.update_launchpad_credentials_secret(
            GIT_UBUNTU_SYSTEM_USER_USERNAME, GIT_UBUNTU_USER_HOME_DIR, lp_key_data
        ):
            self.unit.status = ops.BlockedStatus(
                "Failed to update Launchpad credentials for git-ubuntu user."
            )
            return False

        return True

    def _refresh_git_ubuntu_source(self) -> bool:
        """Refresh the git-ubuntu source code from the configured URL.

        Returns:
            True if the source was refreshed successfully, False otherwise.
        """
        self.unit.status = ops.MaintenanceStatus("Refreshing git-ubuntu source.")

        # Set https proxy environment variable if available.
        https_proxy = env.get_juju_https_proxy_url()

        if https_proxy != "":
            logger.info("Using https proxy %s for git-ubuntu source refresh.", https_proxy)

        # Run clone or pull of git-ubuntu source.
        if not usr.refresh_git_ubuntu_source(
            GIT_UBUNTU_SYSTEM_USER_USERNAME,
            GIT_UBUNTU_USER_HOME_DIR,
            GIT_UBUNTU_SOURCE_URL,
            https_proxy,
        ):
            self.unit.status = ops.BlockedStatus("Failed to refresh git-ubuntu source.")
            return False

        return True

    def _refresh_ssh_config(self) -> bool:
        """Refresh the SSH config for the git-ubuntu user.

        Returns:
            True if the config was updated successfully, False otherwise.
        """
        self.unit.status = ops.MaintenanceStatus("Refreshing SSH config.")

        if not usr.update_ssh_config(
            GIT_UBUNTU_SYSTEM_USER_USERNAME,
            GIT_UBUNTU_USER_HOME_DIR,
            env.get_juju_http_proxy_url(),
        ):
            self.unit.status = ops.BlockedStatus(
                "Failed to update SSH config for git-ubuntu user."
            )
            return False

        return True

    def _refresh_importer_node(self) -> None:
        """Remove old and install new git-ubuntu services."""
        self.unit.status = ops.MaintenanceStatus("Refreshing git-ubuntu services.")

        if not node.reset(GIT_UBUNTU_USER_HOME_DIR):
            self.unit.status = ops.BlockedStatus("Failed to remove old git-ubuntu services.")
            return

        if self._is_primary:
            if not node.setup_primary_node(
                GIT_UBUNTU_USER_HOME_DIR,
                GIT_UBUNTU_SYSTEM_USER_USERNAME,
                self._controller_port,
                env.get_juju_http_proxy_url(),
                env.get_juju_https_proxy_url(),
            ):
                self.unit.status = ops.BlockedStatus("Failed to install git-ubuntu services.")
                return
            logger.info("Initialized importer node as primary.")
        else:
            primary_ip = self._get_primary_node_address()

            if primary_ip is None:
                self.unit.status = ops.BlockedStatus("Secondary node requires a peer relation.")
                return

            if not node.setup_secondary_node(
                GIT_UBUNTU_USER_HOME_DIR,
                GIT_UBUNTU_SYSTEM_USER_USERNAME,
                self._is_publishing_active,
                self._controller_port,
                primary_ip,
                Path(GIT_UBUNTU_USER_HOME_DIR, ".config/lp-credentials.oauth").as_posix(),
                env.get_juju_https_proxy_url(),
            ):
                self.unit.status = ops.BlockedStatus("Failed to install git-ubuntu services.")
                return
            logger.info("Initialized importer node as secondary.")

        self.unit.status = ops.ActiveStatus("Importer node install complete.")

    def _start_services(self) -> None:
        """Start the services and note the result through status."""
        if node.start(GIT_UBUNTU_USER_HOME_DIR, self._node_id, self._num_workers):
            node_type_str = "primary" if self._is_primary else "secondary"
            self.unit.status = ops.ActiveStatus(
                f"Running git-ubuntu importer {node_type_str} node."
            )
        else:
            self.unit.status = ops.BlockedStatus("Failed to start services.")

    def _on_start(self, _: ops.StartEvent) -> None:
        """Handle start event."""
        self._start_services()

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

        self.unit.status = ops.MaintenanceStatus("Installing socat.")

        if not pkgs.socat_install():
            self.unit.status = ops.BlockedStatus("Failed to install socat.")
            return

        self.unit.status = ops.MaintenanceStatus("Setting up git-ubuntu user.")
        usr.setup_git_ubuntu_user(GIT_UBUNTU_SYSTEM_USER_USERNAME, GIT_UBUNTU_USER_HOME_DIR)

        self.unit.status = ops.MaintenanceStatus("Setting up git-ubuntu user services directory.")
        if not usr.setup_git_ubuntu_user_services_dir(
            GIT_UBUNTU_SYSTEM_USER_USERNAME, GIT_UBUNTU_USER_HOME_DIR
        ):
            self.unit.status = ops.BlockedStatus("Failed to set up git-ubuntu services directory.")
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
        """Handle updates to config items.

        Update user settings, git config, the git-ubuntu snap and source, open ports, and keys.
        If everything is successful, refresh git-ubuntu services.
        """
        if (
            self._update_git_user_config()
            and self._update_lpuser_config()
            and self._update_git_ubuntu_snap()
            and self._open_controller_port()
            and self._refresh_secret_keys()
            and self._refresh_ssh_config()
            and self._refresh_git_ubuntu_source()
        ):
            # Initialize or re-install git-ubuntu services as needed.
            self._refresh_importer_node()

    def _on_leader_elected(self, _: ops.LeaderElectedEvent) -> None:
        """Refresh services and update peer data when the unit is elected as leader."""
        if not self._set_peer_primary_node_address():
            self.unit.status = ops.BlockedStatus(
                "Failed to update primary node IP in peer relation."
            )

    def _on_replicas_relation_changed(self, _: ops.RelationChangedEvent) -> None:
        """Refresh services for secondary nodes when peer relations change."""
        if not self._is_primary:
            self._refresh_importer_node()
            self._start_services()


if __name__ == "__main__":  # pragma: nocover
    ops.main(GitUbuntuCharm)
