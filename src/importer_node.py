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
    node_id: int,
    num_workers: int,
    system_user: str,
    push_to_lp: bool,
    primary_port: int,
    primary_ip: str,
) -> bool:
    """Set up necessary services for a worker-only git-ubuntu importer node.

    Args:
        git_ubuntu_user_home: The home directory of the git-ubuntu user.
        node_id: The unique ID of this node.
        num_workers: The number of worker instances to set up.
        system_user: The user + group to run the services as.
        push_to_lp: True if publishing repositories to Launchpad.
        primary_port: The network port used for worker assignments.
        primary_ip: The IP or network location of the primary node.

    Returns:
        True if installation succeeded, False otherwise.
    """
    services_folder = pathops.LocalPath(git_ubuntu_user_home, "services")

    for i in range(num_workers):
        worker_name = f"{node_id}_{i}"
        if not git_ubuntu.setup_worker_service(
            services_folder.as_posix(),
            system_user,
            system_user,
            worker_name,
            push_to_lp,
            primary_ip,
            primary_port,
        ):
            logger.error("Failed to setup worker %s service.", worker_name)
            return False

    return True


def setup_primary_node(
    git_ubuntu_user_home: str,
    node_id: int,
    num_workers: int,
    system_user: str,
    push_to_lp: bool,
    primary_port: int,
) -> bool:
    """Set up necessary services for a primary git-ubuntu importer node.

    Args:
        git_ubuntu_user_home: The home directory of the git-ubuntu user.
        node_id: The unique ID of this node.
        num_workers: The number of worker instances to set up.
        system_user: The user + group to run the services as.
        push_to_lp: True if publishing repositories to Launchpad.
        primary_port: The network port used for worker assignments.

    Returns:
        True if installation succeeded, False otherwise.
    """
    services_folder = pathops.LocalPath(git_ubuntu_user_home, "services")

    if not setup_secondary_node(
        git_ubuntu_user_home,
        node_id,
        num_workers,
        system_user,
        push_to_lp,
        primary_port,
        "127.0.0.1",
    ):
        return False

    # Setup broker service.
    if not git_ubuntu.setup_broker_service(
        services_folder.as_posix(),
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
        services_folder.as_posix(),
        system_user,
        system_user,
        denylist.as_posix(),
    ):
        logger.error("Failed to setup poller service.")
        return False

    return True


def start(git_ubuntu_user_home: str) -> bool:
    """Start all git-ubuntu services.

    Args:
        git_ubuntu_user_home: The home directory of the git-ubuntu user.

    Returns:
        True if all services were started successfully, False otherwise.
    """
    services_folder = pathops.LocalPath(git_ubuntu_user_home, "services")

    if not git_ubuntu.start_services(services_folder.as_posix()):
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
