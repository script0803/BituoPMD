import logging
import requests
import json
import asyncio
from datetime import timedelta
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfApparentPower,
    UnitOfPower,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS,
)
try:
    from homeassistant.const import UnitOfReactivePower
    POWER_VOLT_AMPERE_REACTIVE = UnitOfReactivePower.VOLT_AMPERE_REACTIVE
except (ImportError, AttributeError):
    from homeassistant.const import POWER_VOLT_AMPERE_REACTIVE

from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from packaging import version
from .const import DOMAIN, CONF_HOST_IP, CONF_KIND, CONF_DIAL_SN, DIAL_SCAN_INTERVAL, EW_SCAN_INTERVAL
from .device_api import (
    DIAL_METER_EXCLUDE,
    KIND_DIAL,
    DeviceProbeError,
    probe_device,
    scale_ew_power_fields,
    normalize_dial_meter,
)

_LOGGER = logging.getLogger(__name__)

SETTINGS_FILE = "custom_components/bituopmd/settings.json"
OTA_VERSIONS_FILE = "custom_components/bituopmd/ota_versions.json"

def load_settings():
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        _LOGGER.warning("Settings file not found, using default values.")
        return {"devices": {}}
    except json.JSONDecodeError as err:
        _LOGGER.error(f"Error decoding settings file: {err}")
        return {"devices": {}}

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f)
    except IOError as err:
        _LOGGER.error(f"Error saving settings: {err}")

