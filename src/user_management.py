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


def setup_git_ubuntu_user(user: str, home_dir: str) -> None:
    """Create the user for running git and git-ubuntu.

    Args:
        user: The user to create.
        home_dir: The home directory for the user.
    """
    new_user = passwd.add_user(user, home_dir=home_dir, create_home=True)
    logger.info("Created user %s with home directory at %s.", new_user, home_dir)


def setup_git_ubuntu_user_services_dir(user: str, home_dir: str) -> bool:
    """Create the folder for containing git-ubuntu services.

    Args:
        user: The user to install the folder for.
        home_dir: The home directory for the user.

    Returns:
        True if the folder was created successfully, False otherwise.
    """
    # Create the services folder if it does not yet exist
    services_dir = pathops.LocalPath(home_dir, "services")

    return _mkdir_for_user_with_error_checking(services_dir, user)


def refresh_git_ubuntu_source(
    user: str, home_dir: str, source_url: str, https_proxy: str = ""
) -> bool:
    """Clone or update the git-ubuntu git repo in the home directory.

    Args:
        user: The user to run git clone as.
        home_dir: The home directory for the user.
        source_url: git-ubuntu's git repo url.
        https_proxy: The https proxy URL if required.

    Returns:
        True if the clone succeeded, False otherwise.
    """
    directory_path = pathops.LocalPath(home_dir)
    if not directory_path.is_dir():
        logger.error("Failed to clone git-ubuntu sources: %s is not a valid directory.", home_dir)
        return False

    clone_dir = pathops.LocalPath(directory_path, "live-allowlist-denylist-source")

    if clone_dir.is_dir():
        logger.info("Updating existing git-ubuntu source in %s", clone_dir.as_posix())

        # Update origin to the current source url
        if not _run_command_as_user(
            user, f"git -C {clone_dir.as_posix()} remote set-url origin {source_url}"
        ):
            logger.error("Failed to update git-ubuntu source origin.")
            return False

        # Run git pull to get up to date
        pull_command = f"git -C {clone_dir.as_posix()} pull"
        if https_proxy != "":
            pull_command = f"https_proxy={https_proxy} {pull_command}"

        if not _run_command_as_user(user, pull_command):
            logger.error("Failed to update existing git-ubuntu source.")
            return False

        return True

    # Clone the repository
    clone_command = f"git clone {source_url} {clone_dir.as_posix()}"
    if https_proxy != "":
        clone_command = f"https_proxy={https_proxy} {clone_command}"

    logger.info("Cloning git-ubuntu source to %s", clone_dir.as_posix())
    if not _run_command_as_user(user, clone_command):
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


def update_launchpad_credentials_secret(user: str, home_dir: str, lp_key_data: str) -> bool:
    """Create or refresh the credentials file for launchpad access.

    Args:
        user: The git-ubuntu user.
        home_dir: The home directory for the user.
        lp_key_data: The private credential data.

    Returns:
        True if directory and file creation succeeded, False otherwise.
    """
    lp_key_file = pathops.LocalPath(home_dir, ".config/lp-credentials.oauth")

    parent_dir = lp_key_file.parent

    if not _mkdir_for_user_with_error_checking(parent_dir, user, 0o700):
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
        logger.error("Failed to create lp credentials entry due to directory issues: %s", str(e))
    except LookupError as e:
        logger.error(
            "Failed to create lp credentials entry due to issues with root user: %s", str(e)
        )
    except PermissionError as e:
        logger.error("Failed to create lp credentials entry due to permission issues: %s", str(e))
    return key_success


def update_ssh_config(user: str, home_dir: str, http_proxy: str = "") -> bool:
    """Create or refresh the .ssh/config file for git.launchpad.net handling.

    Args:
        user: The git-ubuntu user.
        home_dir: The home directory for the user.
        http_proxy: The http proxy URL if required.

    Returns:
        True if directory and file creation succeeded, False otherwise.
    """
    ssh_config_file = pathops.LocalPath(home_dir, ".ssh/config")

    parent_dir = ssh_config_file.parent

    if not _mkdir_for_user_with_error_checking(parent_dir, user, 0o700):
        return False

    config_success = False

    ssh_config_content: str = (
        "Host git.launchpad.net\n"
        + "  HostName git.launchpad.net\n"
        + "  Port 22\n"
        + "  IdentityFile ~/.ssh/id\n"
    )

    # Use socat to proxy ssh data if needed.
    if http_proxy != "":
        proxy_base_url = http_proxy.replace("http://", "").split(":")[0]
        proxy_port = (
            http_proxy.replace("http://", "").split(":")[1] if ":" in http_proxy else "3128"
        )
        ssh_config_content += (
            "  ProxyCommand /usr/bin/socat - "
            + f"PROXY:{proxy_base_url}:%h:%p,proxyport={proxy_port}\n"
        )

    try:
        ssh_config_file.write_text(
            ssh_config_content,
            mode=0o664,
            user=user,
            group=user,
        )
        config_success = True
    except (FileNotFoundError, NotADirectoryError) as e:
        logger.error("Failed to create ssh config due to directory issues: %s", str(e))
    except LookupError as e:
        logger.error("Failed to create ssh config due to issues with root user: %s", str(e))
    except PermissionError as e:
        logger.error("Failed to create ssh config due to permission issues: %s", str(e))
    return config_success


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
