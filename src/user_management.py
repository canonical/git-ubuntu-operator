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
        logger.error("Command %s exited with result %d.", command, command_result)
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
    if not _run_command_as_user(cloning_user, f"git clone {source_url} {clone_dir}"):
        logger.error("Failed to clone git-ubuntu source.")
        return False

    return True


def _write_python_keyring_config_file(user: str, home_dir: str) -> bool:
    """Create a python_keyring/keyringrc.cfg file that enforces plaintext keyring usage.

    Args:
        user: The git-ubuntu user.
        home_dir: The home directory for the user.

    Returns:
        True if directory and file creation succeeded, False otherwise.
    """
    python_keyring_config = pathops.LocalPath(home_dir, ".config/python_keyring/keyringrc.cfg")

    parent_dir = python_keyring_config.parent
    config_dir_success = False

    try:
        parent_dir.mkdir(parents=True, user=user, group=user)
        config_dir_success = True
    except FileExistsError:
        logger.info("User config directory %s already exists.", parent_dir.as_posix())
        config_dir_success = True
    except NotADirectoryError:
        logger.error(
            "User config directory location %s already exists as a file.", parent_dir.as_posix()
        )
    except PermissionError:
        logger.error(
            "Unable to create new user config directory %s: permission denied.",
            parent_dir.as_posix(),
        )
    except LookupError:
        logger.error(
            "Unable to create config directory %s: unknown user/group %s",
            parent_dir.as_posix(),
            user,
        )

    if not config_dir_success:
        return False

    keyring_config_success = False

    try:
        python_keyring_config.write_text(
            "[backend]\n"
            + "default-keyring=keyrings.alt.file.PlaintextKeyring\n"
            + "keyring-path=/home/ubuntu/.cache/keyring\n",
            user=user,
            group=user,
        )
        keyring_config_success = True
    except (FileNotFoundError, NotADirectoryError) as e:
        logger.error("Failed to create keyringrc.cfg due to directory issues: %s", str(e))
    except LookupError as e:
        logger.error("Failed to create keyringrc.cfg due to issues with root user: %s", str(e))
    except PermissionError as e:
        logger.error("Failed to create keyringrc.cfg due to permission issues: %s", str(e))

    return keyring_config_success


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
        python_keyring config

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

    if not services_dir_success:
        return False

    return _write_python_keyring_config_file(user, home_dir)


def set_snap_homedirs(home_dir: str) -> bool:
    """Allow snaps to run for a user with a given home directory.

    Args:
        home_dir: The home directory of the user.

    Returns:
        True if the homedirs update succeeded, False otherwise.
    """
    homedirs_entry = pathops.LocalPath(home_dir).parent.as_posix()
    command_result = system(f"snap set system homedirs={homedirs_entry}")
    if command_result != 0:
        logger.error("snap homedir setting exited with result %d.", command_result)
        return False
    return True


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
