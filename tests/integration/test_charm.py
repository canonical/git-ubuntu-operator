#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.


"""Integration tests."""

import logging

import jubilant
from helpers import check_deb_installed, get_services_dict, is_port_open

logger = logging.getLogger(__name__)


def test_installed_apps(app: str, juju: jubilant.Juju):
    """Test that all required applications are installed.

    Args:
        app: The app in charge of this unit.
        juju: The juju model in charge of the app.
    """
    juju.wait(jubilant.all_active)

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


def test_git_ubuntu_source_denylist_exists(app: str, juju: jubilant.Juju):
    """Test that the git-ubuntu source repo has been cloned and contains the denylist.

    Args:
        app: The app in charge of this unit.
        juju: The juju model in charge of the app.
    """
    juju.wait(jubilant.all_active)

    debian_keyring_status = juju.ssh(
        f"{app}/leader",
        "test -f "
        + "/var/local/git-ubuntu/live-allowlist-denylist-source/gitubuntu/"
        + "source-package-denylist.txt | echo $?",
        "",
    ).strip()
    assert debian_keyring_status == "0"


def test_controller_port_open(app: str, juju: jubilant.Juju):
    """Confirm that the git-ubuntu controller leader network port opens.

    Args:
        app: The app in charge of this unit.
        juju: The juju model in charge of the app.
    """
    juju.wait(jubilant.all_active)

    address = None
    for unit in juju.status().get_units(app).values():
        if unit.leader:
            address = unit.public_address

    assert address is not None
    assert is_port_open(address, 1692)


def test_service_status(app: str, juju: jubilant.Juju):
    """Test necessary files exist after startup.

    Args:
        app: The app in charge of this unit.
        juju: The juju model in charge of the app.
    """
    # Wait until machine is ready, then wait an extra 60 seconds for services to fully activate.
    juju.wait(jubilant.all_active)

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

            assert services[f"git-ubuntu-importer-service-worker@w{node_id}-0.service"]["active"]
            assert (
                services[f"git-ubuntu-importer-service-worker@w{node_id}-0.service"]["description"]
                == "git-ubuntu importer service worker"
            )
            assert services[f"git-ubuntu-importer-service-worker@w{node_id}-1.service"]["active"]
            assert (
                services[f"git-ubuntu-importer-service-worker@w{node_id}-1.service"]["description"]
                == "git-ubuntu importer service worker"
            )
