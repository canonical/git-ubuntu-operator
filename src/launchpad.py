#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Launchpad interaction and tools."""

import re


def is_valid_lp_username(lp_username: str) -> bool:
    """Check if the given launchpad username is valid.

    Usernames must be comprised only of lowercase letters, numbers and .-+.

    Args:
        lp_username: The launchpad username to check.

    Returns:
        True if the username is valid, False otherwise.
    """
    if not re.match(r"^[a-z0-9\.\-\+]+$", lp_username):
        return False
    return True
