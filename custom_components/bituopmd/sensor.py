"""Sensor platform for Bituo power monitoring devices."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfReactivePower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from packaging.version import InvalidVersion, Version

from .const import CONF_HOST_IP, CONF_IDENTITY_HOST, DATA_KEY_ENTRIES, DOMAIN
from .coordinator import BituoDataUpdateCoordinator
from .entity import BituoEntity
from .helpers import format_field_entity_id, format_field_name

EXCLUDED_FIELDS = {
    "Post",
    "Time",
    "Config485",
    "MqttStatus",
    "MQTTStatus",
    "ProductModel",
    "productModel",
    "IP",
    "SerialNumber",
    "DeviceType",
    "FWVersion",
    "fwVersion",
    "MCUVersion",
    "Manufactor",
    "Manufacturer",
    "switchstatus",
}

UNIT_MAPPING = (
    ("unbalancelinecurrents", PERCENTAGE),
    ("powerfactor", None),
    ("voltage", UnitOfElectricPotential.VOLT),
    ("current", UnitOfElectricCurrent.AMPERE),
    ("energy", UnitOfEnergy.KILO_WATT_HOUR),
    ("apparentpower", UnitOfApparentPower.VOLT_AMPERE),
    ("reactivepower", UnitOfReactivePower.VOLT_AMPERE_REACTIVE),
    ("activepower", UnitOfPower.WATT),
    ("frequency", UnitOfFrequency.HERTZ),
    ("rssi", SIGNAL_STRENGTH_DECIBELS_MILLIWATT),
)


def _coerce_native_value(value: Any) -> Any:
    """Return numeric strings as numbers while preserving real text states."""
    if not isinstance(value, str):
        return value
    try:
        number = float(value)
    except ValueError:
        return value
    return int(number) if number.is_integer() else number


def _unit_for_field(field: str) -> str | None:
    normalized = field.lower()
    for keyword, unit in UNIT_MAPPING:
        if keyword in normalized:
            return unit
    return None


def _device_class_for_field(field: str) -> SensorDeviceClass | None:
    normalized = field.lower()
    if "unbalancelinecurrents" in normalized:
        return None
    if "powerfactor" in normalized:
        return SensorDeviceClass.POWER_FACTOR
    if "reactivepower" in normalized:
        return SensorDeviceClass.REACTIVE_POWER
    if "apparentpower" in normalized:
        return SensorDeviceClass.APPARENT_POWER
    if "activepower" in normalized:
        return SensorDeviceClass.POWER
    if "energy" in normalized:
        return SensorDeviceClass.ENERGY
    if "current" in normalized:
        return SensorDeviceClass.CURRENT
    if "voltage" in normalized:
        return SensorDeviceClass.VOLTAGE
    if "frequency" in normalized:
        return SensorDeviceClass.FREQUENCY
    if "rssi" in normalized:
        return SensorDeviceClass.SIGNAL_STRENGTH
    return None


def _state_class_for_field(field: str) -> SensorStateClass | None:
    normalized = field.lower()
    if "energy" in normalized:
        return SensorStateClass.TOTAL_INCREASING
    if any(
        keyword in normalized
        for keyword in (
            "voltage",
            "current",
            "power",
            "frequency",
            "rssi",
            "unbalance",
        )
    ):
        return SensorStateClass.MEASUREMENT
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up all fields from the shared device snapshot."""
    coordinator: BituoDataUpdateCoordinator = hass.data[DOMAIN][DATA_KEY_ENTRIES][
        entry.entry_id
    ]["coordinator"]
    identity_host = entry.data.get(CONF_IDENTITY_HOST, entry.data[CONF_HOST_IP])
    ota_versions = await hass.async_add_executor_job(_load_ota_versions)

    entities: list[SensorEntity] = [
        BituoSensor(coordinator, identity_host, field)
        for field in coordinator.data
        if field not in EXCLUDED_FIELDS
    ]
    entities.append(BituoOTASensor(coordinator, identity_host, ota_versions))
    async_add_entities(entities)


class BituoSensor(BituoEntity, SensorEntity):
    """Representation of one field in the Bituo payload."""

    def __init__(
        self,
        coordinator: BituoDataUpdateCoordinator,
        identity_host: str,
        field: str,
    ) -> None:
        """Initialize a metering sensor without changing its unique ID."""
        super().__init__(coordinator, identity_host)
        self._field = field
        self._attr_name = format_field_name(field)
        self._attr_unique_id = f"{identity_host}_{field}"
        self.entity_id = (
            f"sensor.{identity_host.replace('.', '_')}_{format_field_entity_id(field)}"
        )
        self._attr_native_unit_of_measurement = _unit_for_field(field)
        self._attr_device_class = _device_class_for_field(field)
        self._attr_state_class = _state_class_for_field(field)

        normalized = field.lower()
        if any(
            keyword in normalized
            for keyword in ("activepower", "apparentpower", "reactivepower")
        ):
            self._attr_suggested_display_precision = 0
        elif "energy" in normalized:
            self._attr_suggested_display_precision = 2
        elif "voltage" in normalized:
            self._attr_suggested_display_precision = 1
        elif "current" in normalized:
            self._attr_suggested_display_precision = 3
        elif "unbalancelinecurrents" in normalized:
            self._attr_suggested_display_precision = 0

        if normalized in {"rssi", "tp"}:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Any:
        """Return None for a missing field instead of fabricating zero."""
        value = self.coordinator.data.get(self._field)
        return None if value is None else _coerce_native_value(value)


class BituoOTASensor(BituoEntity, SensorEntity):
    """Compatibility sensor comparing firmware to bundled vendor metadata."""

    _attr_icon = "mdi:update"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: BituoDataUpdateCoordinator,
        identity_host: str,
        ota_versions: dict[str, str],
    ) -> None:
        """Initialize the OTA status sensor with the upstream unique ID."""
        super().__init__(coordinator, identity_host)
        self._ota_versions = ota_versions
        self._attr_name = "OTA Status"
        self._attr_unique_id = f"{identity_host}_ota_status"
        self.entity_id = f"sensor.{identity_host.replace('.', '_')}_ota_status"

    @property
    def native_value(self) -> str:
        """Return the firmware comparison result without another HTTP poll."""
        info = self.coordinator.device_info_data
        current = info["fw_version"]
        try:
            current_version = Version(current)
            if current_version.major >= 4:
                latest = self._ota_versions.get("common")
            else:
                latest = self._ota_versions.get(info["model"])
            if not latest:
                return "Unknown"
            return (
                "OTA Available" if current_version < Version(latest) else "Up to Date"
            )
        except InvalidVersion:
            return "Unknown"


def _load_ota_versions() -> dict[str, str]:
    """Load static OTA metadata from the integration package."""
    try:
        with (
            Path(__file__)
            .with_name("ota_versions.json")
            .open(encoding="utf-8") as file_handle
        ):
            payload = json.load(file_handle)
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}
