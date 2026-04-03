"""Support for Tesla cars."""

import asyncio
from datetime import timedelta
from functools import partial
import logging
from typing import Any

import async_timeout
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_ENABLE_TESLAMATE,
    CONF_TESLAHITCH_URL,
    CONF_WAKE_ON_START,
    DATA_LISTENER,
    DEFAULT_ENABLE_TESLAMATE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WAKE_ON_START,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    PLATFORMS,
)
from .services import async_setup_services, async_unload_services
from .tesla_client import TeslaHitchClient, TeslaHitchError
from .teslamate import TeslaMate

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry):
    """Set up Tesla as config entry."""
    hass.data.setdefault(DOMAIN, {})
    config = config_entry.data

    if not hass.data[DOMAIN]:
        async_setup_services(hass)

    teslahitch_url = config.get(CONF_TESLAHITCH_URL)
    if not teslahitch_url:
        _LOGGER.error("No teslaHitch URL configured")
        return False

    controller = TeslaHitchClient(
        teslahitch_url=teslahitch_url,
        update_interval=config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        ),
    )

    try:
        await controller.connect()
    except Exception as ex:
        _LOGGER.error("Cannot connect to teslaHitch at %s: %s", teslahitch_url, ex)
        raise ConfigEntryNotReady(
            f"Cannot connect to teslaHitch: {ex}"
        ) from ex

    try:
        wake_if_asleep = config_entry.options.get(
            CONF_WAKE_ON_START, DEFAULT_WAKE_ON_START
        )
        if config_entry.data.get("initial_setup"):
            wake_if_asleep = True

        cars = await controller.generate_car_objects(wake_if_asleep=wake_if_asleep)

        hass.config_entries.async_update_entry(
            config_entry, data={**config_entry.data, "initial_setup": False}
        )

    except Exception as ex:
        await controller.disconnect()
        _LOGGER.error("Unable to fetch vehicles from Tesla API: %s", ex)
        raise ConfigEntryNotReady(
            f"Unable to fetch vehicles: {ex}"
        ) from ex

    try:
        energysites = await controller.generate_energysite_objects()
    except Exception as ex:
        await controller.disconnect()
        _LOGGER.error("Unable to fetch energy sites from Tesla API: %s", ex)
        raise ConfigEntryNotReady(
            f"Unable to fetch energy sites: {ex}"
        ) from ex

    reload_lock = asyncio.Lock()
    _partial_coordinator = partial(
        TeslaDataUpdateCoordinator,
        hass,
        config_entry=config_entry,
        controller=controller,
        reload_lock=reload_lock,
        update_vehicles=False,
    )
    energy_coordinators = {
        energy_site_id: _partial_coordinator(energy_site_id=energy_site_id)
        for energy_site_id in energysites
    }
    car_coordinators = {vin: _partial_coordinator(vin=vin) for vin in cars}
    coordinators = {**energy_coordinators, **car_coordinators}

    if car_coordinators:
        update_vehicles_coordinator = _partial_coordinator(update_vehicles=True)
        coordinators["update_vehicles"] = update_vehicles_coordinator
        # The update_vehicles coordinator needs a listener to keep it polling,
        # even though individual car coordinators handle their own updates.
        update_vehicles_coordinator.async_add_listener(lambda: None)

    teslamate = TeslaMate(hass=hass, cars=cars, coordinators=coordinators)

    enable_teslamate = config_entry.options.get(
        CONF_ENABLE_TESLAMATE, DEFAULT_ENABLE_TESLAMATE
    )

    await teslamate.enable(enable_teslamate)

    hass.data[DOMAIN][config_entry.entry_id] = {
        "controller": controller,
        "coordinators": coordinators,
        "cars": cars,
        "energysites": energysites,
        "teslamate": teslamate,
        DATA_LISTENER: [config_entry.add_update_listener(update_listener)],
    }
    _LOGGER.debug("Connected to the Tesla API via teslaHitch")

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_unload_entry(hass, config_entry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    controller: TeslaHitchClient = entry_data["controller"]
    await controller.disconnect()

    for listener in entry_data[DATA_LISTENER]:
        listener()

    await entry_data["teslamate"].unload()

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)
        _LOGGER.debug("Unloaded entry for %s", config_entry.title)

        if not hass.data[DOMAIN]:
            async_unload_services(hass)

        return True

    return False


