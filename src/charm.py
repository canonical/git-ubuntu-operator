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
import re
from os import system

import ops
from charms.operator_libs_linux.v0 import apt
from charms.operator_libs_linux.v2 import snap

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)

VALID_LOG_LEVELS = ["info", "debug", "warning", "error", "critical"]


class GitUbuntuCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.install, self._on_install)

    def _on_start(self, event: ops.StartEvent):
        """Handle start event."""
        self.unit.status = ops.ActiveStatus()

    def _update_lpuser_config(self):
        """Update the launchpad user setting."""
        # Confirm lpuser follows Launchpad User ID requirements.
        lpuser = str(self.config.get("lpuser"))
        if not re.match(r"^[a-z0-9\.\-\+]+$", lpuser):
            self.unit.status = ops.BlockedStatus(
                "lpuser does not match Launchpad User ID requirements."
            )
            return False

        # Attempt to update the global git config with the new Launchpad User ID.
        update_config_result = system(f'git config --global gitubuntu.lpuser "{lpuser}"')
        if update_config_result != 0:
            self.unit.status = ops.BlockedStatus("Failed to update lpuser config.")
            return False

        return True

    def _update_git_ubuntu_snap(self):
        """Install or refresh the git-ubuntu snap with the given channel version."""
        self.unit.status = ops.MaintenanceStatus("Installing git-ubuntu snap")

        # Confirm the channel is valid.
        channel = self.config.get("channel")
        if channel not in ("beta", "edge", "stable"):
            self.unit.status = ops.BlockedStatus("Invalid channel configured.")
            return False

        # Install or refresh the git-ubuntu snap.
        try:
            cache = snap.SnapCache()
            git_ubuntu_snap = cache["git-ubuntu"]
            git_ubuntu_snap.ensure(snap.SnapState.Latest, classic=True, channel=channel)
        except snap.SnapError as e:
            self.unit.status = ops.BlockedStatus(f"Failed to install git-ubuntu snap: {str(e)}")
            return False

        return True

    def _on_install(self, event: ops.InstallEvent):
        """Handle install event."""
        # Install git
        self.unit.status = ops.MaintenanceStatus("Installing git")
        try:
            apt.update()
            apt.add_package("git")
        except apt.PackageError as e:
            self.unit.status = ops.BlockedStatus(f"Failed to install git: {str(e)}")
            return

        # Set lpuser config
        if not self._update_lpuser_config():
            return

        # Install git-ubuntu snap
        if not self._update_git_ubuntu_snap():
            return

        self.unit.status = ops.ActiveStatus("Ready")

    def _on_config_changed(self, event: ops.ConfigChangedEvent):
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
