"""Switch platform for relay-capable Bituo devices."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
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
    """Set up a relay only when the device advertises one."""
    coordinator: BituoDataUpdateCoordinator = hass.data[DOMAIN][DATA_KEY_ENTRIES][
        entry.entry_id
    ]["coordinator"]
    if coordinator.supports_switch:
        identity_host = entry.data.get(
            CONF_IDENTITY_HOST,
            entry.data[CONF_HOST_IP],
        )
        async_add_entities((BituoSwitch(coordinator, identity_host),))


class BituoSwitch(BituoEntity, SwitchEntity):
    """Representation of a Bituo device relay."""

    _attr_name = "Switch"

    def __init__(
        self,
        coordinator: BituoDataUpdateCoordinator,
        identity_host: str,
    ) -> None:
        """Initialize the relay without changing its upstream unique ID."""
        super().__init__(coordinator, identity_host)
        self._attr_unique_id = f"{identity_host}_switch"
        self.entity_id = f"switch.{identity_host.replace('.', '_')}_switch"

    @property
    def is_on(self) -> bool:
        """Return the current relay state."""
        return bool(self.coordinator.data.get("switchstatus", False))

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the relay."""
        await self._async_set_state("switchon")

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the relay."""
        await self._async_set_state("switchoff")

    async def _async_set_state(self, action: str) -> None:
        """Run a relay action and refresh state."""
        try:
            await self.coordinator.client.async_get_action(action)
        except BituoApiError as err:
            raise HomeAssistantError(
                f"Unable to control BituoPMD relay: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
