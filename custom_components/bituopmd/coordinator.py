"""Shared data coordinator for Bituo power monitoring devices."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BituoApiClient, BituoApiError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, FAILURE_THRESHOLD
from .helpers import normalize_meter_data

_LOGGER = logging.getLogger(__name__)


class BituoDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate one bounded poll for every entity on a device."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: BituoApiClient,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize the coordinator."""
        self.client = client
        self.supports_switch = False
        self._consecutive_failures = 0
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN}_{client.host}",
            update_interval=timedelta(seconds=scan_interval),
        )

    @property
    def host(self) -> str:
        """Return the configured device address."""
        return self.client.host

    @property
    def device_info_data(self) -> dict[str, str]:
        """Return normalized metadata from the latest payload."""
        data = self.data or {}
        return {
            "model": str(
                data.get("ProductModel") or data.get("productModel") or "Unknown Model"
            ),
            "fw_version": str(
                data.get("FWVersion") or data.get("fwVersion") or "Unknown"
            ),
            "manufacturer": str(
                data.get("Manufactor") or data.get("Manufacturer") or "BITUO TECHNIK"
            ),
            "mcu_version": str(data.get("MCUVersion") or "Unknown"),
            "serial_number": str(data.get("SerialNumber") or ""),
        }

    async def async_detect_capabilities(self) -> None:
        """Probe optional capabilities once without making setup depend on them."""
        if "switchstatus" in (self.data or {}):
            self.supports_switch = True
            return
        try:
            auxiliary = await self.client.async_get_auxiliary_data()
        except BituoApiError as err:
            _LOGGER.debug("Capability probe failed for %s: %s", self.host, err)
            return
        self.supports_switch = "switchstatus" in auxiliary

    def set_scan_interval(self, seconds: int) -> None:
        """Apply a new polling interval without reloading the integration."""
        self.update_interval = timedelta(seconds=seconds)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch and normalize one device snapshot."""
        try:
            data = normalize_meter_data(await self.client.async_get_data())
            if self.supports_switch:
                data["switchstatus"] = await self.client.async_get_switch_state()
        except BituoApiError as err:
            self._consecutive_failures += 1
            if self.data is not None and self._consecutive_failures < FAILURE_THRESHOLD:
                _LOGGER.debug(
                    "Ignoring transient failure %s/%s for %s, keeping last data: %s",
                    self._consecutive_failures,
                    FAILURE_THRESHOLD,
                    self.host,
                    err,
                )
                return self.data
            raise UpdateFailed(
                f"Error communicating with Bituo device {self.host}: {err}"
            ) from err
        self._consecutive_failures = 0
        return data
