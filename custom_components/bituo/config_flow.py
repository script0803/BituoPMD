"""Adds config flow for Bituo."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
import requests
from .const import DOMAIN, CONF_HOST_IP

_LOGGER = logging.getLogger(__name__)

class BituoFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Bituo in Home Assistant."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            host_ip = user_input[CONF_HOST_IP]
            try:
                # Validate connection to the device
                await self.hass.async_add_executor_job(
                    requests.get, f"http://{host_ip}/data"
                )
                return self.async_create_entry(
                    title="Bituo",
                    data=user_input
                )
            except Exception as e:
                errors["base"] = "cannot_connect"
                _LOGGER.error("Error connecting to Bituo device: %s", e)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST_IP): str
            }),
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BituoOptionsFlowHandler(config_entry)

class BituoOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Bituo."""

    def __init__(self, config_entry):
        """Initialize Bituo options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Optional(CONF_HOST_IP, default=self.config_entry.options.get(CONF_HOST_IP, "")): str
                })
            )

        return self.async_create_entry(title="", data=user_input)

# by Script0803