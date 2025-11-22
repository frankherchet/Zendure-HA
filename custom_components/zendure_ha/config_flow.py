"""Config flow for Zendure Integration integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .api import Api
from .const import (
    CONF_DEVICE_KEY,
    CONF_DEVICE_NAME,
    CONF_MQTTLOG,
    CONF_MQTTPORT,
    CONF_MQTTPSW,
    CONF_MQTTSERVER,
    CONF_MQTTUSER,
    CONF_P1METER,
    CONF_PRODUCT_KEY,
    CONF_PRODUCT_MODEL,
    CONF_SIM,
    DOMAIN,
)
from .manager import ZendureConfigEntry

_LOGGER = logging.getLogger(__name__)


class ZendureConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zendure Integration."""

    VERSION = 1
    _input_data: dict[str, Any]

    def __init__(self) -> None:
        """Initialize."""
        self._user_input: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Step when user initializes a integration."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._user_input = user_input

            try:
                # Validate connection (optional, maybe just check if we can connect to MQTT?)
                # For now, we assume the input is correct and proceed to create the entry.
                # We might want to verify MQTT connection here.

                await self.async_set_unique_id("Zendure", raise_on_progress=False)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Zendure", data=self._user_input)

            except Exception as err:  # pylint: disable=broad-except
                errors["base"] = f"invalid input {err}"

        schema = vol.Schema(
            {
                vol.Required(CONF_MQTTSERVER): str,
                vol.Required(CONF_MQTTPORT, default=1883): int,
                vol.Required(CONF_MQTTUSER): str,
                vol.Optional(CONF_MQTTPSW): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD,
                    ),
                ),
                vol.Required(CONF_DEVICE_NAME): str,
                vol.Required(CONF_DEVICE_KEY): str,
                vol.Required(CONF_PRODUCT_KEY): str,
                vol.Required(CONF_PRODUCT_MODEL): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=sorted(list(Api.createdevice.keys())),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                ),
                vol.Required(CONF_P1METER, description={"suggested_value": "sensor.power_actual"}): selector.EntitySelector(),
                vol.Required(CONF_MQTTLOG): bool,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Add reconfigure step to allow to reconfigure a config entry."""
        errors: dict[str, str] = {}

        entry = self._get_reconfigure_entry()
        
        if user_input is not None:
            self._user_input = self._user_input | user_input
            
            try:
                await self.async_set_unique_id("Zendure", raise_on_progress=False)
                self._abort_if_unique_id_mismatch()

                return self.async_update_reload_and_abort(entry, data=self._user_input)
            except Exception as err:
                 errors["base"] = f"invalid input {err}"

        schema = vol.Schema(
            {
                vol.Required(CONF_MQTTSERVER, default=entry.data.get(CONF_MQTTSERVER)): str,
                vol.Required(CONF_MQTTPORT, default=entry.data.get(CONF_MQTTPORT, 1883)): int,
                vol.Required(CONF_MQTTUSER, default=entry.data.get(CONF_MQTTUSER)): str,
                vol.Optional(CONF_MQTTPSW, default=entry.data.get(CONF_MQTTPSW)): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD,
                    ),
                ),
                vol.Required(CONF_DEVICE_NAME, default=entry.data.get(CONF_DEVICE_NAME)): str,
                vol.Required(CONF_DEVICE_KEY, default=entry.data.get(CONF_DEVICE_KEY)): str,
                vol.Required(CONF_PRODUCT_KEY, default=entry.data.get(CONF_PRODUCT_KEY)): str,
                vol.Required(CONF_PRODUCT_MODEL, default=entry.data.get(CONF_PRODUCT_MODEL)): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=sorted(list(Api.createdevice.keys())),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                ),
                vol.Required(CONF_P1METER, default=entry.data.get(CONF_P1METER)): selector.EntitySelector(),
                vol.Required(CONF_MQTTLOG, default=entry.data.get(CONF_MQTTLOG)): bool,
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(_config_entry: ZendureConfigEntry) -> ZendureOptionsFlowHandler:
        """Get the options flow for this handler."""
        return ZendureOptionsFlowHandler()


class ZendureOptionsFlowHandler(OptionsFlow):
    """Handles the options flow."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle options flow."""
        if user_input is not None:
            data = self.config_entry.data | user_input
            self.hass.config_entries.async_update_entry(self.config_entry, data=data)
            return self.async_create_entry(title="", data=data)

        options_schema = vol.Schema(
            {
                vol.Required(CONF_P1METER, default=self.config_entry.data[CONF_P1METER]): str,
                vol.Required(CONF_MQTTLOG, default=self.config_entry.data[CONF_MQTTLOG]): bool,
                vol.Optional(CONF_SIM, default=self.config_entry.data.get(CONF_SIM, False)): bool,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(options_schema, self.config_entry.data),
        )


class ZendureConnectionError(HomeAssistantError):
    """Error to indicate there is a connection issue with Zendure Integration."""

    def __init__(self) -> None:
        """Initialize the connection error."""
        super().__init__("Zendure Integration")
