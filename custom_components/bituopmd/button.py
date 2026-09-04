"""Button platform for Bituo power monitoring devices."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import BituoApiError
from .const import CONF_HOST_IP, CONF_IDENTITY_HOST, DATA_KEY_ENTRIES, DOMAIN
from .coordinator import BituoDataUpdateCoordinator
from .entity import BituoEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up buttons from the shared coordinator."""
    coordinator: BituoDataUpdateCoordinator = hass.data[DOMAIN][DATA_KEY_ENTRIES][
        entry.entry_id
    ]["coordinator"]
    identity_host = entry.data.get(CONF_IDENTITY_HOST, entry.data[CONF_HOST_IP])
    async_add_entities(
        (
            DataRefreshButton(coordinator, identity_host),
            DeviceLocatingButton(coordinator, identity_host),
        )
    )


class DataRefreshButton(BituoEntity, ButtonEntity):
    """Request an immediate coordinator refresh."""

    _attr_name = "Data Refresh"
    _attr_icon = "mdi:refresh"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: BituoDataUpdateCoordinator,
        identity_host: str,
    ) -> None:
        """Initialize the refresh button with its upstream identity."""
        super().__init__(coordinator, identity_host)
        self._attr_unique_id = f"{identity_host}_data_refresh"
        self.entity_id = f"button.{identity_host.replace('.', '_')}_data_refresh"

    async def async_press(self) -> None:
        """Refresh device data."""
        await self.coordinator.async_request_refresh()


class DeviceLocatingButton(BituoEntity, ButtonEntity):
    """Ask the physical device to identify itself."""

    _attr_name = "Device Locating"
    _attr_icon = "mdi:map-marker"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: BituoDataUpdateCoordinator,
        identity_host: str,
    ) -> None:
        """Initialize the locating button with its upstream identity."""
        super().__init__(coordinator, identity_host)
        self._attr_unique_id = f"{identity_host}_device_locating"
        self.entity_id = f"button.{identity_host.replace('.', '_')}_device_locating"

    async def async_press(self) -> None:
        """Run the device locating command."""
        try:
            await self.coordinator.client.async_get_action("location")
        except BituoApiError as err:
            raise HomeAssistantError(
                f"Unable to locate BituoPMD device: {err}"
            ) from err
