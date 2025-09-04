#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Snap and Apt package installation and update functions."""

import logging

from charms.operator_libs_linux.v0 import apt
from charms.operator_libs_linux.v2 import snap

from user_management import run_command_as_user

logger = logging.getLogger(__name__)


def git_update_user_name_config(user: str, name: str) -> bool:
    """Update the git user full name entry.

    Args:
        user: The system user to update the config for.
        name: The full name for the git user.

    Returns:
        True if config update succeeded, False otherwise.
    """
    logger.info("Setting git user.name to %s for user %s.", name, user)
    return run_command_as_user(user, f"git config --global user.name '{name}'")


def git_update_user_email_config(user: str, email: str) -> bool:
    """Update the git user email address entry.

    Args:
        user: The system user to update the config for.
        email: The email address for the git user.

    Returns:
        True if config update succeeded, False otherwise.
    """
    logger.info("Setting git user.email to %s for user %s.", email, user)
    return run_command_as_user(user, f"git config --global user.email {email}")


def git_update_lpuser_config(user: str, lp_username: str) -> bool:
    """Update the launchpad user setting for git.

    Args:
        user: The system user to update the config for.
        lp_username: The launchpad username set in git.

    Returns:
        True if config update succeeded, False otherwise.
    """
    logger.info("Setting git gitubuntu.lpuser to %s for user %s.", lp_username, user)
    return run_command_as_user(user, f"git config --global gitubuntu.lpuser {lp_username}")


def git_install() -> bool:
    """Install git from apt.

    Returns:
        True if git install succeeded, False otherwise.
    """
    try:
        apt.update()
        apt.add_package("git")
        logger.info("Installed git package.")
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
        logger.info("Installed sqlite3 package.")
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
        logger.info("Refreshed git-ubuntu snap to channel %s.", channel)
    except snap.SnapError as e:
        logger.error("Failed to refresh git-ubuntu snap to channel %s: %s", channel, e)
        return False

    return True
