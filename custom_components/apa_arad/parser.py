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
    location_input = re.search(
        r"<input\b(?=[^>]*\btitle=['\"]Loc consum['\"])[^>]*"
        r"\bvalue=['\"](?P<value>[^'\"]+)['\"]",
        html,
        re.IGNORECASE,
    )
    location_value = unescape(location_input.group("value")) if location_input else None

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
            r"(?:num[ăa]r(?:ul)?\s+(?:de\s+)?contor|serie\s+contor)"
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
    service_address = _search(
        (
            r"loc\s+consum\s+(?:[A-Z0-9./-]+\s*-\s*)?"
            r"(?P<value>[^|]{5,180}?)(?=\s+\||$)",
            r"(?:adres[ăa](?:\s+(?:de\s+consum|locului\s+de\s+consum))?)"
            r"\s*[:|-]\s*(?P<value>[^|]{5,180}?)(?=\s+\||$)",
        ),
        text,
    )
    if location_value:
        location_parts = re.split(r"\s+-\s+", location_value, maxsplit=1)
        if len(location_parts) == 2:
            service_address = location_parts[1].strip()

    return {
        "username": username,
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


_UNPAID_STATUS_RE = re.compile(r"nepl[ăa]tit|restant", re.IGNORECASE)
_ROW_AMOUNT_KEYS = (
    "rest_de_plata",
    "restdeplata",
    "rest_plata",
    "restplata",
    "suma_restanta",
    "de_plata",
    "deplata",
    "sold",
    "rest",
)


def parse_unpaid_invoices(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Sum the unpaid amounts from invoice tables, when the portal provides them.

    Only column names are kept for diagnostics, never values.
    """
    found = False
    total = 0.0
    count = 0
    for row in rows:
        lowered = {str(key).lower(): value for key, value in row.items()}
        amount = None
        for key, value in lowered.items():
            if any(key == name or key.endswith("_" + name) for name in _ROW_AMOUNT_KEYS):
                amount = _number(str(value))
                if amount is not None:
                    break
        if amount is None:
            continue
        found = True
        if amount > 0.009:
            total += amount
            count += 1
    keys = sorted({",".join(sorted(str(k) for k in row.keys()))[:200] for row in rows})
    return {
        "unpaid_total_table": round(total, 2) if found else None,
        "unpaid_count_table": count if found else None,
        "dataset_keys": keys[:10],
    }


def _portal_date(value: str | None):
    from datetime import datetime

    if not value:
        return None
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError:
        return None


def compute_amount_due(data: dict[str, Any], today) -> dict[str, Any]:
    """Work out what is left to pay and what is overdue.

    The portal "sold" only counts overdue money ("facturile sunt la zi" means 0),
    so an issued but unpaid invoice is added from the invoice table or, failing
    that, from the latest invoice and its status.
    """
    balance = data.get("balance") or 0.0
    table_total = data.get("unpaid_total_table")
    last_invoice = data.get("last_invoice") or 0.0
    last_unpaid = bool(_UNPAID_STATUS_RE.search(data.get("last_invoice_status") or ""))

    if table_total is not None:
        due = table_total
        count = data.get("unpaid_count_table") or 0
        source = "tabel facturi"
    elif balance > 0:
        due = balance
        count = 1
        source = "sold portal"
    elif last_unpaid and last_invoice > 0:
        due = last_invoice
        count = 1
        source = "ultima factură"
    else:
        due = 0.0
        count = 0
        source = "la zi"

    due_date = _portal_date(data.get("last_invoice_due_date"))
    overdue = 0.0
    if due > 0 and due_date is not None and due_date < today:
        overdue = due

    return {
        "amount_due": round(due, 2),
        "amount_overdue": round(overdue, 2),
        "unpaid_count": count,
        "amount_due_source": source,
    }