def load_ota_versions():
    try:
        with open(OTA_VERSIONS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        _LOGGER.warning("OTA versions file not found.")
        return {}
    except json.JSONDecodeError as err:
        _LOGGER.error(f"Error decoding OTA versions file: {err}")
        return {}

settings = load_settings()
ota_versions = load_ota_versions()



UNIT_MAPPING = {
    "unbalancelinecurrents": PERCENTAGE,
    "powerfactor": None,
    "voltage": UnitOfElectricPotential.VOLT,
    "current": UnitOfElectricCurrent.AMPERE,
    "energy": UnitOfEnergy.KILO_WATT_HOUR,
    "apparent": UnitOfApparentPower.VOLT_AMPERE,
    "reactive": POWER_VOLT_AMPERE_REACTIVE,
    "power": UnitOfPower.WATT,
    "frequency": UnitOfFrequency.HERTZ,
    "rssi": SIGNAL_STRENGTH_DECIBELS,
}

STATE_CLASSES = {
    "voltage": SensorStateClass.MEASUREMENT,
    "current": SensorStateClass.MEASUREMENT,
    "power": SensorStateClass.MEASUREMENT,
    "energy": SensorStateClass.TOTAL_INCREASING,
    "frequency": SensorStateClass.MEASUREMENT,
    "rssi": SensorStateClass.MEASUREMENT,
}

EXCLUDE_FIELDS = {"Post", "Time", "Config485", "MqttStatus", "ProductModel", "IP", "SerialNumber", "DeviceType", "FWVersion", "MCUVersion", "Manufactor"}

DIAL_SENSOR_FIELDS = (
    "VoltageX",
    "VoltageY",
    "VoltageZ",
    "CurrentX",
    "CurrentY",
    "CurrentZ",
    "ActivePowerX",
    "ActivePowerY",
    "ActivePowerZ",
    "TotalActivePower",
    "TotalForwardEnergy",
    "TotalReverseEnergy",
    "RSSI",
)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensor platform."""
    host_ip = entry.data[CONF_HOST_IP]
    kind = entry.data.get(CONF_KIND)
    default_interval = DIAL_SCAN_INTERVAL if kind == KIND_DIAL else EW_SCAN_INTERVAL
    current_scan_interval = settings["devices"].get(host_ip, {}).get(
        "scan_interval", default_interval
    )
    coordinator = BituoDataUpdateCoordinator(hass, entry, current_scan_interval)
    entry_store = hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {})
    entry_store["sensor_coordinator"] = coordinator
    await coordinator.async_enable_mqtt()
    if coordinator.is_dial:
        await asyncio.sleep(1)
    await coordinator.async_config_entry_first_refresh()

    # Fetch device model and firmware version
    try:
        device_info = await coordinator.fetch_device_info()
    except UpdateFailed:
        _LOGGER.error("Failed to fetch device info for %s", host_ip)
        device_info = {}

    sensors = []
    if coordinator.is_dial:
        hub_id = f"dial-{host_ip}"
        sensors.append(
            DialHubSensor(
                coordinator,
                host_ip,
                hub_id,
                device_info.get("manufacturer", "BITUO TECHNIK"),
            )
        )
        for meter in (coordinator.data.get("meters") or {}).values():
            sn = meter.get("sn")
            if not sn:
                continue
            label = meter.get("label") or sn
            fields = list(DIAL_SENSOR_FIELDS)
            for field in meter.keys():
                if (
                    field not in fields
                    and field not in DIAL_METER_EXCLUDE
                    and field not in ("sn", "label", "online")
                ):
                    fields.append(field)
            for field in fields:
                sensors.append(
                    BituoSensor(
                        coordinator,
                        host_ip,
                        field,
                        label,
                        device_info.get("fw_version", "Unknown"),
                        device_info.get("manufacturer", "Unknown"),
                        device_info.get("mcu_version", "Unknown"),
                        sn=sn,
                        hub_id=hub_id,
                    )
                )
            sensors.append(
                BituoSensor(
                    coordinator,
                    host_ip,
                    "online",
                    label,
                    device_info.get("fw_version", "Unknown"),
                    device_info.get("manufacturer", "Unknown"),
                    device_info.get("mcu_version", "Unknown"),
                    sn=sn,
                    hub_id=hub_id,
                )
            )
    else:
        sensors = [
            BituoSensor(coordinator, host_ip, field, device_info.get("model", "Unknown Model"), device_info.get("fw_version", "Unknown"), device_info.get("manufacturer", "Unknown"), device_info.get("mcu_version", "Unknown"))
            for field in coordinator.data.keys()
            if field not in EXCLUDE_FIELDS
        ]
        ota_sensor = BituoOTASensor(coordinator, host_ip, device_info.get("model", "Unknown Model"), device_info.get("fw_version", "Unknown"), device_info.get("manufacturer", "Unknown"), device_info.get("mcu_version", "Unknown"))
        sensors.append(ota_sensor)
        coordinator.ota_entity = ota_sensor

    async_add_entities(sensors, False)

    async def handle_set_frequency(call):
        """Handle the service call to set the data fetch frequency."""
        frequency = call.data.get("frequency", 5)
        device_id = call.data.get("device_id")  # 获取设备 ID

        # 更新特定设备的频率配置
        settings["devices"].setdefault(device_id, {})["scan_interval"] = frequency
        save_settings(settings)
        
        # 立即刷新设备数据
        await coordinator.async_refresh()

        # 更新协调器的扫描间隔
        coordinator.update_interval = timedelta(seconds=frequency)

    hass.services.async_register(DOMAIN, "set_frequency", handle_set_frequency)

class BituoDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the device."""

    def __init__(self, hass, entry, scan_interval):
        """Initialize."""
        self.entry = entry
        self.host_ip = entry.data[CONF_HOST_IP]
        self.kind = entry.data.get(CONF_KIND)
        self.dial_sn = entry.data.get(CONF_DIAL_SN)
        unique_id = entry.unique_id or ""
        if not self.dial_sn and unique_id.startswith("dial-"):
            self.dial_sn = unique_id[5:]
        if self.dial_sn:
            self.kind = KIND_DIAL
        self.ota_versions = load_ota_versions()
        self.ota_entity = None
        self._mqtt_unsubs = []
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=scan_interval))

        self.hass.loop.create_task(self._periodically_update_scan_interval())
        if not self.is_dial:
            self._ota_update_task = hass.loop.create_task(self._schedule_ota_update_checks())

    @property
    def is_dial(self):
        return self.kind == KIND_DIAL

    def _meters_from_registry(self):
        """Reuse SNs and labels already created by a previous setup."""
        from homeassistant.helpers import device_registry as dr
        from homeassistant.helpers import entity_registry as er

        meters = {}
        registry = er.async_get(self.hass)
        devices = dr.async_get(self.hass)
        for ent in registry.entities.values():
            if ent.config_entry_id != self.entry.entry_id:
                continue
            uid = ent.unique_id or ""
            sn = uid.split("_", 1)[0]
            if len(sn) != 12:
                continue
            label = sn
            device = devices.async_get_device({(DOMAIN, sn)})
            if device:
                label = device.name_by_user or device.name or sn
            meters.setdefault(sn, {"sn": sn, "label": label, "online": False})
        return meters

    def _apply_meter_names(self, meters):
        from homeassistant.helpers import device_registry as dr

        registry = dr.async_get(self.hass)
        for sn, meter in meters.items():
            label = meter.get("label")
            if not label:
                continue
            device = registry.async_get_device({(DOMAIN, sn)})
            if device is None:
                continue
            kwargs = {}
            if device.name != label:
                kwargs["name"] = label
            if device.name_by_user in (None, sn) and label != sn:
                kwargs["name_by_user"] = label
            if kwargs:
                registry.async_update_device(device.id, **kwargs)

    def _merge_meter(self, meter):
        data = dict(self.data or {})
        meters = dict(data.get("meters") or {})
        sn = meter.get("sn")
        if not sn:
            return
        prev = dict(meters.get(sn) or {})
        prev.update(meter)
        meters[sn] = prev
        data["meters"] = meters
        data["_kind"] = KIND_DIAL
        if self.dial_sn:
            data["dial_sn"] = self.dial_sn
        self.async_set_updated_data(data)

    @callback
    def _on_mqtt_meter(self, msg):
        raw = msg.payload
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return
        meter = normalize_dial_meter(payload)
        if meter is None:
            return
        self._merge_meter(meter)

    @callback
    def _on_mqtt_mdata(self, msg):
        raw = msg.payload
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return
        if payload.get("dial_sn"):
            self.dial_sn = payload.get("dial_sn") or self.dial_sn
        data = dict(self.data or {})
        meters = dict(data.get("meters") or {})
        changed = False
        for item in payload.get("meters") or []:
            if not isinstance(item, dict) or not item.get("sn"):
                continue
            sn = item.get("sn")
            prev = dict(meters.get(sn) or {"sn": sn, "online": False})
            prev["sn"] = sn
            prev["label"] = item.get("label") or prev.get("label") or sn
            meters[sn] = prev
            changed = True
        if not changed and not payload.get("dial_sn"):
            return
        data["meters"] = meters
        data["_kind"] = KIND_DIAL
        if self.dial_sn:
            data["dial_sn"] = self.dial_sn
        self.async_set_updated_data(data)
        self._apply_meter_names(meters)

    @callback
    def _on_mqtt_summary(self, msg):
        raw = msg.payload
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return
        data = dict(self.data or {})
        meters = dict(data.get("meters") or {})
        changed = False
        for item in payload.get("meters") or []:
            if not isinstance(item, dict) or not item.get("sn"):
                continue
            sn = item.get("sn")
            prev = dict(meters.get(sn) or {"sn": sn})
            prev["label"] = item.get("label") or prev.get("label") or sn
            prev["online"] = bool(item.get("online"))
            if "TotalActivePower" in item:
                prev["TotalActivePower"] = item.get("TotalActivePower")
            if item.get("_rssi") is not None:
                prev["RSSI"] = item.get("_rssi")
            meters[sn] = prev
            changed = True
        if not changed:
            return
        data["meters"] = meters
        data["_kind"] = KIND_DIAL
        if self.dial_sn:
            data["dial_sn"] = self.dial_sn
        self.async_set_updated_data(data)

    async def async_enable_mqtt(self):
        """Dial publishes outbound MQTT even when inbound HTTP is unreachable."""
        if not self.is_dial or not self.dial_sn:
            _LOGGER.warning("Dial MQTT skip: kind=%s sn=%s", self.kind, self.dial_sn)
            return
        try:
            from homeassistant.components import mqtt
        except Exception as err:
            _LOGGER.warning("MQTT component missing, Dial stays on last data: %s", err)
            return
        try:
            await mqtt.async_wait_for_mqtt_client(self.hass)
        except Exception as err:
            _LOGGER.warning("MQTT client not ready: %s", err)
            return
        try:
            self._mqtt_unsubs.append(
                await mqtt.async_subscribe(
                    self.hass,
                    f"bituo-dial/{self.dial_sn}/meters/+/data",
                    self._on_mqtt_meter,
                    0,
                )
            )
            self._mqtt_unsubs.append(
                await mqtt.async_subscribe(
                    self.hass,
                    f"bituo-dial/{self.dial_sn}/mdata",
                    self._on_mqtt_mdata,
                    0,
                )
            )
            self._mqtt_unsubs.append(
                await mqtt.async_subscribe(
                    self.hass,
                    f"bituo-dial/{self.dial_sn}/summary",
                    self._on_mqtt_summary,
                    0,
                )
            )
            _LOGGER.info("Dial %s subscribed to MQTT telemetry", self.dial_sn)
        except Exception as err:
            _LOGGER.warning("Dial MQTT subscribe failed: %s", err)

    def get_scan_interval(self):
        """Get the scan interval from settings."""
        default = DIAL_SCAN_INTERVAL if self.is_dial else EW_SCAN_INTERVAL
        return settings["devices"].get(self.host_ip, {}).get("scan_interval", default)
    
    async def _periodically_update_scan_interval(self):
        """Periodically update the scan interval from settings.json."""
        while True:
            new_interval = self.get_scan_interval()
            if new_interval != self.update_interval.total_seconds():
                _LOGGER.info(f"Updating scan interval for {self.host_ip} to {new_interval} seconds")
                self.update_interval = timedelta(seconds=new_interval)
            await asyncio.sleep(60)

    async def _async_update_data(self):
        """EW meters poll HTTP. Dial is MQTT-only; HTTP /data is often unreachable."""
        if self.is_dial:
            if self.data:
                return self.data
            return {
                "_kind": KIND_DIAL,
                "dial_sn": self.dial_sn,
                "meters": self._meters_from_registry(),
            }
        try:
            probed = await self.hass.async_add_executor_job(probe_device, self.host_ip)
            if probed["kind"] == KIND_DIAL:
                self.kind = KIND_DIAL
                self.dial_sn = probed.get("dial_sn") or self.dial_sn
                meters = {meter["sn"]: meter for meter in probed["meters"]}
                return {
                    "_kind": KIND_DIAL,
                    "dial_sn": self.dial_sn,
                    "meters": meters,
                }
            return scale_ew_power_fields(dict(probed.get("payload") or {}))
        except (DeviceProbeError, Exception) as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def fetch_device_info(self):
        """Fetch device model and firmware version information."""
        if self.is_dial:
            return {
                "model": "bituo-dial",
                "fw_version": "Unknown",
                "manufacturer": "BITUO TECHNIK",
                "mcu_version": "Unknown",
            }
        try:
            probed = await self.hass.async_add_executor_job(probe_device, self.host_ip)
            data = probed.get("payload") or {}
            return {
                "model": data.get("ProductModel", "Unknown Model"),
                "fw_version": data.get("FWVersion", "Unknown"),
                "manufacturer": "BITUO TECHNIK",
                "mcu_version": data.get("MCUVersion", "Unknown"),
            }
        except Exception as err:
            raise UpdateFailed(f"Error fetching device info: {err}")

    async def check_for_ota_updates(self):
        """Check for OTA updates."""
        try:
            if self.ota_entity is None:
                return

            device_info = await self.fetch_device_info()
            current_version = device_info.get("fw_version", "Unknown")

            if current_version != "Unknown" and int(current_version.split('.')[0]) >= 4:
                latest_version = self.ota_versions.get("common", "Unknown")
            else:
                model = device_info.get("model", "Unknown Model")
                latest_version = self.ota_versions.get(model, "Unknown")

            if latest_version != "Unknown" and current_version != "Unknown" and version.parse(current_version) < version.parse(latest_version):
                self.ota_entity._attr_state = "OTA Available"
            else:
                self.ota_entity._attr_state = "Up to Date"
            self.ota_entity.async_write_ha_state()
        except Exception as err:
            _LOGGER.error(f"Error checking OTA updates: {err}")
    
    async def _schedule_ota_update_checks(self):
        """Schedule periodic OTA update checks."""
        while True:
            await self.check_for_ota_updates()
            await asyncio.sleep(1800)  # Wait for 30 minutes

class BituoSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, coordinator, host_ip, field, model, fw_version, manufacturer, mcu_version, sn=None, hub_id=None):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._field = field
        self._sn = sn
        self._attr_name = self.format_field_name(field)
        if sn:
            self._attr_unique_id = f"{sn}_{field}"
            self.entity_id = f"sensor.{sn.lower()}_{self.format_field_entity_id(field)}"
            identifiers = {(DOMAIN, sn)}
            via_device = (DOMAIN, hub_id) if hub_id else None
            device_kwargs = {
                "identifiers": identifiers,
                "name": model,
                "manufacturer": manufacturer,
                "model": model,
                "sw_version": f"S{fw_version}_M{self.format_version(mcu_version)}",
                "configuration_url": f"http://{host_ip}",
            }
            if via_device:
                device_kwargs["via_device"] = via_device
            self._attr_device_info = DeviceInfo(**device_kwargs)
        else:
            self._attr_unique_id = f"{host_ip}_{field}"
            self.entity_id = f"sensor.{host_ip.replace('.', '_')}_{self.format_field_entity_id(field)}"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, host_ip)},
                name=f"{model} - {host_ip}",
                manufacturer=manufacturer,
                model=model,
                sw_version=f"S{fw_version}_M{self.format_version(mcu_version)}",
                configuration_url=f"http://{host_ip}"  # embed URL
            )
        self._host_ip = host_ip
        self._hub_id = hub_id
        self._manufacturer = manufacturer
        self._fw_version = fw_version
        self._mcu_version = mcu_version
        self._native_unit_of_measurement = self.get_initial_unit_of_measurement()
        self._attr_state_class = self.get_state_class()
        self._attr_device_class = self.get_device_class()
        if "power" in self._field.lower() and "active" in self._field.lower():
            self._attr_suggested_display_precision = 0
        if "power" in self._field.lower() and "apparent" in self._field.lower():
            self._attr_suggested_display_precision = 0
        if "unbalancelinecurrents" in self._field.lower():
            self._attr_suggested_display_precision = 0

    def _meter_label(self):
        if not self._sn:
            return None
        meter = ((self.coordinator.data or {}).get("meters") or {}).get(self._sn) or {}
        return meter.get("label") or self._sn

    @property
    def device_info(self):
        if not self._sn:
            return self._attr_device_info
        label = self._meter_label()
        via_device = (DOMAIN, self._hub_id) if self._hub_id else None
        info = {
            "identifiers": {(DOMAIN, self._sn)},
            "name": label,
            "manufacturer": self._manufacturer,
            "model": label,
            "sw_version": f"S{self._fw_version}_M{self.format_version(self._mcu_version)}",
            "configuration_url": f"http://{self._host_ip}",
        }
        if via_device:
            info["via_device"] = via_device
        return DeviceInfo(**info)

    def get_initial_unit_of_measurement(self):
        """Determine the initial unit of measurement based on the field."""
        for unit_keyword, unit in UNIT_MAPPING.items():
            if unit_keyword in self._field.lower():
                return unit
        return None

    def get_state_class(self):
        """Determine the state class based on the field."""
        for state_class_keyword, state_class in STATE_CLASSES.items():
            if state_class_keyword in self._field.lower():
                return state_class
        return SensorStateClass.MEASUREMENT  # Default state class

    def get_device_class(self):
        """Determine the device class based on the field."""
        if "unbalancelinecurrents" in self._field.lower():
            return SensorDeviceClass.POWER_FACTOR
        if "power" in self._field.lower():
            if "factor" in self._field.lower():
                return SensorDeviceClass.POWER_FACTOR
            elif "reactive" in self._field.lower():
                return SensorDeviceClass.REACTIVE_POWER
            elif "apparent" in self._field.lower():
                return SensorDeviceClass.APPARENT_POWER
            elif "active" in self._field.lower():
                return SensorDeviceClass.POWER
        elif "energy" in self._field.lower():
            return SensorDeviceClass.ENERGY
        elif "current" in self._field.lower():
            return SensorDeviceClass.CURRENT
        elif "voltage" in self._field.lower():
            return SensorDeviceClass.VOLTAGE
        elif "frequency" in self._field.lower():
            return SensorDeviceClass.FREQUENCY
        elif "rssi" in self._field.lower():
            return SensorDeviceClass.SIGNAL_STRENGTH
        return None

    @staticmethod
    def format_field_name(field):
        """Format field name to be more readable."""
        formatted_name = ''.join([' ' + char if char.isupper() else char for char in field]).title().strip()
        formatted_name = formatted_name.replace("X", " X").replace("Y", " Y").replace("Z", " Z")
        return formatted_name
    
    @staticmethod
    def format_field_entity_id(field):
        """Format field name to be more suitable for unique_id."""
        import re
        
        formatted_name = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', field).lower()
        
        formatted_name = re.sub(r'_+', '_', formatted_name)
        
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

    @property
    def native_value(self):
        """Return the native state of the sensor."""
        data = self.coordinator.data or {}
        if self._sn:
            value = (data.get("meters") or {}).get(self._sn, {}).get(self._field)
        else:
            value = data.get(self._field)
        if value is None:
            return 0
        return value

    @property
    def native_unit_of_measurement(self):
        """Return the native unit of measurement."""
        return self._native_unit_of_measurement

    @property
    def device_class(self):
        """Return the class of this device."""
        return self._attr_device_class

