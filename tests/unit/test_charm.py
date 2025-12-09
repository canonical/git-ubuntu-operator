# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

"""Unit tests for git-ubuntu charm."""

from unittest.mock import call, patch

from charmlibs.apt import PackageError
from ops.testing import ActiveStatus, BlockedStatus, Context, State
from pytest import fixture

from charm import GitUbuntuCharm


@fixture
def ctx():
    """Create a standard context for the charm."""
    return Context(GitUbuntuCharm)


@fixture
def base_state(ctx):
    """Create a base state for the charm."""
    return State(leader=True)


@patch("charmlibs.apt.update")
@patch("charmlibs.apt.add_package")
@patch("charm.usr.setup_git_ubuntu_user")
@patch("charm.usr.setup_git_ubuntu_user_files")
@patch("charm.usr.set_snap_homedirs")
@patch("charm.pkgs.git_ubuntu_add_debian_archive_keyring")
def test_install_success(
    mock_git_ubuntu_add_debian_archive_keyring,
    mock_set_snap_homedirs,
    mock_setup_git_ubuntu_user_files,
    mock_setup_git_ubuntu_user,
    mock_add_package,
    mock_apt_update,
    ctx,
    base_state,
):
    """Test successful installation with valid config."""
    mock_setup_git_ubuntu_user_files.return_value = True
    out = ctx.run(ctx.on.install(), base_state)

    assert out.unit_status == ActiveStatus("Install complete.")

    mock_apt_update.assert_called()
    mock_add_package.assert_has_calls([call("git"), call("sqlite3")])
    mock_setup_git_ubuntu_user.assert_called_once_with("git-ubuntu", "/var/local/git-ubuntu")
    mock_setup_git_ubuntu_user_files.assert_called_once_with("git-ubuntu", "/var/local/git-ubuntu")
    mock_set_snap_homedirs.assert_called_once_with("/var/local/git-ubuntu")
    mock_git_ubuntu_add_debian_archive_keyring.assert_called_once()


@patch("charmlibs.apt.update")
@patch("charmlibs.apt.add_package")
def test_install_apt_error(
    mock_add_package,
    mock_update,
    ctx,
    base_state,
):
    """Test installation when apt operations fail."""
    mock_add_package.side_effect = PackageError("Failed to install package")

    out = ctx.run(ctx.on.install(), base_state)

    assert isinstance(out.unit_status, BlockedStatus)
    assert "Failed to install git" in str(out.unit_status.message)

    mock_update.assert_called_once()
