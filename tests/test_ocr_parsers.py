"""Regex/Heuristik-Tests für ``app/ocr/parsers.py``."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.ocr.parsers import (
    parse_address,
    parse_datetime,
    parse_gps,
    parse_nvt_numbers,
    parse_overlay,
)


class TestParseNvtNumbers:
    def test_simple_nvt_with_space(self) -> None:
        assert parse_nvt_numbers("NVT 7107 Hauptstrasse") == ["7107"]

    def test_nvt_with_underscore(self) -> None:
        assert parse_nvt_numbers("NVT_7101.jpg") == ["7101"]

    def test_nvt_with_dash(self) -> None:
        assert parse_nvt_numbers("NVT-7101 Anlage") == ["7101"]

    def test_nvt_concatenated(self) -> None:
        assert parse_nvt_numbers("Info: NVT7101 Standort") == ["7101"]

    def test_netzverteiler_prefix(self) -> None:
        assert parse_nvt_numbers("Netzverteiler 7103 Roxel") == ["7103"]

    def test_case_insensitive(self) -> None:
        assert parse_nvt_numbers("nvt 7107 UND Nvt 7108") == ["7107", "7108"]

    def test_ocr_o_for_zero(self) -> None:
        # "NVT 71O7" (OCR-Verwechsler) wird zu 7107
        assert parse_nvt_numbers("NVT 71O7 Foto") == ["7107"]

    def test_multiple_deduplicated(self) -> None:
        assert parse_nvt_numbers("NVT 7107 auch NVT 7107 nochmal") == ["7107"]

    def test_multiple_different(self) -> None:
        assert parse_nvt_numbers("NVT 7107, NVT 7108") == ["7107", "7108"]

    def test_ignores_bare_numbers(self) -> None:
        # 4-stellige Zahl ohne NVT-Prefix wird NICHT als NVT-Nummer interpretiert
        assert parse_nvt_numbers("48161 Muenster 7107 Foto") == []

    def test_no_match(self) -> None:
        assert parse_nvt_numbers("nur ganz normaler Text") == []


class TestParseAddress:
    def test_full_address(self) -> None:
        street, hn, plz, city = parse_address("Roxeler Straße 42 48161 Münster")
        assert street == "Roxeler Straße"
        assert hn == "42"
        assert plz == "48161"
        assert city == "Münster"

    def test_house_number_with_letter(self) -> None:
        # Hausnummern mit Buchstaben werden korrekt gelesen, wenn die Straße eine
        # typische Endung hat. Präpositions-Straßen ("Am Sandberg") liegen
        # bewusst außerhalb der Endungsliste und fallen auf None.
        street, hn, _, _ = parse_address("Hauptstraße 12a 48159 Münster")
        assert street == "Hauptstraße"
        assert hn == "12a"

    def test_house_number_range(self) -> None:
        street, hn, _, _ = parse_address("Frankfurter Allee 5-7 60313 Frankfurt am Main")
        assert street == "Frankfurter Allee"
        assert hn == "5-7"

    def test_uppercase(self) -> None:
        street, _, _, city = parse_address("ROXELER STRASSE 42 48161 MÜNSTER")
        assert street == "ROXELER STRASSE"
        assert city == "MÜNSTER"

    def test_only_plz_city(self) -> None:
        # "Frankfurt am Main" muss durchgehen → wir kappen erst nach 4 Wörtern.
        # Ein einzelnes Wort nach dem Ortsnamen bleibt daher enthalten und
        # wird vom Reviewer im UI korrigiert.
        street, hn, plz, city = parse_address("Text vorher 48161 Münster, Rest")
        assert street is None
        assert hn is None
        assert plz == "48161"
        assert city == "Münster"

    def test_no_address(self) -> None:
        assert parse_address("kein Overlay-Text hier") == (None, None, None, None)


class TestParseGps:
    def test_decimal_dot(self) -> None:
        assert parse_gps("GPS: 51.965432, 7.517890") == (
            Decimal("51.965432"),
            Decimal("7.517890"),
        )

    def test_labeled_hemispheres(self) -> None:
        result = parse_gps("N 51,965° E 7,517°")
        assert result is not None
        lat, lon = result
        assert lat == Decimal("51.965")
        assert lon == Decimal("7.517")

    def test_south_and_west_negative(self) -> None:
        result = parse_gps("S 33.865, W 151.209")
        assert result is not None
        lat, lon = result
        assert lat == Decimal("-33.865")
        assert lon == Decimal("-151.209")

    def test_no_gps(self) -> None:
        assert parse_gps("keine Koordinaten hier") is None

    def test_invalid_range_rejected(self) -> None:
        # 200° Latitude ist Unfug, aber der Parser prüft nur Grundgrenzen
        assert parse_gps("Text 200.0, 7.5 mehr") is None


class TestParseDatetime:
    def test_german_date_only(self) -> None:
        dt = parse_datetime("Foto vom 13.08.2026 unterwegs")
        assert dt is not None
        assert dt.year == 2026 and dt.month == 8 and dt.day == 13

    def test_german_date_time(self) -> None:
        dt = parse_datetime("13.08.2026 14:32:15")
        assert dt is not None
        assert dt.hour == 14 and dt.minute == 32 and dt.second == 15

    def test_iso_date(self) -> None:
        dt = parse_datetime("2026-08-13T09:15:22Z Rest")
        assert dt is not None
        assert dt.hour == 9 and dt.minute == 15

    def test_invalid_date(self) -> None:
        assert parse_datetime("32.13.2026") is None
        assert parse_datetime("keine Datumangabe") is None


class TestParseOverlay:
    def test_full_overlay(self) -> None:
        r = parse_overlay(
            "NVT 7107 Roxeler Straße 42 48161 Münster 13.08.2026 14:32 "
            "GPS: 51.965432, 7.517890"
        )
        assert r.nvt_number == "7107"
        assert r.street == "Roxeler Straße"
        assert r.house_number == "42"
        assert r.postal_code == "48161"
        assert r.city == "Münster"
        assert r.gps_lat == Decimal("51.965432")
        assert r.captured_at is not None
        assert r.warnings == []
        assert r.has_address is True
        assert r.has_gps is True

    def test_multiple_nvts_warns(self) -> None:
        r = parse_overlay("NVT 7107 und NVT 7108")
        assert r.nvt_number == "7107"
        assert r.nvt_number_candidates == ["7107", "7108"]
        assert len(r.warnings) == 1
        assert "Mehrere NVT" in r.warnings[0]

    def test_empty_input(self) -> None:
        r = parse_overlay("")
        assert r.nvt_number is None
        assert r.has_address is False
        assert r.has_gps is False
        assert r.captured_at is None

    @pytest.mark.parametrize(
        "text",
        [
            "NVT 7101 Hauptstraße 12 48159 Münster",
            "Foto vom 01.02.2026 - NVT_7103 - Musterweg 5",
        ],
    )
    def test_smoke(self, text: str) -> None:
        r = parse_overlay(text)
        assert r.nvt_number is not None
