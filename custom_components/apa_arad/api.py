import logging
import re
from typing import Any
from urllib.parse import urljoin

import aiohttp

from .parser import parse_dashboard

_LOGGER = logging.getLogger(__name__)

LOGIN_URL = "https://user.croscloud.com/croscloudpwd/openid"
PORTAL_URL = "https://myarad.croscloud.com/crosweb"
LOGIN_FORM_RE = re.compile(
    r'<button[^>]+id=["\']submit["\'][^>]+formaction=["\'](?P<action>[^"\']+)["\']',
    re.IGNORECASE,
)
COMMUNITY_RE = re.compile(
    r'<input[^>]+name=["\']selected_community["\'][^>]+value=["\'](?P<value>[^"\']+)["\']',
    re.IGNORECASE,
)
NOTIFICATION_RE = re.compile(
    r'showNotificationMessages\(\{"msg":\[\{"value":"(?P<message>.*?)",\s*"type":"ERROR"',
    re.IGNORECASE,
)


class ApaAradApi:
    """Minimal API client for Compania de Apa Arad portal.

    This client performs a form-based login against the OpenID endpoint
    used by the portal and keeps an aiohttp session with cookies. The
    integration uses the session to poll the main portal page as a
    lightweight health check. If the service offers JSON endpoints in
    the future, this class can be extended to fetch structured data.
    """

    def __init__(self, username: str, password: str, websession: aiohttp.ClientSession | None = None) -> None:
        self._username = username
        self._password = password
        self._external_session = websession is not None
        self.session = websession or aiohttp.ClientSession()

    async def async_login(self) -> bool:
        login_url = LOGIN_URL
        selected_community = "APARAD.MYACCOUNT"

        try:
            async with self.session.get(PORTAL_URL, allow_redirects=True) as resp:
                login_html = await resp.text()
                form_match = LOGIN_FORM_RE.search(login_html)
                if form_match:
                    login_url = urljoin(str(resp.url), form_match.group("action"))

                community_match = COMMUNITY_RE.search(login_html)
                if community_match:
                    selected_community = community_match.group("value")

                _LOGGER.debug("Using login URL: %s", login_url)
        except aiohttp.ClientError as err:
            _LOGGER.debug("Failed to load login form: %s", err)
            return False

        data = {
            "selected_community": selected_community,
            "username": self._username,
            "password": self._password,
            "rememberme": "on",
            "croscloud_pwd": "",
        }

        try:
            async with self.session.post(login_url, data=data, allow_redirects=True) as resp:
                text = await resp.text()
                _LOGGER.debug("Login response status: %s, url: %s", resp.status, resp.url)
                if resp.status >= 400:
                    return False

                error_message = self._extract_login_error(text)
                if error_message:
                    _LOGGER.debug("Login rejected by portal: %s", error_message)
                    return False

                return self._is_authenticated(str(resp.url), text)
        except aiohttp.ClientError as err:
            _LOGGER.debug("Login failed: %s", err)
            return False

    async def async_get_dashboard(self) -> Any:
        """Fetch the portal homepage as a health check.

        Returns parsed information or raw HTML on success, or raises
        exceptions on network errors so callers can handle retries.
        """
        async with self.session.get(PORTAL_URL, allow_redirects=True) as resp:
            resp.raise_for_status()
            text = await resp.text()
            if not self._is_authenticated(str(resp.url), text):
                if not await self.async_login():
                    raise PermissionError("Apa Arad session expired")
                async with self.session.get(PORTAL_URL, allow_redirects=True) as retry:
                    retry.raise_for_status()
                    text = await retry.text()
                    if not self._is_authenticated(str(retry.url), text):
                        raise PermissionError("Apa Arad authentication failed")
            return text

    @staticmethod
    def _is_authenticated(url: str, html: str) -> bool:
        """Return true when the response no longer looks like the login form."""
        if "form-password" in html or "croscloud_pwd" in html:
            return False
        return "myarad.croscloud.com/crosweb" in url or "croswebSession" in html

    @staticmethod
    def _extract_login_error(html: str) -> str | None:
        """Extract the portal login error message when one is present."""
        match = NOTIFICATION_RE.search(html)
        if not match:
            return None
        return match.group("message")

    async def async_close(self) -> None:
        if not self._external_session:
            await self.session.close()

    # --- Higher level parsing helpers ---
    async def async_fetch_parsed_dashboard(self) -> dict:
        """Fetch the dashboard HTML and parse useful values.

        Returns a dictionary with parsed values. Values may be None if not found.
        """
        html = await self.async_get_dashboard()
        return parse_dashboard(html, self._username)

    async def async_request_with_reauth(self, method: str, url: str, **kwargs):
        """Perform a request and re-authenticate once on 401/403."""
        try:
            async with self.session.request(method, url, **kwargs) as resp:
                if resp.status in (401, 403):
                    # try re-login once
                    ok = await self.async_login()
                    if not ok:
                        resp.raise_for_status()
                    async with self.session.request(method, url, **kwargs) as resp2:
                        resp2.raise_for_status()
                        return await resp2.text()
                resp.raise_for_status()
                return await resp.text()
        except aiohttp.ClientError:
            raise
