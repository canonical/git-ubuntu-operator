#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Snap and Apt package configuration and management functions."""

from os import system

from charms.operator_libs_linux.v2 import snap


def git_update_lpuser_config(lp_username: str) -> bool:
    """
    Update the launchpad user setting for git.

    Args:
        lp_username: The launchpad username set in git.

    Returns:
        true if config update succeeded, false otherwise.
    """
    update_config_result = system(f'git config --global gitubuntu.lpuser "{lp_username}"')
    if update_config_result != 0:
        return False
    return True


def git_ubuntu_snap_refresh(channel: str) -> bool:
    """
    Install or refresh the git-ubuntu snap with the given channel version.

    Args:
        channel: The channel to install the snap from.

    Returns:
        true if the snap install succeeded, false otherwise.
    """
    try:
        cache = snap.SnapCache()
        git_ubuntu_snap = cache["git-ubuntu"]
        git_ubuntu_snap.ensure(snap.SnapState.Latest, classic=True, channel=channel)
    except snap.SnapError:
        return False

    return True
