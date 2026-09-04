"""Bituo power monitoring device integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BituoApiClient
from .const import (
    CONF_HOST_IP,
    CONF_SCAN_INTERVAL,
    DATA_KEY_ENTRIES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .coordinator import BituoDataUpdateCoordinator
from .frontend import async_setup_frontend

_LOGGER = logging.getLogger(__name__)

PLATFORMS = (Platform.SENSOR, Platform.BUTTON, Platform.SWITCH)

SERVICE_SET_FREQUENCY = "set_frequency"
SERVICE_SET_FREQUENCY_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("frequency"): vol.All(
            vol.Coerce(int),
            vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
        ),
    }
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up shared integration resources."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data.setdefault(DATA_KEY_ENTRIES, {})

    async def async_handle_set_frequency(call: ServiceCall) -> None:
        """Update one device's coordinator interval and persisted options."""
        host = call.data["device_id"]
        frequency = call.data["frequency"]
        entries: dict[str, dict[str, Any]] = domain_data[DATA_KEY_ENTRIES]

        for entry_id, runtime in entries.items():
            coordinator: BituoDataUpdateCoordinator = runtime["coordinator"]
            if coordinator.host != host:
                continue

            coordinator.set_scan_interval(frequency)
            entry = hass.config_entries.async_get_entry(entry_id)
            if entry is not None:
                hass.config_entries.async_update_entry(
                    entry,
                    options={**entry.options, CONF_SCAN_INTERVAL: frequency},
                )
            await coordinator.async_request_refresh()
            return

        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="device_not_found",
            translation_placeholders={"host": host},
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FREQUENCY,
        async_handle_set_frequency,
        schema=SERVICE_SET_FREQUENCY_SCHEMA,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BituoPMD from a config entry."""
    host = entry.data[CONF_HOST_IP]
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    client = BituoApiClient(async_get_clientsession(hass), host)
    coordinator = BituoDataUpdateCoordinator(hass, entry, client, scan_interval)

    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_detect_capabilities()

    info = coordinator.device_info_data
    expected_title = f"{info['model']} - {coordinator.host}"
    if entry.title != expected_title:
        hass.config_entries.async_update_entry(entry, title=expected_title)

    hass.data[DOMAIN][DATA_KEY_ENTRIES][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Keep the vendor settings panel for compatibility, but register it once.
    await async_setup_frontend(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry cleanly."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN][DATA_KEY_ENTRIES].pop(entry.entry_id, None)
    return unload_ok
