# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

"""Unit tests for git-ubuntu instance classes."""

from git_ubuntu import generate_systemd_service_string


def test_generate_systemd_service_string_10():
    """
    Test generate_systemd_service_string with all optional parameters except wanted_by.

    This test verifies that the function correctly generates a systemd service string
    when all optional parameters are provided except for wanted_by. It checks that
    the resulting string includes all the specified service configurations.
    """
    result = generate_systemd_service_string(
        description="Test Service",
        service_user="ubuntu",
        service_group="testgroup",
        service_type="simple",
        exec_start="/snap/bin/git-ubuntu importer-service-broker tcp://*:1692",
        service_restart="on-failure",
        restart_sec=5,
        timeout_start_sec=259200,
        watchdog_sec=60,
        runtime_dir="git-ubuntu",
        private_tmp=True,
        environment="PATH=/usr/local/bin:/usr/bin:/bin",
    )

    expected = """[Unit]
Description=Test Service

[Service]
User=ubuntu
Group=testgroup
Type=simple
ExecStart=/snap/bin/git-ubuntu importer-service-broker tcp://*:1692
Restart=on-failure
RestartSec=5
TimeoutStartSec=259200
WatchdogSec=60
RuntimeDirectory=git-ubuntu
PrivateTmp=yes
Environment=PATH=/usr/local/bin:/usr/bin:/bin"""

    assert result == expected


def test_generate_systemd_service_string_2():
    """
    Test generate_systemd_service_string with various optional parameters set.

    This test verifies the function's behavior when restart_sec, timeout_start_sec,
    watchdog_sec, runtime_dir, private_tmp, environment, and wanted_by are provided,
    while service_restart is not set.
    """
    result = generate_systemd_service_string(
        description="Test Service",
        service_user="ubuntu",
        service_group="testgroup",
        service_type="simple",
        exec_start="/snap/bin/git-ubuntu importer-service-broker tcp://*:1692",
        restart_sec=10,
        timeout_start_sec=60,
        watchdog_sec=259200,
        runtime_dir="git-ubuntu",
        private_tmp=True,
        environment="PATH=/usr/local/bin:/usr/bin:/bin",
        wanted_by="multi-user.target",
    )

    expected_output = (
        "[Unit]\n"
        "Description=Test Service\n"
        "\n"
        "[Service]\n"
        "User=ubuntu\n"
        "Group=testgroup\n"
        "Type=simple\n"
        "ExecStart=/snap/bin/git-ubuntu importer-service-broker tcp://*:1692\n"
        "RestartSec=10\n"
        "TimeoutStartSec=60\n"
        "WatchdogSec=259200\n"
        "RuntimeDirectory=git-ubuntu\n"
        "PrivateTmp=yes\n"
        "Environment=PATH=/usr/local/bin:/usr/bin:/bin\n"
        "\n"
        "[Install]\n"
        "WantedBy=multi-user.target"
    )

    assert result == expected_output


def test_generate_systemd_service_string_3():
    """
    Test generate_systemd_service_string with specific parameters.

    This test verifies that the function correctly generates a systemd service string
    when service_restart, timeout_start_sec, watchdog_sec, runtime_dir, private_tmp,
    environment, and wanted_by are provided, but restart_sec is not.
    """
    result = generate_systemd_service_string(
        description="Test Service",
        service_user="ubuntu",
        service_group="testgroup",
        service_type="simple",
        exec_start="/snap/bin/git-ubuntu importer-service-broker tcp://*:1692",
        service_restart="on-failure",
        timeout_start_sec=60,
        watchdog_sec=259200,
        runtime_dir="git-ubuntu",
        private_tmp=True,
        environment="PATH=/usr/bin",
        wanted_by="multi-user.target",
    )

    expected = """[Unit]
Description=Test Service

[Service]
User=ubuntu
Group=testgroup
Type=simple
ExecStart=/snap/bin/git-ubuntu importer-service-broker tcp://*:1692
Restart=on-failure
TimeoutStartSec=60
WatchdogSec=259200
RuntimeDirectory=git-ubuntu
PrivateTmp=yes
Environment=PATH=/usr/bin

[Install]
WantedBy=multi-user.target"""

    assert result == expected


