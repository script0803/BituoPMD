"""Compatibility sidebar panel and secured device proxy."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.components.panel_custom import async_register_panel
from homeassistant.core import HomeAssistant

from .api import BituoApiClient, BituoApiError
from .const import (
    CONF_HOST_IP,
    DATA_KEY_ENTRIES,
    DATA_KEY_FRONTEND,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

READ_ONLY_GET_ACTIONS = frozenset({"data", "hadata", "status"})
ADMIN_GET_ACTIONS = frozenset({"zeroenergy", "ota"})
ADMIN_POST_ACTIONS = frozenset({"save-config"})


def _client_for_host(hass: HomeAssistant, host: str) -> BituoApiClient:
    """Resolve a configured host instead of accepting an arbitrary URL."""
    for runtime in hass.data[DOMAIN][DATA_KEY_ENTRIES].values():
        client: BituoApiClient = runtime["client"]
        if client.host == host:
            return client
    raise web.HTTPNotFound(text="Unknown BituoPMD device")


def _require_admin(request: web.Request) -> None:
    """Restrict commands that change physical device configuration."""
    user = request.get("hass_user")
    if user is None or not user.is_admin:
        raise web.HTTPUnauthorized(
            text="Administrator access is required for this action"
        )


class DeviceListView(HomeAssistantView):
    """Provide configured devices to the compatibility panel."""

    url = "/api/bituopmd/devices"
    name = "api:bituopmd:devices"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return configured devices."""
        hass: HomeAssistant = request.app["hass"]
        devices = [
            {
                "name": entry.title,
                "ip": entry.data[CONF_HOST_IP],
                "id": entry.entry_id,
            }
            for entry in hass.config_entries.async_entries(DOMAIN)
        ]
        return self.json(devices)


class DeviceProxyView(HomeAssistantView):
    """Proxy only known actions to explicitly configured devices."""

    url = "/api/bituopmd/proxy/{device_ip}/{action}"
    name = "api:bituopmd:proxy"
    requires_auth = True

    async def get(
        self, request: web.Request, device_ip: str, action: str
    ) -> web.Response:
        """Run a whitelisted GET action."""
        if action not in READ_ONLY_GET_ACTIONS | ADMIN_GET_ACTIONS:
            raise web.HTTPBadRequest(text="Unsupported BituoPMD action")
        if action in ADMIN_GET_ACTIONS:
            _require_admin(request)

        client = _client_for_host(request.app["hass"], device_ip)
        try:
            response = await client.async_get_action(action)
        except BituoApiError as err:
            raise web.HTTPBadGateway(text=str(err)) from err
        return self.json({"response": response})

    async def post(
        self, request: web.Request, device_ip: str, action: str
    ) -> web.Response:
        """Run a whitelisted administrator-only POST action."""
        if action not in ADMIN_POST_ACTIONS:
            raise web.HTTPBadRequest(text="Unsupported BituoPMD action")
        _require_admin(request)
        client = _client_for_host(request.app["hass"], device_ip)
        try:
            payload: Any = await request.json()
        except ValueError as err:
            raise web.HTTPBadRequest(text="Expected a JSON body") from err
        if not isinstance(payload, dict):
            raise web.HTTPBadRequest(text="Expected a JSON object")

        try:
            response = await client.async_post_action(action, payload)
        except BituoApiError as err:
            raise web.HTTPBadGateway(text=str(err)) from err
        return self.json({"response": response})


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Register the compatibility panel and API exactly once."""
    if hass.data[DOMAIN].get(DATA_KEY_FRONTEND):
        return

    static_path = Path(__file__).parent / "www" / "bituo_panel.js"
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                "/custom_components/bituopmd/www/bituo_panel.js",
                str(static_path),
                False,
            )
        ]
    )
    hass.http.register_view(DeviceListView)
    hass.http.register_view(DeviceProxyView)
    await async_register_panel(
        hass,
        frontend_url_path="bituopmd",
        webcomponent_name="bituo-panel",
        sidebar_title="BituoPMD",
        sidebar_icon="mdi:home-lightning-bolt",
        require_admin=True,
        config={"title": "BituoPMD"},
        js_url="/custom_components/bituopmd/www/bituo_panel.js",
    )
    hass.data[DOMAIN][DATA_KEY_FRONTEND] = True
    _LOGGER.debug("Registered secured BituoPMD compatibility panel")
