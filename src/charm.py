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

    def _on_start(self, _: ops.StartEvent) -> None:
        """Handle start event."""
        self.unit.status = ops.ActiveStatus()

    def _update_lpuser_config(self) -> bool:
        """Attempt to update git config with the new Launchpad User ID."""
        lpuser = str(self.config.get("lpuser"))
        if lp.is_valid_lp_username(lpuser):
            if not pkgs.git_update_lpuser_config(lpuser):
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
        channel = str(self.config.get("channel"))
        if channel not in ("beta", "edge", "stable"):
            self.unit.status = ops.BlockedStatus("Invalid channel configured.")
            return False

        # Install or refresh the git-ubuntu snap.
        if not pkgs.git_ubuntu_snap_refresh(channel):
            self.unit.status = ops.BlockedStatus("Failed to install or refresh git-ubuntu snap")
            return False

        return True

    def _on_install(self, _: ops.InstallEvent) -> None:
        """Handle install event."""
        # Install git and update lp user
        self.unit.status = ops.MaintenanceStatus("Installing git")

        if not pkgs.git_install():
            self.unit.status = ops.BlockedStatus("Failed to install git")
            return

        if not self._update_lpuser_config():
            return

        # Install git-ubuntu snap
        if not self._update_git_ubuntu_snap():
            return

        self.unit.status = ops.ActiveStatus("Ready")

    def _on_config_changed(self, _: ops.ConfigChangedEvent) -> None:
        """Handle updates to config items."""
        # Update lpuser config
        if not self._update_lpuser_config():
            return

        # Update git-ubuntu snap
        if not self._update_git_ubuntu_snap():
            return

        self.unit.status = ops.ActiveStatus("Ready")


if __name__ == "__main__":  # pragma: nocover
    ops.main(GitUbuntuCharm)
