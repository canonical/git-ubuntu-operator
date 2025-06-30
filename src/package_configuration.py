#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Snap and Apt package configuration and management functions."""

from os import system


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
