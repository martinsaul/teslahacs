"""Tesla car data model.

Replaces teslajsonpy.car.TeslaCar with a thin wrapper around the raw
Tesla API vehicle_data response. Commands are sent via TeslaHitchClient.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .tesla_client import TeslaHitchClient

_LOGGER = logging.getLogger(__name__)


class TeslaCar:
    """Represents a Tesla vehicle.

    Wraps the raw vehicle_data dict from the Tesla API and provides
    property accessors matching the teslajsonpy interface. Commands
    are dispatched to teslaHitch.
    """

    def __init__(
        self,
        vehicle_data: dict,
        car_data: dict,
        client: TeslaHitchClient,
    ) -> None:
        # Full vehicle_data response (charge_state, climate_state, etc.)
        self._vehicle_data: dict = vehicle_data
        # Top-level product entry (id, vin, state, display_name)
        self._car_data: dict = car_data
        self._client = client

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _charge(self, key: str, default=None):
        return self._vehicle_data.get("charge_state", {}).get(key, default)

    def _climate(self, key: str, default=None):
        return self._vehicle_data.get("climate_state", {}).get(key, default)

    def _drive(self, key: str, default=None):
        return self._vehicle_data.get("drive_state", {}).get(key, default)

    def _vehicle(self, key: str, default=None):
        return self._vehicle_data.get("vehicle_state", {}).get(key, default)

    def _config(self, key: str, default=None):
        return self._vehicle_data.get("vehicle_config", {}).get(key, default)

    def _gui(self, key: str, default=None):
        return self._vehicle_data.get("gui_settings", {}).get(key, default)

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def vin(self) -> str:
        return (
            self._vehicle_data.get("vin")
            or self._car_data.get("vin", "")
        )

    @property
    def id(self) -> int:
        return (
            self._vehicle_data.get("id")
            or self._car_data.get("id", 0)
        )

    @property
    def vehicle_id(self) -> int:
        return (
            self._vehicle_data.get("vehicle_id")
            or self._car_data.get("vehicle_id", 0)
        )

    @property
    def display_name(self) -> str | None:
        return (
            self._vehicle_data.get("display_name")
            or self._car_data.get("display_name")
        )

    @property
    def state(self) -> str:
        return (
            self._vehicle_data.get("state")
            or self._car_data.get("state", "unknown")
        )

    @property
    def is_on(self) -> bool:
        return self.state == "online"

    @property
    def car_type(self) -> str:
        return self._config("car_type", "")

    @property
    def car_version(self) -> str | None:
        return self._vehicle("car_version")

    # ------------------------------------------------------------------
    # Charge state
    # ------------------------------------------------------------------

    @property
    def charging_state(self) -> str | None:
        return self._charge("charging_state")

    @property
    def battery_level(self) -> int | None:
        return self._charge("battery_level")

    @property
    def usable_battery_level(self) -> int | None:
        return self._charge("usable_battery_level")

    @property
    def charge_limit_soc(self) -> int | None:
        return self._charge("charge_limit_soc")

    @property
    def charge_limit_soc_min(self) -> int | None:
        return self._charge("charge_limit_soc_min")

    @property
    def charge_limit_soc_max(self) -> int | None:
        return self._charge("charge_limit_soc_max")

    @property
    def battery_range(self) -> float | None:
        return self._charge("battery_range")

    @property
    def ideal_battery_range(self) -> float | None:
        return self._charge("ideal_battery_range")

    @property
    def charge_rate(self) -> float | None:
        return self._charge("charge_rate")

    @property
    def time_to_full_charge(self) -> float | None:
        return self._charge("time_to_full_charge")

    @property
    def charge_energy_added(self) -> float | None:
        return self._charge("charge_energy_added")

    @property
    def charge_miles_added_rated(self) -> float | None:
        return self._charge("charge_miles_added_rated")

    @property
    def charge_miles_added_ideal(self) -> float | None:
        return self._charge("charge_miles_added_ideal")

    @property
    def charge_current_request(self) -> int | None:
        return self._charge("charge_current_request")

    @property
    def charge_current_request_max(self) -> int | None:
        return self._charge("charge_current_request_max")

    @property
    def charger_power(self) -> int | None:
        return self._charge("charger_power")

    @property
    def charger_voltage(self) -> int | None:
        return self._charge("charger_voltage")

    @property
    def charger_actual_current(self) -> int | None:
        return self._charge("charger_actual_current")

    @property
    def charger_phases(self) -> int | None:
        return self._charge("charger_phases")

    @property
    def charge_port_door_open(self) -> bool:
        return bool(self._charge("charge_port_door_open"))

    @property
    def is_charge_port_door_open(self) -> bool:
        return self.charge_port_door_open

    @property
    def charge_port_latch(self) -> str | None:
        return self._charge("charge_port_latch")

    @property
    def conn_charge_cable(self) -> str | None:
        return self._charge("conn_charge_cable")

    @property
    def fast_charger_present(self) -> bool:
        return bool(self._charge("fast_charger_present"))

    @property
    def fast_charger_brand(self) -> str | None:
        return self._charge("fast_charger_brand")

    @property
    def fast_charger_type(self) -> str | None:
        return self._charge("fast_charger_type")

    @property
    def scheduled_charging_mode(self) -> str | None:
        return self._charge("scheduled_charging_mode")

    @property
    def scheduled_charging_start_time_app(self) -> int | None:
        return self._charge("scheduled_charging_start_time_app")

    @property
    def is_preconditioning_enabled(self) -> bool:
        return bool(self._charge("preconditioning_enabled"))

    @property
    def is_preconditioning_weekday_only(self) -> bool:
        return bool(self._charge("preconditioning_weekday_only"))

    @property
    def is_off_peak_charging_enabled(self) -> bool:
        return bool(self._charge("off_peak_charging_enabled"))

    @property
    def is_off_peak_charging_weekday_only(self) -> bool:
        return bool(self._charge("off_peak_charging_weekday_only"))

    @property
    def off_peak_hours_end_time(self) -> int | None:
        return self._charge("off_peak_hours_end_time")

    @property
    def scheduled_departure_time_minutes(self) -> int | None:
        return self._charge("scheduled_departure_time_minutes")

    @property
    def gui_range_display(self) -> str | None:
        return self._gui("gui_range_display")

    @property
    def gui_distance_units(self) -> str | None:
        return self._gui("gui_distance_units")

    # ------------------------------------------------------------------
    # Climate state
    # ------------------------------------------------------------------

    @property
    def inside_temp(self) -> float | None:
        return self._climate("inside_temp")

    @property
    def outside_temp(self) -> float | None:
        return self._climate("outside_temp")

    @property
    def is_climate_on(self) -> bool:
        return bool(self._climate("is_climate_on"))

    @property
    def is_preconditioning(self) -> bool:
        return bool(self._climate("is_preconditioning"))

    @property
    def driver_temp_setting(self) -> float | None:
        return self._climate("driver_temp_setting")

    @property
    def max_avail_temp(self) -> float | None:
        return self._climate("max_avail_temp")

    @property
    def min_avail_temp(self) -> float | None:
        return self._climate("min_avail_temp")

    @property
    def defrost_mode(self) -> int:
        return self._climate("defrost_mode", 0)

    @property
    def climate_keeper_mode(self) -> str | int | None:
        return self._climate("climate_keeper_mode")

    @property
    def bioweapon_mode(self) -> bool:
        return bool(self._climate("bioweapon_mode"))

    @property
    def cabin_overheat_protection(self) -> str | None:
        return self._climate("cabin_overheat_protection")

    @property
    def steering_wheel_heater(self) -> bool:
        return bool(self._climate("steering_wheel_heater"))

    @property
    def is_steering_wheel_heater_on(self) -> bool:
        return bool(self._climate("steering_wheel_heat_high")) or bool(
            self._climate("steering_wheel_heater")
        )

    @property
    def is_auto_steering_wheel_heat(self) -> bool:
        return bool(self._climate("auto_steering_wheel_heat"))

    @property
    def has_seat_cooling(self) -> bool:
        return bool(self._config("has_seat_cooling"))

    @property
    def rear_seat_heaters(self) -> int | None:
        return self._config("rear_seat_heaters")

    @property
    def third_row_seats(self) -> str | None:
        return self._config("third_row_seats")

    def get_seat_heater_status(self, seat_id: int) -> int | None:
        """Return seat heater level for given seat_id."""
        seat_map = {
            0: "seat_heater_left",
            1: "seat_heater_right",
            2: "seat_heater_rear_left",
            4: "seat_heater_rear_center",
            5: "seat_heater_rear_right",
            6: "seat_heater_third_row_left",
            7: "seat_heater_third_row_right",
        }
        key = seat_map.get(seat_id)
        if key:
            return self._climate(key)
        return None

    def get_seat_cooler_status(self, seat_id: int) -> int | None:
        """Return seat cooler level for given seat_id."""
        seat_map = {
            1: "seat_fan_front_left",
            2: "seat_fan_front_right",
        }
        key = seat_map.get(seat_id)
        if key:
            return self._climate(key)
        return None

    def get_heated_steering_wheel_level(self) -> int | None:
        """Return heated steering wheel level (None if not variable)."""
        return self._climate("steering_wheel_heat_level")

    @property
    def is_auto_seat_climate_left(self) -> bool:
        return bool(self._climate("auto_seat_climate_left"))

    @property
    def is_auto_seat_climate_right(self) -> bool:
        return bool(self._climate("auto_seat_climate_right"))

    def __getattr__(self, name: str):
        """Handle dynamic attribute access for is_auto_seat_climate_{seat}."""
        if name.startswith("is_auto_seat_climate_"):
            seat = name[len("is_auto_seat_climate_"):]
            return bool(self._climate(f"auto_seat_climate_{seat}"))
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    # ------------------------------------------------------------------
    # Drive state
    # ------------------------------------------------------------------

    @property
    def latitude(self) -> float | None:
        return self._drive("latitude")

    @property
    def longitude(self) -> float | None:
        return self._drive("longitude")

    @property
    def heading(self) -> int | None:
        return self._drive("heading")

    @property
    def speed(self) -> int | None:
        return self._drive("speed")

    @property
    def shift_state(self) -> str | None:
        return self._drive("shift_state")

    @property
    def active_route_latitude(self) -> float | None:
        return self._drive("active_route_latitude")

    @property
    def active_route_longitude(self) -> float | None:
        return self._drive("active_route_longitude")

    @property
    def active_route_miles_to_arrival(self) -> float | None:
        return self._drive("active_route_miles_to_arrival")

    @property
    def active_route_minutes_to_arrival(self) -> float | None:
        return self._drive("active_route_minutes_to_arrival")

    @property
    def active_route_traffic_minutes_delay(self) -> float | None:
        return self._drive("active_route_traffic_minutes_delay")

    @property
    def active_route_energy_at_arrival(self) -> float | None:
        return self._drive("active_route_energy_at_arrival")

    @property
    def active_route_destination(self) -> str | None:
        return self._drive("active_route_destination")

    # ------------------------------------------------------------------
    # Vehicle state
    # ------------------------------------------------------------------

    @property
    def odometer(self) -> float | None:
        return self._vehicle("odometer")

    @property
    def door_df(self) -> bool:
        return bool(self._vehicle("df"))

    @property
    def door_dr(self) -> bool:
        return bool(self._vehicle("dr"))

    @property
    def door_pf(self) -> bool:
        return bool(self._vehicle("pf"))

    @property
    def door_pr(self) -> bool:
        return bool(self._vehicle("pr"))

    @property
    def window_fd(self) -> bool:
        return bool(self._vehicle("fd_window"))

    @property
    def window_fp(self) -> bool:
        return bool(self._vehicle("fp_window"))

    @property
    def window_rd(self) -> bool:
        return bool(self._vehicle("rd_window"))

    @property
    def window_rp(self) -> bool:
        return bool(self._vehicle("rp_window"))

    @property
    def is_locked(self) -> bool:
        return bool(self._vehicle("locked"))

    @property
    def locked(self) -> bool:
        return self.is_locked

    @property
    def is_frunk_closed(self) -> bool:
        return self._vehicle("ft", 0) == 0

    @property
    def is_trunk_closed(self) -> bool:
        return self._vehicle("rt", 0) == 0

    @property
    def powered_lift_gate(self) -> bool:
        return bool(self._config("plg"))

    @property
    def is_window_closed(self) -> bool:
        return not (self.window_fd or self.window_fp or self.window_rd or self.window_rp)

    @property
    def sentry_mode(self) -> bool:
        return bool(self._vehicle("sentry_mode"))

    @property
    def sentry_mode_available(self) -> bool:
        return bool(self._vehicle("sentry_mode_available"))

    @property
    def is_valet_mode(self) -> bool:
        return bool(self._vehicle("valet_mode"))

    @property
    def homelink_nearby(self) -> bool:
        return bool(self._vehicle("homelink_nearby"))

    @property
    def homelink_device_count(self) -> int:
        return self._vehicle("homelink_device_count", 0)

    @property
    def pedestrian_speaker(self) -> bool:
        return bool(self._config("pedestrian_speaker", False))

    # TPMS
    @property
    def tpms_pressure_fl(self) -> float | None:
        return self._vehicle("tpms_pressure_fl")

    @property
    def tpms_pressure_fr(self) -> float | None:
        return self._vehicle("tpms_pressure_fr")

    @property
    def tpms_pressure_rl(self) -> float | None:
        return self._vehicle("tpms_pressure_rl")

    @property
    def tpms_pressure_rr(self) -> float | None:
        return self._vehicle("tpms_pressure_rr")

    # Software
    @property
    def software_update(self) -> dict | None:
        return self._vehicle("software_update")

    # ------------------------------------------------------------------
    # Commands (async, via teslaHitch)
    # ------------------------------------------------------------------

    async def _cmd(self, endpoint: str, body: dict | None = None):
        return await self._client.send_command(self.vin, endpoint, body)

    async def wake_up(self):
        return await self._client.wake_up(self.vin)

    async def start_charge(self):
        return await self._cmd("charge_start")

    async def stop_charge(self):
        return await self._cmd("charge_stop")

    async def change_charge_limit(self, value: int):
        return await self._cmd("set_charge_limit", {"percent": int(value)})

    async def set_charging_amps(self, value: int):
        return await self._cmd("set_charging_amps", {"charging_amps": int(value)})

    async def charge_port_door_open(self):
        return await self._cmd("charge_port_door_open")

    async def charge_port_door_close(self):
        return await self._cmd("charge_port_door_close")

    async def lock(self):
        return await self._cmd("door_lock")

    async def unlock(self):
        return await self._cmd("door_unlock")

    async def set_hvac_mode(self, mode: str):
        if mode == "off":
            return await self._cmd("auto_conditioning_stop")
        return await self._cmd("auto_conditioning_start")

    async def set_temperature(self, temp: float):
        return await self._cmd("set_temps", {
            "driver_temp": temp,
            "passenger_temp": temp,
        })

    async def set_max_defrost(self, value: int):
        return await self._cmd("set_preconditioning_max", {"on": value == 2})

    async def set_climate_keeper_mode(self, value: int):
        return await self._cmd("set_climate_keeper_mode", {
            "climate_keeper_mode": value
        })

    async def set_bioweapon_mode(self, on: bool):
        return await self._cmd("set_bioweapon_mode", {
            "on": on, "manual_override": True
        })

    async def set_cabin_overheat_protection(self, option: str):
        if option == "Off":
            return await self._cmd("set_cabin_overheat_protection", {"on": False, "fan_only": False})
        elif option == "No A/C":
            return await self._cmd("set_cabin_overheat_protection", {"on": True, "fan_only": True})
        else:  # "On"
            return await self._cmd("set_cabin_overheat_protection", {"on": True, "fan_only": False})

    async def set_heated_steering_wheel(self, on: bool):
        return await self._cmd("remote_steering_wheel_heater_request", {"on": on})

    async def set_heated_steering_wheel_level(self, level: int):
        return await self._cmd("remote_steering_wheel_heat_level_request", {"level": level})

    async def remote_auto_steering_wheel_heat_climate_request(self, on: bool):
        return await self._cmd("remote_auto_steering_wheel_heat_climate_request", {"on": on})

    async def remote_auto_seat_climate_request(self, seat_id: int, on: bool):
        return await self._cmd("remote_auto_seat_climate_request", {
            "auto_seat_position": seat_id,
            "auto_climate_on": on,
        })

    async def remote_seat_heater_request(self, level: int, seat_id: int):
        return await self._cmd("remote_seat_heater_request", {
            "heater": seat_id,
            "level": level,
        })

    async def remote_seat_cooler_request(self, level: int, seat_id: int):
        return await self._cmd("remote_seat_cooler_request", {
            "seat_position": seat_id,
            "seat_cooler_level": level,
        })

    async def set_sentry_mode(self, on: bool):
        return await self._cmd("set_sentry_mode", {"on": on})

    async def valet_mode(self, on: bool):
        return await self._cmd("set_valet_mode", {"on": on})

    async def toggle_frunk(self):
        return await self._cmd("actuate_trunk", {"which_trunk": "front"})

    async def toggle_trunk(self):
        return await self._cmd("actuate_trunk", {"which_trunk": "rear"})

    async def close_windows(self):
        return await self._cmd("window_control", {
            "command": "close", "lat": 0, "lon": 0,
        })

    async def vent_windows(self):
        return await self._cmd("window_control", {
            "command": "vent", "lat": 0, "lon": 0,
        })

    async def honk_horn(self):
        return await self._cmd("honk_horn")

    async def flash_lights(self):
        return await self._cmd("flash_lights")

    async def trigger_homelink(self):
        lat = self.latitude or 0
        lon = self.longitude or 0
        return await self._cmd("trigger_homelink", {"lat": lat, "lon": lon})

    async def remote_start(self):
        return await self._cmd("remote_start_drive")

    async def remote_boombox(self):
        return await self._cmd("remote_boombox")

    async def schedule_software_update(self, offset_sec: int = 0):
        return await self._cmd("schedule_software_update", {
            "offset_sec": offset_sec
        })

    async def update(self, car_id=None, wake_if_asleep: bool = False, force: bool = False):
        """Refresh vehicle data from API."""
        if wake_if_asleep:
            try:
                await self.wake_up()
            except Exception:
                pass
        try:
            data = await self._client.get_vehicle_data(self.vin)
            self._vehicle_data = data
        except Exception as ex:
            _LOGGER.warning("Failed to update vehicle %s: %s", self.vin, ex)
