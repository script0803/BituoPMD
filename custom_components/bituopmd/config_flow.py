import asyncio
import logging
import socket
import requests
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.components.zeroconf import async_get_instance, ZeroconfServiceInfo
import voluptuous as vol
from zeroconf import ServiceBrowser, ServiceStateChange
from .const import DOMAIN, CONF_HOST_IP

_LOGGER = logging.getLogger(__name__)

class BituoFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.host = None
        self.name = None
        self.devices = []

    async def async_step_user(self, user_input=None):
        errors = {}
        
        if user_input is not None:
            if user_input["method"] == "zeroconf":
                return await self.async_step_zeroconf_discovery()
            elif user_input["method"] == "manual":
                return await self.async_step_manual()

        data_schema = vol.Schema({
            vol.Required("method", default="zeroconf"): vol.In({"zeroconf": "Use zeroconf to scan devices", "manual": "Use IP to pair devices"})
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo):
        """Handle zeroconf discovery."""
        self.host = discovery_info.host
        self.name = discovery_info.name.split(".")[0]

        if "bituotechnik" not in self.name.lower():
            return self.async_abort(reason="not_bituotechnik_device")

        await self.async_set_unique_id(self.host)
        self._abort_if_unique_id_configured()

        self.context.update({
            "title_placeholders": {
                "name": self.name,
                "host": self.host,
            }
        })

        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(self, user_input=None):
        """Handle zeroconf discovery confirmation."""
        if user_input is not None:
            entry = self.async_create_entry(
                title=self.name,
                data={CONF_HOST_IP: self.host}
            )
            # remove paired device
            self.devices = [device for device in self.devices if device["ip"] != self.host]
            return entry

        data_schema = vol.Schema({
            vol.Required("confirmation", default=f"Do you want to set up this device?"): vol.In([f"Do you want to set up this device?"])
        })

        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=data_schema,
            description_placeholders={
                "name": self.name,
            },
        )
    
    async def async_step_zeroconf_discovery(self, user_input=None):
        """Handle manual zeroconf scanning triggered by the user."""
        errors = {}
        devices = await self._discover_devices()
        if devices:
            existing_entries = self._async_current_entries()
            new_devices = [device for device in devices if not any(entry.data.get(CONF_HOST_IP) == device["ip"] for entry in existing_entries)]
            
            if new_devices:
                # Show discovered devices for the user to configure
                return self.async_show_form(
                    step_id="zeroconf_discovery_selected",
                    data_schema=vol.Schema({
                        vol.Required("device", default=new_devices[0]["ip"]): vol.In({device["ip"]: device["name"] for device in new_devices})
                    }),
                    errors=errors,
                )
            else:
                errors["base"] = "no_new_devices_found"
                return self.async_show_form(
                    step_id="zeroconf_discovery",
                    errors=errors
                )
        else:
            errors["base"] = "no_devices_found"
            return self.async_show_form(
                step_id="zeroconf_discovery",
                errors=errors
            )

    async def async_step_zeroconf_discovery_selected(self, user_input=None):
        """Handle the user's device selection after manual zeroconf scanning."""
        if user_input is not None:
            selected_device_ip = user_input["device"]
            selected_device_name = next(device["name"] for device in self.devices if device["ip"] == selected_device_ip)
            return self.async_create_entry(title=f"{selected_device_name} - {selected_device_ip}", data={CONF_HOST_IP: selected_device_ip})

        return self.async_abort(reason="no_device_selected")

    async def async_step_manual(self, user_input=None):
        errors = {}
        if user_input is not None:
            # if exist
            existing_entries = self._async_current_entries()
            if any(entry.data.get(CONF_HOST_IP) == user_input[CONF_HOST_IP] for entry in existing_entries):
                errors["base"] = "device_already_configured"
            else:
                # if correct
                ip_address = user_input.get(CONF_HOST_IP)
                try:
                    response = await self.hass.async_add_executor_job(
                        requests.get, f"http://{ip_address}/data"
                    )
                    response.raise_for_status()
                    data = response.json()

                    # check json
                    if not data:
                        raise requests.exceptions.RequestException("No data returned")
                except requests.exceptions.RequestException:
                    errors["base"] = "device_not_found"
                    return self.async_show_form(
                        step_id="manual",
                        data_schema=self._get_manual_schema(user_input),
                        errors=errors,
                    )

                entry = self.async_create_entry(title=f"Manual IP Configuration - {user_input[CONF_HOST_IP]}", data=user_input)
            
                # remove device discovered
                self.devices = [device for device in self.devices if device["ip"] != ip_address]
                return entry
            
        data_schema = vol.Schema({
            vol.Required(CONF_HOST_IP): str,
        })

        return self.async_show_form(
            step_id="manual",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                CONF_HOST_IP: "Device IP",
            },
        )
    
    def _get_manual_schema(self, user_input=None):
        """Helper to generate the manual input schema."""
        return vol.Schema({
            vol.Required(CONF_HOST_IP, default=user_input.get(CONF_HOST_IP) if user_input else ""): str,
        })

    async def _discover_devices(self):
        self.devices = []
        zeroconf = await async_get_instance(self.hass)  # Use the shared Zeroconf instance
        loop = asyncio.get_running_loop()
        browser = ServiceBrowser(zeroconf, "_http._tcp.local.", handlers=[self._on_service_state_change])

        def _stop_browser():
            browser.cancel()

        try:
            await asyncio.sleep(5)  # Wait for devices to be discovered
        finally:
            loop.call_soon(_stop_browser)

        return self.devices

    @callback
    def _on_service_state_change(self, zeroconf, service_type, name, state_change):
        if state_change == ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                address = socket.inet_ntoa(info.addresses[0])
                if "bituotechnik" in name.lower():  # Ensure the device name contains 'bituotechnik'
                    # Check if the device is already in the list or already configured
                    if not any(device["ip"] == address for device in self.devices):
                        existing_entries = self._async_current_entries()
                        if not any(entry.data.get(CONF_HOST_IP) == address for entry in existing_entries):
                            self.devices.append({"ip": address, "name": name.split(".")[0]})
