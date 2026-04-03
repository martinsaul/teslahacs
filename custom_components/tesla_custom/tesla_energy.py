"""Tesla energy site data model.

Replaces teslajsonpy.energy.EnergySite with a thin wrapper around the
raw Tesla API energy site response. Commands are sent via TeslaHitchClient.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tesla_client import TeslaHitchClient

_LOGGER = logging.getLogger(__name__)

# Constants (previously from teslajsonpy.const)
RESOURCE_TYPE_BATTERY = "battery"
RESOURCE_TYPE_SOLAR = "solar"
GRID_ACTIVE = "Active"
BACKUP_RESERVE_MIN = 0
BACKUP_RESERVE_MAX = 100


class EnergySite:
    """Represents a Tesla energy site (Powerwall, Solar).

    Wraps the raw product listing + live_status data from the Tesla API.
    """

    def __init__(
        self,
        product_data: dict,
        live_data: dict,
        client: TeslaHitchClient,
    ) -> None:
        self._product_data = product_data
        self._live_data = live_data
        self._client = client

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def energysite_id(self) -> str:
        return str(self._product_data.get("energy_site_id", ""))

    @property
    def site_name(self) -> str:
        return self._product_data.get("site_name", "Tesla Energy")

    @property
    def resource_type(self) -> str:
        return self._product_data.get("resource_type", "")

    @property
    def version(self) -> str:
        return self._product_data.get("version", "")

    @property
    def has_load_meter(self) -> bool:
        components = self._product_data.get("components", {})
        return bool(components.get("load_meter"))

    @property
    def has_solar(self) -> bool:
        components = self._product_data.get("components", {})
        return bool(components.get("solar"))

    # ------------------------------------------------------------------
    # Live data
    # ------------------------------------------------------------------

    @property
    def solar_power(self) -> float:
        return self._live_data.get("solar_power", 0.0)

    @property
    def grid_power(self) -> float:
        return self._live_data.get("grid_power", 0.0)

    @property
    def load_power(self) -> float:
        return self._live_data.get("load_power", 0.0)

    @property
    def battery_power(self) -> float:
        return self._live_data.get("battery_power", 0.0)

    @property
    def percentage_charged(self) -> float:
        return self._live_data.get("percentage_charged", 0.0)

    @property
    def energy_left(self) -> float:
        return self._live_data.get("energy_left", 0.0)

    @property
    def grid_status(self) -> str:
        return self._live_data.get("grid_status", "Unknown")

    @property
    def backup_reserve_percent(self) -> float:
        return self._live_data.get(
            "backup_reserve_percent",
            self._product_data.get("backup_reserve_percent", 0.0),
        )

    @property
    def grid_charging(self) -> bool:
        components = self._product_data.get("components", {})
        return bool(components.get("grid_charging"))

    @property
    def export_rule(self) -> str:
        components = self._product_data.get("components", {})
        return components.get("customer_preferred_export_rule", "")

    @property
    def operation_mode(self) -> str:
        return self._product_data.get("default_real_mode", "")

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def _cmd(self, endpoint: str, body: dict | None = None):
        site_id = self.energysite_id
        return await self._client.send_command(site_id, endpoint, body)

    async def set_reserve_percent(self, value: int):
        return await self._cmd("backup", {"backup_reserve_percent": int(value)})

    async def set_operation_mode(self, mode: str):
        return await self._cmd("operation", {"default_real_mode": mode})

    async def set_export_rule(self, rule: str):
        return await self._cmd("grid_import_export", {
            "customer_preferred_export_rule": rule
        })

    async def set_grid_charging(self, on: bool):
        return await self._cmd("grid_import_export", {
            "disallow_charge_from_grid_with_solar_installed": not on
        })
