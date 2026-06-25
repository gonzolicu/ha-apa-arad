import logging
import re
from typing import Any
from urllib.parse import urljoin

import aiohttp

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
        async with self.session.get(PORTAL_URL) as resp:
            # If redirected to login page or unauthorized, raise for caller to handle
            if resp.status in (401, 403):
                resp.raise_for_status()
            resp.raise_for_status()
            text = await resp.text()
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
        parsed = {
            "balance": None,
            "balance_raw": None,
            "last_invoice": None,
            "last_invoice_date": None,
            "consumption_last_period": None,
            "meter_number": None,
        }

        # Balance: look for 'Sold' or 'sold' followed by amount and optional RON/lei
        import re

        # Normalize whitespace
        norm = re.sub(r"\s+", " ", html)

        m = re.search(r"Sold[:\s]*([0-9\.,]+)\s*(RON|lei|Lei|RON)?", norm, re.IGNORECASE)
        if not m:
            m = re.search(r"Balans?[:\s]*([0-9\.,]+)\s*(RON|lei|Lei|RON)?", norm, re.IGNORECASE)
        if m:
            raw = m.group(1)
            parsed["balance_raw"] = raw
            try:
                parsed["balance"] = float(raw.replace(".", "").replace(",", "."))
            except Exception:
                parsed["balance"] = None

        # Last invoice: amount and date (common labels: Factura)
        m = re.search(r"Factura[^0-9\n]*([0-9\.,]+)\s*(RON|lei|Lei)?", norm, re.IGNORECASE)
        if m:
            raw = m.group(1)
            try:
                parsed["last_invoice"] = float(raw.replace(".", "").replace(",", "."))
            except Exception:
                parsed["last_invoice"] = None

        # Try to find a date near 'Factura' (simple date formats)
        mdate = re.search(r"Factura[^\n\r]{0,100}([0-3]?\d[\.\-/][0-1]?\d[\.\-/][12]\d{3})", html)
        if mdate:
            parsed["last_invoice_date"] = mdate.group(1)

        # Consumption: look for numbers followed by m3
        m = re.search(r"([0-9\.,]+)\s*m3", norm, re.IGNORECASE)
        if m:
            raw = m.group(1)
            try:
                parsed["consumption_last_period"] = float(raw.replace(".", "").replace(",", "."))
            except Exception:
                parsed["consumption_last_period"] = None

        # Meter number: search for 'Contor' or 'Numar contor'
        m = re.search(r"(Contor|Numar contor)[:\s]*([A-Za-z0-9\-]+)", norm, re.IGNORECASE)
        if m:
            parsed["meter_number"] = m.group(2)

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
