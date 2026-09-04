"""Shared entities for the BituoPMD integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BituoDataUpdateCoordinator


def format_version(value: str) -> str:
    """Normalize the vendor's zero-padded MCU version."""
    if not value or value.lower() == "unknown":
        return "Unknown"
    parts: list[str] = []
    for part in value.split("."):
        try:
            parts.append(str(int(part)))
        except ValueError:
            parts.append(part or "unknown")
    return ".".join(parts)


class BituoEntity(CoordinatorEntity[BituoDataUpdateCoordinator]):
    """Base class that preserves the upstream device identity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BituoDataUpdateCoordinator,
        identity_host: str,
    ) -> None:
        """Initialize a Bituo entity."""
        super().__init__(coordinator)
        info = coordinator.device_info_data
        serial_number = info["serial_number"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identity_host)},
            name=f"{info['model']} - {coordinator.host}",
            manufacturer=info["manufacturer"],
            model=info["model"],
            serial_number=serial_number or None,
            sw_version=(
                f"S{info['fw_version']}_M{format_version(info['mcu_version'])}"
            ),
            configuration_url=f"http://{coordinator.host}",
        )
