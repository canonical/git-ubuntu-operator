# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

"""Unit tests for importer node management."""

from unittest.mock import patch

import importer_node


@patch("importer_node.git_ubuntu.setup_worker_service")
def test_setup_secondary_node_success(mock_setup_worker):
    """Test successful secondary node setup."""
    mock_setup_worker.return_value = True

    result = importer_node.setup_secondary_node(
        "/var/local/git-ubuntu", 1, 2, "git-ubuntu", True, 1692, "192.168.1.1"
    )

    assert result is True
    assert mock_setup_worker.call_count == 2


@patch("importer_node.git_ubuntu.setup_worker_service")
def test_setup_secondary_node_failure(mock_setup_worker):
    """Test secondary node setup failure."""
    mock_setup_worker.return_value = False

    result = importer_node.setup_secondary_node(
        "/var/local/git-ubuntu", 1, 1, "git-ubuntu", True, 1692, "192.168.1.1"
    )

    assert result is False


@patch("importer_node.git_ubuntu.setup_poller_service")
@patch("importer_node.git_ubuntu.setup_broker_service")
def test_setup_primary_node_success(mock_broker, mock_poller):
    """Test successful primary node setup."""
    mock_broker.return_value = True
    mock_poller.return_value = True

    result = importer_node.setup_primary_node("/var/local/git-ubuntu", "git-ubuntu", 1692)

    assert result is True
    mock_broker.assert_called_once()
    mock_poller.assert_called_once()


@patch("importer_node.setup_secondary_node")
def test_setup_primary_node_secondary_failure(mock_secondary):
    """Test primary node setup with secondary failure."""
    mock_secondary.return_value = False

    result = importer_node.setup_primary_node("/var/local/git-ubuntu", "git-ubuntu", 1692)

    assert result is False


@patch("importer_node.git_ubuntu.setup_broker_service")
@patch("importer_node.setup_secondary_node")
def test_setup_primary_node_broker_failure(mock_secondary, mock_broker):
    """Test primary node setup with broker failure."""
    mock_secondary.return_value = True
    mock_broker.return_value = False

    result = importer_node.setup_primary_node("/var/local/git-ubuntu", "git-ubuntu", 1692)

    assert result is False


@patch("importer_node.git_ubuntu.setup_poller_service")
@patch("importer_node.git_ubuntu.setup_broker_service")
@patch("importer_node.setup_secondary_node")
def test_setup_primary_node_poller_failure(mock_secondary, mock_broker, mock_poller):
    """Test primary node setup with poller failure."""
    mock_secondary.return_value = True
    mock_broker.return_value = True
    mock_poller.return_value = False

    result = importer_node.setup_primary_node("/var/local/git-ubuntu", "git-ubuntu", 1692)

    assert result is False


@patch("importer_node.git_ubuntu.start_services")
def test_start_success(mock_start_services):
    """Test successful service start."""
    mock_start_services.return_value = True

    result = importer_node.start("/var/local/git-ubuntu")

    assert result is True
    mock_start_services.assert_called_once_with("/var/local/git-ubuntu/services")


@patch("importer_node.git_ubuntu.start_services")
def test_start_failure(mock_start_services):
    """Test service start failure."""
    mock_start_services.return_value = False

    result = importer_node.start("/var/local/git-ubuntu")

    assert result is False


@patch("importer_node.git_ubuntu.destroy_services")
@patch("importer_node.git_ubuntu.stop_services")
def test_reset_success(mock_stop, mock_destroy):
    """Test successful service reset."""
    mock_stop.return_value = True
    mock_destroy.return_value = True

    result = importer_node.reset("/var/local/git-ubuntu")

    assert result is True
    mock_stop.assert_called_once_with("/var/local/git-ubuntu/services")
    mock_destroy.assert_called_once_with("/var/local/git-ubuntu/services")


@patch("importer_node.git_ubuntu.stop_services")
def test_reset_stop_failure(mock_stop):
    """Test reset with stop failure."""
    mock_stop.return_value = False

    result = importer_node.reset("/var/local/git-ubuntu")

    assert result is False


@patch("importer_node.git_ubuntu.destroy_services")
@patch("importer_node.git_ubuntu.stop_services")
def test_reset_destroy_failure(mock_stop, mock_destroy):
    """Test reset with destroy failure."""
    mock_stop.return_value = True
    mock_destroy.return_value = False

    result = importer_node.reset("/var/local/git-ubuntu")

    assert result is False
