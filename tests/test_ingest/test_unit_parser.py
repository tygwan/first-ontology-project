"""Tests for bimkg.ingest.unit_parser.

Test cases are drawn from actual value patterns observed in the
2026-04-07 DXTnavis snapshot (sampled via SQLite raw_properties_json).
"""

from __future__ import annotations

import math

import pytest

from bimkg.ingest.unit_parser import (
    parse_length,
    parse_npd,
    parse_pressure,
    parse_temperature,
    parse_weight,
)


def approx(expected: float, rel: float = 1e-4) -> pytest.approx:
    return pytest.approx(expected, rel=rel)


# ---------- parse_length ----------

class TestParseLength:
    def test_feet_inches_decimal(self) -> None:
        # "21 ft  4.00 in" -> 21*0.3048 + 4*0.0254 = 6.4008 + 0.1016 = 6.5024
        assert parse_length("21 ft  4.00 in") == approx(6.5024)

    def test_feet_inches_integer_zero(self) -> None:
        # "24 ft  0  in" -> 7.3152
        assert parse_length("24 ft  0  in") == approx(7.3152)

    def test_feet_inches_subfoot(self) -> None:
        # "0 ft  9.00 in" -> 0.2286
        assert parse_length("0 ft  9.00 in") == approx(0.2286)

    def test_inches_fractional_half(self) -> None:
        # "2 1/2 in" -> 2.5 * 0.0254 = 0.0635
        assert parse_length("2 1/2 in") == approx(0.0635)

    def test_inches_fractional_large(self) -> None:
        # "17 1/2 in" -> 17.5 * 0.0254 = 0.4445
        assert parse_length("17 1/2 in") == approx(0.4445)

    def test_inches_decimal(self) -> None:
        # "29.53 in" -> 0.75006
        assert parse_length("29.53 in") == approx(0.75006)

    def test_inches_integer(self) -> None:
        # "4 in" -> 0.1016
        assert parse_length("4 in") == approx(0.1016)

    def test_feet_only(self) -> None:
        assert parse_length("21 ft") == approx(6.4008)

    def test_empty_returns_none(self) -> None:
        assert parse_length("") is None
        assert parse_length("   ") is None

    def test_none_returns_none(self) -> None:
        assert parse_length(None) is None

    def test_garbage_returns_none(self) -> None:
        assert parse_length("not a length") is None
        assert parse_length("17 ft  bogus in") is None

    def test_case_insensitive(self) -> None:
        assert parse_length("4 IN") == approx(0.1016)
        assert parse_length("21 FT  4.00 IN") == approx(6.5024)

    def test_leading_dot_inches(self) -> None:
        # "24 ft   .43 in" -> 24*0.3048 + 0.43*0.0254 = 7.3152 + 0.010922
        assert parse_length("24 ft   .43 in") == approx(7.326122, rel=1e-4)

    def test_millimeters(self) -> None:
        assert parse_length("200 mm") == approx(0.200)
        assert parse_length("1500mm") == approx(1.500)


# ---------- parse_weight ----------

class TestParseWeight:
    def test_integer_lbm(self) -> None:
        # "24 lbm" -> 10.8862
        assert parse_weight("24 lbm") == approx(10.8862)

    def test_decimal_lbm(self) -> None:
        # "178.55 lbm" -> 80.989...
        assert parse_weight("178.55 lbm") == approx(80.989, rel=1e-3)

    def test_zero_lbm(self) -> None:
        assert parse_weight("0 lbm") == 0.0

    def test_small_decimal(self) -> None:
        # "8.9 lbm" -> 4.0370
        assert parse_weight("8.9 lbm") == approx(4.0370)

    def test_empty_returns_none(self) -> None:
        assert parse_weight("") is None

    def test_none_returns_none(self) -> None:
        assert parse_weight(None) is None

    def test_garbage_returns_none(self) -> None:
        assert parse_weight("24 kg") is None  # we only accept lbm
        assert parse_weight("not a weight") is None


# ---------- parse_pressure ----------

class TestParsePressure:
    def test_zero_psi(self) -> None:
        assert parse_pressure("0.00 psi") == 0.0

    def test_decimal_psi(self) -> None:
        # "150 psi" -> 1034.21
        assert parse_pressure("150 psi") == approx(1034.21, rel=1e-3)

    def test_empty_returns_none(self) -> None:
        assert parse_pressure("") is None

    def test_none_returns_none(self) -> None:
        assert parse_pressure(None) is None

    def test_garbage_returns_none(self) -> None:
        assert parse_pressure("150 bar") is None


# ---------- parse_temperature ----------

