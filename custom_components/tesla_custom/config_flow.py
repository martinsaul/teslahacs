"""Tesla Config Flow."""

from http import HTTPStatus
import logging

from homeassistant import config_entries, core, exceptions
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_DOMAIN,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.httpx_client import SERVER_SOFTWARE, USER_AGENT
import httpx
from teslajsonpy import Controller as TeslaAPI, TeslaException
from teslajsonpy.const import AUTH_DOMAIN
from teslajsonpy.exceptions import IncompleteCredentials
import voluptuous as vol

from .const import (
    ATTR_POLLING_POLICY_ALWAYS,
    ATTR_POLLING_POLICY_CONNECTED,
    ATTR_POLLING_POLICY_NORMAL,
    CONF_API_PROXY_CERT,
    CONF_API_PROXY_ENABLE,
    CONF_API_PROXY_URL,
    CONF_ENABLE_TESLAMATE,
    CONF_EXPIRATION,
    CONF_INCLUDE_ENERGYSITES,
    CONF_INCLUDE_VEHICLES,
    CONF_POLLING_POLICY,
    CONF_TESLAHITCH_URL,
    CONF_WAKE_ON_START,
    DEFAULT_ENABLE_TESLAMATE,
    DEFAULT_POLLING_POLICY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WAKE_ON_START,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .util import SSL_CONTEXT

_LOGGER = logging.getLogger(__name__)


async def _fetch_teslahitch_config(hass: core.HomeAssistant, teslahitch_url: str) -> dict:
    """Fetch configuration from teslahitch /api/ha/config endpoint."""
    url = f"{teslahitch_url.rstrip('/')}/api/ha/config"
    async with httpx.AsyncClient(verify=SSL_CONTEXT, timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


class TeslaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tesla."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the tesla flow."""
        self.username = None
        self.reauth = False

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""
        return await self.async_step_user(import_config)

    async def async_step_user(self, user_input=None):
        """Handle the config flow - single step via teslahitch."""
        errors = {}

        if user_input is not None:
            existing_entry = self._async_entry_for_username(user_input[CONF_USERNAME])
            if existing_entry and not self.reauth:
                return self.async_abort(reason="already_configured")

            try:
                info = await validate_input(self.hass, user_input)
                info.update({"initial_setup": True})
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"

            if not errors:
                if existing_entry:
                    self.hass.config_entries.async_update_entry(
                        existing_entry, data=info
                    )
                    await self.hass.config_entries.async_reload(existing_entry.entry_id)
                    return self.async_abort(reason="reauth_successful")

                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=info
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_TESLAHITCH_URL): str,
                vol.Required(CONF_USERNAME, default=self.username): str,
                vol.Required(CONF_INCLUDE_VEHICLES, default=True): bool,
                vol.Required(CONF_INCLUDE_ENERGYSITES, default=True): bool,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={},
        )

    async def async_step_reauth(self, data):
        """Handle configuration by re-auth."""
        self.username = data[CONF_USERNAME]
        self.reauth = True
        return await self.async_step_user()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler()

    @callback
    def _async_entry_for_username(self, username):
        """Find an existing entry for a username."""
        for entry in self._async_current_entries():
            if entry.data.get(CONF_USERNAME) == username:
                return entry
        return None


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a option flow for Tesla."""

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(cv.positive_int, vol.Clamp(min=MIN_SCAN_INTERVAL)),
                vol.Optional(
                    CONF_WAKE_ON_START,
                    default=self.config_entry.options.get(
                        CONF_WAKE_ON_START, DEFAULT_WAKE_ON_START
                    ),
                ): bool,
                vol.Required(
                    CONF_POLLING_POLICY,
                    default=self.config_entry.options.get(
                        CONF_POLLING_POLICY, DEFAULT_POLLING_POLICY
                    ),
                ): vol.In(
                    [
                        ATTR_POLLING_POLICY_NORMAL,
                        ATTR_POLLING_POLICY_CONNECTED,
                        ATTR_POLLING_POLICY_ALWAYS,
                    ]
                ),
                vol.Optional(
                    CONF_ENABLE_TESLAMATE,
                    default=self.config_entry.options.get(
                        CONF_ENABLE_TESLAMATE, DEFAULT_ENABLE_TESLAMATE
                    ),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)


async def validate_input(hass: core.HomeAssistant, data) -> dict:
    """Validate the user input allows us to connect.

    Fetches config from teslahitch and validates with Tesla API.
    """

    teslahitch_url = data[CONF_TESLAHITCH_URL]

    try:
        hitch_config = await _fetch_teslahitch_config(hass, teslahitch_url)
    except httpx.HTTPStatusError as ex:
        if ex.response.status_code == 412:
            _LOGGER.error(
                "teslahitch OAuth not completed. Complete the OAuth flow on teslahitch first."
            )
            raise InvalidAuth() from ex
        _LOGGER.error("Failed to fetch config from teslahitch: %s", ex)
        raise CannotConnect() from ex
    except (httpx.ConnectError, httpx.ConnectTimeout) as ex:
        _LOGGER.error("Cannot connect to teslahitch at %s: %s", teslahitch_url, ex)
        raise CannotConnect() from ex

    refresh_token = hitch_config.get("refresh_token", "")
    client_id = hitch_config["client_id"]
    proxy_url = hitch_config["proxy_url"]

    config = {}
    async_client = httpx.AsyncClient(
        headers={USER_AGENT: SERVER_SOFTWARE}, timeout=60, verify=SSL_CONTEXT
    )

    try:
        controller = TeslaAPI(
            async_client,
            email=data[CONF_USERNAME],
            refresh_token=refresh_token,
            access_token=hitch_config.get("access_token", ""),
            update_interval=DEFAULT_SCAN_INTERVAL,
            expiration=hitch_config.get("expiration", 0),
            auth_domain=AUTH_DOMAIN,
            polling_policy=data.get(CONF_POLLING_POLICY, DEFAULT_POLLING_POLICY),
            api_proxy_url=proxy_url,
            client_id=client_id,
        )
        result = await controller.connect(test_login=True)
        config[CONF_TOKEN] = result["refresh_token"]
        config[CONF_ACCESS_TOKEN] = result[CONF_ACCESS_TOKEN]
        config[CONF_EXPIRATION] = result[CONF_EXPIRATION]
        config[CONF_USERNAME] = data[CONF_USERNAME]
        config[CONF_DOMAIN] = AUTH_DOMAIN
        config[CONF_INCLUDE_VEHICLES] = data[CONF_INCLUDE_VEHICLES]
        config[CONF_INCLUDE_ENERGYSITES] = data[CONF_INCLUDE_ENERGYSITES]
        config[CONF_API_PROXY_URL] = proxy_url
        config[CONF_CLIENT_ID] = client_id
        config[CONF_TESLAHITCH_URL] = teslahitch_url

    except IncompleteCredentials as ex:
        _LOGGER.error("Authentication error: %s %s", ex.message, ex)
        raise InvalidAuth() from ex
    except TeslaException as ex:
        if ex.code == HTTPStatus.UNAUTHORIZED or isinstance(ex, IncompleteCredentials):
            _LOGGER.error("Invalid credentials: %s", ex.message)
            raise InvalidAuth() from ex
        _LOGGER.error("Unable to communicate with Tesla API: %s", ex.message)
        raise CannotConnect() from ex
    finally:
        await async_client.aclose()
    _LOGGER.debug("Credentials successfully connected to the Tesla API")
    return config


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
