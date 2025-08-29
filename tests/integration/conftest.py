#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.


"""Integration test configuration."""

import subprocess
from pathlib import Path

import jubilant
import pytest


@pytest.fixture(scope="module")
def juju(request: pytest.FixtureRequest):
    """Create a temporary juju model for testing."""
    with jubilant.temp_model() as juju:
        yield juju

        if request.session.testsfailed:
            log = juju.debug_log(limit=1000)
            print(log, end="")


@pytest.fixture(scope="session")
def charm():
    """Build the charm for integration testing."""
    subprocess.check_call(["charmcraft", "pack"])
    # Modify below if you're building for multiple bases or architectures.
    return next(Path(".").glob("*.charm"))
