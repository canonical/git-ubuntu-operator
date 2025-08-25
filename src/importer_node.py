#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Manager of files and git-ubuntu instances on the local system."""

import logging
from os import system
from shutil import move, rmtree

from charmlibs import pathops

from git_ubuntu import GitUbuntuBroker, GitUbuntuPoller, GitUbuntuWorker

logger = logging.getLogger(__name__)


class ImporterNode:
    """Manager of git-ubuntu workers on this system."""

    def __init__(
        self,
        node_id: int,
        num_workers: int,
        system_user: str,
        push_to_lp: bool,
        primary_port: int,
        primary_ip: str,
    ) -> None:
        """Initialize git-ubuntu instance and local file variables.

        Args:
            node_id: The unique ID of this node.
            num_workers: The number of worker instances to set up.
            system_user: The user + group to run the services as.
            push_to_lp: True if publishing repositories to Launchpad.
            primary_port: The network port used for worker assignments.
            primary_ip: The IP or network location of the primary node.
        """
        self._node_id = node_id
        self._user = system_user
        self._push_to_lp = push_to_lp
        self._port = primary_port
        self._primary_ip = primary_ip
        self._workers = [GitUbuntuWorker() for _ in range(num_workers)]

    def _setup_worker(self, worker: GitUbuntuWorker, worker_number: int) -> bool:
        """Set up a worker with the current node settings.

        Args:
            worker: The allocated git-ubuntu worker to set up.
            worker_number: The worker's numeric id.

        Returns: True if the worker was set up, False otherwise.
        """
        return worker.setup(
            self._user,
            self._user,
            f"{self._node_id}_{worker_number}",
            self._push_to_lp,
            self._primary_ip,
            self._port,
        )

    def install(self) -> bool:
        """Run git-ubuntu instance install and setup for workers.

        Returns:
            True if installation succeeded, False otherwise.
        """
        for i, worker in enumerate(self._workers):
            if not self._setup_worker(worker, i):
                return False

        return True

    def update(
        self,
        force_refresh: bool,
        node_id: int,
        num_workers: int,
        system_user: str,
        push_to_lp: bool,
        primary_port: int,
        primary_ip: str,
    ) -> bool:
        """Update the importer node's configuration.

        Args:
            force_refresh: Enforce removal and recreation of systemd services.
            node_id: The unique ID of this node.
            num_workers: The number of worker instances to set up.
            system_user: The user + group to run the services as.
            push_to_lp: True if publishing repositories to Launchpad.
            primary_port: The network port used for worker assignments.
            primary_ip: The IP or network location of the primary node.

        Returns:
            True if the update succeeded, False otherwise.
        """
        needs_refresh = (
            force_refresh
            or node_id != self._node_id
            or system_user != self._user
            or push_to_lp != self._push_to_lp
            or primary_port != self._port
            or primary_ip != self._primary_ip
        )
        original_num_workers = len(self._workers)

        self._node_id = node_id
        self._user = system_user
        self._port = primary_port
        self._primary_ip = primary_ip

        # Remove unneeded workers.
        for _ in range(original_num_workers - num_workers):
            worker = self._workers.pop()
            if not worker.destroy():
                return False

        # Add as many new workers as needed.
        for i in range(original_num_workers, num_workers):
            new_worker = GitUbuntuWorker()
            if not self._setup_worker(new_worker, i):
                return False

        # Refresh all old workers if requested.
        if needs_refresh:
            for i in range(original_num_workers):
                if not self._workers[i].destroy() or not self._setup_worker(self._workers[i], i):
                    return False

        return True

    def start(self) -> bool:
        """Start all git-ubuntu processes.

        Returns:
            True if all started successfully, False otherwise.
        """
        for worker in self._workers:
            if not worker.start():
                return False

        return True

    def stop(self) -> bool:
        """Stop all git-ubuntu processes.

        Returns:
            True on stop success for all processes, False otherwise.
        """
        for worker in self._workers:
            if not worker.stop():
                return False

        return True

    def destroy(self) -> bool:
        """Destroy services for all git-ubuntu processes.

        Returns:
            True on destroy success for all processes, False otherwise.
        """
        for worker in self._workers:
            if not worker.destroy():
                return False

        return True


