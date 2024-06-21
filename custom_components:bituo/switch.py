import logging
import requests
from datetime import timedelta
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryNotReady
from .const import DOMAIN, CONF_HOST_IP

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up switch platform."""
    host_ip = entry.data[CONF_HOST_IP]
    coordinator = BituoDataUpdateCoordinator(hass, host_ip)
    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as e:
        _LOGGER.error("Error initializing switch platform: %s", e)
        raise ConfigEntryNotReady from e

    switches = []
    if coordinator.data:
        if "switchstatus" in coordinator.data:
            switches.append(BituoSwitch(coordinator, host_ip))

    async_add_entities(switches, True)

class BituoDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the device."""

    def __init__(self, hass, host_ip):
        """Initialize."""
        self.host_ip = host_ip
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    async def _async_update_data(self):
        """Fetch data from the device."""
        try:
            response = await self.hass.async_add_executor_job(
                requests.get, f"http://{self.host_ip}/hadata"
            )
            return response.json()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

class BituoSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Switch."""

    def __init__(self, coordinator, host_ip):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._host_ip = host_ip
        self._attr_name = "Switch"
        self._attr_unique_id = f"{host_ip}_switch"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host_ip)},
            name=f"Bituo Device - {host_ip}",
            manufacturer="Your Manufacturer",
            model=coordinator.data.get("productModel", "Unknown"),
        )

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self.coordinator.data.get("switchstatus", False)

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self.hass.async_add_executor_job(
            requests.get, f"http://{self._host_ip}/switchon"
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self.hass.async_add_executor_job(
            requests.get, f"http://{self._host_ip}/switchoff"
        )
        await self.coordinator.async_request_refresh()

# by Script0803