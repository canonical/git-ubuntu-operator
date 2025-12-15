#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.


"""Integration test utility functions."""

import json
import socket

import jubilant


def check_deb_installed(app: str, unit: int, juju: jubilant.Juju, package_name: str) -> bool:
    """Check if a deb pkg is installed on a specific unit.

    Args:
        app: The app in charge of this unit.
        unit: The unit number to check.
        juju: The juju model in charge of the app.
        package_name: The name of the deb package.

    Returns:
        True if the package is installed, False otherwise.
    """
    install_status = juju.ssh(
        f"{app}/{unit}", f"dpkg-query --show --showformat='${{Status}}' {package_name}"
    )
    return "installed" in install_status


def get_services_dict(unit_name: str, juju: jubilant.Juju) -> dict[str, dict[str, bool | str]]:
    """Get a dictionary of running systemd services on the app's unit.

    Args:
        unit_name: The name of the unit to check.
        juju: The juju model in charge of the app.

    Returns:
        A dict mapping unit name to if the service is active and its description.
    """
    service_output = juju.ssh(
        unit_name,
        "systemctl list-units --type service --full --all --output json --no-pager | cat -v",
        "",
    )
    service_json = json.loads(service_output)
    service_dict = dict()

    for service_entry in service_json:
        service_dict[service_entry["unit"]] = {
            "active": service_entry["active"] == "active",
            "description": service_entry["description"],
        }

    return service_dict


def is_port_open(host: str, port: int) -> bool:
    """Check if a port is opened in a particular host.

    Args:
        host: The host network location.
        port: The port number to check.

    Returns: True if the port is open, False otherwise.
    """
    try:
        with socket.create_connection((host, port), timeout=5):
            return True
    except (ConnectionRefusedError, TimeoutError):
        return False


def wait_for_all_units_running(app: str, juju: jubilant.Juju) -> None:
    """Wait until all units of an application are active and contain the correct running message.

    Args:
        app: The application name.
        juju: The juju model in charge of the app.
    """
    juju.wait(
        lambda status: all(
            unit_status.is_active
            and "Running git-ubuntu importer" in unit_status.juju_status.message
            for unit_status in status.apps[app].units.values()
        )
    )