def test_generate_systemd_service_string_4():
    """
    Test generate_systemd_service_string with specific path constraints.

    This test verifies the function's behavior when:
    - service_restart is provided
    - restart_sec is provided
    - timeout_start_sec is not provided
    - watchdog_sec is provided
    - runtime_dir is provided
    - private_tmp is True
    - environment is provided
    - wanted_by is provided
    """
    result = generate_systemd_service_string(
        description="Test Service",
        service_user="ubuntu",
        service_group="testgroup",
        service_type="simple",
        exec_start="/usr/bin/test",
        service_restart="on-failure",
        restart_sec=5,
        watchdog_sec=259200,
        runtime_dir="git-ubuntu",
        private_tmp=True,
        environment="PATH=/usr/bin",
        wanted_by="multi-user.target",
    )

    expected_output = """[Unit]
Description=Test Service

[Service]
User=ubuntu
Group=testgroup
Type=simple
ExecStart=/usr/bin/test
Restart=on-failure
RestartSec=5
WatchdogSec=259200
RuntimeDirectory=git-ubuntu
PrivateTmp=yes
Environment=PATH=/usr/bin

[Install]
WantedBy=multi-user.target"""

    assert result == expected_output


def test_generate_systemd_service_string_5():
    """
    Test generate_systemd_service_string with specific parameter combinations.

    This test verifies the function's behavior when service_restart, restart_sec,
    timeout_start_sec, runtime_dir, private_tmp, environment, and wanted_by are
    provided, but watchdog_sec is not. It ensures that the generated systemd
    service string contains the expected content and structure.
    """
    result = generate_systemd_service_string(
        description="Test Service",
        service_user="ubuntu",
        service_group="testgroup",
        service_type="simple",
        exec_start="/snap/bin/git-ubuntu importer-service-broker tcp://*:1692",
        service_restart="on-failure",
        restart_sec=5,
        timeout_start_sec=259200,
        runtime_dir="git-ubuntu",
        private_tmp=True,
        environment="PATH=/usr/local/bin:/usr/bin:/bin",
        wanted_by="multi-user.target",
    )

    expected_output = """[Unit]
Description=Test Service

[Service]
User=ubuntu
Group=testgroup
Type=simple
ExecStart=/snap/bin/git-ubuntu importer-service-broker tcp://*:1692
Restart=on-failure
RestartSec=5
TimeoutStartSec=259200
RuntimeDirectory=git-ubuntu
PrivateTmp=yes
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target"""

    assert result == expected_output


def test_generate_systemd_service_string_6():
    """
    Test generate_systemd_service_string with specific path constraints.

    This test verifies the function's behavior when service_restart, restart_sec,
    timeout_start_sec, watchdog_sec, private_tmp, environment, and wanted_by are
    provided, while runtime_dir is not provided.
    """
    result = generate_systemd_service_string(
        description="Test Service",
        service_user="ubuntu",
        service_group="testgroup",
        service_type="simple",
        exec_start="/snap/bin/git-ubuntu importer-service-broker tcp://*:1692",
        service_restart="on-failure",
        restart_sec=5,
        timeout_start_sec=259200,
        watchdog_sec=60,
        private_tmp=True,
        environment="VAR1=value1 VAR2=value2",
        wanted_by="multi-user.target",
    )

    expected_output = """[Unit]
Description=Test Service

[Service]
User=ubuntu
Group=testgroup
Type=simple
ExecStart=/snap/bin/git-ubuntu importer-service-broker tcp://*:1692
Restart=on-failure
RestartSec=5
TimeoutStartSec=259200
WatchdogSec=60
PrivateTmp=yes
Environment=VAR1=value1 VAR2=value2

[Install]
WantedBy=multi-user.target"""

    assert result == expected_output


def test_generate_systemd_service_string_7():
    """
    Test generate_systemd_service_string with all optional parameters set.

    This test verifies that the function correctly generates a systemd service string
    when all optional parameters are provided, including service_restart, restart_sec,
    timeout_start_sec, watchdog_sec, runtime_dir, private_tmp (set to False),
    environment, and wanted_by.
    """
    result = generate_systemd_service_string(
        description="Test Service",
        service_user="ubuntu",
        service_group="testgroup",
        service_type="simple",
        exec_start="/snap/bin/git-ubuntu importer-service-broker tcp://*:1692",
        service_restart="always",
        restart_sec=10,
        timeout_start_sec=60,
        watchdog_sec=259200,
        runtime_dir="git-ubuntu",
        private_tmp=False,
        environment="TEST_VAR=test_value",
        wanted_by="multi-user.target",
    )

    expected = """[Unit]
Description=Test Service

[Service]
User=ubuntu
Group=testgroup
Type=simple
ExecStart=/snap/bin/git-ubuntu importer-service-broker tcp://*:1692
Restart=always
RestartSec=10
TimeoutStartSec=60
WatchdogSec=259200
RuntimeDirectory=git-ubuntu
PrivateTmp=no
Environment=TEST_VAR=test_value

[Install]
WantedBy=multi-user.target"""

    assert result == expected


