"""Pure helpers shared by the BituoPMD integration and its tests."""

from __future__ import annotations

import re
from statistics import fmean
from typing import Any

PHASES = ("X", "Y", "Z")


def number(value: Any) -> float | int | None:
    """Convert a device value to a number when possible."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (float, int)):
        return value
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _derived_sum(data: dict[str, Any], prefix: str) -> float | None:
    """Return the sum of three phase values when all are available."""
    values = [number(data.get(f"{prefix}{phase}")) for phase in PHASES]
    if any(value is None for value in values):
        return None
    return sum(value for value in values if value is not None)


def _derived_average(data: dict[str, Any], prefix: str) -> float | None:
    """Return the average of three phase values when all are available."""
    values = [number(data.get(f"{prefix}{phase}")) for phase in PHASES]
    if any(value is None for value in values):
        return None
    return fmean(value for value in values if value is not None)


def normalize_meter_data(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize units and restore useful totals removed by newer firmware."""
    data = dict(payload)

    # Firmware reports active/reactive/apparent power in kW/kvar/kVA.
    # Home Assistant power device classes use W/var/VA.
    for key, value in tuple(data.items()):
        key_lower = key.lower()
        if "power" not in key_lower or "factor" in key_lower:
            continue
        numeric = number(value)
        if numeric is not None:
            data[key] = numeric * 1000

    derived_values = {
        "TotalCurrent": _derived_sum(data, "Current"),
        "AverageLineCurrent": _derived_average(data, "Current"),
        "AverageVoltageLN": _derived_average(data, "Voltage"),
        "TotalActivePower": _derived_sum(data, "ActivePower"),
        "TotalReactivePower": _derived_sum(data, "ReactivePower"),
        "TotalApparentPower": _derived_sum(data, "ApparentPower"),
        "TotalForwardEnergy": _derived_sum(data, "ForwardEnergy"),
        "TotalReverseEnergy": _derived_sum(data, "ReverseEnergy"),
    }
    for key, value in derived_values.items():
        if value is not None and key not in data:
            data[key] = value

    # Per-phase and overall total energy, from native or derived
    # forward/reverse figures. Firmware-provided values always win.
    for phase in PHASES:
        key = f"TotalEnergy{phase}"
        if key in data:
            continue
        forward = number(data.get(f"ForwardEnergy{phase}"))
        reverse = number(data.get(f"ReverseEnergy{phase}"))
        if forward is not None and reverse is not None:
            data[key] = forward + reverse

    if "TotalEnergy" not in data:
        forward = number(data.get("TotalForwardEnergy"))
        reverse = number(data.get("TotalReverseEnergy"))
        if forward is not None and reverse is not None:
            data["TotalEnergy"] = forward + reverse

    return data


def format_field_entity_id(field: str) -> str:
    """Format a device field exactly like upstream V1.0.4."""
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", field).lower()
    return re.sub(r"_+", "_", value).strip("_")


def format_field_name(field: str) -> str:
    """Turn a camel-case device field into a readable entity name."""
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", field)
    return value.replace("_", " ").strip().title()
