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


def _mkdir_for_user_with_error_checking(
    directory: pathops.LocalPath, user: str, mode: int = 0o755
) -> bool:
    """Create a directory and handle possible mkdir errors.

    Args:
        directory: The directory to create, skipping if it exists.
        user: The user who should own this directory.
        mode: The permissions mode for the folder, defaults to standard rwxr-xr-x.

    Returns:
        True if the folder was created, False otherwise.
    """
    try:
        directory.mkdir(parents=True, user=user, group=user, mode=mode)
        return True
    except FileExistsError:
        logger.info("Directory %s already exists.", directory.as_posix())
        return True
    except NotADirectoryError:
        logger.error("Directory location %s already exists as a file.", directory.as_posix())
    except PermissionError:
        logger.error(
            "Unable to create new directory %s: permission denied.",
            directory.as_posix(),
        )
    except LookupError:
        logger.error(
            "Unable to create directory %s: unknown user/group %s",
            directory.as_posix(),
            user,
        )

    return False


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

    if not _mkdir_for_user_with_error_checking(parent_dir, user):
        return False

    keyring_config_success = False

    try:
        python_keyring_config.write_text(
            "[backend]\n"
            + "default-keyring=keyrings.alt.file.PlaintextKeyring\n"
            + f"keyring-path={home_dir}/.cache/keyring\n",
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


def setup_git_ubuntu_user_files(user: str, home_dir: str) -> bool:
    """Create necessary files for git-ubuntu user.

    Files include:
        The services folder
        python_keyring config

    Args:
        user: The user to install the files for.
        home_dir: The home directory for the user.

    Returns:
        True if the files were installed successfully, False otherwise.
    """
    # Create the services folder if it does not yet exist
    services_dir = pathops.LocalPath(home_dir, "services")

    if not _mkdir_for_user_with_error_checking(services_dir, user):
        return False

    return _write_python_keyring_config_file(user, home_dir)


def refresh_git_ubuntu_source(user: str, home_dir: str, source_url: str) -> bool:
    """Clone or update the git-ubuntu git repo in the home directory.

    Args:
        user: The user to run git clone as.
        home_dir: The home directory for the user.
        source_url: git-ubuntu's git repo url.

    Returns:
        True if the clone succeeded, False otherwise.
    """
    directory_path = pathops.LocalPath(home_dir)
    if not directory_path.is_dir():
        logger.error("Failed to clone git-ubuntu sources: %s is not a valid directory.", home_dir)
        return False

    clone_dir = pathops.LocalPath(directory_path, "live-allowlist-denylist-source")

    if clone_dir.is_dir():
        logger.info("Updating existing git-ubuntu source in %s", clone_dir)

        # Update origin to the current source url
        if not _run_command_as_user(
            user, f"git -C {clone_dir.as_posix()} remote set-url origin {source_url}"
        ):
            logger.error("Failed to update git-ubuntu source origin.")
            return False

        # Run git pull to get up to date
        if not _run_command_as_user(user, f"git -C {clone_dir.as_posix()} pull"):
            logger.error("Failed to update existing git-ubuntu source.")
            return False

        return True

    # Clone the repository
    logger.info("Cloning git-ubuntu source to %s", clone_dir)
    if not _run_command_as_user(user, f"git clone {source_url} {clone_dir}"):
        logger.error("Failed to clone git-ubuntu source.")
        return False

    return True


def update_ssh_private_key(user: str, home_dir: str, ssh_key_data: str) -> bool:
    """Create or refresh the .ssh/id private key file for launchpad access.

    Args:
        user: The git-ubuntu user.
        home_dir: The home directory for the user.
        ssh_key_data: The private key data.

    Returns:
        True if directory and file creation succeeded, False otherwise.
    """
    ssh_key_file = pathops.LocalPath(home_dir, ".ssh/id")

    parent_dir = ssh_key_file.parent

    if not _mkdir_for_user_with_error_checking(parent_dir, user, 0o700):
        return False

    key_success = False

    try:
        ssh_key_file.write_text(
            ssh_key_data,
            mode=0o600,
            user=user,
            group=user,
        )
        key_success = True
    except (FileNotFoundError, NotADirectoryError) as e:
        logger.error("Failed to create ssh private key due to directory issues: %s", str(e))
    except LookupError as e:
        logger.error("Failed to create ssh private key due to issues with root user: %s", str(e))
    except PermissionError as e:
        logger.error("Failed to create ssh private key due to permission issues: %s", str(e))

    return key_success


def update_launchpad_keyring_secret(user: str, home_dir: str, lp_key_data: str) -> bool:
    """Create or refresh the python keyring file for launchpad access.

    Args:
        user: The git-ubuntu user.
        home_dir: The home directory for the user.
        lp_key_data: The private keyring data.

    Returns:
        True if directory and file creation succeeded, False otherwise.
    """
    lp_key_file = pathops.LocalPath(home_dir, ".local/share/python_keyring/keyring_pass.cfg")

    parent_dir = lp_key_file.parent

    if not _mkdir_for_user_with_error_checking(parent_dir, user):
        return False

    key_success = False

    try:
        lp_key_file.write_text(
            lp_key_data,
            mode=0o600,
            user=user,
            group=user,
        )
        key_success = True
    except (FileNotFoundError, NotADirectoryError) as e:
        logger.error("Failed to create lp key entry due to directory issues: %s", str(e))
    except LookupError as e:
        logger.error("Failed to create lp key entry due to issues with root user: %s", str(e))
    except PermissionError as e:
        logger.error("Failed to create lp key entry due to permission issues: %s", str(e))

    return key_success


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
