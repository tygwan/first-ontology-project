"""Parse SP3D string property values to SI units.

SP3D exports physical quantities as strings with imperial units mixed with
spaces and fractions, e.g.:
    "21 ft  4.00 in"   -> 6.5024 m
    "2 1/2 in"          -> 0.0635 m
    "178.55 lbm"        -> 80.989 kg
    "0.00 psi"          -> 0.0 kPa
    "492.80 F"          -> 256.0 C
    "4in x 6in"         -> (0.1016, 0.1524)  # NPD reducer ends

All parse functions return ``None`` when the input is empty, None, or
unparseable. They never raise on bad input — callers that need strictness
should check for None explicitly.

Reference conversions:
    1 ft  = 0.3048 m
    1 in  = 0.0254 m
    1 lbm = 0.45359237 kg
    1 psi = 6.894757 kPa
    T(C)  = (T(F) - 32) * 5/9
"""

from __future__ import annotations

import re

# Conversion constants
FT_TO_M: float = 0.3048
IN_TO_M: float = 0.0254
MM_TO_M: float = 0.001
LBM_TO_KG: float = 0.45359237
PSI_TO_KPA: float = 6.894757

# Decimal number pattern that allows leading dot: "4", "4.00", ".43", "-4.5"
_NUM = r"-?(?:\d+(?:\.\d+)?|\.\d+)"


def _to_float(s: str) -> float | None:
    """Parse a float, tolerating common formats. Returns None on failure."""
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _parse_inches_token(token: str) -> float | None:
    """Parse an inches token that may contain a fraction.

    Accepts: "4", "4.00", "2 1/2", "17 1/2", "29.53"
    Returns inches as float, or None.
    """
    token = token.strip()
    if not token:
        return None

    # Fractional form: "2 1/2" or "1/2"
    if "/" in token:
        m = re.fullmatch(r"(?:(\d+)\s+)?(\d+)\s*/\s*(\d+)", token)
        if not m:
            return None
        whole = int(m.group(1)) if m.group(1) else 0
        num = int(m.group(2))
        den = int(m.group(3))
        if den == 0:
            return None
        return float(whole) + num / den

    return _to_float(token)


_LENGTH_FT_IN_RE = re.compile(
    rf"^\s*(?P<ft>{_NUM})\s*ft\s+(?P<in>{_NUM}(?:\s+\d+/\d+)?|\d+/\d+)\s*in\s*$",
    re.IGNORECASE,
)
_LENGTH_IN_ONLY_RE = re.compile(
    rf"^\s*(?P<in>{_NUM}(?:\s+\d+/\d+)?|\d+/\d+)\s*in\s*$",
    re.IGNORECASE,
)
_LENGTH_FT_ONLY_RE = re.compile(rf"^\s*(?P<ft>{_NUM})\s*ft\s*$", re.IGNORECASE)
_LENGTH_MM_RE = re.compile(rf"^\s*(?P<mm>{_NUM})\s*mm\s*$", re.IGNORECASE)


def parse_length(value: str | None) -> float | None:
    """Parse a length string to meters.

    Supported formats:
        "21 ft  4.00 in"   -> 6.5024
        "24 ft  0  in"     -> 7.3152
        "0 ft  9.00 in"    -> 0.2286
        "2 1/2 in"          -> 0.0635
        "17 1/2 in"         -> 0.4445
        "29.53 in"          -> 0.7500
        "4 in"              -> 0.1016
        "21 ft"             -> 6.4008
        ""                  -> None
        None                -> None
    """
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None

    # Feet + inches: "21 ft  4.00 in", "2 ft  1/2 in"
    m = _LENGTH_FT_IN_RE.match(s)
    if m:
        ft = _to_float(m.group("ft"))
        inches = _parse_inches_token(m.group("in"))
        if ft is None or inches is None:
            return None
        return ft * FT_TO_M + inches * IN_TO_M

    # Inches only: "29.53 in", "4 in", "2 1/2 in"
    m = _LENGTH_IN_ONLY_RE.match(s)
    if m:
        inches = _parse_inches_token(m.group("in"))
        if inches is None:
            return None
        return inches * IN_TO_M

    # Feet only: "21 ft"
    m = _LENGTH_FT_ONLY_RE.match(s)
    if m:
        ft = _to_float(m.group("ft"))
        if ft is None:
            return None
        return ft * FT_TO_M

    # Millimeters: "200 mm"
    m = _LENGTH_MM_RE.match(s)
    if m:
        mm = _to_float(m.group("mm"))
        if mm is None:
            return None
        return mm * MM_TO_M

    return None


_WEIGHT_LBM_RE = re.compile(r"^\s*(?P<n>-?\d+(?:\.\d+)?)\s*lbm\s*$", re.IGNORECASE)


