#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Manager of files and git-ubuntu instances on the local system."""

import logging
from os import system
from pathlib import Path
from shutil import move, rmtree

from git_ubuntu import GitUbuntuBroker, GitUbuntuPoller, GitUbuntuWorker

logger = logging.getLogger(__name__)


class ImporterNode:
    """Manager of git-ubuntu importer components on this system."""

    def __init__(
        self, primary: bool, num_workers: int, data_directory: str, source_directory: str
    ):
        """Initialize git-ubuntu instance and local file variables.

        Args:
            primary: True if this is the primary node, create broker and poller instances.
            num_workers: The number of worker instances to set up.
            data_directory: The database and state info directory location.
            source_directory: The directory to keep the git-ubuntu source in.
        """
        self._primary = primary

        if self._primary:
            self._broker = GitUbuntuBroker()
            self._poller = GitUbuntuPoller()

        self._workers = [GitUbuntuWorker() for _ in range(num_workers)]

        self._data_dir = data_directory
        self._source_dir = source_directory

        self._git_ubuntu_source_url = "https://git.launchpad.net/git-ubuntu"
        self._git_ubuntu_source_subdir = "live-allowlist-denylist-source"

    def _clone_git_ubuntu_source(self, directory: Path) -> bool:
        """Clone the git-ubuntu git repo to a given directory.

        Returns:
            True if the clone succeeded, False otherwise.
        """
        if not directory.is_dir():
            logger.error(
                "Failed to clone git-ubuntu sources: %s is not a valid directory.", directory
            )
            return False

        clone_dir = directory / self._git_ubuntu_source_subdir
        logger.info("Cloning git-ubuntu source to %s", clone_dir)
        result = system(f"git clone {self._git_ubuntu_source_url} {clone_dir}")

        if result != 0:
            logger.error(
                "Failed to clone git-ubuntu source, process exited with result %d.", result
            )
            return False

        return True

    def install(self) -> bool:
        """Set up database and denylist if primary, and run git-ubuntu instance setup.

        Returns:
            True if installation succeeded, False otherwise.
        """
        if self._primary:
            if not self._broker.setup():
                return False
            if not self._poller.setup():
                return False

        for worker in self._workers:
            if not worker.setup():
                return False

        return True

    def start(self) -> bool:
        """Start all git-ubuntu processes.

        Returns:
            True if all started successfully, False otherwise.
        """
        if self._primary:
            if not self._broker.start():
                return False
            if not self._poller.start():
                return False

        for worker in self._workers:
            if not worker.start():
                return False

        return True

    def stop(
        self, stop_broker: bool = True, stop_poller: bool = True, stop_workers: bool = True
    ) -> bool:
        """Stop all marked git-ubuntu processes.

        Args:
            stop_broker: Whether to stop the broker process, True by default.
            stop_poller: Whether to stop the poller process, True by default.
            stop_workers: Whether to stop all worker processes, True by default.

        Returns:
            True on stop success for all relevant processes, False otherwise.
        """
        if self._primary:
            if stop_poller and not self._poller.stop():
                return False
            if stop_broker and not self._broker.stop():
                return False

        if stop_workers:
            for worker in self._workers:
                if not worker.stop():
                    return False

        return True

    def destroy(
        self,
        destroy_broker: bool = True,
        destroy_poller: bool = True,
        destroy_workers: bool = True,
    ) -> bool:
        """Destroy services for all marked git-ubuntu processes.

        Args:
            destroy_broker: Whether to destroy the broker process, True by default.
            destroy_poller: Whether to destroy the poller process, True by default.
            destroy_workers: Whether to destroy all worker processes, True by default.

        Returns:
            True on destroy success for all relevant processes, False otherwise.
        """
        if self._primary:
            if destroy_poller and not self._poller.destroy():
                return False
            if destroy_broker and not self._broker.destroy():
                return False

        if destroy_workers:
            for worker in self._workers:
                if not worker.destroy():
                    return False

        return True

    def update_data_directory(self, data_directory: str) -> bool:
        """Update the data directory location, notify git-ubuntu, and move existing data.

        If data already exists in new directory, it will not be overridden.

        Args:
            data_directory: The new data directory location.

        Returns:
            True if data directory migration succeeded, False otherwise.
        """
        # Ignore request if secondary node or data directory name has not changed.
        if not self._primary or data_directory == self._data_dir:
            return True

        new_dir = Path(data_directory)
        new_dir_success = False

        # Create directory if it does not yet exist
        try:
            new_dir.mkdir(parents=True)
            logger.info("Created new data directory %s.", data_directory)
            new_dir_success = True
        except FileExistsError:
            if new_dir.is_dir():
                logger.info("Data directory %s already exists.", data_directory)
                new_dir_success = True
            else:
                logger.error(
                    "Data directory location %s already exists as a file.", data_directory
                )
        except PermissionError:
            logger.error(
                "Unable to create new data directory %s: permission denied.", data_directory
            )
        except OSError as e:
            logger.error("Unable to create new data directory %s: %s", data_directory, e)

        if not new_dir_success:
            return False

        # Confirm broker and poller are shut down
        if not self.stop(stop_workers=False):
            return False

        # Check for existing database in new directory, if there is none then move the old one.
        new_db_file = new_dir / "db"
        old_db_file = Path(self._data_dir) / "db"

        if new_db_file.exists():
            logger.info(
                "Database already exists in new data directory %s, using it now.", data_directory
            )
        elif old_db_file.exists():
            logger.info("Moving database from %s to %s.", self._data_dir, data_directory)
            try:
                move(old_db_file, new_db_file)
            except OSError as e:
                logger.error("Failed to move database: %s", e)
                return False

        self._data_dir = data_directory

        # Update poller and broker configs to match new directory.
        if (
            not self.destroy(destroy_workers=False)
            or not self._broker.setup()
            or not self._poller.setup()
        ):
            return False

        return True

    def update_source_directory(self, source_directory: str) -> bool:
        """Update the source directory location, notify git-ubuntu, and re-clone source.

        Args:
            source_directory: The new source directory location.

        Returns:
            True if new source directory setup succeeded, False otherwise.
        """
        # Ignore request if secondary node or source directory name has not changed.
        if not self._primary or source_directory == self._source_dir:
            return True

        new_dir = Path(source_directory)
        new_dir_success = False

        # Create directory if it does not yet exist
        try:
            new_dir.mkdir(parents=True)
            logger.info("Created new source directory %s.", source_directory)
            new_dir_success = True
        except FileExistsError:
            if new_dir.is_dir():
                logger.info("Source directory %s already exists.", source_directory)
                new_dir_success = True
            else:
                logger.error(
                    "Source directory location %s already exists as a file.", source_directory
                )
        except PermissionError:
            logger.error(
                "Unable to create new source directory %s: permission denied.", source_directory
            )
        except OSError as e:
            logger.error("Unable to create new source directory %s: %s", source_directory, e)

        if not new_dir_success:
            return False

        # Confirm the poller is shut down
        if not self.stop(stop_broker=False, stop_workers=False):
            return False

        # Clear out any existing files where the source is to be cloned
        new_clone_dir = new_dir / self._git_ubuntu_source_subdir

        if new_clone_dir.exists():
            try:
                rmtree(new_clone_dir)
            except OSError as e:
                logger.error(
                    "Failed to remove existing files in new source directory %s: %s.",
                    source_directory,
                    e,
                )
                return False

        # Clone the source, then update poller config with new directory.
        if (
            not self._clone_git_ubuntu_source(new_dir)
            or not self.destroy(destroy_broker=False, destroy_workers=False)
            or not self._poller.setup()
        ):
            return False

        self._source_dir = source_directory
        return True
