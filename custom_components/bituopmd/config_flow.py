"""Config flow for Bituo power monitoring devices."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import BituoApiClient, BituoApiError, normalize_host
from .const import (
    CONF_HOST_IP,
    CONF_IDENTITY_HOST,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)


async def _async_validate_device(
    hass: HomeAssistant, host: str
) -> tuple[str, dict[str, Any]]:
    """Connect to a device and return its normalized host and payload."""
    normalized_host = normalize_host(host)
    client = BituoApiClient(async_get_clientsession(hass), normalized_host)
    data = await client.async_get_data()
    return normalized_host, data


def _is_bituo_device(name: str) -> bool:
    """Match Bituo devices advertised via mDNS.

    Devices ship with either "EnergySensor-<model>-<sn>" or
    "BITUO TECHNIK-<model>-<sn>" hostnames depending on firmware.
    """
    lowered = name.lower()
    return "energysensor" in lowered or "bituo" in lowered


class BituoFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle BituoPMD configuration."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize discovery state."""
        self._discovered_host: str | None = None
        self._discovered_name: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return BituoOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Set up a device by IP address."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                host, data = await _async_validate_device(
                    self.hass, user_input[CONF_HOST_IP]
                )
            except BituoApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                if self._host_is_configured(host):
                    return self.async_abort(reason="already_configured")
                model = data.get("ProductModel") or data.get("productModel", "BituoPMD")
                return self.async_create_entry(
                    title=f"{model} - {host}",
                    data={CONF_HOST_IP: host},
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST_IP,
                    default=(user_input.get(CONF_HOST_IP, "") if user_input else ""),
                ): str
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle Home Assistant's native zeroconf discovery."""
        name = discovery_info.name.split(".")[0]
        if not _is_bituo_device(name):
            return self.async_abort(reason="not_bituotechnik_device")

        try:
            host = normalize_host(discovery_info.host)
        except BituoApiError:
            return self.async_abort(reason="cannot_connect")

        await self.async_set_unique_id(host)
        self._abort_if_unique_id_configured()
        if self._host_is_configured(host):
            return self.async_abort(reason="already_configured")

        self._discovered_host = host
        self._discovered_name = name
        self.context["title_placeholders"] = {
            "name": name,
            "host": host,
        }
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm a discovered device."""
        if self._discovered_host is None:
            return self.async_abort(reason="cannot_connect")

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                host, data = await _async_validate_device(
                    self.hass, self._discovered_host
                )
            except BituoApiError:
                errors["base"] = "cannot_connect"
            else:
                model = data.get("ProductModel") or data.get(
                    "productModel", self._discovered_name or "BituoPMD"
                )
                return self.async_create_entry(
                    title=f"{model} - {host}",
                    data={CONF_HOST_IP: host},
                )

        return self.async_show_form(
            step_id="zeroconf_confirm",
            errors=errors,
            description_placeholders={
                "name": self._discovered_name or "BituoPMD",
                "host": self._discovered_host,
            },
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Allow an IP change without deleting entities or history."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                host, data = await _async_validate_device(
                    self.hass, user_input[CONF_HOST_IP]
                )
            except BituoApiError:
                errors["base"] = "cannot_connect"
            else:
                if self._host_is_configured(host, exclude_entry_id=entry.entry_id):
                    errors["base"] = "already_configured"
                else:
                    model = data.get("ProductModel") or data.get(
                        "productModel", "BituoPMD"
                    )
                    return self.async_update_reload_and_abort(
                        entry,
                        data_updates={
                            CONF_HOST_IP: host,
                            CONF_IDENTITY_HOST: entry.data.get(
                                CONF_IDENTITY_HOST,
                                entry.data[CONF_HOST_IP],
                            ),
                        },
                        title=f"{model} - {host}",
                    )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST_IP,
                        default=entry.data[CONF_HOST_IP],
                    ): str
                }
            ),
            errors=errors,
        )

    def _host_is_configured(
        self, host: str, exclude_entry_id: str | None = None
    ) -> bool:
        """Return whether another entry already uses the address."""
        return any(
            entry.entry_id != exclude_entry_id and entry.data.get(CONF_HOST_IP) == host
            for entry in self._async_current_entries()
        )


class BituoOptionsFlow(config_entries.OptionsFlowWithReload):
    """Configure local polling without writing into the integration folder."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the polling interval."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                        ),
                    )
                }
            ),
        )
