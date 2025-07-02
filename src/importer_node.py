#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Manager of files and git-ubuntu instances on the local system."""

from git_ubuntu import GitUbuntuBroker, GitUbuntuPoller, GitUbuntuWorker


class ImporterNode:
    """Manager of git-ubuntu importer components on this system."""

    def __init__(self, primary: bool, num_workers: int):
        """Initialize git-ubuntu instance and local file variables.

        Args:
            primary: True if this is the primary node, create broker and poller instances.
            num_workers: The number of worker instances to set up.
        """
        self._primary = primary

        self._broker = None
        self._poller = None

        if primary:
            self._broker = GitUbuntuBroker()
            self._poller = GitUbuntuPoller()

        self._workers = [GitUbuntuWorker() for _ in range(num_workers)]
