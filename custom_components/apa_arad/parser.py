"""Helpers for extracting account data from the Apa Arad portal."""

from __future__ import annotations

from html import unescape
import re
from typing import Any

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
_AMOUNT = r"[-+]?\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2})|[-+]?\d+(?:[.,]\d{1,2})?"
_DATE = r"\d{1,2}[./-]\d{1,2}[./-]\d{4}"
_TOKEN_RE = re.compile(
    r"(?:eyJ|[A-Za-z0-9_-]{30,}\.)[A-Za-z0-9_.-]{40,}",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")


def _text_from_html(html: str) -> str:
    """Return normalized readable text while preserving field separation."""
    text = re.sub(r"</(?:div|p|li|tr|td|th|section|article|h[1-6])>", " | ", html, flags=re.I)
    text = _TAG_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", unescape(text)).strip()


def _number(value: str) -> float | None:
    """Parse common Romanian and international number formats."""
    value = value.replace("\xa0", "").replace(" ", "")
    if not value:
        return None

    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    elif value.count(".") > 1:
        value = value.replace(".", "")

    try:
        return float(value)
    except ValueError:
        return None


def _search(patterns: tuple[str, ...], text: str, group: str = "value") -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(group).strip(" :-|")
    return None


def _debug_contexts(text: str) -> list[str]:
    """Return short contexts useful for adapting the parser to portal changes."""
    contexts: list[str] = []
    for label in (
        "sold",
        "factur",
        "consum",
        "index",
        "contor",
        "loc consum",
        "adres",
    ):
        match = re.search(label, text, re.IGNORECASE)
        if match:
            start = max(0, match.start() - 60)
            end = min(len(text), match.end() + 180)
            context = _TOKEN_RE.sub("<redacted_token>", text[start:end])
            context = _EMAIL_RE.sub("<redacted_email>", context)
            contexts.append(context)
    return contexts


def parse_dashboard(html: str, username: str) -> dict[str, Any]:
    """Extract supported values from dashboard HTML."""
    text = _text_from_html(html)

    balance_raw = _search(
        (
            rf"(?:sold(?:\s+(?:curent|restant|de\s+plat[ăa]))?|total\s+de\s+plat[ăa])"
            rf".{{0,100}}?(?P<value>{_AMOUNT})\s*(?:RON|LEI)\b",
        ),
        text,
    )
    if balance_raw is None and re.search(
        r"facturile\s+(?:sunt\s+)?la\s+zi", text, re.IGNORECASE
    ):
        balance_raw = "0"

    invoice_raw = _search(
        (
            rf"factur[ăa]\s+[A-Z0-9 /.-]+"
            rf".{{0,250}}?(?P<value>{_AMOUNT})\s*(?:RON|LEI)\b",
            rf"(?:ultima\s+factur[ăa]|factur[ăa])"
            rf".{{0,250}}?(?P<value>{_AMOUNT})\s*(?:RON|LEI)\b",
        ),
        text,
    )
    invoice_number = _search(
        (
            r"factur[ăa]\s+(?P<value>[A-Z]{2,}\d*\s+\d+)",
        ),
        text,
    )
    invoice_date = _search(
        (
            rf"factur[ăa].{{0,180}}?emitere\s+(?P<value>{_DATE})",
            rf"(?:ultima\s+factur[ăa]|factur[ăa]).{{0,180}}?(?P<value>{_DATE})",
            rf"(?P<value>{_DATE}).{{0,100}}?(?:ultima\s+factur[ăa]|factur[ăa])",
        ),
        text,
    )
    invoice_due_date = _search(
        (
            rf"scaden[țt][ăa]\s+(?P<value>{_DATE})",
        ),
        text,
    )
    invoice_status = _search(
        (
            r"\b(?P<value>pl[ăa]tit[ăa]|nepl[ăa]tit[ăa]|restant[ăa])\b",
        ),
        text,
    )
    consumption_raw = _search(
        (
            rf"(?:consum(?:ul)?(?:\s+(?:ultimei\s+perioade|curent|facturat))?)"
            rf".{{0,120}}?(?P<value>{_AMOUNT})\s*m(?:³|3)\b",
            rf"(?P<value>{_AMOUNT})\s*m(?:³|3)\b.{{0,80}}?consum",
        ),
        text,
    )
    latest_index_raw = _search(
        (
            rf"ultimul\s+index\s+facturat\s+(?P<value>{_AMOUNT})\b",
        ),
        text,
    )
    reading_matches = re.findall(
        rf"citire\s+electronic[ăa]\s+{_DATE}\s+(?P<value>{_AMOUNT})\b",
        text,
        re.IGNORECASE,
    )
    if latest_index_raw is None and reading_matches:
        latest_index_raw = reading_matches[0]

    if consumption_raw is None and len(reading_matches) >= 2:
        latest_reading = _number(reading_matches[0])
        previous_reading = _number(reading_matches[1])
        if (
            latest_reading is not None
            and previous_reading is not None
            and latest_reading >= previous_reading
        ):
            consumption_raw = str(latest_reading - previous_reading)

    meter_number = _search(
        (
            r"(?:num[ăa]r(?:ul)?\s+(?:de\s+)?contor|serie\s+contor|contor)"
            r".{0,60}?(?P<value>[A-Z0-9][A-Z0-9./-]{3,})",
        ),
        text,
    )
    self_reading_code = _search(
        (
            r"cod\s+autocitire\s+(?P<value>\d+)",
        ),
        text,
    )
    contract_number = _search(
        (
            r"contract\s+(?P<value>[A-Z0-9./-]+)",
        ),
        text,
    )
    customer_name = _search(
        (
            r"(?:nume\s+(?:client|titular)|client|titular)"
            r"\s*[:|-]\s*(?P<value>[^|]{3,100}?)(?=\s+\||$)",
        ),
        text,
    )
    service_address = _search(
        (
            r"loc\s+consum\s+(?:[A-Z0-9./-]+\s*-\s*)?"
            r"(?P<value>[^|]{5,180}?)(?=\s+\||$)",
            r"(?:adres[ăa](?:\s+(?:de\s+consum|locului\s+de\s+consum))?)"
            r"\s*[:|-]\s*(?P<value>[^|]{5,180}?)(?=\s+\||$)",
        ),
        text,
    )

    return {
        "username": username,
        "customer_name": customer_name,
        "service_address": service_address,
        "balance": _number(balance_raw) if balance_raw else None,
        "balance_raw": balance_raw,
        "last_invoice": _number(invoice_raw) if invoice_raw else None,
        "last_invoice_number": invoice_number,
        "last_invoice_date": invoice_date,
        "last_invoice_due_date": invoice_due_date,
        "last_invoice_status": invoice_status,
        "consumption_last_period": _number(consumption_raw) if consumption_raw else None,
        "latest_index": _number(latest_index_raw) if latest_index_raw else None,
        "meter_number": meter_number,
        "self_reading_code": self_reading_code,
        "contract_number": contract_number,
        "parser_debug": _debug_contexts(text),
    }


def parse_consumption_history(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the latest monthly consumption from portal chart rows."""
    valid_rows = [
        row
        for row in rows
        if str(row.get("an", "")).isdigit()
        and str(row.get("luna", "")).isdigit()
        and _number(str(row.get("consum", ""))) is not None
    ]
    if not valid_rows:
        return {}

    latest = max(valid_rows, key=lambda row: (int(row["an"]), int(row["luna"])))
    return {
        "consumption_last_period": _number(str(latest["consum"])),
        "consumption_period": f"{int(latest['luna']):02d}.{latest['an']}",
    }
