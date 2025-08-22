# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

"""Unit tests for importer node management."""

from pathlib import Path
from unittest.mock import patch

from pytest import fixture

from git_ubuntu import GitUbuntuBroker, GitUbuntuPoller
from importer_node import ImporterNode, PrimaryImporterNode


@fixture
def default_node():
    """Create a node with default settings."""
    return PrimaryImporterNode(0, 2, "ubuntu", True, 1692, "/var/local/git-ubuntu", "/home/ubuntu")


def test_init_creates_correct_instances(default_node):
    """Test creation of broker, poller, and number of workers."""
    assert isinstance(default_node._broker, GitUbuntuBroker)
    assert isinstance(default_node._poller, GitUbuntuPoller)
    assert len(default_node._workers) == 2

    secondary_triple_node = ImporterNode(1, 3, "ubuntu", True, 1692, "192.168.1.2")
    assert len(secondary_triple_node._workers) == 3


@patch("importer_node.PrimaryImporterNode.destroy")
@patch("importer_node.PrimaryImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.pathops.LocalPath.exists")
@patch("importer_node.pathops.LocalPath.mkdir")
def test_data_directory_update_same_success(
    mock_mkdir, mock_exists, mock_move, mock_stop, mock_destroy, default_node
):
    """Test data_directory update attempt with same name."""
    assert default_node._update_data_directory("/var/local/git-ubuntu")

    mock_mkdir.assert_not_called()
    mock_exists.assert_not_called()
    mock_move.assert_not_called()
    mock_stop.assert_not_called()
    mock_destroy.assert_not_called()


