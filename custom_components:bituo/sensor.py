import logging
import requests
from datetime import timedelta
from homeassistant.const import (
    ENERGY_KILO_WATT_HOUR,
    FREQUENCY_HERTZ,
    ELECTRIC_CURRENT_AMPERE,
    ELECTRIC_POTENTIAL_VOLT,
    POWER_KILO_WATT,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from .const import DOMAIN, CONF_HOST_IP

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)

UNIT_MAPPING = {
    "unbalancelinecurrents": PERCENTAGE,
    "powerfactor": None,
    "voltage": ELECTRIC_POTENTIAL_VOLT,
    "current": ELECTRIC_CURRENT_AMPERE,
    "power": POWER_KILO_WATT,
    "energy": ENERGY_KILO_WATT_HOUR,
    "frequency": FREQUENCY_HERTZ,
    "rssi": SIGNAL_STRENGTH_DECIBELS,
}

EXCLUDE_FIELDS = {"post", "Post",  "Config485", "MqttStatus", "productModel", "ProductModel", "Serialnumber", "SerialNumber", "devicetype", "DeviceType", "FWVersion"}
 
async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensor platform."""
    host_ip = entry.data[CONF_HOST_IP]
    coordinator = BituoDataUpdateCoordinator(hass, host_ip)
    await coordinator.async_config_entry_first_refresh()

    # Fetch device model and firmware version
    try:
        device_info = await coordinator.fetch_device_info()
    except UpdateFailed:
        _LOGGER.error("Failed to fetch device info for %s", host_ip)
        device_info = {}

    # Create sensor entities for each data field
    sensors = [
        BituoSensor(coordinator, host_ip, field, device_info.get("model", "Unknown Model"), device_info.get("fw_version", "Unknown"))
        for field in coordinator.data.keys()
        if field not in EXCLUDE_FIELDS
    ]
    async_add_entities(sensors, True)

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
                requests.get, f"http://{self.host_ip}/data"
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

class BituoSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, coordinator, host_ip, field, model, fw_version):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._field = field
        self._attr_name = self.format_field_name(field)
        self._attr_unique_id = f"{host_ip}_{field}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host_ip)},
            name=f"{model} - {host_ip}",
            manufacturer="BituoTechnik",
            model=model,
            sw_version=fw_version,
        )
        self._host_ip = host_ip

    @staticmethod
    def format_field_name(field):
        """Format field name to be more readable."""
        formatted_name = ''.join([' ' + char if char.isupper() else char for char in field]).title().strip()
        formatted_name = formatted_name.replace("X", " X").replace("Y", " Y").replace("Z", " Z")
        return formatted_name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._field)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        for unit_keyword, unit in UNIT_MAPPING.items():
            if unit_keyword in self._field.lower():
                return unit
        return None

# by Script0803