#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Snap and Apt package installation and update functions."""

import logging
from pathlib import Path
from shutil import copy

from charmlibs import pathops
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


def git_ubuntu_setup_etc_dir() -> bool:
    """Set up /etc/git-ubuntu directory.

    Returns:
        True if the directory was created or exists already, False otherwise.
    """
    etc_dir = pathops.LocalPath("/etc/git-ubuntu")
    etc_dir_success = False

    try:
        etc_dir.mkdir(user="root", group="root")
        logger.info("Created /etc/git-ubuntu directory.")
        etc_dir_success = True
    except FileExistsError:
        logger.info("/etc/git-ubuntu already exists.")
        etc_dir_success = True
    except NotADirectoryError:
        logger.error("/etc/git-ubuntu already exists as a file.")
    except PermissionError:
        logger.error("Unable to create /etc/git-ubuntu directory: permission denied.")

    return etc_dir_success


def git_ubuntu_add_debian_archive_keyring(keyring_folder: Path) -> bool:
    """Copy debian archive keyring file from dumped charm files.

    Args:
        keyring_folder: The directory containing the keyring file in the charm dump.

    Returns:
        True if the file was copied over, False otherwise.
    """
    if not git_ubuntu_setup_etc_dir():
        return False

    copy(
        keyring_folder / "debian-archive-keyring.gpg",
        Path("/etc/git-ubuntu/debian-archive-keyring.gpg"),
    )

    return True
