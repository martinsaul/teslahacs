"""TeslaHitch API client.

Replaces teslajsonpy's Controller by talking directly to teslaHitch,
which handles all token management, auth, and proxies commands to the
Tesla Fleet API via tesla_http_proxy.
"""

import json
import logging
import time

import httpx

from .util import SSL_CONTEXT

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30


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
        self._last_update_times: dict[str, float] = {}
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
        url = f"{self.teslahitch_url}/internal/vehicles/{site_id}/live_status"
        resp = await self._client.get(url)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", data)

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

    async def update(
        self,
        vins: set | None = None,
        energy_site_ids: set | None = None,
        update_vehicles: bool = False,
    ) -> dict:
        """Fetch latest data for specified vehicles/energy sites.

        Returns the raw data dict. Updates internal TeslaCar/EnergySite
        objects in-place.
        """
        result = {}

        for vin in vins or set():
            if not vin or not self._polling_enabled.get(vin, True):
                continue
            try:
                data = await self.get_vehicle_data(vin)
                car = self._cars.get(vin)
                if car:
                    car._vehicle_data = data
                    state = data.get("state", "")
                    self._car_online_status[vin] = state == "online"
                self._last_update_times[vin] = time.time()
                result[vin] = data
            except httpx.HTTPStatusError as ex:
                _LOGGER.warning("Failed to update vehicle %s: %s", vin, ex)
                if ex.response.status_code in (401, 403):
                    raise TeslaHitchError(
                        str(ex), code=ex.response.status_code
                    ) from ex
                result[vin] = None
            except Exception as ex:
                _LOGGER.warning("Failed to update vehicle %s: %s", vin, ex)
                result[vin] = None

        for site_id in energy_site_ids or set():
            if not site_id:
                continue
            try:
                data = await self.get_energy_site_data(site_id)
                site = self._energysites.get(site_id)
                if site:
                    site._live_data = data
                result[site_id] = data
            except Exception as ex:
                _LOGGER.warning("Failed to update energy site %s: %s", site_id, ex)
                result[site_id] = None

        if update_vehicles:
            # Re-fetch the products list to detect new/removed vehicles
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
            except Exception as ex:
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
