"""TeslaHitch API client.

Replaces teslajsonpy's Controller by talking directly to teslaHitch,
which handles all token management, auth, and proxies commands to the
Tesla Fleet API via tesla_http_proxy.
"""

import json
import logging
import time

import httpx

from .const import MAX_SCAN_INTERVAL
from .util import SSL_CONTEXT

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30

# Backoff on consecutive fetch failures is capped here so a persistently
# failing target (asleep car, Fleet API EXCEEDED_LIMIT, outage) is probed at
# most once per this many seconds rather than every coordinator tick.
MAX_BACKOFF_INTERVAL = MAX_SCAN_INTERVAL


class TeslaHitchError(Exception):
    """Base exception for TeslaHitch client errors."""

    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.message = message
        self.code = code


class TeslaHitchClient:
    """Client for the teslaHitch API.

    teslaHitch is the sole token authority. This client never touches
    Tesla's auth endpoints directly -- it delegates everything to
    teslaHitch's internal API.
    """

    def __init__(self, teslahitch_url: str, update_interval: int = 660):
        self.teslahitch_url = teslahitch_url.rstrip("/")
        self.update_interval = update_interval

        self._cars: dict = {}  # vin -> TeslaCar
        self._energysites: dict = {}  # site_id -> EnergySite
        self._last_update_times: dict[str, float] = {}  # last SUCCESSFUL fetch
        self._last_attempt_times: dict[str, float] = {}  # last ATTEMPT (throttle key)
        self._consecutive_failures: dict[str, int] = {}  # per-key failure streak
        self._last_wake_up_times: dict[str, float] = {}
        self._car_online_status: dict[str, bool] = {}
        self._polling_enabled: dict[str, bool] = {}
        self._update_intervals: dict[str, int] = {}

        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self):
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                verify=SSL_CONTEXT, timeout=DEFAULT_TIMEOUT
            )

    async def disconnect(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # teslaHitch endpoints
    # ------------------------------------------------------------------

    async def get_config(self) -> dict:
        """Fetch config from teslaHitch (tokens, client_id, proxy_url)."""
        await self._ensure_client()
        url = f"{self.teslahitch_url}/internal/ha/config"
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.json()

    async def connect(self) -> dict:
        """Verify connection to teslaHitch and return config."""
        config = await self.get_config()
        _LOGGER.info("Connected to teslaHitch at %s", self.teslahitch_url)
        return config

    async def list_products(self) -> list[dict]:
        """List all Tesla products (vehicles + energy sites)."""
        await self._ensure_client()
        url = f"{self.teslahitch_url}/internal/products"
        resp = await self._client.get(url)
        resp.raise_for_status()
        data = resp.json()
        # Tesla API returns {"response": [...], "count": N}
        return data.get("response", data if isinstance(data, list) else [])

    async def get_vehicle_data(self, vin: str) -> dict:
        """Fetch full vehicle data for a VIN."""
        await self._ensure_client()
        url = f"{self.teslahitch_url}/internal/vehicles/{vin}/vehicle_data"
        resp = await self._client.get(url)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", data)

    async def get_energy_site_data(self, site_id: str) -> dict:
        """Fetch energy site live status."""
        await self._ensure_client()
        url = f"{self.teslahitch_url}/internal/energy_sites/{site_id}/live_status"
        resp = await self._client.get(url)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", data)

    async def send_energy_command(
        self, site_id: str, endpoint: str, body: dict | None = None
    ) -> dict:
        """Send a command to an energy site via teslaHitch."""
        await self._ensure_client()
        url = f"{self.teslahitch_url}/internal/energy_sites/{site_id}/{endpoint}"
        body_str = json.dumps(body) if body else None
        resp = await self._client.post(url, content=body_str, headers={
            "Content-Type": "application/json"
        } if body_str else None)
        resp.raise_for_status()
        try:
            return resp.json()
        except (json.JSONDecodeError, ValueError):
            return {"result": resp.status_code == 200}

    async def send_command(
        self, vin: str, endpoint: str, body: dict | None = None
    ) -> dict:
        """Send a command to a vehicle via teslaHitch."""
        await self._ensure_client()
        url = f"{self.teslahitch_url}/internal/vehicles/{vin}/command/{endpoint}"
        body_str = json.dumps(body) if body else None
        resp = await self._client.post(url, content=body_str, headers={
            "Content-Type": "application/json"
        } if body_str else None)
        resp.raise_for_status()
        try:
            return resp.json()
        except (json.JSONDecodeError, ValueError):
            return {"result": resp.status_code == 200}

    async def wake_up(self, vin: str) -> dict:
        """Wake up a vehicle."""
        await self._ensure_client()
        url = f"{self.teslahitch_url}/internal/vehicles/{vin}/command/wake_up"
        resp = await self._client.post(url)
        resp.raise_for_status()
        # Record the wake so the poller resumes vehicle_data fetches for a car
        # that was being skipped while asleep.
        self._last_wake_up_times[vin] = time.time()
        try:
            return resp.json()
        except (json.JSONDecodeError, ValueError):
            return {}

    # ------------------------------------------------------------------
    # Raw API passthrough (used by services.py)
    # ------------------------------------------------------------------

    async def api(self, name: str, path_vars: dict | None = None, **kwargs) -> dict:
        """Make a raw API call through teslaHitch.

        This replaces teslajsonpy's controller.api() method used by the
        services integration for arbitrary Tesla API calls.
        """
        path_vars = path_vars or {}
        vin = path_vars.get("vehicle_id", "")
        endpoint = name
        body = kwargs if kwargs else None
        return await self.send_command(vin, endpoint, body)

    # ------------------------------------------------------------------
    # Car / energy site object management
    # ------------------------------------------------------------------

    async def generate_car_objects(self, wake_if_asleep: bool = False):
        """Discover vehicles and create TeslaCar objects."""
        from .tesla_car import TeslaCar

        products = await self.list_products()
        cars = {}
        for product in products:
            vin = product.get("vin")
            if not vin:
                continue

            if wake_if_asleep and product.get("state") == "asleep":
                _LOGGER.info("Waking vehicle %s...", vin)
                try:
                    await self.wake_up(vin)
                except Exception as ex:
                    _LOGGER.warning("Failed to wake %s: %s", vin, ex)

            # Fetch full vehicle data
            try:
                vehicle_data = await self.get_vehicle_data(vin)
            except Exception as ex:
                _LOGGER.warning(
                    "Could not fetch vehicle data for %s, using product listing: %s",
                    vin, ex,
                )
                vehicle_data = product

            car = TeslaCar(vehicle_data, product, self)
            cars[vin] = car
            self._car_online_status[vin] = product.get("state") == "online"
            self._last_update_times[vin] = time.time()
            self._last_wake_up_times[vin] = time.time()
            self._polling_enabled[vin] = True

        self._cars = cars
        return cars

    async def generate_energysite_objects(self):
        """Discover energy sites and create EnergySite objects."""
        from .tesla_energy import EnergySite

        products = await self.list_products()
        sites = {}
        for product in products:
            site_id = product.get("energy_site_id")
            if not site_id:
                continue

            site_id_str = str(site_id)

            try:
                live_data = await self.get_energy_site_data(site_id_str)
            except Exception as ex:
                _LOGGER.warning(
                    "Could not fetch energy site data for %s: %s", site_id, ex
                )
                live_data = {}

            site = EnergySite(product, live_data, self)
            sites[site_id_str] = site

        self._energysites = sites
        return sites

    # ------------------------------------------------------------------
    # Poll throttling
    # ------------------------------------------------------------------

    def _poll_due(self, key: str, interval: int, now: float) -> bool:
        """Whether a real Fleet API fetch for `key` is due.

        Throttling keys off the last ATTEMPT, not the last success. If it
        keyed off the last success, a target that keeps failing (asleep car,
        Fleet API EXCEEDED_LIMIT, outage) would never advance its timestamp
        and would be re-fetched on every coordinator tick (~15s), silently
        blowing the Tesla Fleet API quota. On top of the base interval,
        consecutive failures add exponential backoff up to
        MAX_BACKOFF_INTERVAL so a persistently failing target is probed
        sparingly.
        """
        last_attempt = self._last_attempt_times.get(key, 0)
        if not last_attempt:
            return True
        fails = self._consecutive_failures.get(key, 0)
        wait = interval
        if fails > 1:
            # First retry waits one interval; each further consecutive failure
            # doubles the wait (2x, 4x, 8x, ...) up to the cap.
            wait = min(interval * (2 ** min(fails - 1, 6)), MAX_BACKOFF_INTERVAL)
        return now - last_attempt >= wait

    def _note_success(self, key: str, now: float) -> None:
        self._last_update_times[key] = now
        self._consecutive_failures[key] = 0

    def _note_failure(self, key: str) -> None:
        self._consecutive_failures[key] = (
            self._consecutive_failures.get(key, 0) + 1
        )

    async def update(
        self,
        vins: set | None = None,
        energy_site_ids: set | None = None,
        update_vehicles: bool = False,
    ) -> dict:
        """Fetch latest data for specified vehicles/energy sites.

        Returns the raw data dict. Updates internal TeslaCar/EnergySite
        objects in-place. Real API calls are throttled to update_interval
        seconds per vehicle/site (with failure backoff); cached data is
        returned between calls.
        """
        result = {}
        now = time.time()

        for vin in vins or set():
            if not vin or not self._polling_enabled.get(vin, True):
                continue

            interval = self._update_intervals.get(vin, self.update_interval)

            # Sleep-awareness: don't spend a vehicle_data call (which also
            # wakes the car and drains the 12V battery) on a car we know is
            # asleep/offline. It is re-detected as online by the cheap
            # products poll below; a recent wake request resumes polling.
            online = self._car_online_status.get(vin, True)
            wake_recent = (
                now - self._last_wake_up_times.get(vin, 0)
            ) < interval
            if not online and not wake_recent:
                car = self._cars.get(vin)
                if car:
                    result[vin] = car._vehicle_data
                continue

            if not self._poll_due(vin, interval, now):
                car = self._cars.get(vin)
                if car:
                    result[vin] = car._vehicle_data
                continue

            # Claim the slot before awaiting so two coordinators firing on the
            # same tick don't both slip through and double-call.
            self._last_attempt_times[vin] = now

            try:
                data = await self.get_vehicle_data(vin)
                car = self._cars.get(vin)
                if car:
                    car._vehicle_data = data
                    state = data.get("state", "")
                    self._car_online_status[vin] = state == "online"
                self._note_success(vin, now)
                result[vin] = data
            except httpx.HTTPStatusError as ex:
                self._note_failure(vin)
                _LOGGER.warning("Failed to update vehicle %s: %s", vin, ex)
                if ex.response.status_code in (401, 403):
                    raise TeslaHitchError(
                        str(ex), code=ex.response.status_code
                    ) from ex
                result[vin] = None
            except Exception as ex:
                self._note_failure(vin)
                _LOGGER.warning("Failed to update vehicle %s: %s", vin, ex)
                result[vin] = None

        for site_id in energy_site_ids or set():
            if not site_id:
                continue

            if not self._poll_due(site_id, self.update_interval, now):
                site = self._energysites.get(site_id)
                if site:
                    result[site_id] = site._live_data
                continue

            self._last_attempt_times[site_id] = now

            try:
                data = await self.get_energy_site_data(site_id)
                site = self._energysites.get(site_id)
                if site:
                    site._live_data = data
                self._note_success(site_id, now)
                result[site_id] = data
            except Exception as ex:
                self._note_failure(site_id)
                _LOGGER.warning("Failed to update energy site %s: %s", site_id, ex)
                result[site_id] = None

        if update_vehicles:
            # Re-fetch the products list to detect new/removed vehicles and
            # refresh online/asleep state, throttled (with backoff) like
            # vehicle data fetches.
            key = "__vehicle_list__"
            if self._poll_due(key, self.update_interval, now):
                self._last_attempt_times[key] = now
                try:
                    products = await self.list_products()
                    for product in products:
                        vin = product.get("vin")
                        if vin:
                            self._car_online_status[vin] = (
                                product.get("state") == "online"
                            )
                            car = self._cars.get(vin)
                            if car:
                                car._car_data = product
                    self._note_success(key, now)
                except Exception as ex:
                    self._note_failure(key)
                    _LOGGER.debug("Failed to refresh vehicle list: %s", ex)

        return result or None

    # ------------------------------------------------------------------
    # State accessors (replaces Controller methods)
    # ------------------------------------------------------------------

    def get_last_update_time(self, vin: str = "") -> float:
        return self._last_update_times.get(vin, 0)

    def get_last_wake_up_time(self, vin: str = "") -> float:
        return self._last_wake_up_times.get(vin, 0)

    def is_car_online(self, vin: str = "") -> bool:
        return self._car_online_status.get(vin, False)

    def get_updates(self, vin: str = "") -> bool | None:
        return self._polling_enabled.get(vin)

    def set_updates(self, vin: str = "", value: bool = True):
        self._polling_enabled[vin] = value

    def get_update_interval_vin(self, vin: str = "") -> int:
        return self._update_intervals.get(vin, self.update_interval)

    def set_update_interval_vin(self, vin: str = "", value: int = 660):
        self._update_intervals[vin] = value
