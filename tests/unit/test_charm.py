# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

"""Unit tests for git-ubuntu charm."""

from unittest.mock import call, patch

from charms.operator_libs_linux.v0.apt import PackageError
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


@patch("charms.operator_libs_linux.v0.apt.update")
@patch("charms.operator_libs_linux.v0.apt.add_package")
@patch("charm.usr.setup_git_ubuntu_user")
def test_install_success(
    mock_setup_git_ubuntu_user, mock_add_package, mock_apt_update, ctx, base_state
):
    """Test successful installation with valid config."""
    out = ctx.run(ctx.on.install(), base_state)

    assert out.unit_status == ActiveStatus("Install complete.")

    mock_apt_update.assert_called()
    mock_add_package.assert_has_calls([call("git"), call("sqlite3")])
    mock_setup_git_ubuntu_user.assert_called_once_with("git-ubuntu", "/var/local/git-ubuntu")


@patch("charms.operator_libs_linux.v0.apt.update")
@patch("charms.operator_libs_linux.v0.apt.add_package")
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
