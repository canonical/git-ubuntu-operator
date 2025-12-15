#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Manager of files and git-ubuntu instances on the local system."""

import logging

from charmlibs import pathops

import git_ubuntu

logger = logging.getLogger(__name__)


def setup_secondary_node(
    git_ubuntu_user_home: str,
    system_user: str,
    push_to_lp: bool,
    primary_port: int,
    primary_ip: str,
    lp_credentials_filename: str = "",
    https_proxy: str = "",
) -> bool:
    """Set up necessary services for a worker-only git-ubuntu importer node.

    Args:
        git_ubuntu_user_home: The home directory of the git-ubuntu user.
        system_user: The user + group to run the services as.
        push_to_lp: True if publishing repositories to Launchpad.
        primary_port: The network port used for worker assignments.
        primary_ip: The IP or network location of the primary node.
        lp_credentials_filename: The filename for specific Launchpad credentials if needed.
        https_proxy: URL for the environment's https proxy if required.

    Returns:
        True if installation succeeded, False otherwise.
    """
    if not git_ubuntu.setup_worker_service(
        git_ubuntu_user_home,
        system_user,
        system_user,
        push_to_lp,
        primary_ip,
        primary_port,
        lp_credentials_filename,
        https_proxy,
    ):
        logger.error("Failed to setup worker service file.")
        return False

    return True


def setup_primary_node(
    git_ubuntu_user_home: str,
    system_user: str,
    primary_port: int,
    http_proxy: str = "",
    https_proxy: str = "",
) -> bool:
    """Set up poller and broker services to create a primary git-ubuntu importer node.

    Args:
        git_ubuntu_user_home: The home directory of the git-ubuntu user.
        system_user: The user + group to run the services as.
        primary_port: The network port used for worker assignments.
        http_proxy: URL for the environment's http proxy if required.
        https_proxy: URL for the environment's https proxy if required.

    Returns:
        True if installation succeeded, False otherwise.
    """
    # Setup broker service.
    if not git_ubuntu.setup_broker_service(
        git_ubuntu_user_home,
        system_user,
        system_user,
        primary_port,
    ):
        logger.error("Failed to setup broker service.")
        return False

    denylist = pathops.LocalPath(
        git_ubuntu_user_home,
        "live-allowlist-denylist-source/gitubuntu/source-package-denylist.txt",
    )

    # Setup poller service.
    if not git_ubuntu.setup_poller_service(
        git_ubuntu_user_home,
        system_user,
        system_user,
        denylist.as_posix(),
        http_proxy,
        https_proxy,
    ):
        logger.error("Failed to setup poller service.")
        return False

    return True


def start(git_ubuntu_user_home: str, node_id: int, num_workers: int) -> bool:
    """Start all git-ubuntu services and wait for their startups to complete.

    Args:
        git_ubuntu_user_home: The home directory of the git-ubuntu user.
        node_id: The node ID of this node.
        num_workers: The number of worker services to start if secondary.

    Returns:
        True if all services were started successfully, False otherwise.
    """
    services_folder = pathops.LocalPath(git_ubuntu_user_home, "services")

    if not git_ubuntu.start_services(services_folder.as_posix(), node_id, num_workers):
        logger.error("Failed to start all services.")
        return False

    logger.info("Started git-ubuntu services.")
    return True


def reset(git_ubuntu_user_home: str) -> bool:
    """Stop and destroy all git-ubuntu services.

    Args:
        git_ubuntu_user_home: The home directory of the git-ubuntu user.

    Returns:
        True if all services were removed successfully, False otherwise.
    """
    services_folder = pathops.LocalPath(git_ubuntu_user_home, "services")

    if not git_ubuntu.stop_services(services_folder.as_posix()):
        logger.error("Failed to stop all services.")
        return False

    if not git_ubuntu.destroy_services(services_folder.as_posix()):
        logger.error("Failed to destroy all services.")
        return False

    logger.info("Reset git-ubuntu services.")
    return True