def test_generate_systemd_service_string_8():
    """
    Test generate_systemd_service_string with all optional parameters except private_tmp.

    This test verifies that the function correctly generates a systemd service string
    when all optional parameters are provided except private_tmp, which is left as None.
    The test checks if the generated string includes all the expected service lines
    in the correct order and format.
    """
    result = generate_systemd_service_string(
        description="Test Service",
        service_user="ubuntu",
        service_group="testgroup",
        service_type="simple",
        exec_start="/usr/bin/test",
        service_restart="always",
        restart_sec=5,
        timeout_start_sec=60,
        watchdog_sec=259200,
        runtime_dir="git-ubuntu",
        private_tmp=None,
        environment="PATH=/usr/bin",
        wanted_by="multi-user.target",
    )

    expected_output = """[Unit]
Description=Test Service

[Service]
User=ubuntu
Group=testgroup
Type=simple
ExecStart=/usr/bin/test
Restart=always
RestartSec=5
TimeoutStartSec=60
WatchdogSec=259200
RuntimeDirectory=git-ubuntu
Environment=PATH=/usr/bin

[Install]
WantedBy=multi-user.target"""

    assert result == expected_output


def test_generate_systemd_service_string_9():
    """
    Test generate_systemd_service_string with specific parameters set.

    This test verifies that the function generates the correct systemd service string
    when service_restart, restart_sec, timeout_start_sec, watchdog_sec, runtime_dir,
    private_tmp, and wanted_by are set, while environment is not set.
    """
    result = generate_systemd_service_string(
        description="Test Service",
        service_user="ubuntu",
        service_group="testgroup",
        service_type="simple",
        exec_start="/snap/bin/git-ubuntu importer-service-broker tcp://*:1692",
        service_restart="always",
        restart_sec=10,
        timeout_start_sec=259200,
        watchdog_sec=60,
        runtime_dir="git-ubuntu",
        private_tmp=True,
        environment=None,
        wanted_by="multi-user.target",
    )

    expected_output = (
        "[Unit]\n"
        "Description=Test Service\n"
        "\n"
        "[Service]\n"
        "User=ubuntu\n"
        "Group=testgroup\n"
        "Type=simple\n"
        "ExecStart=/snap/bin/git-ubuntu importer-service-broker tcp://*:1692\n"
        "Restart=always\n"
        "RestartSec=10\n"
        "TimeoutStartSec=259200\n"
        "WatchdogSec=60\n"
        "RuntimeDirectory=git-ubuntu\n"
        "PrivateTmp=yes\n"
        "\n"
        "[Install]\n"
        "WantedBy=multi-user.target"
    )

    assert result == expected_output


def test_generate_systemd_service_string_with_all_optional_parameters():
    """
    Test generate_systemd_service_string with all optional parameters provided.

    This test verifies that the function correctly generates a systemd service string
    when all optional parameters are supplied, including service_restart, restart_sec,
    timeout_start_sec, watchdog_sec, runtime_dir, private_tmp (True), environment,
    and wanted_by.
    """
    result = generate_systemd_service_string(
        description="Test Service",
        service_user="ubuntu",
        service_group="testgroup",
        service_type="simple",
        exec_start="/snap/bin/git-ubuntu importer-service-broker tcp://*:1692",
        service_restart="always",
        restart_sec=5,
        timeout_start_sec=60,
        watchdog_sec=259200,
        runtime_dir="git-ubuntu",
        private_tmp=True,
        environment="PYTHONUNBUFFERED=1",
        wanted_by="multi-user.target",
    )

    expected_output = """[Unit]
Description=Test Service

[Service]
User=ubuntu
Group=testgroup
Type=simple
ExecStart=/snap/bin/git-ubuntu importer-service-broker tcp://*:1692
Restart=always
RestartSec=5
TimeoutStartSec=60
WatchdogSec=259200
RuntimeDirectory=git-ubuntu
PrivateTmp=yes
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target"""

    assert result == expected_output