class PrimaryImporterNode(ImporterNode):
    """Manager of git-ubuntu importer components on the primary node's system."""

    def __init__(
        self,
        node_id: int,
        num_workers: int,
        system_user: str,
        push_to_lp: bool,
        primary_port: int,
        data_directory: str,
        source_directory: str,
    ) -> None:
        """Initialize git-ubuntu instance and local file variables.

        Args:
            node_id: The unique ID of this node.
            num_workers: The number of worker instances to set up.
            system_user: The user + group to run the services as.
            push_to_lp: True if publishing repositories to Launchpad.
            primary_port: The network port used for worker assignments.
            data_directory: The database and state info directory location.
            source_directory: The directory to keep the git-ubuntu source in.
        """
        self._broker = GitUbuntuBroker()
        self._poller = GitUbuntuPoller()

        self._data_dir = data_directory
        self._source_dir = source_directory

        self._git_ubuntu_source_url = "https://git.launchpad.net/git-ubuntu"
        self._git_ubuntu_source_subdir = "live-allowlist-denylist-source"

        super().__init__(node_id, num_workers, system_user, push_to_lp, primary_port, "127.0.0.1")

    def _clone_git_ubuntu_source(self, directory: pathops.LocalPath) -> bool:
        """Clone the git-ubuntu git repo to a given directory.

        Returns:
            True if the clone succeeded, False otherwise.
        """
        if not directory.is_dir():
            logger.error(
                "Failed to clone git-ubuntu sources: %s is not a valid directory.", directory
            )
            return False

        clone_dir = pathops.LocalPath(directory, self._git_ubuntu_source_subdir)
        logger.info("Cloning git-ubuntu source to %s", clone_dir)
        result = system(f"git clone {self._git_ubuntu_source_url} {clone_dir}")

        if result != 0:
            logger.error(
                "Failed to clone git-ubuntu source, process exited with result %d.", result
            )
            return False

        return True

    def install(self) -> bool:
        """Set up database and denylist, and run git-ubuntu instance setup.

        Returns:
            True if installation succeeded, False otherwise.
        """
        if not self._broker.setup(self._user, self._user, self._port):
            return False
        if not self._poller.setup(
            self._user,
            self._user,
            pathops.LocalPath(self._source_dir)
            / self._git_ubuntu_source_subdir
            / "gitubuntu/source-package-denylist.txt",
        ):
            return False
        if not super().install():
            return False

        return True

    def start(self) -> bool:
        """Start all git-ubuntu processes.

        Returns:
            True if all started successfully, False otherwise.
        """
        if not self._broker.start():
            return False
        if not self._poller.start():
            return False
        if not super().start():
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
        if stop_poller and not self._poller.stop():
            return False
        if stop_broker and not self._broker.stop():
            return False
        if stop_workers and not super().stop():
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
        if destroy_poller and not self._poller.destroy():
            return False
        if destroy_broker and not self._broker.destroy():
            return False
        if destroy_workers and not super().destroy():
            return False

        return True

    def update(
        self,
        force_refresh: bool,
        node_id: int,
        num_workers: int,
        system_user: str,
        push_to_lp: bool,
        primary_port: int,
        primary_ip: str = "127.0.0.1",
        data_directory: str = "",
        source_directory: str = "",
    ) -> bool:
        """Update the importer node's configuration.

        Args:
            force_refresh: Enforce removal and recreation of systemd services.
            node_id: The unique ID of this node.
            num_workers: The number of worker instances to set up.
            system_user: The user + group to run the services as.
            push_to_lp: True if publishing repositories to Launchpad.
            primary_port: The network port used for worker assignments.
            primary_ip: The IP or network location of the primary node.
            data_directory: The database and state info directory location.
            source_directory: The directory to keep the git-ubuntu source in.

        Returns:
            True if the update succeeded, False otherwise.
        """
        full_refresh_needed = (
            force_refresh or system_user != self._user or data_directory != self._data_dir
        )
        broker_refresh_needed = full_refresh_needed or primary_port != self._port
        poller_refresh_needed = full_refresh_needed or source_directory != self._source_dir

        # Update directories if needed.
        if not self._update_data_directory(data_directory) or not self._update_source_directory(
            source_directory
        ):
            return False

        # Destroy broker and/or poller if needed, let super class handle workers.
        if not self.destroy(broker_refresh_needed, poller_refresh_needed, False):
            return False

        # Handle variable and worker updates.
        if not super().update(
            force_refresh, node_id, num_workers, system_user, push_to_lp, primary_port, primary_ip
        ):
            return False

        # Refresh broker if needed.
        if broker_refresh_needed and not self._broker.setup(self._user, self._user, self._port):
            return False

        # Refresh poller if needed.
        if poller_refresh_needed and not self._poller.setup(
            self._user,
            self._user,
            pathops.LocalPath(self._source_dir)
            / self._git_ubuntu_source_subdir
            / "gitubuntu/source-package-denylist.txt",
        ):
            return False

        return True

    def _update_data_directory(self, data_directory: str) -> bool:
        """Update the data directory location, notify git-ubuntu, and move existing data.

        If data already exists in new directory, it will not be overridden.

        Args:
            data_directory: The new data directory location.

        Returns:
            True if data directory migration succeeded, False otherwise.
        """
        # Ignore request if secondary node or data directory name has not changed.
        if data_directory == self._data_dir:
            return True

        new_dir = pathops.LocalPath(data_directory)
        new_dir_success = False

        # Create directory if it does not yet exist
        try:
            new_dir.mkdir(parents=True, user=self._user, group=self._user)
            logger.info("Created new data directory %s.", data_directory)
            new_dir_success = True
        except FileExistsError:
            logger.info("Data directory %s already exists.", data_directory)
            new_dir_success = True
        except NotADirectoryError:
            logger.error("Data directory location %s already exists as a file.", data_directory)
        except PermissionError:
            logger.error(
                "Unable to create new data directory %s: permission denied.", data_directory
            )
        except LookupError:
            logger.error(
                "Unable to create new data directory %s: unknown user/group %s",
                data_directory,
                self._user,
            )

        if not new_dir_success:
            return False

        # Confirm broker and poller are shut down
        if not self.stop(stop_workers=False):
            return False

        # Check for existing database in new directory, if there is none then move the old one.
        new_db_file = pathops.LocalPath(new_dir, "db")
        old_db_file = pathops.LocalPath(self._data_dir, "db")

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
            or not self._broker.setup(self._user, self._user, self._port)
            or not self._poller.setup(
                self._user,
                self._user,
                pathops.LocalPath(self._source_dir)
                / self._git_ubuntu_source_subdir
                / "gitubuntu/source-package-denylist.txt",
            )
        ):
            return False

        return True

    def _update_source_directory(self, source_directory: str) -> bool:
        """Update the source directory location, notify git-ubuntu, and re-clone source.

        Args:
            source_directory: The new source directory location.

        Returns:
            True if new source directory setup succeeded, False otherwise.
        """
        # Ignore request if secondary node or source directory name has not changed.
        if source_directory == self._source_dir:
            return True

        new_dir = pathops.LocalPath(source_directory)
        new_dir_success = False

        # Create directory if it does not yet exist
        try:
            new_dir.mkdir(parents=True, user=self._user, group=self._user)
            logger.info("Created new source directory %s.", source_directory)
            new_dir_success = True
        except FileExistsError:
            logger.info("Source directory %s already exists.", source_directory)
            new_dir_success = True
        except NotADirectoryError:
            logger.error(
                "Source directory location %s already exists as a file.", source_directory
            )
        except PermissionError:
            logger.error(
                "Unable to create new source directory %s: permission denied.", source_directory
            )
        except LookupError:
            logger.error(
                "Unable to create new source directory %s: unknown user/group %s",
                source_directory,
                self._user,
            )

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
            or not self._poller.setup(
                self._user,
                self._user,
                pathops.LocalPath(self._source_dir)
                / self._git_ubuntu_source_subdir
                / "gitubuntu/source-package-denylist.txt",
            )
        ):
            return False

        self._source_dir = source_directory
        return True


class EmptyImporterNode(ImporterNode):
    """A placeholder importer node that does nothing."""

    def __init__(self) -> None:
        """Initialize an empty representation of the node."""
        super().__init__(0, 0, "", False, 0, "")

    def install(self) -> bool:
        """Override install for empty node.

        Returns:
            False
        """
        logger.error("Failed to install, not initialized.")
        return False

    def start(self) -> bool:
        """Override start for empty node.

        Returns:
            False
        """
        logger.error("Failed to start services, not initialized.")
        return False

    def stop(self) -> bool:
        """Override stop for empty node.

        Returns:
            False
        """
        logger.error("Failed to stop services, not initialized.")
        return False

    def destroy(self) -> bool:
        """Override destroy for empty node.

        Returns:
            False
        """
        logger.error("Failed to destroy services, not initialized.")
        return False
