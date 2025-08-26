import pytest
import subprocess

from pathlib import Path

import jubilant

@pytest.fixture(scope="module")
def juju(request: pytest.FixtureRequest):
    with jubilant.temp_model() as juju:
        yield juju

        if request.session.testsfailed:
            log = juju.debug_log(limit=1000)
            print(log, end="")


@pytest.fixture(scope="session")
def charm():
    subprocess.check_call(["charmcraft", "pack"])
    # Modify below if you're building for multiple bases or architectures.
    return next(Path(".").glob("*.charm"))
