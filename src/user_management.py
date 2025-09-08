#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Machine user management functions."""

import logging
from os import system

from charmlibs import pathops
from charms.operator_libs_linux.v0 import passwd

logger = logging.getLogger(__name__)


def _run_command_as_user(user: str, command: str) -> bool:
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


def _clone_git_ubuntu_source(cloning_user: str, parent_directory: str, source_url: str) -> bool:
    """Clone the git-ubuntu git repo to a given directory.

    Args:
        cloning_user: The user to run git clone as.
        parent_directory: The directory to clone the repo into.
        source_url: git-ubuntu's git repo url.

    Returns:
        True if the clone succeeded, False otherwise.
    """
    directory_path = pathops.LocalPath(parent_directory)
    if not directory_path.is_dir():
        logger.error(
            "Failed to clone git-ubuntu sources: %s is not a valid directory.", parent_directory
        )
        return False

    clone_dir = pathops.LocalPath(directory_path, "live-allowlist-denylist-source")
    logger.info("Cloning git-ubuntu source to %s", clone_dir)
    result = _run_command_as_user(cloning_user, f"git clone {source_url} {clone_dir}")

    if result != 0:
        logger.error("Failed to clone git-ubuntu source, process exited with result %d.", result)
        return False

    return True


def setup_git_ubuntu_user(user: str, home_dir: str) -> None:
    """Create the user for running git and git-ubuntu.

    Args:
        user: The user to create.
        home_dir: The home directory for the user.
    """
    new_user = passwd.add_user(user, home_dir=home_dir, create_home=True)
    logger.info("Created user %s with home directory at %s.", new_user, home_dir)


def setup_git_ubuntu_user_files(user: str, home_dir: str, git_ubuntu_source_url: str) -> bool:
    """Create necessary files for git-ubuntu user.

    Files include:
        The services folder
        git-ubuntu source code

    Args:
        user: The user to install the files for.
        home_dir: The home directory for the user.
        git_ubuntu_source_url: git-ubuntu's git repo url.

    Returns:
        True if the files were installed successfully, False otherwise.
    """
    if not _clone_git_ubuntu_source(user, home_dir, git_ubuntu_source_url):
        return False

    # Create the services folder if it does not yet exist
    services_dir = pathops.LocalPath(home_dir, "services")
    services_dir_success = False

    try:
        services_dir.mkdir(parents=True, user=user, group=user)
        logger.info("Created services directory %s.", services_dir)
        services_dir_success = True
    except FileExistsError:
        logger.info("Services directory %s already exists.", services_dir)
        services_dir_success = True
    except NotADirectoryError:
        logger.error("Service directory location %s already exists as a file.", services_dir)
    except PermissionError:
        logger.error("Unable to create new service directory %s: permission denied.", services_dir)
    except LookupError:
        logger.error(
            "Unable to create service directory %s: unknown user/group %s",
            services_dir,
            user,
        )

    return services_dir_success


def update_git_user_name(user: str, name: str) -> bool:
    """Update the git user full name entry.

    Args:
        user: The system user to update the config for.
        name: The full name for the git user.

    Returns:
        True if config update succeeded, False otherwise.
    """
    logger.info("Setting git user.name to %s for user %s.", name, user)
    return _run_command_as_user(user, f"git config --global user.name '{name}'")


def update_git_email(user: str, email: str) -> bool:
    """Update the git user email address entry.

    Args:
        user: The system user to update the config for.
        email: The email address for the git user.

    Returns:
        True if config update succeeded, False otherwise.
    """
    logger.info("Setting git user.email to %s for user %s.", email, user)
    return _run_command_as_user(user, f"git config --global user.email {email}")


def update_git_ubuntu_lpuser(user: str, lp_username: str) -> bool:
    """Update the launchpad user setting for git.

    Args:
        user: The system user to update the config for.
        lp_username: The launchpad username set in git.

    Returns:
        True if config update succeeded, False otherwise.
    """
    logger.info("Setting git gitubuntu.lpuser to %s for user %s.", lp_username, user)
    return _run_command_as_user(user, f"git config --global gitubuntu.lpuser {lp_username}")
