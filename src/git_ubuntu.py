#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Git Ubuntu service runner and configurator."""


def generate_systemd_service_string(
    description: str,
    service_user: str,
    service_group: str,
    service_type: str,
    exec_start: str,
    service_restart: str | None = None,
    restart_sec: int | None = None,
    timeout_start_sec: int | None = None,
    watchdog_sec: int | None = None,
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
        watchdog_sec: The watchdog trigger time in seconds.
        runtime_dir: The active directory during runtime.
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

    if watchdog_sec is not None:
        service_lines.append(f"WatchdogSec={watchdog_sec}")

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

    def setup(self) -> bool:
        """Set up worker systemd file with designated worker name.

        Returns:
            True if setup succeeded, False otherwise.
        """
        return True
