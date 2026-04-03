"""Support for Tesla services."""

import logging

from homeassistant.const import ATTR_COMMAND, CONF_EMAIL, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    ATTR_PARAMETERS,
    ATTR_PATH_VARS,
    ATTR_VIN,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SERVICE_API,
    SERVICE_SCAN_INTERVAL,
)
from .tesla_client import TeslaHitchClient

_LOGGER = logging.getLogger(__name__)


API_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_EMAIL): vol.All(cv.string, vol.Length(min=1)),
        vol.Required(ATTR_COMMAND, default=""): vol.All(cv.string, vol.Length(min=1)),
        vol.Optional(ATTR_PARAMETERS, default={}): dict,
    }
)

SCAN_INTERVAL_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_EMAIL): vol.All(cv.string, vol.Length(min=1)),
        vol.Optional(ATTR_VIN): vol.All(cv.string, vol.Length(min=1)),
        vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=-1, max=3600)
        ),
    }
)


def _get_controller(hass, email: str = "") -> TeslaHitchClient:
    """Get the TeslaHitchClient for a given email (or the only one)."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if len(entries) > 1 and not email:
        raise ValueError("Email address missing")
    for entry in entries:
        if len(entries) > 1 and entry.title != email:
            continue
        return hass.data[DOMAIN][entry.entry_id]["controller"]
    raise ValueError(f"No Tesla controllers found for email {email}")


@callback
def async_setup_services(hass) -> None:
    """Set up services for Tesla integration."""

    async def async_call_tesla_service(service_call) -> None:
        """Call correct Tesla service."""
        service = service_call.service
        if service == SERVICE_API:
            return await api(service_call)
        elif service == SERVICE_SCAN_INTERVAL:
            return await set_update_interval(service_call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_API,
        async_call_tesla_service,
        schema=API_SCHEMA,
        supports_response=True,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SCAN_INTERVAL,
        async_call_tesla_service,
        schema=SCAN_INTERVAL_SCHEMA,
        supports_response=True,
    )

    async def api(call):
        """Handle api service request."""
        service_data = call.data
        email = service_data.get(CONF_EMAIL, "")
        controller = _get_controller(hass, email)

        command = call.data.get(ATTR_COMMAND)
        parameters: dict = call.data.get(ATTR_PARAMETERS, {})
        _LOGGER.debug(
            "Service api called with email: %s command: %s parameters: %s",
            email,
            command,
            parameters,
        )
        path_vars = parameters.pop(ATTR_PATH_VARS, {})
        return await controller.api(name=command, path_vars=path_vars, **parameters)

    async def set_update_interval(call):
        """Handle polling interval service request."""
        service_data = call.data
        email = service_data.get(CONF_EMAIL, "")
        controller = _get_controller(hass, email)

        vin = service_data.get(ATTR_VIN, "")
        update_interval = service_data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        _LOGGER.debug(
            "Service %s called with email: %s vin %s interval %s",
            SERVICE_SCAN_INTERVAL,
            email,
            vin,
            update_interval,
        )
        old_update_interval = controller.get_update_interval_vin(vin=vin)
        if old_update_interval != update_interval:
            _LOGGER.debug(
                "Changing update_interval from %s to %s for %s",
                old_update_interval,
                update_interval,
                vin,
            )
            controller.set_update_interval_vin(vin=vin, value=update_interval)
        return {
            "result": True,
            "message": f"Update interval set to {update_interval} for VIN {vin}",
        }


@callback
def async_unload_services(hass) -> None:
    """Unload Tesla services."""
    hass.services.async_remove(DOMAIN, SERVICE_API)
    hass.services.async_remove(DOMAIN, SERVICE_SCAN_INTERVAL)