@patch("importer_node.GitUbuntuBroker.setup")
@patch("importer_node.GitUbuntuPoller.setup")
@patch("importer_node.PrimaryImporterNode.destroy")
@patch("importer_node.PrimaryImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.pathops.LocalPath.exists")
@patch("importer_node.pathops.LocalPath.mkdir")
def test_data_directory_update_exists_success(
    mock_mkdir,
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
    mock_exists.return_value = True
    mock_destroy.return_value = True
    mock_poller_setup.return_value = True
    mock_broker_setup.return_value = True

    assert default_node._update_data_directory("/var/new/git-ubuntu")

    mock_mkdir.assert_called_once()
    mock_exists.assert_called_once()
    mock_move.assert_not_called()
    mock_stop.assert_called_once_with(stop_workers=False)
    mock_destroy.assert_called_once_with(destroy_workers=False)
    mock_poller_setup.assert_called_once()
    mock_broker_setup.assert_called_once()


@patch("importer_node.GitUbuntuBroker.setup")
@patch("importer_node.GitUbuntuPoller.setup")
@patch("importer_node.PrimaryImporterNode.destroy")
@patch("importer_node.PrimaryImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.pathops.LocalPath.exists")
@patch("importer_node.pathops.LocalPath.mkdir")
def test_data_directory_update_folder_exists_success(
    mock_mkdir,
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
    mock_exists.return_value = False
    mock_destroy.return_value = True
    mock_poller_setup.return_value = True
    mock_broker_setup.return_value = True

    assert default_node._update_data_directory("/var/new/git-ubuntu")

    mock_mkdir.assert_called_once()
    mock_exists.assert_called()
    mock_move.assert_not_called()
    mock_stop.assert_called_once_with(stop_workers=False)
    mock_destroy.assert_called_once_with(destroy_workers=False)
    mock_poller_setup.assert_called_once()
    mock_broker_setup.assert_called_once()


@patch("importer_node.PrimaryImporterNode.destroy")
@patch("importer_node.PrimaryImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.pathops.LocalPath.exists")
@patch("importer_node.pathops.LocalPath.mkdir")
def test_data_directory_update_mkdir_file_fail(
    mock_mkdir, mock_exists, mock_move, mock_stop, mock_destroy, default_node
):
    """Test data_directory update attempt with new directory being an existing file."""
    mock_mkdir.side_effect = NotADirectoryError()

    assert not default_node._update_data_directory("/var/new/git-ubuntu")

    mock_mkdir.assert_called_once()
    mock_exists.assert_not_called()
    mock_move.assert_not_called()
    mock_stop.assert_not_called()
    mock_destroy.assert_not_called()


@patch("importer_node.PrimaryImporterNode.destroy")
@patch("importer_node.PrimaryImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.pathops.LocalPath.exists")
@patch("importer_node.pathops.LocalPath.mkdir")
def test_data_directory_update_permission_fail(
    mock_mkdir, mock_exists, mock_move, mock_stop, mock_destroy, default_node
):
    """Test data_directory update attempt with a permission error on mkdir."""
    mock_mkdir.side_effect = PermissionError()

    assert not default_node._update_data_directory("/var/new/git-ubuntu")

    mock_mkdir.assert_called_once()
    mock_exists.assert_not_called()
    mock_move.assert_not_called()
    mock_stop.assert_not_called()
    mock_destroy.assert_not_called()


@patch("importer_node.PrimaryImporterNode.destroy")
@patch("importer_node.PrimaryImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.pathops.LocalPath.exists")
@patch("importer_node.pathops.LocalPath.mkdir")
def test_data_directory_update_user_lookup_fail(
    mock_mkdir, mock_exists, mock_move, mock_stop, mock_destroy, default_node
):
    """Test data_directory update attempt with a user/group check error."""
    mock_mkdir.side_effect = LookupError()

    assert not default_node._update_data_directory("/var/new/git-ubuntu")

    mock_mkdir.assert_called_once()
    mock_exists.assert_not_called()
    mock_move.assert_not_called()
    mock_stop.assert_not_called()
    mock_destroy.assert_not_called()


@patch("importer_node.PrimaryImporterNode.destroy")
@patch("importer_node.PrimaryImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.pathops.LocalPath.exists")
@patch("importer_node.pathops.LocalPath.mkdir")
def test_data_directory_stop_fail(
    mock_mkdir, mock_exists, mock_move, mock_stop, mock_destroy, default_node
):
    """Test data_directory update attempt when git-ubuntu fails to stop."""
    mock_stop.return_value = False

    assert not default_node._update_data_directory("/var/new/git-ubuntu")

    mock_mkdir.assert_called_once()
    mock_exists.assert_not_called()
    mock_move.assert_not_called()
    mock_stop.assert_called_once_with(stop_workers=False)
    mock_destroy.assert_not_called()


@patch("importer_node.GitUbuntuBroker.setup")
@patch("importer_node.GitUbuntuPoller.setup")
@patch("importer_node.PrimaryImporterNode.destroy")
@patch("importer_node.PrimaryImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.pathops.LocalPath.exists")
@patch("importer_node.pathops.LocalPath.mkdir")
def test_data_directory_destroy_fail(
    mock_mkdir,
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

    assert not default_node._update_data_directory("/var/new/git-ubuntu")

    mock_mkdir.assert_called_once()
    mock_exists.assert_called_once()
    mock_move.assert_not_called()
    mock_stop.assert_called_once_with(stop_workers=False)
    mock_destroy.assert_called_once_with(destroy_workers=False)
    mock_poller_setup.assert_not_called()
    mock_broker_setup.assert_not_called()


@patch("importer_node.GitUbuntuBroker.setup")
@patch("importer_node.GitUbuntuPoller.setup")
@patch("importer_node.PrimaryImporterNode.destroy")
@patch("importer_node.PrimaryImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.pathops.LocalPath.exists")
@patch("importer_node.pathops.LocalPath.mkdir")
def test_data_directory_poller_fail(
    mock_mkdir,
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

    assert not default_node._update_data_directory("/var/new/git-ubuntu")

    mock_mkdir.assert_called_once()
    mock_exists.assert_called_once()
    mock_move.assert_not_called()
    mock_stop.assert_called_once_with(stop_workers=False)
    mock_destroy.assert_called_once_with(destroy_workers=False)
    mock_poller_setup.assert_called_once()
    mock_broker_setup.assert_called_once()


@patch("importer_node.GitUbuntuBroker.setup")
@patch("importer_node.GitUbuntuPoller.setup")
@patch("importer_node.PrimaryImporterNode.destroy")
@patch("importer_node.PrimaryImporterNode.stop")
@patch("importer_node.move")
@patch("importer_node.pathops.LocalPath.exists")
@patch("importer_node.pathops.LocalPath.mkdir")
def test_data_directory_broker_fail(
    mock_mkdir,
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

    assert not default_node._update_data_directory("/var/new/git-ubuntu")

    mock_mkdir.assert_called_once()
    mock_exists.assert_called_once()
    mock_move.assert_not_called()
    mock_stop.assert_called_once_with(stop_workers=False)
    mock_destroy.assert_called_once_with(destroy_workers=False)
    mock_poller_setup.assert_not_called()
    mock_broker_setup.assert_called_once()


@patch("importer_node.GitUbuntuPoller.setup")
@patch("importer_node.PrimaryImporterNode.destroy")
@patch("importer_node.PrimaryImporterNode.stop")
@patch("importer_node.rmtree")
@patch("importer_node.pathops.LocalPath.exists")
@patch("importer_node.pathops.LocalPath.mkdir")
def test_source_directory_update_same_success(
    mock_mkdir,
    mock_exists,
    mock_rmtree,
    mock_stop,
    mock_destroy,
    mock_poller_setup,
    default_node,
):
    """Test source_directory update attempt with same name."""
    assert default_node._update_source_directory("/home/ubuntu")

    mock_mkdir.assert_not_called()
    mock_exists.assert_not_called()
    mock_rmtree.assert_not_called()
    mock_stop.assert_not_called()
    mock_destroy.assert_not_called()
    mock_poller_setup.assert_not_called()


@patch("importer_node.GitUbuntuPoller.setup")
@patch("importer_node.PrimaryImporterNode._clone_git_ubuntu_source")
@patch("importer_node.PrimaryImporterNode.destroy")
@patch("importer_node.PrimaryImporterNode.stop")
@patch("importer_node.rmtree")
@patch("importer_node.pathops.LocalPath.exists")
@patch("importer_node.pathops.LocalPath.mkdir")
def test_source_directory_update_source_exists_success(
    mock_mkdir,
    mock_exists,
    mock_rmtree,
    mock_stop,
    mock_destroy,
    mock_clone,
    mock_poller_setup,
    default_node,
):
    """Test source_directory update attempt when source already exists."""
    mock_mkdir.side_effect = FileExistsError()
    mock_stop.return_value = True
    mock_exists.return_value = True
    mock_destroy.return_value = True
    mock_poller_setup.return_value = True

    assert default_node._update_source_directory("/home/user2")

    mock_mkdir.assert_called_once()
    mock_exists.assert_called_once()
    mock_rmtree.assert_called_once_with(Path("/home/user2/live-allowlist-denylist-source"))
    mock_stop.assert_called_once_with(stop_broker=False, stop_workers=False)
    mock_destroy.assert_called_once_with(destroy_broker=False, destroy_workers=False)
    mock_poller_setup.assert_called_once()


@patch("importer_node.GitUbuntuPoller.setup")
@patch("importer_node.PrimaryImporterNode._clone_git_ubuntu_source")
@patch("importer_node.PrimaryImporterNode.destroy")
@patch("importer_node.PrimaryImporterNode.stop")
@patch("importer_node.rmtree")
@patch("importer_node.pathops.LocalPath.exists")
@patch("importer_node.pathops.LocalPath.mkdir")
def test_source_directory_update_directory_exists_success(
    mock_mkdir,
    mock_exists,
    mock_rmtree,
    mock_stop,
    mock_destroy,
    mock_clone,
    mock_poller_setup,
    default_node,
):
    """Test source_directory update attempt when the new directory already exists."""
    mock_mkdir.side_effect = FileExistsError()
    mock_stop.return_value = True
    mock_exists.return_value = False
    mock_clone.return_value = True
    mock_destroy.return_value = True
    mock_poller_setup.return_value = True

    assert default_node._update_source_directory("/home/user2")

    mock_mkdir.assert_called_once()
    mock_exists.assert_called_once()
    mock_rmtree.assert_not_called()
    mock_clone.assert_called_once()
    mock_stop.assert_called_once_with(stop_broker=False, stop_workers=False)
    mock_destroy.assert_called_once_with(destroy_broker=False, destroy_workers=False)
    mock_poller_setup.assert_called_once()


@patch("importer_node.GitUbuntuPoller.setup")
@patch("importer_node.PrimaryImporterNode._clone_git_ubuntu_source")
@patch("importer_node.PrimaryImporterNode.destroy")
@patch("importer_node.PrimaryImporterNode.stop")
@patch("importer_node.rmtree")
@patch("importer_node.pathops.LocalPath.exists")
@patch("importer_node.pathops.LocalPath.mkdir")
def test_source_directory_update_file_exists_fail(
    mock_mkdir,
    mock_exists,
    mock_rmtree,
    mock_stop,
    mock_destroy,
    mock_clone,
    mock_poller_setup,
    default_node,
):
    """Test source_directory update attempt when the new directory already exists as file."""
    mock_mkdir.side_effect = NotADirectoryError()

    assert not default_node._update_source_directory("/home/user2")

    mock_mkdir.assert_called_once()
    mock_exists.assert_not_called()
    mock_rmtree.assert_not_called()
    mock_clone.assert_not_called()
    mock_stop.assert_not_called()
    mock_destroy.assert_not_called()
    mock_poller_setup.assert_not_called()


@patch("importer_node.GitUbuntuPoller.setup")
@patch("importer_node.PrimaryImporterNode._clone_git_ubuntu_source")
@patch("importer_node.PrimaryImporterNode.destroy")
@patch("importer_node.PrimaryImporterNode.stop")
@patch("importer_node.rmtree")
@patch("importer_node.pathops.LocalPath.exists")
@patch("importer_node.pathops.LocalPath.mkdir")
def test_source_directory_update_permission_fail(
    mock_mkdir,
    mock_exists,
    mock_rmtree,
    mock_stop,
    mock_destroy,
    mock_clone,
    mock_poller_setup,
    default_node,
):
    """Test source_directory update attempt with permission error."""
    mock_mkdir.side_effect = PermissionError()

    assert not default_node._update_source_directory("/home/user2")

    mock_mkdir.assert_called_once()
    mock_exists.assert_not_called()
    mock_rmtree.assert_not_called()
    mock_clone.assert_not_called()
    mock_stop.assert_not_called()
    mock_destroy.assert_not_called()
    mock_poller_setup.assert_not_called()


@patch("importer_node.GitUbuntuPoller.setup")
@patch("importer_node.PrimaryImporterNode._clone_git_ubuntu_source")
@patch("importer_node.PrimaryImporterNode.destroy")
@patch("importer_node.PrimaryImporterNode.stop")
@patch("importer_node.rmtree")
@patch("importer_node.pathops.LocalPath.exists")
@patch("importer_node.pathops.LocalPath.mkdir")
def test_source_directory_update_user_lookup_fail(
    mock_mkdir,
    mock_exists,
    mock_rmtree,
    mock_stop,
    mock_destroy,
    mock_clone,
    mock_poller_setup,
    default_node,
):
    """Test source_directory update attempt with a user/group lookup error."""
    mock_mkdir.side_effect = LookupError()

    assert not default_node._update_source_directory("/home/user2")

    mock_mkdir.assert_called_once()
    mock_exists.assert_not_called()
    mock_rmtree.assert_not_called()
    mock_clone.assert_not_called()
    mock_stop.assert_not_called()
    mock_destroy.assert_not_called()
    mock_poller_setup.assert_not_called()


@patch("importer_node.GitUbuntuPoller.setup")
@patch("importer_node.PrimaryImporterNode._clone_git_ubuntu_source")
@patch("importer_node.PrimaryImporterNode.destroy")
@patch("importer_node.PrimaryImporterNode.stop")
@patch("importer_node.rmtree")
@patch("importer_node.pathops.LocalPath.exists")
@patch("importer_node.pathops.LocalPath.mkdir")
def test_source_directory_update_stop_fail(
    mock_mkdir,
    mock_exists,
    mock_rmtree,
    mock_stop,
    mock_destroy,
    mock_clone,
    mock_poller_setup,
    default_node,
):
    """Test source_directory update attempt when git-ubuntu stop fails."""
    mock_stop.return_value = False

    assert not default_node._update_source_directory("/home/user2")

    mock_mkdir.assert_called_once()
    mock_exists.assert_not_called()
    mock_rmtree.assert_not_called()
    mock_clone.assert_not_called()
    mock_stop.assert_called_once_with(stop_broker=False, stop_workers=False)
    mock_destroy.assert_not_called()
    mock_poller_setup.assert_not_called()


@patch("importer_node.GitUbuntuPoller.setup")
@patch("importer_node.PrimaryImporterNode._clone_git_ubuntu_source")
@patch("importer_node.PrimaryImporterNode.destroy")
@patch("importer_node.PrimaryImporterNode.stop")
@patch("importer_node.rmtree")
@patch("importer_node.pathops.LocalPath.exists")
@patch("importer_node.pathops.LocalPath.mkdir")
def test_source_directory_update_rmtree_fail(
    mock_mkdir,
    mock_exists,
    mock_rmtree,
    mock_stop,
    mock_destroy,
    mock_clone,
    mock_poller_setup,
    default_node,
):
    """Test source_directory update attempt when rmtree fails."""
    mock_mkdir.side_effect = FileExistsError()
    mock_stop.return_value = True
    mock_exists.return_value = True
    mock_rmtree.side_effect = OSError()

    assert not default_node._update_source_directory("/home/user2")

    mock_mkdir.assert_called_once()
    mock_exists.assert_called_once()
    mock_rmtree.assert_called_once()
    mock_clone.assert_not_called()
    mock_stop.assert_called_once_with(stop_broker=False, stop_workers=False)
    mock_destroy.assert_not_called()
    mock_poller_setup.assert_not_called()


@patch("importer_node.GitUbuntuPoller.setup")
@patch("importer_node.PrimaryImporterNode._clone_git_ubuntu_source")
@patch("importer_node.PrimaryImporterNode.destroy")
@patch("importer_node.PrimaryImporterNode.stop")
@patch("importer_node.rmtree")
@patch("importer_node.pathops.LocalPath.exists")
@patch("importer_node.pathops.LocalPath.mkdir")
def test_source_directory_update_clone_fail(
    mock_mkdir,
    mock_exists,
    mock_rmtree,
    mock_stop,
    mock_destroy,
    mock_clone,
    mock_poller_setup,
    default_node,
):
    """Test source_directory update attempt when git-ubuntu source clone fails."""
    mock_stop.return_value = True
    mock_exists.return_value = False
    mock_clone.return_value = False

    assert not default_node._update_source_directory("/home/user2")

    mock_mkdir.assert_called_once()
    mock_exists.assert_called_once()
    mock_rmtree.assert_not_called()
    mock_clone.assert_called_once_with(Path("/home/user2"))
    mock_stop.assert_called_once_with(stop_broker=False, stop_workers=False)
    mock_destroy.assert_not_called()
    mock_poller_setup.assert_not_called()
