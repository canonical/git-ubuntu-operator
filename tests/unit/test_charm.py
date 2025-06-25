# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

from unittest.mock import patch

import pytest
from charms.operator_libs_linux.v0.apt import PackageError
from ops.testing import ActiveStatus, BlockedStatus, Context, State

from charm import GitUbuntuCharm


@pytest.fixture
def ctx():
    return Context(GitUbuntuCharm)


@pytest.fixture
def base_state(ctx):
    return State(leader=True)


@patch("charms.operator_libs_linux.v0.apt.update")
@patch("charms.operator_libs_linux.v0.apt.add_package")
def test_install_success(mock_add_package, mock_update, ctx, base_state):
    """Test successful installation with valid config."""
    out = ctx.run(ctx.on.install(), base_state)
    assert out.unit_status == ActiveStatus("Ready")
    mock_update.assert_called_once()
    mock_add_package.assert_called_once_with("git")


@patch("charms.operator_libs_linux.v0.apt.update")
@patch("charms.operator_libs_linux.v0.apt.add_package")
def test_install_apt_error(mock_add_package, mock_update, ctx, base_state):
    """Test installation when apt operations fail."""
    mock_add_package.side_effect = PackageError("Failed to install package")
    out = ctx.run(ctx.on.install(), base_state)
    assert isinstance(out.unit_status, BlockedStatus)
    assert "Failed to install git" in str(out.unit_status.message)


@patch("charms.operator_libs_linux.v0.apt.update")
@patch("charms.operator_libs_linux.v0.apt.add_package")
def test_install_invalid_lpuser(mock_add_package, mock_update, ctx):
    """Test installation with invalid lpuser."""
    state = State(config={"channel": "beta", "lpuser": "Invalid@User"})
    out = ctx.run(ctx.on.install(), state)
    assert isinstance(out.unit_status, BlockedStatus)
    assert "lpuser does not match" in str(out.unit_status.message)


@patch("charms.operator_libs_linux.v0.apt.update")
@patch("charms.operator_libs_linux.v0.apt.add_package")
def test_install_invalid_channel(mock_add_package, mock_update, ctx):
    """Test installation with invalid channel."""
    state = State(config={"channel": "invalid", "lpuser": "git-ubuntu-bot"})
    out = ctx.run(ctx.on.install(), state)
    assert isinstance(out.unit_status, BlockedStatus)
    assert "Invalid channel" in str(out.unit_status.message)
