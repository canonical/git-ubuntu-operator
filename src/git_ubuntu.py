#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Git Ubuntu service runner and configurator."""

import abc
import logging
from pathlib import Path

from charmlibs import pathops

from service_management import daemon_reload, start_service, stop_service

logger = logging.getLogger(__name__)


def generate_systemd_service_string(
    description: str,
    service_user: str,
    service_group: str,
    service_type: str,
    exec_start: str,
    service_restart: str | None = None,
    restart_sec: int | None = None,
    timeout_start_sec: int | None = None,
    timeout_abort_sec: int | None = None,
    watchdog_sec: int | None = None,
    watchdog_signal: str | None = None,
    runtime_dir: str | None = None,
    private_tmp: bool | None = None,
    environment: str | None = None,
    wanted_by: str | None = None,
) -> str:
    """Create a string containing systemd service information to add to a service file.

    Args:
        description: The systemd unit description.
        service_user: The user to run the service as.
        service_group: The permissions group to run the service as.
        service_type: The service startup type.
        exec_start: The commands to run on service startup.
        service_restart: How to restart the service after exit.
        restart_sec: The restart delay in seconds.
        timeout_start_sec: The start timeout limit in seconds.
        timeout_abort_sec: Time to force terminate on abort.
        watchdog_sec: The watchdog trigger time in seconds.
        watchdog_signal: The watchdog termination signal.
        runtime_dir: Writable runtime directory to create.
        private_tmp: Provide a private tmp area for the service.
        environment: Environment variables set for this process.
        wanted_by: List of weak dependencies on this unit.

    Returns:
        The service file contents as a string.
    """
    service_lines = [
        "[Unit]",
        f"Description={description}",
        "",
        "[Service]",
        f"User={service_user}",
        f"Group={service_group}",
        f"Type={service_type}",
        f"ExecStart={exec_start}",
    ]

    if service_restart is not None:
        service_lines.append(f"Restart={service_restart}")

    if restart_sec is not None:
        service_lines.append(f"RestartSec={restart_sec}")

    if timeout_start_sec is not None:
        service_lines.append(f"TimeoutStartSec={timeout_start_sec}")

    if timeout_abort_sec is not None:
        service_lines.append(f"TimeoutAbortSec={timeout_abort_sec}")

    if watchdog_sec is not None:
        service_lines.append(f"WatchdogSec={watchdog_sec}")

    if watchdog_signal is not None:
        service_lines.append(f"WatchdogSignal={watchdog_signal}")

    if runtime_dir is not None:
        service_lines.append(f"RuntimeDirectory={runtime_dir}")

    if private_tmp:
        service_lines.append("PrivateTmp=yes")
    elif private_tmp is not None:
        service_lines.append("PrivateTmp=no")

    if environment is not None:
        service_lines.append(f"Environment={environment}")

    if wanted_by is not None:
        service_lines.append(f"\n[Install]\nWantedBy={wanted_by}")

    return "\n".join(service_lines)


def create_systemd_service_file(filename: str, file_content: str) -> bool:
    """Create a systemd service file in the service files directory, belonging to root.

    Args:
        filename: The name of the service file to create.
        file_content: The content of the service file.

    Returns:
        True if the file was created, False otherwise.
    """
    try:
        service_file = pathops.LocalPath("/etc/systemd/system/", filename)
        service_file.write_text(file_content, encoding="utf-8", user="root", group="root")
    except (FileNotFoundError, NotADirectoryError) as e:
        logger.error(
            "Failed to create service file %s due to directory issues: %s", filename, str(e)
        )
        return False
    except LookupError as e:
        logger.error(
            "Failed to create service file %s due to issues with root user: %s", filename, str(e)
        )
        return False
    except PermissionError as e:
        logger.error(
            "Failed to create service file %s due to permission issues: %s", filename, str(e)
        )
        return False
    return True


class GitUbuntu:
    """Abstract git-ubuntu importer runner class."""

    __metaclass__ = abc.ABCMeta

    def __init__(self) -> None:
        """Initialize the git-ubuntu instance."""
        self._service_file = ""
        self._started = False

    @abc.abstractmethod
    def setup(self, user: str, group: str) -> bool:
        """Set up an instance of git-ubuntu with a systemd service file.

        Args:
            user: The user to run the service as.
            group: The permissions group to run the service as.
        """

    def start(self) -> bool:
        """Start the git-ubuntu instance with systemd.

        Returns:
            True if the service has started, False otherwise.
        """
        if start_service(self._service_file):
            self._started = True
        else:
            logger.error("Failed to start %s", self._service_file)
        return self._started

    def stop(self) -> bool:
        """Stop the git-ubuntu instance.

        Returns:
            True if the service has stopped, False otherwise.
        """
        if stop_service(self._service_file):
            self._started = False
        else:
            logger.error("Failed to stop %s", self._service_file)
        return not self._started

    def destroy(self) -> bool:
        """Destroy the instance and its service file.

        Make sure the service is stopped prior to destruction.

        Returns:
            True if the instance and file were removed, False otherwise.
        """
        if self._started and not self.stop():
            return False

        try:
            Path(f"/etc/systemd/system/{self._service_file}").unlink(missing_ok=True)
        except (PermissionError, IOError, OSError) as e:
            logger.error("Failed to remove service file %s: %s", self._service_file, str(e))
            return False

        self._service_file = ""

        if not daemon_reload():
            return False

        return True


