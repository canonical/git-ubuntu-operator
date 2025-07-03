# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

"""Unit tests for importer node management."""

from unittest.mock import patch

from pytest import fixture

from git_ubuntu import GitUbuntuBroker, GitUbuntuPoller
from importer_node import ImporterNode


@fixture
def default_node():
    """Create a node with default settings."""
    return ImporterNode(True, 2, "/var/local/git-ubuntu", "/home/ubuntu")


def test_init_creates_correct_instances(default_node):
    """Test creation of broker, poller, and number of workers."""
    assert isinstance(default_node._broker, GitUbuntuBroker)
    assert isinstance(default_node._poller, GitUbuntuPoller)
    assert len(default_node._workers) == 2

    secondary_triple_node = ImporterNode(False, 3, "/var/local/git-ubuntu", "/home/ubuntu")
    assert len(secondary_triple_node._workers) == 3


@patch("importer_node.ImporterNode.destroy")
@patch("importer_node.ImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.Path.exists")
@patch("importer_node.Path.is_dir")
@patch("importer_node.Path.mkdir")
def test_data_directory_update_same_success(
    mock_mkdir, mock_isdir, mock_exists, mock_move, mock_stop, mock_destroy, default_node
):
    """Test data_directory update attempt with same name."""
    assert default_node.update_data_directory("/var/local/git-ubuntu")

    mock_mkdir.assert_not_called()
    mock_isdir.assert_not_called()
    mock_exists.assert_not_called()
    mock_move.assert_not_called()
    mock_stop.assert_not_called()
    mock_destroy.assert_not_called()


@patch("importer_node.GitUbuntuBroker.setup")
@patch("importer_node.GitUbuntuPoller.setup")
@patch("importer_node.ImporterNode.destroy")
@patch("importer_node.ImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.Path.exists")
@patch("importer_node.Path.is_dir")
@patch("importer_node.Path.mkdir")
def test_data_directory_update_exists_success(
    mock_mkdir,
    mock_isdir,
    mock_exists,
    mock_move,
    mock_stop,
    mock_destroy,
    mock_poller_setup,
    mock_broker_setup,
    default_node,
):
    """Test data_directory update attempt when db already exists."""
    mock_mkdir.side_effect = FileExistsError()
    mock_stop.return_value = True
    mock_isdir.return_value = True
    mock_exists.return_value = True
    mock_destroy.return_value = True
    mock_poller_setup.return_value = True
    mock_broker_setup.return_value = True

    assert default_node.update_data_directory("/var/new/git-ubuntu")

    mock_mkdir.assert_called_once()
    mock_isdir.assert_called_once()
    mock_exists.assert_called_once()
    mock_move.assert_not_called()
    mock_stop.assert_called_once_with(stop_workers=False)
    mock_destroy.assert_called_once_with(destroy_workers=False)
    mock_poller_setup.assert_called_once()
    mock_broker_setup.assert_called_once()


@patch("importer_node.GitUbuntuBroker.setup")
@patch("importer_node.GitUbuntuPoller.setup")
@patch("importer_node.ImporterNode.destroy")
@patch("importer_node.ImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.Path.exists")
@patch("importer_node.Path.is_dir")
@patch("importer_node.Path.mkdir")
def test_data_directory_update_folder_exists_success(
    mock_mkdir,
    mock_isdir,
    mock_exists,
    mock_move,
    mock_stop,
    mock_destroy,
    mock_poller_setup,
    mock_broker_setup,
    default_node,
):
    """Test data_directory update attempt when new folder already exists."""
    mock_mkdir.side_effect = FileExistsError()
    mock_stop.return_value = True
    mock_isdir.return_value = True
    mock_exists.return_value = False
    mock_destroy.return_value = True
    mock_poller_setup.return_value = True
    mock_broker_setup.return_value = True

    assert default_node.update_data_directory("/var/new/git-ubuntu")

    mock_mkdir.assert_called_once()
    mock_isdir.assert_called_once()
    mock_exists.assert_called()
    mock_move.assert_not_called()
    mock_stop.assert_called_once_with(stop_workers=False)
    mock_destroy.assert_called_once_with(destroy_workers=False)
    mock_poller_setup.assert_called_once()
    mock_broker_setup.assert_called_once()


@patch("importer_node.ImporterNode.destroy")
@patch("importer_node.ImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.Path.exists")
@patch("importer_node.Path.is_dir")
@patch("importer_node.Path.mkdir")
def test_data_directory_update_mkdir_file_fail(
    mock_mkdir, mock_isdir, mock_exists, mock_move, mock_stop, mock_destroy, default_node
):
    """Test data_directory update attempt with new directory being an existing file."""
    mock_mkdir.side_effect = FileExistsError()
    mock_isdir.return_value = False

    assert not default_node.update_data_directory("/var/new/git-ubuntu")

    mock_mkdir.assert_called_once()
    mock_isdir.assert_called_once()
    mock_exists.assert_not_called()
    mock_move.assert_not_called()
    mock_stop.assert_not_called()
    mock_destroy.assert_not_called()


@patch("importer_node.ImporterNode.destroy")
@patch("importer_node.ImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.Path.exists")
@patch("importer_node.Path.is_dir")
@patch("importer_node.Path.mkdir")
def test_data_directory_update_permission_fail(
    mock_mkdir, mock_isdir, mock_exists, mock_move, mock_stop, mock_destroy, default_node
):
    """Test data_directory update attempt with a permission error on mkdir."""
    mock_mkdir.side_effect = PermissionError()

    assert not default_node.update_data_directory("/var/new/git-ubuntu")

    mock_mkdir.assert_called_once()
    mock_isdir.assert_not_called()
    mock_exists.assert_not_called()
    mock_move.assert_not_called()
    mock_stop.assert_not_called()
    mock_destroy.assert_not_called()


