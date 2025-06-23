# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

import pytest
from ops.testing import ActiveStatus, Context, State

from charm import GitUbuntuCharm


@pytest.fixture
def ctx():
    return Context(GitUbuntuCharm)


@pytest.fixture
def base_state(ctx):
    return State(leader=True)


def test_install_success(ctx, base_state):
    out = ctx.run(ctx.on.install(), base_state)
    assert out.unit_status == ActiveStatus("Ready")
