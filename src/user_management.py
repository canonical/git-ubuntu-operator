#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Machine user management functions."""

import logging
from os import system

from charms.operator_libs_linux.v0 import passwd

logger = logging.getLogger(__name__)


def setup_git_ubuntu_user(user: str, home_dir: str) -> None:
    """Create the user for running git and git-ubuntu.

    Args:
        user: The user to create.
    """
    new_user = passwd.add_user(user, home_dir=home_dir, create_home=True)
    logger.info("Created user %s with home directory at %s.", new_user, home_dir)


def run_command_as_user(user: str, command: str) -> bool:
    """Run a command as a user.

    Args:
        user: The user to run the command as.
        command: The command to run.

    Returns:
        True if the command was run successfully, False otherwise.
    """
    command_result = system(f'su - {user} -s /bin/bash -c "{command}"')
    if command_result != 0:
        return False
    return True
