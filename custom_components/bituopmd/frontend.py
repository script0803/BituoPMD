import logging
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.panel_custom import async_register_panel
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN, CONF_HOST_IP

_LOGGER = logging.getLogger(__name__)

class DeviceListView(HomeAssistantView):
    """Provide a JSON endpoint for device list."""

    url = "/api/bituopmd/devices"
    name = "api:bituopmd:devices"
    requires_auth = True

    async def get(self, request):
        hass = request.app["hass"]
        devices = []

        for entry in hass.config_entries.async_entries(DOMAIN):
            host_ip = entry.data.get(CONF_HOST_IP, "Unknown IP")
            title = entry.title
            devices.append({"name": title, "ip": host_ip, "id": entry.entry_id})
            _LOGGER.debug(f"Device entry: {entry.entry_id}, IP: {host_ip}")

        _LOGGER.info("Device list: %s", devices)
        return self.json(devices)

class DeviceProxyView(HomeAssistantView):
    """Proxy HTTP requests to the device."""

    url = "/api/bituopmd/proxy/{device_ip}/{action}"
    name = "api:bituopmd:proxy"
    requires_auth = True

    async def get(self, request, device_ip, action):
        url = f"http://{device_ip}/{action}"
        _LOGGER.debug(f"Proxying GET request to {url}")
        async with async_get_clientsession(request.app["hass"]).get(url) as resp:
            data = await resp.text()
            return self.json({"response": data})

    async def post(self, request, device_ip, action):
        data = await request.json()
        if action == "set_frequency":
            # 调用处理频率更新的服务
            await request.app["hass"].services.async_call(DOMAIN, "set_frequency", {"frequency": data["frequency"]})
            return self.json({"status": "frequency updated"})
        url = f"http://{device_ip}/{action}"
        _LOGGER.debug(f"Proxying POST request to {url} with data {data}")
        async with async_get_clientsession(request.app["hass"]).post(url, json=data) as resp:
            data = await resp.text()
            return self.json({"response": data})

async def setup_frontend(hass):
    """Set up the frontend for the BituoPMD integration."""
    hass.http.register_static_path(
        "/custom_components/bituopmd/www/bituo_panel.js",
        hass.config.path("custom_components/bituopmd/www/bituo_panel.js"),
        False
    )

    # Register the panel only once
    if not hass.data.get(f"{DOMAIN}_panel_registered"):
        await async_register_panel(
            hass,
            frontend_url_path="bituopmd",
            webcomponent_name="bituo-panel",
            sidebar_title="BituoPMD",
            sidebar_icon="mdi:home-lightning-bolt",
            require_admin=False,
            config={"title": "BituoPMD"},
            js_url="/custom_components/bituopmd/www/bituo_panel.js"
        )
        hass.data[f"{DOMAIN}_panel_registered"] = True

    hass.http.register_view(DeviceListView)
    hass.http.register_view(DeviceProxyView)
    _LOGGER.info("API endpoints registered for BituoPMD")
