import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady
from .const import DOMAIN, CONF_HOST_IP, CONF_KIND, CONF_DIAL_SN
from .device_api import KIND_DIAL, DeviceProbeError, probe_device
from .frontend import setup_frontend
_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BUTTON, Platform.SWITCH]


def _platforms_for_kind(kind):
    if kind == KIND_DIAL:
        return [Platform.SENSOR, Platform.BUTTON]
    return list(PLATFORMS)

def _dial_sn_from_entry(entry: ConfigEntry):
    sn = entry.data.get(CONF_DIAL_SN)
    if sn:
        return sn
    unique_id = entry.unique_id or ""
    if unique_id.startswith("dial-"):
        return unique_id[5:]
    title = entry.title or ""
    prefix = "Bituo Dial "
    if title.startswith(prefix):
        return title[len(prefix):].strip()
    return None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BituoPMD integration from a config entry."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    host_ip = entry.data[CONF_HOST_IP]
    _LOGGER.info("Setting up BituoPMD integration for %s", host_ip)

    kind = entry.data.get(CONF_KIND)
    dial_sn = _dial_sn_from_entry(entry)
    if kind == KIND_DIAL or dial_sn:
        if not dial_sn:
            dial_sn = "DIAL"
        new_data = dict(entry.data)
        if new_data.get(CONF_KIND) != KIND_DIAL or new_data.get(CONF_DIAL_SN) != dial_sn:
            new_data[CONF_KIND] = KIND_DIAL
            new_data[CONF_DIAL_SN] = dial_sn
            hass.config_entries.async_update_entry(entry, data=new_data)
        _LOGGER.info("Dial %s: skip HTTP probe, use MQTT", dial_sn)
        platforms = _platforms_for_kind(KIND_DIAL)
        hass.data[DOMAIN][entry.entry_id] = {"platforms": platforms}
        await hass.config_entries.async_forward_entry_setups(entry, platforms)
        await setup_frontend(hass)
        return True

    try:
        probed = await hass.async_add_executor_job(probe_device, host_ip)
    except DeviceProbeError as e:
        _LOGGER.error("Error fetching device data from %s: %s", host_ip, e)
        raise ConfigEntryNotReady from e

    new_data = dict(entry.data)
    new_data[CONF_KIND] = probed["kind"]
    if probed["kind"] == KIND_DIAL:
        new_data[CONF_DIAL_SN] = probed["dial_sn"]
    hass.config_entries.async_update_entry(
        entry, data=new_data, title=probed["title"]
    )

    platforms = _platforms_for_kind(probed["kind"])
    hass.data[DOMAIN][entry.entry_id] = {"platforms": platforms}

    try:
        await hass.config_entries.async_forward_entry_setups(entry, platforms)
    except ConfigEntryNotReady as e:
        _LOGGER.error("Error setting up platforms for BituoPMD: %s", e)
        raise ConfigEntryNotReady from e

    await setup_frontend(hass)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a BituoPMD config entry."""
    _LOGGER.info("Unloading BituoPMD integration for %s", entry.data[CONF_HOST_IP])

    platforms = (
        hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("platforms")
        or _platforms_for_kind(entry.data.get(CONF_KIND))
    )
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        _LOGGER.info("Successfully unloaded BituoPMD integration for %s", entry.data[CONF_HOST_IP])
        if DOMAIN in hass.data:
            hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok

async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry."""
    _LOGGER.info("Removing BituoPMD integration for %s", entry.data[CONF_HOST_IP])
    if DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)
