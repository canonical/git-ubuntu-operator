#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Environment information extraction."""

import os


def get_juju_http_proxy_url() -> str:
    """Get the Juju-managed http proxy URL if available.

    Returns:
        The proxy URL or an empty string if it does not exist.
    """
    env = os.environ.copy()
    http_proxy = env.get("JUJU_CHARM_HTTP_PROXY")

    if http_proxy:
        return http_proxy

    return ""


def get_juju_https_proxy_url() -> str:
    """Get the Juju-managed https proxy URL if available.

    Returns:
        The proxy URL or an empty string if it does not exist.
    """
    env = os.environ.copy()
    https_proxy = env.get("JUJU_CHARM_HTTPS_PROXY")

    if https_proxy:
        return https_proxy

    return ""