class DialHubSensor(CoordinatorEntity, SensorEntity):
    """Gateway sensor: how many BLE meters behind this Dial are online."""

    def __init__(self, coordinator, host_ip, hub_id, manufacturer):
        super().__init__(coordinator)
        self._host_ip = host_ip
        self._attr_name = "Online meters"
        self._attr_unique_id = f"{hub_id}_online_count"
        self.entity_id = f"sensor.{hub_id.replace('.', '_')}_online_count"
        self._attr_icon = "mdi:counter"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hub_id)},
            name=f"Bituo Dial - {host_ip}",
            manufacturer=manufacturer,
            model="bituo-dial",
            configuration_url=f"http://{host_ip}",
        )

    @property
    def native_value(self):
        meters = (self.coordinator.data or {}).get("meters") or {}
        return sum(1 for meter in meters.values() if meter.get("online"))


class BituoOTASensor(CoordinatorEntity, SensorEntity):
    """Representation of an OTA status sensor."""

    def __init__(self, coordinator, host_ip, model, fw_version, manufacturer, mcu_version):
        """Initialize the OTA status sensor."""
        super().__init__(coordinator)
        self._attr_name = "OTA Status"
        self._attr_unique_id = f"{host_ip}_ota_status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host_ip)},
            name=f"{model} - {host_ip}",
            manufacturer=manufacturer,
            model=model,
            sw_version=f"S{fw_version}_M{self.format_version(mcu_version)}",
            configuration_url=f"http://{host_ip}"  # embed URL
        )
        self._host_ip = host_ip
        self._attr_state = "unknown"
        coordinator.ota_entity = self  # 存储自身的引用到协调器中
        self._attr_icon = "mdi:update"
        self.entity_id = f"sensor.{self._attr_unique_id.replace('.', '_')}"
    
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
    def native_value(self):
        """Return the native state of the sensor."""
        return self._attr_state

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # Set up the initial state
        await self.coordinator.check_for_ota_updates()

    async def async_update(self):
        """Update the sensor."""
        await self.coordinator.check_for_ota_updates()
