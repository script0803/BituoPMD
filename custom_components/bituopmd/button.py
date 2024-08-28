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
        device_info = {"model": "Unknown Model", "fw_version": "Unknown", "manufacturer": "Unknown", "MCUVersion": "Unknown", "manufacturer": "Unknown", "mcu_version": "Unknown"}

    buttons = []

    sensor_coordinator = hass.data[DOMAIN][entry.entry_id]['sensor_coordinator']
    buttons.append(DataRefreshButton(sensor_coordinator, host_ip, device_info["model"], device_info["fw_version"], device_info["manufacturer"], device_info["mcu_version"]))

    if coordinator.data:
        for field, action in coordinator.data.items():
            if "switch" in field.lower():
                continue  # Skip buttons with 'switch' in the name
            if field == "zero":
                field = "zero_Energy"  # Rename 'zero' to 'zeroenergy'
            buttons.append(BituoButton(coordinator, host_ip, field, action, device_info["model"], device_info["fw_version"], device_info["manufacturer"], device_info["mcu_version"]))

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
                "manufacturer": data.get("Manufactor", "Unknown"),
                "mcu_version": data.get("MCUVersion", "Unknown"),
            }
        except Exception as err:
            raise UpdateFailed(f"Error fetching device info: {err}")

class BituoButton(CoordinatorEntity, ButtonEntity):
    """Representation of a Button."""

    def __init__(self, coordinator, host_ip, field, action, model, fw_version, manufacturer, mcu_version):
        """Initialize the button."""
        super().__init__(coordinator)
        self._field = field
        self._action = action
        self._attr_name = f"{field.replace('_', ' ').title()}"
        self._attr_unique_id = f"{host_ip}_{field}"
        self.entity_id = f"button.{host_ip.replace('.', '_')}_{self.format_field_entity_id(field)}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host_ip)},
            name=f"{model} - {host_ip}",
            manufacturer=manufacturer,
            model=model,
            sw_version=f"S{fw_version}_M{self.format_version(mcu_version)}",
            configuration_url=f"http://{host_ip}"  # embed URL
        )
        self._host_ip = host_ip

    async def async_press(self):
        """Handle the button press."""
        await self.hass.async_add_executor_job(
            requests.get, f"http://{self._host_ip}/{self._action}"
        )
    
    @staticmethod
    def format_field_entity_id(field):
        """Format field name to be more suitable for unique_id."""
        formatted_name = ''.join(['_' + char.lower() if char.isupper() else char for char in field])
        return formatted_name.strip('_')
    
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
    
class DataRefreshButton(CoordinatorEntity, ButtonEntity):
    """Representation of a Data Refresh Button."""

    def __init__(self, coordinator, host_ip, model, fw_version, manufacturer, mcu_version):
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_name = "Data Refresh"
        self._attr_unique_id = f"{host_ip}_data_refresh"
        self.entity_id = f"button.{host_ip.replace('.', '_')}_data_refresh"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host_ip)},
            name=f"{model} - {host_ip}",
            manufacturer=manufacturer,
            model=model,
            sw_version=f"S{fw_version}_M{self.format_version(mcu_version)}",
            configuration_url=f"http://{host_ip}"  # embed URL
        )
        self._host_ip = host_ip
        self._attr_icon = "mdi:refresh"

    async def async_press(self):
        """Handle the button press to refresh data."""
        await self.coordinator.async_request_refresh()

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

# by Script0803