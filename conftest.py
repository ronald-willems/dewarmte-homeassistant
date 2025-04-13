"""Configure pytest for the DeWarmte API tests."""
import pytest
import pytest_socket

def pytest_addoption(parser):
    """Add command line options."""
    parser.addoption(
        "--use-real-website",
        action="store_true",
        default=False,
        help="Run tests against the real website instead of mocks",
    )

@pytest.fixture(autouse=True)
def socket_enabled(use_real_website):
    """Enable socket connections when using real website."""
    if use_real_website:
        pytest_socket.disable_socket()  # Disable socket blocking to allow real connections
    else:
        pytest_socket.enable_socket()  # Enable socket blocking for mock tests

@pytest.fixture
def use_real_website(request):
    """Fixture to determine if tests should use real website."""
    return request.config.getoption("--use-real-website")

@pytest.fixture
def real_credentials(use_real_website):
    """Fixture to provide real credentials when using real website."""
    if use_real_website:
        import yaml
        try:
            with open("tests/secrets.yaml", "r") as f:
                secrets = yaml.safe_load(f)
                if "dewarmte" in secrets:
                    return secrets["dewarmte"]["username"], secrets["dewarmte"]["password"]
        except Exception as e:
            print(f"Error loading credentials: {e}")
    return None, None 