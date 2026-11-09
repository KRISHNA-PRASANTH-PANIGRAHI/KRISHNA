"""Keep each test's temporary rate window isolated from other tests."""
import pytest
from classguard.security import request_limits


@pytest.fixture(autouse=True)
def isolated_request_limits():
    request_limits.reset()
    yield
    request_limits.reset()
