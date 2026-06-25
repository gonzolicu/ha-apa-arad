import logging
import json
import re
from typing import Any
from urllib.parse import urljoin

import aiohttp

from .parser import parse_consumption_history, parse_dashboard

_LOGGER = logging.getLogger(__name__)

LOGIN_URL = "https://user.croscloud.com/croscloudpwd/openid"
PORTAL_URL = "https://myarad.croscloud.com/crosweb"
PORTAL_PAGES = (
    "/facturi/index",
    "/facturi/istoric_facturi",
    "/evolutie_consum/index",
    "/index_utilitati/index",
    "/profile/index",
)
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
BODY_RESOURCE_RE = re.compile(
    r'"bodyResource"\s*:\s*"(?P<url>https?:\\?/\\?/[^"]+)"',
    re.IGNORECASE,
)
LAZY_DATA_RE = re.compile(
    r'\\"data\\"\s*:\s*\\"(?P<url>https?:\\\\?/\\\\?/[^"]+?ajaxEndpoint[^"]+?)\\"',
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

    async def _async_get_authenticated_text(self, url: str) -> str:
        """Fetch an authenticated portal resource."""
        async with self.session.get(url, allow_redirects=True) as resp:
            resp.raise_for_status()
            text = await resp.text()
            if not self._is_authenticated(str(resp.url), text):
                raise PermissionError("Apa Arad session expired")
            return text

    @staticmethod
    def _decode_embedded_url(url: str) -> str:
        return url.replace("\\/", "/")

    async def _async_fetch_rendered_page(
        self, path: str
    ) -> tuple[str, list[dict[str, Any]]]:
        """Fetch a CrosWeb page body and any lazy-loaded tabular data."""
        page_url = urljoin(f"{PORTAL_URL}/", path.lstrip("/"))
        page_html = await self._async_get_authenticated_text(page_url)
        fragments = [page_html]
        datasets: list[dict[str, Any]] = []

        body_match = BODY_RESOURCE_RE.search(page_html)
        if not body_match:
            return "\n".join(fragments), datasets

        body_url = self._decode_embedded_url(body_match.group("url"))
        body_text = await self._async_get_authenticated_text(body_url)
        fragments.append(body_text)

        try:
            body_payload = json.loads(body_text)
        except json.JSONDecodeError:
            return "\n".join(fragments), datasets

        body_html = body_payload.get("body")
        if isinstance(body_html, str):
            fragments.append(body_html)

        for match in LAZY_DATA_RE.finditer(body_text):
            data_url = self._decode_embedded_url(match.group("url"))
            data_text = await self._async_get_authenticated_text(data_url)
            try:
                data = json.loads(data_text)
            except json.JSONDecodeError:
                continue
            if isinstance(data, list):
                datasets.extend(item for item in data if isinstance(item, dict))

        return "\n".join(fragments), datasets

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
        await self.async_get_dashboard()

        fragments: list[str] = []
        datasets: list[dict[str, Any]] = []
        for path in PORTAL_PAGES:
            try:
                page_html, page_datasets = await self._async_fetch_rendered_page(path)
            except (aiohttp.ClientError, PermissionError) as err:
                _LOGGER.debug("Unable to fetch Apa Arad page %s: %s", path, err)
                continue
            fragments.append(page_html)
            datasets.extend(page_datasets)

        parsed = parse_dashboard("\n".join(fragments), self._username)
        parsed.update(parse_consumption_history(datasets))
        return parsed

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
