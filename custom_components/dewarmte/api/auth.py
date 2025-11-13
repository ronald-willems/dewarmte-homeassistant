"""Authentication module for DeWarmte."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Tokens appear to expire hourly; refresh proactively a minute before.
DEFAULT_TOKEN_LIFETIME = timedelta(minutes=60)
REFRESH_BUFFER = timedelta(seconds=60)


class DeWarmteAuth:
    """Authentication handler for DeWarmte."""

    def __init__(self, username: str, password: str, session: aiohttp.ClientSession) -> None:
        """Initialize the auth handler."""
        self._username = username
        self._password = password
        self._base_url = "https://api.mydewarmte.com/v1"
        self._session = session
        self._access_token: str | None = None
        self._token_issued_at: datetime | None = None
        self._token_lifetime: timedelta = DEFAULT_TOKEN_LIFETIME

        self._headers = {
            "Accept": "application/json",
            "Accept-Language": "en-US",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Content-Type": "application/json",
            "Origin": "https://mydewarmte.com",
            "Referer": "https://mydewarmte.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:136.0) Gecko/20100101 Firefox/136.0",
            "Authorization": "Bearer null",  # Required for initial login
        }

    async def ensure_token(self, *, force: bool = False, buffer_seconds: int | None = None) -> bool:
        """Ensure a valid token is available, refreshing if needed."""
        if not force and not self.needs_refresh(buffer_seconds=buffer_seconds):
            return True

        try:
            login_url = f"{self._base_url}/auth/token/"
            login_data = {
                "email": self._username,
                "password": self._password,
            }
            _LOGGER.debug("Attempting login with email: %s", self._username)
            async with self._session.post(login_url, json=login_data, headers=self._headers) as response:
                if response.status != 200:
                    _LOGGER.error("Login failed with status %d: %s", response.status, await response.text())
                    return False
                data = await response.json()
                token = data.get("access")
                if not token:
                    _LOGGER.error("No access token in response")
                    return False

                self._access_token = token
                self._headers["Authorization"] = f"Bearer {token}"
                self._token_issued_at = datetime.now(timezone.utc)
                _LOGGER.debug("Successfully obtained access token")
                return True

        except Exception as err:
            _LOGGER.error("Error during login: %s", str(err))
            _LOGGER.error("Error type: %s", type(err).__name__)
            import traceback

            _LOGGER.error("Traceback: %s", traceback.format_exc())
            return False

    def needs_refresh(self, buffer_seconds: int | None = None) -> bool:
        """Determine whether the token should be refreshed."""
        if self._access_token is None or self._token_issued_at is None:
            return True

        buffer = REFRESH_BUFFER if buffer_seconds is None else timedelta(seconds=buffer_seconds)
        expires_at = self._token_issued_at + self._token_lifetime
        now = datetime.now(timezone.utc)
        return now >= expires_at - buffer

    def mark_expired(self) -> None:
        """Mark the current token as expired so the next call refreshes."""
        self._access_token = None
        self._token_issued_at = None
        self._headers["Authorization"] = "Bearer null"

    @property
    def access_token(self) -> str | None:
        """Get the current access token."""
        return self._access_token

    @property
    def headers(self) -> dict[str, str]:
        """Get the current headers."""
        return self._headers.copy()

    @property
    def base_url(self) -> str:
        """Get the base URL."""
        return self._base_url