async def update_listener(hass, config_entry):
    """Update when config_entry options update."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    controller: TeslaHitchClient = entry_data["controller"]
    old_update_interval = controller.update_interval
    controller.update_interval = config_entry.options.get(
        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
    )
    if old_update_interval != controller.update_interval:
        _LOGGER.debug(
            "Changing scan_interval from %s to %s",
            old_update_interval,
            controller.update_interval,
        )

    enable_teslamate = config_entry.options.get(
        CONF_ENABLE_TESLAMATE, DEFAULT_ENABLE_TESLAMATE
    )

    await entry_data["teslamate"].enable(enable_teslamate)


class TeslaDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Tesla data."""

    def __init__(
        self,
        hass,
        *,
        config_entry,
        controller: TeslaHitchClient,
        reload_lock: asyncio.Lock,
        vin: str | None = None,
        energy_site_id: str | None = None,
        update_vehicles: bool = False,
    ) -> None:
        """Initialize global Tesla data updater."""
        self.controller = controller
        self.config_entry = config_entry
        self.reload_lock = reload_lock
        self.vin = vin
        self.vins = {vin} if vin else set()
        self.energy_site_id = energy_site_id
        self.energy_site_ids = {energy_site_id} if energy_site_id else set()
        self.update_vehicles = update_vehicles
        self._cancel_debounce_timer = None
        self._debounce_last_run = None
        self.last_update_time: float | None = None
        self.assumed_state = True

        update_interval = timedelta(seconds=MIN_SCAN_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        controller = self.controller

        data = None
        try:
            async with async_timeout.timeout(30):
                data = await controller.update(
                    vins=self.vins,
                    energy_site_ids=self.energy_site_ids,
                    update_vehicles=self.update_vehicles,
                )
        except TeslaHitchError as err:
            if err.code in (401, 403):
                _LOGGER.warning(
                    "Tesla API returned %s during update, reloading integration...",
                    err.code,
                )
                if not self.reload_lock.locked():
                    async with self.reload_lock:
                        await self.hass.config_entries.async_reload(
                            self.config_entry.entry_id
                        )
                return
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        else:
            if data is None and self.last_update_time is not None:
                _LOGGER.warning(
                    "Tesla controller returned no data, reloading integration..."
                )
                if not self.reload_lock.locked():
                    async with self.reload_lock:
                        await self.hass.config_entries.async_reload(
                            self.config_entry.entry_id
                        )
                return
            if vin := self.vin:
                self.last_update_time = controller.get_last_update_time(vin=vin)
                self.assumed_state = not controller.is_car_online(vin=vin) and (
                    self.last_update_time - controller.get_last_wake_up_time(vin=vin)
                    > controller.update_interval
                )
        return data

    @callback
    def async_update_listeners_debounced(
        self, delay_since_last=0.1, max_delay=1.0
    ) -> None:
        """Debounced version of async_update_listeners."""
        if self._cancel_debounce_timer:
            self._cancel_debounce_timer()

        self._cancel_debounce_timer = async_call_later(
            self.hass, delay_since_last, partial(self._async_debounced, max_delay)
        )

    @callback
    def _async_debounced(self, max_delay: float, *args: Any) -> None:
        """Debounce method that waits a certain delay since the last update."""
        now = self.hass.loop.time()
        if not self._debounce_last_run or now - self._debounce_last_run >= max_delay:
            self._debounce_last_run = now
            self.async_update_listeners()
        else:
            self._cancel_debounce_timer = async_call_later(
                self.hass,
                max_delay - (now - self._debounce_last_run),
                partial(self._async_debounced, max_delay),
            )
