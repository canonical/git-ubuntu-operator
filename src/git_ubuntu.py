#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Git Ubuntu service runner and configurator."""


class GitUbuntu:
    """An instance of git-ubuntu."""

    def __init__(self) -> None:
        """Initialize the git-ubuntu instance."""
        self._service_file = None

    def setup(self) -> bool:
        """Set up an instance of git-ubuntu with a systemd service file.

        Returns:
            True if setup succeeded, False otherwise.
        """
        return True

    def start(self) -> bool:
        """Start the git-ubuntu instance with systemd.

        Returns:
            True if systemd start was successful, False otherwise.
        """
        return True

    def stop(self) -> bool:
        """Stop the git-ubuntu instance.

        Returns:
            True if systemd stop was successful, False otherwise.
        """
        return True

    def destroy(self) -> bool:
        """Destroy the instance and its service file.

        Returns:
            True if the instance and file were removed, False otherwise.
        """
        return True


class GitUbuntuBroker(GitUbuntu):
    """An instance of git-ubuntu running as the broker node.

    The git-ubuntu broker checks the database for package update requests, then assigns worker
    nodes to import them.
    """

    def setup(self) -> bool:
        """Obtain necessary files for running the broker.

        Returns:
            True if setup succeeded, False otherwise.
        """
        # Get allow/denylist from git
        return True


class GitUbuntuPoller(GitUbuntu):
    """An instance of git-ubuntu running as a poller node.

    The git-ubuntu poller checks launchpad on a set interval to see if there are new package
    updates. If so, it queues imports for allowed packages.
    """


class GitUbuntuWorker(GitUbuntu):
    """An instance of git-ubuntu running as a worker node.

    A git-ubuntu worker is assigned packages to run through the history of, then develop and
    upload a git tree corresponding to them.
    """
