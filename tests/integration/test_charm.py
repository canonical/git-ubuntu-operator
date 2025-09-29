#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.


"""Integration tests."""

import json
import logging

import jubilant

logger = logging.getLogger(__name__)


def test_service_status(app: str, juju: jubilant.Juju):
    """Test necessary files exist after startup.

    Args:
        app: The app in charge of this unit.
        juju: The juju model in charge of the app.
    """
    juju.wait(jubilant.all_active)

    def get_services_dict(app: str, juju: jubilant.Juju) -> dict[str, dict[str, bool | str]]:
        """Get a dictionary of running systemd services on the app's unit 0.

        Args:
            app: The app in charge of this unit.
            juju: The juju model in charge of the app.

        Returns:
            A dict mapping unit name to if the service is active and its description.
        """
        service_output = juju.ssh(
            f"{app}/0",
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

    services = get_services_dict(app, juju)

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
    assert services["git-ubuntu-importer-service-worker0_0.service"]["active"]
    assert (
        services["git-ubuntu-importer-service-worker0_0.service"]["description"]
        == "git-ubuntu importer service worker"
    )
    assert services["git-ubuntu-importer-service-worker0_1.service"]["active"]
    assert (
        services["git-ubuntu-importer-service-worker0_1.service"]["description"]
        == "git-ubuntu importer service worker"
    )


def test_installed_apps(app: str, juju: jubilant.Juju):
    """Test that all required applications are installed.

    Args:
        app: The app in charge of this unit.
        juju: The juju model in charge of the app.
    """
    juju.wait(jubilant.all_active)

    git_ubuntu_status = juju.ssh(f"{app}/0", "snap list | grep git-ubuntu", "")
    assert "latest/beta" in git_ubuntu_status
    assert "classic" in git_ubuntu_status
