#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Systemd service management functions."""

import logging
import time
from os import link

from charmlibs import pathops
from charms.operator_libs_linux.v1 import systemd

logger = logging.getLogger(__name__)


def create_systemd_service_file(filename: str, local_folder: str, file_content: str) -> bool:
    """Create a systemd service file in a local folder, linking to the service files directory.

    Args:
        filename: The name of the service file to create.
        local_folder: The local folder to create the file in.
        file_content: The content of the service file.

    Returns:
        True if the file was created, False otherwise.
    """
    file_created = False

    try:
        service_file = pathops.LocalPath(local_folder, filename)
        service_file.write_text(file_content, encoding="utf-8", user="root", group="root")
        logger.info("Created service file at %s.", service_file)
        file_created = True
    except (FileNotFoundError, NotADirectoryError) as e:
        logger.error(
            "Failed to create service file %s due to directory issues: %s", filename, str(e)
        )
    except LookupError as e:
        logger.error(
            "Failed to create service file %s due to issues with root user: %s", filename, str(e)
        )
    except PermissionError as e:
        logger.error(
            "Failed to create service file %s due to permission issues: %s", filename, str(e)
        )

    if not file_created:
        return False

    # Link to services directory
    file_linked = False

    try:
        link(
            pathops.LocalPath(local_folder, filename),
            pathops.LocalPath("/etc/systemd/system", filename),
        )
        logger.info("Linked service file to /etc/systemd/system.")
        file_linked = True
    except FileExistsError:
        logger.error("Service file %s link already exists", filename)
    except PermissionError as e:
        logger.error(
            "Failed to create service file link %s due to permission issues: %s", filename, str(e)
        )
    except OSError as e:
        logger.error("Failed to create service file link %s due to OS error: %s", filename, str(e))

    return file_linked


def start_service(service_name: str) -> bool:
    """Attempt to start a systemd service and confirm it is running.

    Args:
        service_name: The name of the service to start.

    Returns:
        True if the service was started successfully, False otherwise.
    """
    try:
        if not systemd.service_running(service_name):
            logger.info("Starting systemd service %s.", service_name)
            return systemd.service_start(service_name)
    except systemd.SystemdError as e:
        logger.error("Failed to start %s: %s", service_name, str(e))
        return False

    logger.debug("Systemd service %s is already running, leaving it alone.", service_name)
    return True


def stop_service(service_name: str) -> bool:
    """Attempt to stop a systemd service and confirm it is stopped.

    Args:
        service_name: The name of the service to stop.

    Returns:
        True if the service was stopped successfully, False otherwise.
    """
    try:
        if systemd.service_running(service_name):
            logger.info("Stopping systemd service %s.", service_name)
            return systemd.service_stop(service_name)
    except systemd.SystemdError as e:
        logger.error("Failed to stop %s: %s", service_name, str(e))
        return False

    logger.debug("Systemd service %s is not running, leaving it alone.", service_name)
    return True


def wait_for_service_active(service_name: str, timeout_sec: int) -> bool:
    """Wait until a systemd service is active.

    Args:
        service_name: The name of the service to wait for.
        timeout_sec: The cutoff time for failure.

    Returns:
        True if the service started within timeout, False otherwise.
    """
    logger.info("Waiting for service %s to start...", service_name)

    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        if systemd.service_running(service_name):
            logger.info(
                "Service %s started, took %d seconds.", service_name, int(time.time() - start_time)
            )
            return True
        time.sleep(1)

    logger.error("Failed to start service %s within %d seconds.", service_name, timeout_sec)
    return False


def daemon_reload() -> bool:
    """Reload systemd manager configuration.

    Returns:
        True if the daemon was reloaded successfully, False otherwise.
    """
    try:
        if not systemd.daemon_reload():
            logger.error("Failed to run daemon-reload")
            return False
    except systemd.SystemdError as e:
        logger.error("Failed to run daemon-reload: %s", str(e))
        return False

    logger.info("Ran systemd daemon-reload successfully.")
    return True
