import logging
import requests
from datetime import timedelta
from homeassistant.components.button import ButtonEntity
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
    """Set up button platform."""
    host_ip = entry.data[CONF_HOST_IP]
    coordinator = BituoDataUpdateCoordinator(hass, host_ip)
    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as e:
        _LOGGER.error("Error initializing button platform: %s", e)
        raise ConfigEntryNotReady from e

    # Fetch device model and firmware version
    try:
        device_info = await coordinator.fetch_device_info()
    except UpdateFailed:
        _LOGGER.error("Failed to fetch device info for %s", host_ip)
        device_info = {"model": "Unknown Model", "fw_version": "Unknown"}

    buttons = []
    if coordinator.data:
        for field, action in coordinator.data.items():
            if "switch" in field.lower():
                continue  # Skip buttons with 'switch' in the name
            if field == "zero":
                field = "zero_Energy"  # Rename 'zero' to 'zeroenergy'
            buttons.append(BituoButton(coordinator, host_ip, field, action, device_info["model"], device_info["fw_version"]))

    async_add_entities(buttons, True)

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
    
    async def fetch_device_info(self):
        """Fetch device model and firmware version information."""
        try:
            response = await self.hass.async_add_executor_job(
                requests.get, f"http://{self.host_ip}/data"
            )
            data = response.json()
            return {
                "model": data.get("productModel") or data.get("ProductModel", "Unknown Model"),
                "fw_version": data.get("FWVersion") or data.get("fwVersion", "Unknown"),
            }
        except Exception as err:
            raise UpdateFailed(f"Error fetching device info: {err}")

class BituoButton(CoordinatorEntity, ButtonEntity):
    """Representation of a Button."""

    def __init__(self, coordinator, host_ip, field, action, model, fw_version):
        """Initialize the button."""
        super().__init__(coordinator)
        self._field = field
        self._action = action
        self._attr_name = f"{field.replace('_', ' ').title()}"
        self._attr_unique_id = f"{host_ip}_{field}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host_ip)},
            name=f"{model} - {host_ip}",
            manufacturer="BituoTechnik",
            model=model,
            sw_version=fw_version,
        )
        self._host_ip = host_ip

    async def async_press(self):
        """Handle the button press."""
        await self.hass.async_add_executor_job(
            requests.get, f"http://{self._host_ip}/{self._action}"
        )

# by Script0803