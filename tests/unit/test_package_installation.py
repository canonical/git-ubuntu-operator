# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

"""Unit tests for package management and configuration."""

from unittest.mock import patch

from charmlibs import apt
from charms.operator_libs_linux.v2 import snap

import package_installation as pkgs


@patch("package_installation.apt.update")
@patch("package_installation.apt.add_package")
def test_git_install_success(mock_add_package, mock_update):
    """Test successful git install."""
    assert pkgs.git_install()

    mock_update.assert_called_once()
    mock_add_package.assert_called_once_with("git")


@patch("package_installation.apt.update")
@patch("package_installation.apt.add_package")
def test_git_install_fail(mock_add_package, mock_update):
    """Test failed git install."""
    mock_add_package.side_effect = apt.PackageError

    assert not pkgs.git_install()

    mock_update.assert_called_once()
    mock_add_package.assert_called_once_with("git")


@patch("package_installation.apt.update")
@patch("package_installation.apt.add_package")
def test_sqlite3_install_success(mock_add_package, mock_update):
    """Test successful git install."""
    assert pkgs.sqlite3_install()

    mock_update.assert_called_once()
    mock_add_package.assert_called_once_with("sqlite3")


@patch("package_installation.apt.update")
@patch("package_installation.apt.add_package")
def test_sqlite3_install_fail(mock_add_package, mock_update):
    """Test failed git install."""
    mock_add_package.side_effect = apt.PackageError

    assert not pkgs.sqlite3_install()

    mock_update.assert_called_once()
    mock_add_package.assert_called_once_with("sqlite3")


@patch("package_installation.snap.SnapCache")
def test_git_ubuntu_snap_refresh_failure(mock_snap_cache):
    """Test refresh function when a SnapError occurs."""
    mock_snap_cache.side_effect = snap.SnapError

    assert not pkgs.git_ubuntu_snap_refresh("stable")

    mock_snap_cache.assert_called_once()


@patch("package_installation.snap.SnapCache")
def test_git_ubuntu_snap_refresh_success(mock_snap_cache):
    """Test refresh function successful."""
    assert pkgs.git_ubuntu_snap_refresh("stable")

    mock_snap_cache.assert_called_once()
