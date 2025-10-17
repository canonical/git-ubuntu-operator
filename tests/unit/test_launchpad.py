# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

"""Unit tests for launchpad tools."""

import launchpad as lp


def test_check_lpuser_success():
    """Test checker success for lp username."""
    assert lp.is_valid_lp_username("git-ubuntu-bot")
    assert lp.is_valid_lp_username("ubuntu-server")
    assert lp.is_valid_lp_username("test-user.7+")


def test_check_lpuser_fail():
    """Test checker success for lp username."""
    assert not lp.is_valid_lp_username("git?ubuntu?bot")
    assert not lp.is_valid_lp_username("")
    assert not lp.is_valid_lp_username("test()")
