"""Pytest configuration file."""
import os
import yaml
import pytest

def load_secrets():
    """Load secrets from the secrets.yaml file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    secrets_path = os.path.join(current_dir, 'tests', 'secrets.yaml')
    print(f"Looking for secrets file at: {secrets_path}")
    if not os.path.exists(secrets_path):
        print(f"Secrets file not found at: {secrets_path}")
        # Try relative path
        secrets_path = 'tests/secrets.yaml'
        if not os.path.exists(secrets_path):
            print(f"Secrets file not found at relative path: {secrets_path}")
            # Try current directory
            secrets_path = 'secrets.yaml'
            if not os.path.exists(secrets_path):
                print(f"Secrets file not found at: {secrets_path}")
                return None, None
    
    print(f"Found secrets file at: {secrets_path}")
    with open(secrets_path, 'r') as f:
        secrets = yaml.safe_load(f)
        print(f"Loaded secrets: {secrets}")
        if not secrets or 'dewarmte' not in secrets:
            print("No dewarmte section found in secrets")
            return None, None
        username = secrets['dewarmte'].get('username')
        password = secrets['dewarmte'].get('password')
        print(f"Found credentials - username: {username}, password: {'*' * len(password) if password else None}")
        return username, password

def pytest_addoption(parser):
    """Add custom pytest options."""
    parser.addoption(
        "--use-real-website",
        action="store_true",
        default=False,
        help="Run tests against the real mydewarmte.com website"
    )
    parser.addoption(
        "--username",
        action="store",
        default=None,
        help="Username for mydewarmte.com when using real website"
    )
    parser.addoption(
        "--password",
        action="store",
        default=None,
        help="Password for mydewarmte.com when using real website"
    )

@pytest.fixture
def use_real_website(request):
    """Get the use_real_website parameter."""
    value = request.config.getoption("--use-real-website")
    print(f"\nuse_real_website option value: {value}")
    return value

@pytest.fixture
def real_credentials(request, use_real_website):
    """Get the real credentials if provided."""
    if not use_real_website:
        print("Not using real website, returning None for credentials")
        return None, None

    # First try command line arguments
    username = request.config.getoption("--username")
    password = request.config.getoption("--password")
    
    print(f"Command line credentials - username: {username}, password: {'*' * len(password) if password else None}")
    
    # If not provided, try secrets file
    if not username or not password:
        print("No command line credentials, trying secrets file")
        username, password = load_secrets()
    
    print(f"Final credentials - username: {username}, password: {'*' * len(password) if password else None}")
    return username, password 