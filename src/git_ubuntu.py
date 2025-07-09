#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Git Ubuntu service runner and configurator."""

import abc
from pathlib import Path


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
    """Create a systemd service file in the service files directory.

    Args:
        filename: The name of the service file to create.
        file_content: The content of the service file.

    Returns:
        True if the file was created, False otherwise.
    """
    try:
        with open(Path("/etc/systemd/system") / filename, "w") as f:
            f.write(file_content)
    except Exception:
        return False
    return True


class GitUbuntu:
    """Abstract git-ubuntu importer runner class."""

    __metaclass__ = abc.ABCMeta

    def __init__(self) -> None:
        """Initialize the git-ubuntu instance."""
        self._service_file = ""

    @abc.abstractmethod
    def setup(self, user: str, group: str) -> bool:
        """Set up an instance of git-ubuntu with a systemd service file.

        Returns:
            True if setup succeeded, False otherwise.
        """
        return False

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

    def setup(
        self,
        user: str,
        group: str,
        broker_port: int = 1692,
    ) -> bool:
        """Obtain necessary files for running the broker.

        Args:
            user: The user to run the service as.
            group: The permissions group to run the service as.
            broker_port: The network port to provide tasks to workers on.

        Returns:
            True if setup succeeded, False otherwise.
        """
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

        if create_systemd_service_file(filename, service_string):
            self._service_file = filename
            return True

        return False


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

        if create_systemd_service_file(filename, service_string):
            self._service_file = filename
            return True

        return False


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
        broker_ip: str = "127.0.0.1",
        broker_port: int = 1692,
    ) -> bool:
        """Set up worker systemd file with designated worker name.

        Returns:
            True if setup succeeded, False otherwise.
        """
        filename = f"git-ubuntu-importer-service-worker{worker_name}.service"
        exec_start = (
            f"/snap/bin/git-ubuntu importer-service-worker %i tcp://{broker_ip}:{broker_port}"
        )

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

        if create_systemd_service_file(filename, service_string):
            self._service_file = filename
            return True

        return False
