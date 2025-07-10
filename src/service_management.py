#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Systemd service management functions."""

import logging

from charms.operator_libs_linux.v1 import systemd

logger = logging.getLogger(__name__)


def start_service(service_name: str) -> bool:
    """Attempt to start a systemd service and confirm it is running.

    Args:
        service_name: The name of the service to start.

    Returns:
        True if the service was started successfully, False otherwise.
    """
    try:
        if not systemd.service_running(service_name):
            return systemd.service_start(service_name)
    except systemd.SystemdError as e:
        logger.error("Failed to start %s: %s", service_name, str(e))
        return False

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
            return systemd.service_stop(service_name)
    except systemd.SystemdError as e:
        logger.error("Failed to stop %s: %s", service_name, str(e))
        return False

    return True


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

    return True
