#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.


"""Integration tests."""

import json
import logging
import socket
from time import sleep

import jubilant

logger = logging.getLogger(__name__)


def test_service_status(app: str, juju: jubilant.Juju):
    """Test necessary files exist after startup.

    Args:
        app: The app in charge of this unit.
        juju: The juju model in charge of the app.
    """
    # Wait until machine is ready, then wait an extra 60 seconds for services to fully activate.
    juju.wait(jubilant.all_active)
    sleep(90)

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

    for unit_name, unit in juju.status().get_units(app).items():
        services = get_services_dict(unit_name, juju)

        if unit.leader:
            assert services["git-ubuntu-importer-service-broker.service"]["active"]
            assert (
                services["git-ubuntu-importer-service-broker.service"]["description"]
                == "git-ubuntu importer service broker"
            )
            assert services["git-ubuntu-importer-service-poller.service"]["active"]
            assert (
                services["git-ubuntu-importer-service-poller.service"]["description"]
                == "git-ubuntu importer service poller"
            )

        else:
            node_id = int(unit_name.split("/")[-1])

            assert services[f"git-ubuntu-importer-service-worker@{node_id}-0.service"]["active"]
            assert (
                services[f"git-ubuntu-importer-service-worker@{node_id}-0.service"]["description"]
                == "git-ubuntu importer service worker"
            )
            assert services[f"git-ubuntu-importer-service-worker@{node_id}-1.service"]["active"]
            assert (
                services[f"git-ubuntu-importer-service-worker@{node_id}-1.service"]["description"]
                == "git-ubuntu importer service worker"
            )


def test_installed_apps(app: str, juju: jubilant.Juju):
    """Test that all required applications are installed.

    Args:
        app: The app in charge of this unit.
        juju: The juju model in charge of the app.
    """
    juju.wait(jubilant.all_active)

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

    assert check_deb_installed(app, 0, juju, "git")
    assert check_deb_installed(app, 0, juju, "sqlite3")
    assert check_deb_installed(app, 1, juju, "git")
    assert check_deb_installed(app, 1, juju, "sqlite3")

    git_ubuntu_status_1 = juju.ssh(f"{app}/0", "snap list | grep git-ubuntu", "")
    assert "latest/beta" in git_ubuntu_status_1
    assert "classic" in git_ubuntu_status_1

    git_ubuntu_status_2 = juju.ssh(f"{app}/1", "snap list | grep git-ubuntu", "")
    assert "latest/beta" in git_ubuntu_status_2
    assert "classic" in git_ubuntu_status_2


def test_installed_dump_files(app: str, juju: jubilant.Juju):
    """Test that all required dump files are installed.

    Args:
        app: The app in charge of this unit.
        juju: The juju model in charge of the app.
    """
    juju.wait(jubilant.all_active)

    debian_keyring_status = juju.ssh(
        f"{app}/leader", "test -f /etc/git-ubuntu/debian-archive-keyring.gpg | echo $?", ""
    ).strip()
    assert debian_keyring_status == "0"


def test_controller_port_open(app: str, juju: jubilant.Juju):
    """Confirm that the git-ubuntu controller leader network port opens.

    Args:
        app: The app in charge of this unit.
        juju: The juju model in charge of the app.
    """
    juju.wait(jubilant.all_active)

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

    address = None
    for unit in juju.status().get_units(app).values():
        if unit.leader:
            address = unit.public_address

    assert address is not None
    assert is_port_open(address, 1692)
