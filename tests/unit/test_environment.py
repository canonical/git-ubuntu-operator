# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

"""Unit tests for launchpad tools."""

import os

import environment as env


def test_get_juju_http_proxy_url():
    """Test getting Juju http proxy URL when not set."""
    proxy_var_original = os.environ.get("JUJU_CHARM_HTTP_PROXY")

    if proxy_var_original is not None:
        del os.environ["JUJU_CHARM_HTTP_PROXY"]

    proxy_url = env.get_juju_http_proxy_url()
    assert proxy_url == ""

    test_url = "http://proxy.internal:1234"
    os.environ["JUJU_CHARM_HTTP_PROXY"] = test_url
    proxy_url = env.get_juju_http_proxy_url()
    assert proxy_url == test_url

    del os.environ["JUJU_CHARM_HTTP_PROXY"]

    if proxy_var_original is not None:
        os.environ["JUJU_CHARM_HTTP_PROXY"] = proxy_var_original


def test_get_juju_https_proxy_url():
    """Test getting Juju https proxy URL when not set."""
    proxy_var_original = os.environ.get("JUJU_CHARM_HTTPS_PROXY")

    if proxy_var_original is not None:
        del os.environ["JUJU_CHARM_HTTPS_PROXY"]

    proxy_url = env.get_juju_https_proxy_url()
    assert proxy_url == ""

    test_url = "http://httpsproxy.internal:1234"
    os.environ["JUJU_CHARM_HTTPS_PROXY"] = test_url
    proxy_url = env.get_juju_https_proxy_url()
    assert proxy_url == test_url

    del os.environ["JUJU_CHARM_HTTPS_PROXY"]

    if proxy_var_original is not None:
        os.environ["JUJU_CHARM_HTTPS_PROXY"] = proxy_var_original
