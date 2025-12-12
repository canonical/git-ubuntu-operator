#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Git Ubuntu service runner and configurator."""

import logging

from charmlibs import pathops

from service_management import (
    create_systemd_service_file,
    start_service,
    stop_service,
    wait_for_service_active,
)

logger = logging.getLogger(__name__)


def _get_services_list(service_folder: str) -> list[str] | None:
    """Get the list of services from the git-ubuntu service folder.

    Args:
        service_folder: The name of the folder containing the service files.

    Returns:
        A list of service names or None if checking the folder failed.
    """
    service_folder_path = pathops.LocalPath(service_folder)
    collected_services = True
    service_list = []

    try:
        for service_file in service_folder_path.iterdir():
            if service_file.suffix == ".service":
                service_list.append(service_file.name)
            else:
                logger.debug("Skipping non-service file %s", service_file.name)
    except NotADirectoryError:
        logger.error("The provided location %s is not a directory.", service_folder)
        collected_services = False
    except PermissionError as e:
        logger.error("Failed to find services due to permission issues: %s", str(e))
        collected_services = False
    except FileNotFoundError:
        logger.error("Service folder not found.")
        collected_services = False

    if not collected_services:
        return None

    return service_list


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


def setup_broker_service(
    home_dir: str,
    user: str,
    group: str,
    broker_port: int = 1692,
) -> bool:
    """Set up broker systemd service file.

    Args:
        home_dir: The home directory of the user.
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

    services_folder = pathops.LocalPath(home_dir, "services")
    return create_systemd_service_file(filename, services_folder.as_posix(), service_string)


def setup_poller_service(
    home_dir: str,
    user: str,
    group: str,
    denylist: str,
    http_proxy: str = "",
    https_proxy: str = "",
) -> bool:
    """Set up poller systemd service file.

    Args:
        home_dir: The home directory of the user.
        user: The user to run the service as.
        group: The permissions group to run the service as.
        denylist: The location of the package denylist.
        http_proxy: Optional HTTP proxy url.
        https_proxy: Optional HTTPS proxy url.

    Returns:
        True if setup succeeded, False otherwise.
    """
    filename = "git-ubuntu-importer-service-poller.service"
    exec_start = f"/snap/bin/git-ubuntu importer-service-poller --denylist {denylist}"

    environment = "PYTHONUNBUFFERED=1"

    if http_proxy != "":
        environment = f"http_proxy={http_proxy} " + environment

    if https_proxy != "":
        environment = f"https_proxy={https_proxy} " + environment

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

    services_folder = pathops.LocalPath(home_dir, "services")
    return create_systemd_service_file(filename, services_folder.as_posix(), service_string)


def setup_worker_service(
    home_dir: str,
    user: str,
    group: str,
    push_to_lp: bool = True,
    broker_ip: str = "127.0.0.1",
    broker_port: int = 1692,
    lp_credentials_filename: str = "",
    https_proxy: str = "",
) -> bool:
    """Set up worker systemd file.

    Args:
        home_dir: The home directory of the user.
        user: The user to run the service as.
        group: The permissions group to run the service as.
        push_to_lp: True if publishing repositories to Launchpad.
        broker_ip: The IP address of the broker process' node.
        broker_port: The network port that the broker provides tasks on.
        lp_credentials_filename: The filename for specific Launchpad credentials if needed.
        https_proxy: Optional HTTPS proxy url.

    Returns:
        True if setup succeeded, False otherwise.
    """
    filename = "git-ubuntu-importer-service-worker@.service"

    publish_arg = " --no-push" if not push_to_lp else ""
    broker_url = f"tcp://{broker_ip}:{broker_port}"
    exec_start = f"/snap/bin/git-ubuntu importer-service-worker{publish_arg} %i {broker_url}"

    environment = f"HOME={home_dir} PYTHONUNBUFFERED=1"

    if lp_credentials_filename != "":
        environment = f"LP_CREDENTIALS_FILE={lp_credentials_filename} " + environment

    if https_proxy != "":
        environment = f"https_proxy={https_proxy} " + environment

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
        environment=environment,
        wanted_by="multi-user.target",
    )

    services_folder = pathops.LocalPath(home_dir, "services")
    return create_systemd_service_file(filename, services_folder.as_posix(), service_string)


def start_services(service_folder: str) -> bool:
    """Start all git-ubuntu services and wait for startup to complete.

    Args:
        service_folder: The name of the folder containing the service files.

    Returns:
        True if all services were started successfully, False otherwise.
    """
    service_list = _get_services_list(service_folder)

    if service_list is None:
        return False

    services_started = True

    # Start services
    for service in service_list:
        if start_service(service):
            logger.info("Started service %s.", service)
        else:
            logger.error("Failed to start service %s", service)
            services_started = False

    if not services_started:
        return False

    # Wait for startup
    for service in service_list:
        if wait_for_service_active(service, 30):
            logger.info("Service %s startup complete.", service)
        else:
            logger.error("Service %s startup failed.", service)
            return False

    return True


def stop_services(service_folder: str) -> bool:
    """Stop all git-ubuntu services.

    Args:
        service_folder: The name of the folder containing the service files.

    Returns:
        True if all services were stopped successfully, False otherwise.
    """
    service_list = _get_services_list(service_folder)

    if service_list is None:
        return False

    services_stopped = True

    for service in service_list:
        if stop_service(service):
            logger.info("Stopped service %s", service)
        else:
            logger.error("Failed to stop service %s", service)
            services_stopped = False

    return services_stopped


def destroy_services(service_folder: str) -> bool:
    """Destroy all git-ubuntu service files.

    Args:
        service_folder: The name of the folder containing the service files.

    Returns:
        True if all services were deleted successfully, False otherwise.
    """
    service_list = _get_services_list(service_folder)

    if service_list is None:
        return False

    service_folder_path = pathops.LocalPath(service_folder)
    systemd_service_path = pathops.LocalPath("/etc/systemd/system/")

    services_folder_services_removed = False
    systemd_folder_services_removed = False

    # Remove from service folder
    try:
        for service in service_list:
            pathops.LocalPath(service_folder_path, service).unlink(missing_ok=True)
        services_folder_services_removed = True
    except NotADirectoryError:
        logger.error("The provided location %s is not a directory.", service_folder)
    except PermissionError as e:
        logger.error("Failed to start services due to permission issues: %s", str(e))
    except FileNotFoundError:
        logger.error("Service folder not found.")
    except (IOError, OSError) as e:
        logger.error("Failed to remove a service file due to error: %s", str(e))

    # Remove from /etc/systemd/system
    try:
        for service in service_list:
            pathops.LocalPath(systemd_service_path, service).unlink(missing_ok=True)
        systemd_folder_services_removed = True
    except NotADirectoryError:
        logger.error("/etc/systemd/system is not a directory.")
    except PermissionError as e:
        logger.error("Failed to start services due to permission issues: %s", str(e))
    except FileNotFoundError:
        logger.error("/etc/systemd/system folder not found.")
    except (IOError, OSError) as e:
        logger.error("Failed to remove a service file due to error: %s", str(e))

    return services_folder_services_removed and systemd_folder_services_removed
