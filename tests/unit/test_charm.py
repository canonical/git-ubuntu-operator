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


def test_start_empty_importer_node(ctx, base_state):
    """Test startup when importer node is not yet initialized."""
    out = ctx.run(ctx.on.start(), base_state)

    assert out.unit_status == BlockedStatus("Failed to start, services not yet installed.")


@patch("charms.operator_libs_linux.v0.apt.update")
@patch("charms.operator_libs_linux.v0.apt.add_package")
@patch("charm.GitUbuntuCharm._update_lpuser_config")
@patch("charm.GitUbuntuCharm._update_git_ubuntu_snap")
@patch("importer_node.PrimaryImporterNode.install")
def test_install_success(
    mock_install,
    mock_update_git_ubuntu_snap,
    mock_update_lpuser_config,
    mock_add_package,
    mock_apt_update,
    ctx,
    base_state,
):
    """Test successful installation with valid config."""
    mock_update_lpuser_config.return_value = True
    mock_update_git_ubuntu_snap.return_value = True
    mock_install.return_value = True

    out = ctx.run(ctx.on.install(), base_state)

    assert out.unit_status == ActiveStatus("Ready")

    mock_apt_update.assert_called()
    mock_add_package.assert_has_calls([call("git"), call("sqlite3")])
    mock_update_lpuser_config.assert_called_once()
    mock_update_git_ubuntu_snap.assert_called_once()


@patch("charms.operator_libs_linux.v0.apt.update")
@patch("charms.operator_libs_linux.v0.apt.add_package")
@patch("charm.GitUbuntuCharm._update_lpuser_config")
@patch("charm.GitUbuntuCharm._update_git_ubuntu_snap")
@patch("importer_node.ImporterNode.install")
def test_install_secondary_success(
    mock_install,
    mock_update_git_ubuntu_snap,
    mock_update_lpuser_config,
    mock_add_package,
    mock_apt_update,
    ctx,
):
    """Test successful installation when primary is False."""
    mock_update_lpuser_config.return_value = True
    mock_update_git_ubuntu_snap.return_value = True
    mock_install.return_value = True
    state = State(config={"primary": False})

    out = ctx.run(ctx.on.install(), state)

    assert out.unit_status == ActiveStatus("Ready")

    mock_apt_update.assert_called_once()
    mock_add_package.assert_called_once_with("git")
    mock_update_lpuser_config.assert_called_once()
    mock_update_git_ubuntu_snap.assert_called_once()


@patch("charms.operator_libs_linux.v0.apt.update")
@patch("charms.operator_libs_linux.v0.apt.add_package")
@patch("charm.GitUbuntuCharm._update_lpuser_config")
@patch("charm.GitUbuntuCharm._update_git_ubuntu_snap")
def test_install_apt_error(
    mock_update_git_ubuntu_snap,
    mock_update_lpuser_config,
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
    mock_update_lpuser_config.assert_not_called()
    mock_update_git_ubuntu_snap.assert_not_called()


@patch("charms.operator_libs_linux.v0.apt.update")
@patch("charms.operator_libs_linux.v0.apt.add_package")
@patch("charm.GitUbuntuCharm._update_git_ubuntu_snap")
def test_install_invalid_lpuser(mock_update_git_ubuntu_snap, mock_add_package, mock_update, ctx):
    """Test installation with invalid lpuser."""
    state = State(config={"channel": "beta", "lpuser": "Invalid@User"})

    out = ctx.run(ctx.on.install(), state)

    assert isinstance(out.unit_status, BlockedStatus)
    assert "lpuser does not match" in str(out.unit_status.message)

    mock_update.assert_called_once()
    mock_add_package.assert_called_once_with("git")
    mock_update_git_ubuntu_snap.assert_not_called()


@patch("charms.operator_libs_linux.v0.apt.update")
@patch("charms.operator_libs_linux.v0.apt.add_package")
@patch("charm.GitUbuntuCharm._update_lpuser_config")
def test_install_invalid_channel(mock_update_lpuser_config, mock_add_package, mock_update, ctx):
    """Test installation with invalid channel."""
    mock_update_lpuser_config.return_value = True
    state = State(config={"channel": "invalid", "lpuser": "git-ubuntu-bot"})

    out = ctx.run(ctx.on.install(), state)

    assert isinstance(out.unit_status, BlockedStatus)
    assert "Invalid channel" in str(out.unit_status.message)

    mock_update.assert_called()
    mock_add_package.assert_has_calls([call("git"), call("sqlite3")])
    mock_update_lpuser_config.assert_called_once()


@patch("charm.GitUbuntuCharm._update_git_ubuntu_snap")
def test_config_changed_invalid_lpuser(mock_update_git_ubuntu_snap, ctx):
    """Test installation with invalid lpuser."""
    state = State(config={"channel": "beta", "lpuser": "Invalid@User", "primary": False})

    out = ctx.run(ctx.on.config_changed(), state)

    assert isinstance(out.unit_status, BlockedStatus)
    assert "lpuser does not match" in str(out.unit_status.message)

    mock_update_git_ubuntu_snap.assert_not_called()


@patch("charm.GitUbuntuCharm._update_lpuser_config")
def test_config_changed_invalid_channel(mock_update_lpuser_config, ctx):
    """Test installation with invalid channel."""
    mock_update_lpuser_config.return_value = True
    state = State(config={"channel": "invalid", "lpuser": "git-ubuntu-bot", "primary": False})

    out = ctx.run(ctx.on.config_changed(), state)

    assert isinstance(out.unit_status, BlockedStatus)
    assert "Invalid channel" in str(out.unit_status.message)

    mock_update_lpuser_config.assert_called_once()


@patch("charm.pkgs.git_update_lpuser_config")
def test_update_lpuser_config_git_fail(mock_git_config, ctx, base_state):
    """Test a git config update failure on install."""
    mock_git_config.return_value = False

    out = ctx.run(ctx.on.config_changed(), base_state)

    assert isinstance(out.unit_status, BlockedStatus)
    assert "Failed to update lpuser config." in str(out.unit_status.message)


@patch("charm.GitUbuntuCharm._update_lpuser_config")
@patch("charm.pkgs.git_ubuntu_snap_refresh")
def test_update_snap_refresh_fail(
    mock_git_ubuntu_snap_refresh,
    mock_update_lpuser_config,
    ctx,
):
    """Test failure to snap refresh with valid config values."""
    mock_update_lpuser_config.return_value = True
    mock_git_ubuntu_snap_refresh.return_value = False
    state = State(config={"channel": "edge", "lpuser": "git-ubuntu-bot", "primary": False})

    out = ctx.run(ctx.on.config_changed(), state)

    assert isinstance(out.unit_status, BlockedStatus)
    assert "Failed to install or refresh git-ubuntu snap" in str(out.unit_status.message)

    mock_update_lpuser_config.assert_called_once()
    mock_git_ubuntu_snap_refresh.assert_called_once()