def parse_weight(value: str | None) -> float | None:
    """Parse a weight string to kilograms.

    Supported formats:
        "24 lbm"     -> 10.886
        "178.55 lbm" -> 80.989
        "0 lbm"      -> 0.0
    """
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None
    m = _WEIGHT_LBM_RE.match(s)
    if not m:
        return None
    lbm = _to_float(m.group("n"))
    if lbm is None:
        return None
    return lbm * LBM_TO_KG


_PRESSURE_PSI_RE = re.compile(r"^\s*(?P<n>-?\d+(?:\.\d+)?)\s*psi\s*$", re.IGNORECASE)


def parse_pressure(value: str | None) -> float | None:
    """Parse a pressure string to kPa.

    Supported formats:
        "0.00 psi"  -> 0.0
        "150 psi"   -> 1034.2
    """
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None
    m = _PRESSURE_PSI_RE.match(s)
    if not m:
        return None
    psi = _to_float(m.group("n"))
    if psi is None:
        return None
    return psi * PSI_TO_KPA


_TEMP_F_RE = re.compile(r"^\s*(?P<n>-?\d+(?:\.\d+)?)\s*F\s*$")


def parse_temperature(value: str | None) -> float | None:
    """Parse a temperature string to degrees Celsius.

    Supported formats:
        "0.00 F"    -> -17.778
        "100.00 F"  -> 37.778
        "492.80 F"  -> 256.0
    """
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None
    m = _TEMP_F_RE.match(s)
    if not m:
        return None
    fahrenheit = _to_float(m.group("n"))
    if fahrenheit is None:
        return None
    return (fahrenheit - 32.0) * 5.0 / 9.0


_NPD_PAIR_IN_RE = re.compile(
    rf"^\s*(?P<a>{_NUM})\s*in\s*x\s*(?P<b>{_NUM})\s*in\s*$",
    re.IGNORECASE,
)
_NPD_PAIR_MM_RE = re.compile(
    rf"^\s*(?P<a>{_NUM})\s*mm\s*x\s*(?P<b>{_NUM})\s*mm\s*$",
    re.IGNORECASE,
)
_NPD_REDUCER_IN_RE = re.compile(
    rf"^\s*(?P<a>{_NUM})\s*in\s*x\s*(?P<b>0)\s*$",
    re.IGNORECASE,
)
_NPD_REDUCER_MM_RE = re.compile(
    rf"^\s*(?P<a>{_NUM})\s*mm\s*x\s*(?P<b>0)\s*$",
    re.IGNORECASE,
)
_NPD_SINGLE_IN_RE = re.compile(rf"^\s*(?P<a>{_NUM})\s*in\s*$", re.IGNORECASE)
_NPD_SINGLE_MM_RE = re.compile(rf"^\s*(?P<a>{_NUM})\s*mm\s*$", re.IGNORECASE)


def parse_npd(value: str | None) -> tuple[float, float] | None:
    """Parse a Nominal Pipe Diameter string to a (end1, end2) meters pair.

    Supported formats:
        "4in x 4in"        -> (0.1016, 0.1016)
        "6in x 6in"        -> (0.1524, 0.1524)
        "0.75in x 0.75in"  -> (0.01905, 0.01905)
        "4in x 0"          -> (0.1016, 0.0)
        "4 in"             -> (0.1016, 0.1016)
        "200mm x 200mm"    -> (0.200, 0.200)
        "200mm"            -> (0.200, 0.200)
    """
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None

    # Inches pair: "4in x 4in"
    m = _NPD_PAIR_IN_RE.match(s)
    if m:
        a = _to_float(m.group("a"))
        b = _to_float(m.group("b"))
        if a is None or b is None:
            return None
        return (a * IN_TO_M, b * IN_TO_M)

    # Millimeters pair: "200mm x 200mm"
    m = _NPD_PAIR_MM_RE.match(s)
    if m:
        a = _to_float(m.group("a"))
        b = _to_float(m.group("b"))
        if a is None or b is None:
            return None
        return (a * MM_TO_M, b * MM_TO_M)

    # Inches reducer with zero: "4in x 0"
    m = _NPD_REDUCER_IN_RE.match(s)
    if m:
        a = _to_float(m.group("a"))
        if a is None:
            return None
        return (a * IN_TO_M, 0.0)

    # Millimeters reducer with zero: "200mm x 0"
    m = _NPD_REDUCER_MM_RE.match(s)
    if m:
        a = _to_float(m.group("a"))
        if a is None:
            return None
        return (a * MM_TO_M, 0.0)

    # Single inches value: "4 in"
    m = _NPD_SINGLE_IN_RE.match(s)
    if m:
        a = _to_float(m.group("a"))
        if a is None:
            return None
        return (a * IN_TO_M, a * IN_TO_M)

    # Single millimeters value: "200 mm"
    m = _NPD_SINGLE_MM_RE.match(s)
    if m:
        a = _to_float(m.group("a"))
        if a is None:
            return None
        return (a * MM_TO_M, a * MM_TO_M)

    return None
