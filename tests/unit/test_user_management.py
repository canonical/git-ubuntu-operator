# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

"""Unit tests for package management and configuration."""

from unittest.mock import patch

import user_management


@patch("user_management._run_command_as_user")
def test_git_update_user_name_config_success(mock_run_command_as_user):
    """Test successful git user name config update."""
    mock_run_command_as_user.return_value = True

    assert user_management.update_git_user_name("ubuntu", "Test User")
    mock_run_command_as_user.assert_called_once_with(
        "ubuntu", "git config --global user.name 'Test User'"
    )


@patch("user_management._run_command_as_user")
def test_git_update_user_name_config_fail(mock_run_command_as_user):
    """Test failed git user name config update."""
    mock_run_command_as_user.return_value = False

    assert not user_management.update_git_user_name("ubuntu", "Test User")
    mock_run_command_as_user.assert_called_once_with(
        "ubuntu", "git config --global user.name 'Test User'"
    )


@patch("user_management._run_command_as_user")
def test_git_update_user_email_config_success(mock_run_command_as_user):
    """Test successful git user email config update."""
    mock_run_command_as_user.return_value = True

    assert user_management.update_git_email("ubuntu", "test@example.com")
    mock_run_command_as_user.assert_called_once_with(
        "ubuntu", "git config --global user.email test@example.com"
    )


@patch("user_management._run_command_as_user")
def test_git_update_user_email_config_fail(mock_run_command_as_user):
    """Test failed git user email config update."""
    mock_run_command_as_user.return_value = False

    assert not user_management.update_git_email("ubuntu", "test@example.com")
    mock_run_command_as_user.assert_called_once_with(
        "ubuntu", "git config --global user.email test@example.com"
    )


@patch("user_management._run_command_as_user")
def test_lp_user_config_success(mock_run_command_as_user):
    """Test successful launchpad user config update."""
    mock_run_command_as_user.return_value = True

    assert user_management.update_git_ubuntu_lpuser("ubuntu", "test-lp-user")
    mock_run_command_as_user.assert_called_once_with(
        "ubuntu", "git config --global gitubuntu.lpuser test-lp-user"
    )


@patch("user_management._run_command_as_user")
def test_lp_user_config_fail(mock_run_command_as_user):
    """Test failed launchpad user config update."""
    mock_run_command_as_user.return_value = False

    assert not user_management.update_git_ubuntu_lpuser("ubuntu", "test-lp-user")
    mock_run_command_as_user.assert_called_once_with(
        "ubuntu", "git config --global gitubuntu.lpuser test-lp-user"
    )
