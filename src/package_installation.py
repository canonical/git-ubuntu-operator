#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Snap and Apt package installation and update functions."""

import logging

from charms.operator_libs_linux.v0 import apt
from charms.operator_libs_linux.v2 import snap

logger = logging.getLogger(__name__)


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
