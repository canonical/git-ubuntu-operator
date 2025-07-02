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

        if self._primary:
            self._broker = GitUbuntuBroker()
            self._poller = GitUbuntuPoller()

        self._workers = [GitUbuntuWorker() for _ in range(num_workers)]

    def install(self) -> bool:
        """Set up database and denylist if primary, and run git-ubuntu instance setup.

        Returns:
            True if installation succeeded, False otherwise.
        """
        if self._primary:
            self._broker.setup()
            self._poller.setup()

        for worker in self._workers:
            worker.setup()

        return True

    def start(self) -> bool:
        """Start all git-ubuntu processes.

        Returns:
            True if all started successfully, False otherwise.
        """
        if self._primary:
            self._broker.start()
            self._poller.start()

        for worker in self._workers:
            worker.start()

        return True
