# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

"""Unit tests for importer node management."""

from git_ubuntu import GitUbuntuBroker, GitUbuntuPoller
from importer_node import ImporterNode


def test_init_creates_correct_instances():
    """Test creation of broker, poller, and number of workers."""
    primary_node = ImporterNode(True, 2)

    assert isinstance(primary_node._broker, GitUbuntuBroker)
    assert isinstance(primary_node._poller, GitUbuntuPoller)
    assert len(primary_node._workers) == 2

    secondary_triple_node = ImporterNode(False, 3)
    assert len(secondary_triple_node._workers) == 3
