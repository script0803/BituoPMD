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

SCAN_INTERVAL = timedelta(seconds=2)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up switch platform."""
    host_ip = entry.data[CONF_HOST_IP]
    coordinator = BituoDataUpdateCoordinator(hass, host_ip)
    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as e:
        _LOGGER.error("Error initializing switch platform: %s", e)
        raise ConfigEntryNotReady from e

    # Fetch device model and firmware version
    try:
        device_info = await coordinator.fetch_device_info()
    except UpdateFailed:
        _LOGGER.error("Failed to fetch device info for %s", host_ip)
        device_info = {"model": "Unknown Model", "fw_version": "Unknown", "manufacturer": "Unknown", "mcu_version": "Unknown"}

    switches = []
    if coordinator.data and "switchstatus" in coordinator.data:
        switches.append(BituoSwitch(coordinator, host_ip, device_info["model"], device_info["fw_version"], device_info["manufacturer"], device_info["mcu_version"]))

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
            # Fetch data from /hadata
            response = await self.hass.async_add_executor_job(
                requests.get, f"http://{self.host_ip}/hadata"
            )
            data = response.json()

            # Only fetch switch status if 'switchstatus' is in the data
            if "switchstatus" in data:
                status_response = await self.hass.async_add_executor_job(
                    requests.get, f"http://{self.host_ip}/status"
                )
                status = status_response.text.strip().lower() == "true"
                data["switchstatus"] = status

            return data
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
                "manufacturer": data.get("Manufactor", "Unknown"),
                "mcu_version": data.get("MCUVersion", "Unknown"),
            }
        except Exception as err:
            raise UpdateFailed(f"Error fetching device info: {err}")

class BituoSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Switch."""

    def __init__(self, coordinator, host_ip, model, fw_version, manufacturer, mcu_version):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_name = f"{model} - {host_ip}"
        self._attr_unique_id = f"{host_ip}_switch"
        self.entity_id = f"switch.{host_ip.replace('.', '_')}_switch"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host_ip)},
            name=f"{model} - {host_ip}",
            manufacturer=manufacturer,
            model=model,
            sw_version=f"S{fw_version}_M{self.format_version(mcu_version)}",
            configuration_url=f"http://{host_ip}"  # embed URL
        )
        self._host_ip = host_ip
    
    @staticmethod
    def format_version(version):
        if version.lower() == "unknown":
            return version 
        parts = version.split('.')
        formatted_parts = [] 
        for part in parts:
            if part.strip():  # 检查部分是否为空
                try:
                    formatted_parts.append(str(int(part)))
                except ValueError:
                    formatted_parts.append('unknown')
            else:
                formatted_parts.append('unknown')  # 如果部分为空，设置为 'unknown'
        
        formatted_version = '.'.join(formatted_parts)
        return formatted_version

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