@patch("importer_node.ImporterNode.destroy")
@patch("importer_node.ImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.Path.exists")
@patch("importer_node.Path.is_dir")
@patch("importer_node.Path.mkdir")
def test_data_directory_update_os_fail(
    mock_mkdir, mock_isdir, mock_exists, mock_move, mock_stop, mock_destroy, default_node
):
    """Test data_directory update attempt with an OS error on mkdir."""
    mock_mkdir.side_effect = OSError()

    assert not default_node.update_data_directory("/var/new/git-ubuntu")

    mock_mkdir.assert_called_once()
    mock_isdir.assert_not_called()
    mock_exists.assert_not_called()
    mock_move.assert_not_called()
    mock_stop.assert_not_called()
    mock_destroy.assert_not_called()


@patch("importer_node.ImporterNode.destroy")
@patch("importer_node.ImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.Path.exists")
@patch("importer_node.Path.is_dir")
@patch("importer_node.Path.mkdir")
def test_data_directory_stop_fail(
    mock_mkdir, mock_isdir, mock_exists, mock_move, mock_stop, mock_destroy, default_node
):
    """Test data_directory update attempt when git-ubuntu fails to stop."""
    mock_stop.return_value = False

    assert not default_node.update_data_directory("/var/new/git-ubuntu")

    mock_mkdir.assert_called_once()
    mock_isdir.assert_not_called()
    mock_exists.assert_not_called()
    mock_move.assert_not_called()
    mock_stop.assert_called_once_with(stop_workers=False)
    mock_destroy.assert_not_called()


@patch("importer_node.GitUbuntuBroker.setup")
@patch("importer_node.GitUbuntuPoller.setup")
@patch("importer_node.ImporterNode.destroy")
@patch("importer_node.ImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.Path.exists")
@patch("importer_node.Path.is_dir")
@patch("importer_node.Path.mkdir")
def test_data_directory_destroy_fail(
    mock_mkdir,
    mock_isdir,
    mock_exists,
    mock_move,
    mock_stop,
    mock_destroy,
    mock_poller_setup,
    mock_broker_setup,
    default_node,
):
    """Test data_directory update attempt when service destroy fails."""
    mock_stop.return_value = True
    mock_exists.return_value = True
    mock_destroy.return_value = False

    assert not default_node.update_data_directory("/var/new/git-ubuntu")

    mock_mkdir.assert_called_once()
    mock_isdir.assert_not_called()
    mock_exists.assert_called_once()
    mock_move.assert_not_called()
    mock_stop.assert_called_once_with(stop_workers=False)
    mock_destroy.assert_called_once_with(destroy_workers=False)
    mock_poller_setup.assert_not_called()
    mock_broker_setup.assert_not_called()


@patch("importer_node.GitUbuntuBroker.setup")
@patch("importer_node.GitUbuntuPoller.setup")
@patch("importer_node.ImporterNode.destroy")
@patch("importer_node.ImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.Path.exists")
@patch("importer_node.Path.is_dir")
@patch("importer_node.Path.mkdir")
def test_data_directory_poller_fail(
    mock_mkdir,
    mock_isdir,
    mock_exists,
    mock_move,
    mock_stop,
    mock_destroy,
    mock_poller_setup,
    mock_broker_setup,
    default_node,
):
    """Test data_directory update attempt when poller setup fails."""
    mock_stop.return_value = True
    mock_exists.return_value = True
    mock_destroy.return_value = True
    mock_poller_setup.return_value = False
    mock_broker_setup.return_value = True

    assert not default_node.update_data_directory("/var/new/git-ubuntu")

    mock_mkdir.assert_called_once()
    mock_isdir.assert_not_called()
    mock_exists.assert_called_once()
    mock_move.assert_not_called()
    mock_stop.assert_called_once_with(stop_workers=False)
    mock_destroy.assert_called_once_with(destroy_workers=False)
    mock_poller_setup.assert_called_once()
    mock_broker_setup.assert_called_once()


@patch("importer_node.GitUbuntuBroker.setup")
@patch("importer_node.GitUbuntuPoller.setup")
@patch("importer_node.ImporterNode.destroy")
@patch("importer_node.ImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.Path.exists")
@patch("importer_node.Path.is_dir")
@patch("importer_node.Path.mkdir")
def test_data_directory_broker_fail(
    mock_mkdir,
    mock_isdir,
    mock_exists,
    mock_move,
    mock_stop,
    mock_destroy,
    mock_poller_setup,
    mock_broker_setup,
    default_node,
):
    """Test data_directory update attempt when broker setup fails."""
    mock_stop.return_value = True
    mock_exists.return_value = True
    mock_destroy.return_value = True
    mock_poller_setup.return_value = True
    mock_broker_setup.return_value = False

    assert not default_node.update_data_directory("/var/new/git-ubuntu")

    mock_mkdir.assert_called_once()
    mock_isdir.assert_not_called()
    mock_exists.assert_called_once()
    mock_move.assert_not_called()
    mock_stop.assert_called_once_with(stop_workers=False)
    mock_destroy.assert_called_once_with(destroy_workers=False)
    mock_poller_setup.assert_not_called()
    mock_broker_setup.assert_called_once()
