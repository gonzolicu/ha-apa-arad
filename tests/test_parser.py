"""Tests for the Apa Arad dashboard parser."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components" / "apa_arad"))

from parser import parse_consumption_history, parse_dashboard  # noqa: E402


class ParserTests(unittest.TestCase):
    def test_extracts_labeled_values(self) -> None:
        html = """
        <div>Nume client: Cata GonZo</div>
        <div>Adresă de consum: Strada Exemplu nr. 10, Arad</div>
        <div>Sold curent: 123,45 RON</div>
        <div>Ultima factură nr. 202603 din 20.06.2026: 87,20 lei</div>
        <div>Consum facturat: 11,5 m³</div>
        <div>Serie contor: ABC-12345</div>
        """

        result = parse_dashboard(html, "user@example.com")

        self.assertEqual(result["username"], "user@example.com")
        self.assertEqual(result["customer_name"], "Cata GonZo")
        self.assertEqual(result["service_address"], "Strada Exemplu nr. 10, Arad")
        self.assertEqual(result["balance"], 123.45)
        self.assertEqual(result["last_invoice"], 87.2)
        self.assertEqual(result["last_invoice_date"], "20.06.2026")
        self.assertEqual(result["consumption_last_period"], 11.5)
        self.assertEqual(result["meter_number"], "ABC-12345")

    def test_does_not_treat_invoice_number_as_amount(self) -> None:
        html = "<div>Factura 202603 emisă la 20.06.2026</div>"

        result = parse_dashboard(html, "user@example.com")

        self.assertIsNone(result["last_invoice"])

    def test_does_not_use_unlabeled_consumption(self) -> None:
        html = "<div>Diametru branșament 2.0 m3</div>"

        result = parse_dashboard(html, "user@example.com")

        self.assertIsNone(result["consumption_last_period"])

    def test_extracts_values_from_real_portal_labels(self) -> None:
        html = """
        <div>Factură FAR0 349140</div>
        <div>Emitere 11.06.2026</div>
        <div>Scadență 26.06.2026</div>
        <div>60,37 Lei</div>
        <div>Plătită</div>
        <div>Îți mulțumim că ești cu facturile la zi.</div>
        <div>Loc consum 67629/11.10.2024 - str PODGORIEI nr 29 ARAD, jud ARAD</div>
        <div>Ultimul index facturat 116</div>
        <div>Serie contor 81683868</div>
        <div>Cod autocitire 189557</div>
        <div>Contract 67629/11.10.2024</div>
        <div>Citire electronică 09.06.2026 116</div>
        <div>Citire electronică 08.05.2026 109</div>
        """

        result = parse_dashboard(html, "user@example.com")

        self.assertEqual(result["balance"], 0)
        self.assertEqual(result["last_invoice"], 60.37)
        self.assertEqual(result["last_invoice_number"], "FAR0 349140")
        self.assertEqual(result["last_invoice_date"], "11.06.2026")
        self.assertEqual(result["last_invoice_due_date"], "26.06.2026")
        self.assertEqual(result["last_invoice_status"], "Plătită")
        self.assertEqual(result["consumption_last_period"], 7)
        self.assertEqual(result["latest_index"], 116)
        self.assertEqual(result["meter_number"], "81683868")
        self.assertEqual(result["self_reading_code"], "189557")
        self.assertEqual(result["contract_number"], "67629/11.10.2024")
        self.assertEqual(
            result["service_address"], "str PODGORIEI nr 29 ARAD, jud ARAD"
        )

    def test_extracts_latest_monthly_consumption(self) -> None:
        rows = [
            {"an": "2026", "luna": "05", "consum": 6.83},
            {"an": "2025", "luna": "12", "consum": 18.74},
            {"an": "2026", "luna": "06", "consum": 1.75},
        ]

        result = parse_consumption_history(rows)

        self.assertEqual(result["consumption_last_period"], 1.75)
        self.assertEqual(result["consumption_period"], "06.2026")


if __name__ == "__main__":
    unittest.main()
