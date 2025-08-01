#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Snap and Apt package configuration and management functions."""

import logging
from os import system

from charms.operator_libs_linux.v0 import apt
from charms.operator_libs_linux.v2 import snap

logger = logging.getLogger(__name__)


def git_update_user_name_config(name: str) -> bool:
    """Update the git user full name entry.

    Args:
        name: The full name for the git user.

    Returns:
        True if config update succeeded, False otherwise.
    """
    update_config_result = system(f'git config --global user.name "{name}"')
    if update_config_result != 0:
        return False
    return True


def git_update_user_email_config(email: str) -> bool:
    """Update the git user email address entry.

    Args:
        email: The email address for the git user.

    Returns:
        True if config update succeeded, False otherwise.
    """
    update_config_result = system(f'git config --global user.email "{email}"')
    if update_config_result != 0:
        return False
    return True


def git_update_lpuser_config(lp_username: str) -> bool:
    """Update the launchpad user setting for git.

    Args:
        lp_username: The launchpad username set in git.

    Returns:
        True if config update succeeded, False otherwise.
    """
    update_config_result = system(f'git config --global gitubuntu.lpuser "{lp_username}"')
    if update_config_result != 0:
        return False
    return True


def git_install() -> bool:
    """Install git from apt.

    Returns:
        True if git install succeeded, False otherwise.
    """
    try:
        apt.update()
        apt.add_package("git")
    except apt.PackageError as e:
        logger.error("Failed to install git from apt: %s", e)
        return False

    return True


def sqlite3_install() -> bool:
    """Install sqlite3 from apt.

    Returns:
        True if sqlite3 install succeeded, False otherwise.
    """
    try:
        apt.update()
        apt.add_package("sqlite3")
    except apt.PackageError as e:
        logger.error("Failed to install sqlite3 from apt: %s", e)
        return False

    return True


def git_ubuntu_snap_refresh(channel: str) -> bool:
    """Install or refresh the git-ubuntu snap with the given channel version.

    Args:
        channel: The channel to install the snap from.

    Returns:
        True if the snap install succeeded, False otherwise.
    """
    try:
        cache = snap.SnapCache()
        git_ubuntu_snap = cache["git-ubuntu"]
        git_ubuntu_snap.ensure(snap.SnapState.Latest, classic=True, channel=channel)
    except snap.SnapError as e:
        logger.error("Failed to refresh git-ubuntu snap to channel %s: %s", channel, e)
        return False

    return True
