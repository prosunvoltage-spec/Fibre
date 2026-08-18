"""Tests für die Regex-Extraktion aus OCR-Rohtext."""

from __future__ import annotations

from app.ocr.parsers import (
    extract_nvt_from_filename,
    extract_nvt_numbers,
    extract_structured,
)


class TestNvtNumbers:
    def test_basic(self) -> None:
        assert extract_nvt_numbers("NVT 7107") == ["7107"]

    def test_with_dash(self) -> None:
        assert extract_nvt_numbers("NVT-7107") == ["7107"]

    def test_multiple_distinct(self) -> None:
        result = extract_nvt_numbers("NVT 7107 und daneben NVT 7108")
        assert result == ["7107", "7108"]

    def test_duplicate_ignored(self) -> None:
        assert extract_nvt_numbers("NVT 7107 ... NVT 7107 ...") == ["7107"]

    def test_case_insensitive(self) -> None:
        assert extract_nvt_numbers("nvt7107") == ["7107"]

    def test_no_false_positive_on_five_digit(self) -> None:
        # 5-stellige Zahl darf keine NVT-Nummer sein
        assert extract_nvt_numbers("NVT 71070") == []

    def test_from_filename(self) -> None:
        assert extract_nvt_from_filename("NVT_7107.jpg") == "7107"
        assert extract_nvt_from_filename("nvt-7107_01.jpeg") == "7107"
        assert extract_nvt_from_filename("path/to/NVT7107.png") == "7107"

    def test_from_filename_bare_digits(self) -> None:
        assert extract_nvt_from_filename("7107_front.jpg") == "7107"


class TestAddress:
    def test_plz_ort(self) -> None:
        e = extract_structured("Roxel · 48161 Münster · Deutschland")
        assert e.postal_code == "48161"
        assert e.city == "Münster"

    def test_street_and_house(self) -> None:
        e = extract_structured("Roxeler Straße 579\n48161 Münster")
        assert e.street == "Roxeler Straße"
        assert e.house_number == "579"

    def test_street_with_letter(self) -> None:
        e = extract_structured("Lindenstraße 2A, 48161 Münster")
        assert e.street == "Lindenstraße"
        assert e.house_number == "2A"

    def test_street_range(self) -> None:
        e = extract_structured("Schelmenstiege 34-38\n48161 Münster")
        assert e.street == "Schelmenstiege"
        assert e.house_number.replace(" ", "") == "34-38"


class TestGps:
    def test_decimal_degrees(self) -> None:
        e = extract_structured("Foto 51.9488, 7.53963")
        assert e.latitude is not None and abs(e.latitude - 51.9488) < 1e-6
        assert e.longitude is not None and abs(e.longitude - 7.53963) < 1e-6

    def test_comma_decimal(self) -> None:
        e = extract_structured("Position: 51,9488  7,53963")
        assert e.latitude is not None and abs(e.latitude - 51.9488) < 1e-6

    def test_out_of_range_rejected(self) -> None:
        e = extract_structured("Foo 200.0000 300.0000")
        assert e.latitude is None
        assert e.longitude is None


class TestDateTime:
    def test_full(self) -> None:
        e = extract_structured("19.02.2026, 15:01:25")
        assert e.captured_at is not None
        assert e.captured_at.year == 2026
        assert e.captured_at.hour == 15
        assert e.captured_at.second == 25

    def test_without_seconds(self) -> None:
        e = extract_structured("19.02.2026 14:29")
        assert e.captured_at is not None
        assert e.captured_at.minute == 29
        assert e.captured_at.second == 0


class TestRuleplan:
    def test_b2_2(self) -> None:
        e = extract_structured("NVT 7107 - Regelplan B2/2")
        assert e.ruleplan_label == "B2/2"

    def test_vzp1(self) -> None:
        e = extract_structured("Regelplan: VZP1")
        assert e.ruleplan_label == "VZP1"


class TestRealSnippets:
    """Rohtexte, die aus echten Roxel-NVT-Fotos stammen."""

    def test_nvt_7107(self) -> None:
        raw = (
            "E Roxel, NVT ...02.2026.pdf\n\n"
            "NVT 7107 - Regelplan B2/2 ge a\n\n"
            "Standort Einblasbudli inkl\n\nEinblasgerätschaft\n"
        )
        e = extract_structured(raw)
        assert e.nvt_numbers == ["7107"]
        assert e.ruleplan_label == "B2/2"
