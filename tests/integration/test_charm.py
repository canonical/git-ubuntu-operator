#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.


"""Integration tests."""

import logging
from pathlib import Path

import jubilant
import yaml

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
APP_NAME = METADATA["name"]


def test_startup(charm: Path, juju: jubilant.Juju):
    """Test default startup without LP integration."""
    juju.deploy(f"./{charm}", config={"publish": False})

    juju.wait(lambda status: jubilant.all_active(status, APP_NAME))
