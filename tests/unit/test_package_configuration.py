# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

"""Unit tests for package management and configuration."""

from unittest.mock import patch

from charms.operator_libs_linux.v0 import apt
from charms.operator_libs_linux.v2 import snap

import package_configuration as pkgs


@patch("package_configuration.run_command_as_user")
def test_git_update_user_name_config_success(mock_run_command_as_user):
    """Test successful git user name config update."""
    mock_run_command_as_user.return_value = True

    assert pkgs.git_update_user_name_config("ubuntu", "Test User")
    mock_run_command_as_user.assert_called_once_with(
        "ubuntu", "git config --global user.name 'Test User'"
    )


@patch("package_configuration.run_command_as_user")
def test_git_update_user_name_config_fail(mock_run_command_as_user):
    """Test failed git user name config update."""
    mock_run_command_as_user.return_value = False

    assert not pkgs.git_update_user_name_config("ubuntu", "Test User")
    mock_run_command_as_user.assert_called_once_with(
        "ubuntu", "git config --global user.name 'Test User'"
    )


@patch("package_configuration.run_command_as_user")
def test_git_update_user_email_config_success(mock_run_command_as_user):
    """Test successful git user email config update."""
    mock_run_command_as_user.return_value = True

    assert pkgs.git_update_user_email_config("ubuntu", "test@example.com")
    mock_run_command_as_user.assert_called_once_with(
        "ubuntu", "git config --global user.email test@example.com"
    )


@patch("package_configuration.run_command_as_user")
def test_git_update_user_email_config_fail(mock_run_command_as_user):
    """Test failed git user email config update."""
    mock_run_command_as_user.return_value = False

    assert not pkgs.git_update_user_email_config("ubuntu", "test@example.com")
    mock_run_command_as_user.assert_called_once_with(
        "ubuntu", "git config --global user.email test@example.com"
    )


@patch("package_configuration.run_command_as_user")
def test_lp_user_config_success(mock_run_command_as_user):
    """Test successful launchpad user config update."""
    mock_run_command_as_user.return_value = True

    assert pkgs.git_update_lpuser_config("ubuntu", "test-lp-user")
    mock_run_command_as_user.assert_called_once_with(
        "ubuntu", "git config --global gitubuntu.lpuser test-lp-user"
    )


@patch("package_configuration.run_command_as_user")
def test_lp_user_config_fail(mock_run_command_as_user):
    """Test failed launchpad user config update."""
    mock_run_command_as_user.return_value = False

    assert not pkgs.git_update_lpuser_config("ubuntu", "test-lp-user")
    mock_run_command_as_user.assert_called_once_with(
        "ubuntu", "git config --global gitubuntu.lpuser test-lp-user"
    )


@patch("package_configuration.apt.update")
@patch("package_configuration.apt.add_package")
def test_git_install_success(mock_add_package, mock_update):
    """Test successful git install."""
    assert pkgs.git_install()

    mock_update.assert_called_once()
    mock_add_package.assert_called_once_with("git")


@patch("package_configuration.apt.update")
@patch("package_configuration.apt.add_package")
def test_git_install_fail(mock_add_package, mock_update):
    """Test failed git install."""
    mock_add_package.side_effect = apt.PackageError

    assert not pkgs.git_install()

    mock_update.assert_called_once()
    mock_add_package.assert_called_once_with("git")


@patch("package_configuration.apt.update")
@patch("package_configuration.apt.add_package")
def test_sqlite3_install_success(mock_add_package, mock_update):
    """Test successful git install."""
    assert pkgs.sqlite3_install()

    mock_update.assert_called_once()
    mock_add_package.assert_called_once_with("sqlite3")


@patch("package_configuration.apt.update")
@patch("package_configuration.apt.add_package")
def test_sqlite3_install_fail(mock_add_package, mock_update):
    """Test failed git install."""
    mock_add_package.side_effect = apt.PackageError

    assert not pkgs.sqlite3_install()

    mock_update.assert_called_once()
    mock_add_package.assert_called_once_with("sqlite3")


@patch("package_configuration.snap.SnapCache")
def test_git_ubuntu_snap_refresh_failure(mock_snap_cache):
    """Test refresh function when a SnapError occurs."""
    mock_snap_cache.side_effect = snap.SnapError

    assert not pkgs.git_ubuntu_snap_refresh("stable")

    mock_snap_cache.assert_called_once()


@patch("package_configuration.snap.SnapCache")
def test_git_ubuntu_snap_refresh_success(mock_snap_cache):
    """Test refresh function successful."""
    assert pkgs.git_ubuntu_snap_refresh("stable")

    mock_snap_cache.assert_called_once()
