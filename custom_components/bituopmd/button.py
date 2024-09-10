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
    try:
        response = await hass.async_add_executor_job(
            requests.get, f"http://{host_ip}/data"
        )
        data = response.json()
        device_info = {
            "model": data.get("productModel") or data.get("ProductModel", "Unknown Model"),
            "fw_version": data.get("FWVersion") or data.get("fwVersion", "Unknown"),
            "manufacturer": data.get("Manufactor", "Unknown"),
            "mcu_version": data.get("MCUVersion", "Unknown"),
        }
    except Exception as e:
        _LOGGER.error("Failed to fetch device info for %s: %s", host_ip, e)
        device_info = {
            "model": "Unknown Model",
            "fw_version": "Unknown",
            "manufacturer": "Unknown",
            "mcu_version": "Unknown",
        }

    sensor_coordinator = hass.data[DOMAIN][entry.entry_id]['sensor_coordinator']

    buttons = [
        DataRefreshButton(sensor_coordinator, host_ip, device_info["model"], device_info["fw_version"], device_info["manufacturer"], device_info["mcu_version"]),
        DeviceLocatingButton(host_ip, device_info["model"], device_info["fw_version"], device_info["manufacturer"], device_info["mcu_version"])
    ]
    
    async_add_entities(buttons, True)

class DeviceLocatingButton(ButtonEntity):
    """Representation of a Button."""

    def __init__(self, host_ip, model, fw_version, manufacturer, mcu_version):
        """Initialize the button."""
        self._attr_name = "Device Locating"
        self._attr_unique_id = f"{host_ip}_device_locating"
        self.entity_id = f"button.{host_ip.replace('.', '_')}_device_locating"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host_ip)},
            name=f"{model} - {host_ip}",
            manufacturer=manufacturer,
            model=model,
            sw_version=f"S{fw_version}_M{self.format_version(mcu_version)}",
            configuration_url=f"http://{host_ip}"  # embed URL
        )
        self._host_ip = host_ip
        self._attr_icon = "mdi:map-marker"

    async def async_press(self):
        """Handle the button press."""
        await self.hass.async_add_executor_job(
            requests.get, f"http://{self._host_ip}/location"
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