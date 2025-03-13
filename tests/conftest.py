import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--use-real-website",
        action="store_true",
        default=False,
        help="Run tests against the real website"
    )

@pytest.fixture
def use_real_website(request):
    return request.config.getoption("--use-real-website") 