class GitUbuntuBroker(GitUbuntu):
    """An instance of git-ubuntu running as the broker node.

    The git-ubuntu broker checks the database for package update requests, then assigns worker
    nodes to import them.
    """

    def setup(
        self,
        user: str,
        group: str,
        broker_port: int = 1692,
    ) -> bool:
        """Set up broker systemd service file.

        Args:
            user: The user to run the service as.
            group: The permissions group to run the service as.
            broker_port: The network port to provide tasks to workers on.

        Returns:
            True if setup succeeded, False otherwise.
        """
        # Stop the service before editing if it is running.
        if self._started and not self.stop():
            return False

        filename = "git-ubuntu-importer-service-broker.service"
        exec_start = f"/snap/bin/git-ubuntu importer-service-broker tcp://*:{broker_port}"

        service_string = generate_systemd_service_string(
            "git-ubuntu importer service broker",
            user,
            group,
            "simple",
            exec_start,
            service_restart="always",
            environment="PYTHONUNBUFFERED=1",
            runtime_dir="git-ubuntu",
            wanted_by="multi-user.target",
        )

        if not create_systemd_service_file(filename, service_string):
            return False

        # Check if service already existed and daemon-reload if so.
        if self._service_file != "" and not daemon_reload():
            return False

        self._service_file = filename

        return True


class GitUbuntuPoller(GitUbuntu):
    """An instance of git-ubuntu running as a poller node.

    The git-ubuntu poller checks launchpad on a set interval to see if there are new package
    updates. If so, it queues imports for allowed packages.
    """

    def setup(
        self,
        user: str,
        group: str,
        denylist: Path = Path(
            "/home/ubuntu/live-allowlist-denylist-source/gitubuntu/source-package-denylist.txt"
        ),
        proxy: str = "",
    ) -> bool:
        """Set up worker systemd file with designated worker name.

        Args:
            user: The user to run the service as.
            group: The permissions group to run the service as.
            denylist: The location of the package denylist.
            proxy: Optional proxy url.

        Returns:
            True if setup succeeded, False otherwise.
        """
        # Stop the service before editing if it is running.
        if self._started and not self.stop():
            return False

        filename = "git-ubuntu-importer-service-poller.service"
        exec_start = f"/snap/bin/git-ubuntu importer-service-poller --denylist {denylist}"

        environment = "PYTHONUNBUFFERED=1"

        if proxy:
            environment = f"http_proxy={proxy} " + environment

        service_string = generate_systemd_service_string(
            "git-ubuntu importer service poller",
            user,
            group,
            "notify",
            exec_start,
            timeout_start_sec=1200,
            service_restart="always",
            restart_sec=60,
            watchdog_sec=86400,
            environment=environment,
            wanted_by="multi-user.target",
        )

        if not create_systemd_service_file(filename, service_string):
            return False

        # Check if service already existed and daemon-reload if so.
        if self._service_file != "" and not daemon_reload():
            return False

        self._service_file = filename

        return True


class GitUbuntuWorker(GitUbuntu):
    """An instance of git-ubuntu running as a worker node.

    A git-ubuntu worker is assigned packages to run through the history of, then develop and
    upload a git tree corresponding to them.
    """

    def setup(
        self,
        user: str,
        group: str,
        worker_name: str = "",
        push_to_lp: bool = True,
        broker_ip: str = "127.0.0.1",
        broker_port: int = 1692,
    ) -> bool:
        """Set up worker systemd file with designated worker name.

        Args:
            user: The user to run the service as.
            group: The permissions group to run the service as.
            worker_name: The unique worker ID to add to the service filename.
            push_to_lp: True if publishing repositories to Launchpad.
            broker_ip: The IP address of the broker process' node.
            broker_port: The network port that the broker provides tasks on.

        Returns:
            True if setup succeeded, False otherwise.
        """
        # Stop the service before editing if it is running.
        if self._started and not self.stop():
            return False

        filename = f"git-ubuntu-importer-service-worker{worker_name}.service"

        publish_arg = " --no-push" if not push_to_lp else ""
        broker_url = f"tcp://{broker_ip}:{broker_port}"
        exec_start = f"/snap/bin/git-ubuntu importer-service-worker{publish_arg} %i {broker_url}"

        service_string = generate_systemd_service_string(
            "git-ubuntu importer service worker",
            user,
            group,
            "notify",
            exec_start,
            service_restart="always",
            restart_sec=60,
            watchdog_sec=259200,
            timeout_abort_sec=600,
            watchdog_signal="SIGINT",
            private_tmp=True,
            environment="PYTHONUNBUFFERED=1",
            wanted_by="multi-user.target",
        )

        if not create_systemd_service_file(filename, service_string):
            return False

        # Check if service already existed and daemon-reload if so.
        if self._service_file != "" and not daemon_reload():
            return False

        self._service_file = filename

        return True