class TestParseTemperature:
    def test_freezing_fahrenheit(self) -> None:
        # 32 F = 0 C
        assert parse_temperature("32 F") == approx(0.0, rel=1e-6) or \
               abs(parse_temperature("32 F")) < 1e-6

    def test_zero_fahrenheit(self) -> None:
        # 0 F = -17.778 C
        assert parse_temperature("0.00 F") == approx(-17.778, rel=1e-3)

    def test_boiling_fahrenheit(self) -> None:
        # 100 F = 37.778 C
        assert parse_temperature("100.00 F") == approx(37.778, rel=1e-3)

    def test_high_fahrenheit(self) -> None:
        # 492.80 F = 256.0 C
        assert parse_temperature("492.80 F") == approx(256.0, rel=1e-3)

    def test_empty_returns_none(self) -> None:
        assert parse_temperature("") is None

    def test_none_returns_none(self) -> None:
        assert parse_temperature(None) is None


# ---------- parse_npd ----------

class TestParseNpd:
    def test_symmetric_integer(self) -> None:
        # "4in x 4in" -> (0.1016, 0.1016)
        result = parse_npd("4in x 4in")
        assert result is not None
        assert result[0] == approx(0.1016)
        assert result[1] == approx(0.1016)

    def test_symmetric_sub_inch(self) -> None:
        # "0.75in x 0.75in" -> (0.01905, 0.01905)
        result = parse_npd("0.75in x 0.75in")
        assert result is not None
        assert result[0] == approx(0.01905)
        assert result[1] == approx(0.01905)

    def test_reducer_zero(self) -> None:
        # "4in x 0" -> (0.1016, 0.0)
        result = parse_npd("4in x 0")
        assert result is not None
        assert result[0] == approx(0.1016)
        assert result[1] == 0.0

    def test_single_value(self) -> None:
        # "4 in" -> (0.1016, 0.1016)
        result = parse_npd("4 in")
        assert result is not None
        assert result[0] == approx(0.1016)
        assert result[1] == approx(0.1016)

    def test_mm_pair(self) -> None:
        # "200mm x 200mm" -> (0.200, 0.200)
        result = parse_npd("200mm x 200mm")
        assert result is not None
        assert result[0] == approx(0.200)
        assert result[1] == approx(0.200)

    def test_empty_returns_none(self) -> None:
        assert parse_npd("") is None

    def test_none_returns_none(self) -> None:
        assert parse_npd(None) is None


# ---------- integration: real sample values should not raise ----------

REAL_SAMPLES_LENGTH = [
    "21 ft  4.00 in", "45 ft  0.00 in", "24 ft  0  in", "4 ft  2.47 in",
    "3 ft  9.09 in", "44 ft  0.00 in", "12 ft  0.00 in", "29.53 in",
    "7 ft  9.91 in", "38 ft  11.69 in", "4 in", "2 in", "7 in", "6 in",
    "8 in", "2 1/2 in", "1 ft  7.69 in", "9 in", "8 1/2 in", "10 in",
    "14 in", "12 in", "18 in", "17 1/2 in", "0 ft  9.00 in",
]

REAL_SAMPLES_WEIGHT = [
    "24 lbm", "15 lbm", "8.9 lbm", "39 lbm", "178.55 lbm", "1.6 lbm",
    "47 lbm", "123 lbm", "3.99 lbm", "3.5 lbm", "226.76 lbm", "0 lbm",
]

REAL_SAMPLES_PRESSURE = ["0.00 psi"]
REAL_SAMPLES_TEMP = ["0.00 F", "100.00 F", "492.80 F", "80.33 F"]
REAL_SAMPLES_NPD = [
    "4in x 4in", "8in x 8in", "6in x 6in", "2in x 2in", "12in x 12in",
    "10in x 10in", "1in x 1in", "3in x 3in", "0.75in x 0.75in", "4in x 0",
]


def test_real_length_samples_all_parse() -> None:
    for s in REAL_SAMPLES_LENGTH:
        result = parse_length(s)
        assert result is not None, f"Failed to parse: {s!r}"
        assert result > 0.0


def test_real_weight_samples_all_parse() -> None:
    for s in REAL_SAMPLES_WEIGHT:
        result = parse_weight(s)
        assert result is not None, f"Failed to parse: {s!r}"
        assert result >= 0.0


def test_real_pressure_samples_all_parse() -> None:
    for s in REAL_SAMPLES_PRESSURE:
        assert parse_pressure(s) is not None


def test_real_temperature_samples_all_parse() -> None:
    for s in REAL_SAMPLES_TEMP:
        result = parse_temperature(s)
        assert result is not None, f"Failed to parse: {s!r}"
        assert math.isfinite(result)


def test_real_npd_samples_all_parse() -> None:
    for s in REAL_SAMPLES_NPD:
        result = parse_npd(s)
        assert result is not None, f"Failed to parse: {s!r}"
