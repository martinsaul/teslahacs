"""Tests for TeslaCar property accessors and command methods."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.tesla_custom.tesla_car import TeslaCar


SAMPLE_VEHICLE_DATA = {
    "id": 123,
    "vehicle_id": 456,
    "vin": "5YJ3E1EA1PF000001",
    "display_name": "Tess",
    "state": "online",
    "charge_state": {
        "battery_level": 80,
        "usable_battery_level": 78,
        "charging_state": "Complete",
        "charge_limit_soc": 90,
        "charge_limit_soc_min": 50,
        "charge_limit_soc_max": 100,
        "battery_range": 200.5,
        "ideal_battery_range": 210.0,
        "charge_rate": 0.0,
        "time_to_full_charge": 0.0,
        "charge_energy_added": 12.5,
        "charge_miles_added_rated": 40.0,
        "charge_miles_added_ideal": 42.0,
        "charge_current_request": 32,
        "charge_current_request_max": 48,
        "charger_power": 0,
        "charger_voltage": 0,
        "charger_actual_current": 0,
        "charger_phases": None,
        "charge_port_door_open": True,
        "charge_port_latch": "Engaged",
        "conn_charge_cable": "SAE",
        "fast_charger_present": False,
        "fast_charger_brand": "",
        "fast_charger_type": "",
        "scheduled_charging_mode": "Off",
        "scheduled_charging_start_time_app": 0,
        "preconditioning_enabled": False,
        "preconditioning_weekday_only": False,
        "off_peak_charging_enabled": False,
        "off_peak_charging_weekday_only": False,
        "off_peak_hours_end_time": 360,
        "scheduled_departure_time_minutes": 480,
    },
    "climate_state": {
        "inside_temp": 22.5,
        "outside_temp": 15.0,
        "is_climate_on": False,
        "is_preconditioning": False,
        "driver_temp_setting": 21.0,
        "max_avail_temp": 28.0,
        "min_avail_temp": 15.0,
        "defrost_mode": 0,
        "climate_keeper_mode": "off",
        "bioweapon_mode": False,
        "cabin_overheat_protection": "Off",
        "steering_wheel_heater": True,
        "steering_wheel_heat_level": 1,
        "auto_steering_wheel_heat": False,
        "auto_seat_climate_left": True,
        "auto_seat_climate_right": False,
        "seat_heater_left": 0,
        "seat_heater_right": 2,
        "seat_fan_front_left": 1,
    },
    "drive_state": {
        "latitude": 49.2827,
        "longitude": -123.1207,
        "heading": 180,
        "speed": None,
        "shift_state": None,
        "active_route_latitude": 49.0,
        "active_route_longitude": -123.0,
        "active_route_miles_to_arrival": 15.5,
        "active_route_minutes_to_arrival": 22.3,
        "active_route_traffic_minutes_delay": 3.2,
        "active_route_energy_at_arrival": 70,
        "active_route_destination": "Home",
    },
    "vehicle_state": {
        "car_version": "2026.8.3 abc123",
        "odometer": 24260.5,
        "locked": True,
        "df": 0, "dr": 0, "pf": 0, "pr": 0,
        "fd_window": 0, "fp_window": 0, "rd_window": 0, "rp_window": 0,
        "ft": 0, "rt": 0,
        "sentry_mode": True,
        "sentry_mode_available": True,
        "valet_mode": False,
        "homelink_nearby": True,
        "homelink_device_count": 2,
        "is_user_present": False,
        "tpms_pressure_fl": 2.9,
        "tpms_pressure_fr": 3.0,
        "tpms_pressure_rl": 2.8,
        "tpms_pressure_rr": 2.85,
        "software_update": {"status": "available", "version": "2026.9.1"},
    },
    "vehicle_config": {
        "car_type": "modely",
        "rear_seat_heaters": 1,
        "third_row_seats": "None",
        "has_seat_cooling": True,
        "plg": True,
        "pedestrian_speaker": True,
    },
    "gui_settings": {
        "gui_range_display": "Rated",
        "gui_distance_units": "mi/hr",
    },
}

SAMPLE_CAR_DATA = {
    "id": 123,
    "vehicle_id": 456,
    "vin": "5YJ3E1EA1PF000001",
    "display_name": "Tess",
    "state": "online",
}


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.send_command = AsyncMock(return_value={"result": True})
    client.wake_up = AsyncMock(return_value={})
    client.get_vehicle_data = AsyncMock(return_value=SAMPLE_VEHICLE_DATA)
    return client


@pytest.fixture
def car(mock_client):
    return TeslaCar(SAMPLE_VEHICLE_DATA.copy(), SAMPLE_CAR_DATA.copy(), mock_client)


class TestIdentity:
    def test_vin(self, car):
        assert car.vin == "5YJ3E1EA1PF000001"

    def test_id(self, car):
        assert car.id == 123

    def test_vehicle_id(self, car):
        assert car.vehicle_id == 456

    def test_display_name(self, car):
        assert car.display_name == "Tess"

    def test_state(self, car):
        assert car.state == "online"

    def test_is_on(self, car):
        assert car.is_on is True

    def test_car_type(self, car):
        assert car.car_type == "modely"

    def test_car_version(self, car):
        assert car.car_version == "2026.8.3 abc123"


class TestChargeState:
    def test_battery_level(self, car):
        assert car.battery_level == 80

    def test_usable_battery_level(self, car):
        assert car.usable_battery_level == 78

    def test_charging_state(self, car):
        assert car.charging_state == "Complete"

    def test_charge_limit_soc(self, car):
        assert car.charge_limit_soc == 90

    def test_battery_range(self, car):
        assert car.battery_range == 200.5

    def test_charge_rate(self, car):
        assert car.charge_rate == 0.0

    def test_charge_energy_added(self, car):
        assert car.charge_energy_added == 12.5

    def test_charge_current_request(self, car):
        assert car.charge_current_request == 32

    def test_charge_port_latch(self, car):
        assert car.charge_port_latch == "Engaged"

    def test_is_charge_port_door_open(self, car):
        assert car.is_charge_port_door_open is True

    def test_scheduled_charging_mode(self, car):
        assert car.scheduled_charging_mode == "Off"

    def test_gui_range_display(self, car):
        assert car.gui_range_display == "Rated"


class TestClimateState:
    def test_inside_temp(self, car):
        assert car.inside_temp == 22.5

    def test_outside_temp(self, car):
        assert car.outside_temp == 15.0

    def test_is_climate_on(self, car):
        assert car.is_climate_on is False

    def test_driver_temp_setting(self, car):
        assert car.driver_temp_setting == 21.0

    def test_steering_wheel_heater(self, car):
        assert car.steering_wheel_heater is True

    def test_heated_steering_wheel_level(self, car):
        assert car.get_heated_steering_wheel_level() == 1

    def test_seat_heater_status(self, car):
        assert car.get_seat_heater_status(0) == 0  # left
        assert car.get_seat_heater_status(1) == 2  # right

    def test_seat_cooler_status(self, car):
        assert car.get_seat_cooler_status(1) == 1  # left fan

    def test_auto_seat_climate_dynamic(self, car):
        assert car.is_auto_seat_climate_left is True
        assert car.is_auto_seat_climate_right is False


class TestDriveState:
    def test_latitude(self, car):
        assert car.latitude == 49.2827

    def test_longitude(self, car):
        assert car.longitude == -123.1207

    def test_heading(self, car):
        assert car.heading == 180

    def test_shift_state_none(self, car):
        assert car.shift_state is None

    def test_active_route(self, car):
        assert car.active_route_miles_to_arrival == 15.5
        assert car.active_route_destination == "Home"


class TestVehicleState:
    def test_odometer(self, car):
        assert car.odometer == 24260.5

    def test_locked(self, car):
        assert car.is_locked is True

    def test_doors_closed(self, car):
        assert car.door_df is False
        assert car.door_dr is False

    def test_windows_closed(self, car):
        assert car.is_window_closed is True

    def test_frunk_closed(self, car):
        assert car.is_frunk_closed is True

    def test_trunk_closed(self, car):
        assert car.is_trunk_closed is True

    def test_sentry_mode(self, car):
        assert car.sentry_mode is True
        assert car.sentry_mode_available is True

    def test_tpms(self, car):
        assert car.tpms_pressure_fl == 2.9
        assert car.tpms_pressure_rr == 2.85

    def test_software_update(self, car):
        assert car.software_update["status"] == "available"
        assert car.software_update["version"] == "2026.9.1"

    def test_powered_lift_gate(self, car):
        assert car.powered_lift_gate is True

    def test_pedestrian_speaker(self, car):
        assert car.pedestrian_speaker is True


class TestCommands:
    """Verify every command sends the correct endpoint name and body."""

    @pytest.mark.asyncio
    async def test_start_charge(self, car, mock_client):
        await car.start_charge()
        mock_client.send_command.assert_called_with("5YJ3E1EA1PF000001", "charge_start", None)

    @pytest.mark.asyncio
    async def test_stop_charge(self, car, mock_client):
        await car.stop_charge()
        mock_client.send_command.assert_called_with("5YJ3E1EA1PF000001", "charge_stop", None)

    @pytest.mark.asyncio
    async def test_change_charge_limit(self, car, mock_client):
        await car.change_charge_limit(80)
        mock_client.send_command.assert_called_with(
            "5YJ3E1EA1PF000001", "set_charge_limit", {"percent": 80}
        )

    @pytest.mark.asyncio
    async def test_set_charging_amps(self, car, mock_client):
        await car.set_charging_amps(16)
        mock_client.send_command.assert_called_with(
            "5YJ3E1EA1PF000001", "set_charging_amps", {"charging_amps": 16}
        )

    @pytest.mark.asyncio
    async def test_lock(self, car, mock_client):
        await car.lock()
        mock_client.send_command.assert_called_with("5YJ3E1EA1PF000001", "door_lock", None)

    @pytest.mark.asyncio
    async def test_unlock(self, car, mock_client):
        await car.unlock()
        mock_client.send_command.assert_called_with("5YJ3E1EA1PF000001", "door_unlock", None)

    @pytest.mark.asyncio
    async def test_hvac_on(self, car, mock_client):
        await car.set_hvac_mode("on")
        mock_client.send_command.assert_called_with(
            "5YJ3E1EA1PF000001", "auto_conditioning_start", None
        )

    @pytest.mark.asyncio
    async def test_hvac_off(self, car, mock_client):
        await car.set_hvac_mode("off")
        mock_client.send_command.assert_called_with(
            "5YJ3E1EA1PF000001", "auto_conditioning_stop", None
        )

    @pytest.mark.asyncio
    async def test_set_temperature(self, car, mock_client):
        await car.set_temperature(22.5)
        mock_client.send_command.assert_called_with(
            "5YJ3E1EA1PF000001", "set_temps",
            {"driver_temp": 22.5, "passenger_temp": 22.5}
        )

    @pytest.mark.asyncio
    async def test_set_sentry_mode(self, car, mock_client):
        await car.set_sentry_mode(True)
        mock_client.send_command.assert_called_with(
            "5YJ3E1EA1PF000001", "set_sentry_mode", {"on": True}
        )

    @pytest.mark.asyncio
    async def test_honk_horn(self, car, mock_client):
        await car.honk_horn()
        mock_client.send_command.assert_called_with("5YJ3E1EA1PF000001", "honk_horn", None)

    @pytest.mark.asyncio
    async def test_flash_lights(self, car, mock_client):
        await car.flash_lights()
        mock_client.send_command.assert_called_with("5YJ3E1EA1PF000001", "flash_lights", None)

    @pytest.mark.asyncio
    async def test_toggle_frunk(self, car, mock_client):
        await car.toggle_frunk()
        mock_client.send_command.assert_called_with(
            "5YJ3E1EA1PF000001", "actuate_trunk", {"which_trunk": "front"}
        )

    @pytest.mark.asyncio
    async def test_toggle_trunk(self, car, mock_client):
        await car.toggle_trunk()
        mock_client.send_command.assert_called_with(
            "5YJ3E1EA1PF000001", "actuate_trunk", {"which_trunk": "rear"}
        )

    @pytest.mark.asyncio
    async def test_close_windows(self, car, mock_client):
        await car.close_windows()
        mock_client.send_command.assert_called_with(
            "5YJ3E1EA1PF000001", "window_control",
            {"command": "close", "lat": 0, "lon": 0}
        )

    @pytest.mark.asyncio
    async def test_vent_windows(self, car, mock_client):
        await car.vent_windows()
        mock_client.send_command.assert_called_with(
            "5YJ3E1EA1PF000001", "window_control",
            {"command": "vent", "lat": 0, "lon": 0}
        )

    @pytest.mark.asyncio
    async def test_trigger_homelink(self, car, mock_client):
        await car.trigger_homelink()
        mock_client.send_command.assert_called_with(
            "5YJ3E1EA1PF000001", "trigger_homelink",
            {"lat": 49.2827, "lon": -123.1207}
        )

    @pytest.mark.asyncio
    async def test_remote_start(self, car, mock_client):
        await car.remote_start()
        mock_client.send_command.assert_called_with(
            "5YJ3E1EA1PF000001", "remote_start_drive", None
        )

    @pytest.mark.asyncio
    async def test_wake_up(self, car, mock_client):
        await car.wake_up()
        mock_client.wake_up.assert_called_with("5YJ3E1EA1PF000001")

    @pytest.mark.asyncio
    async def test_schedule_software_update(self, car, mock_client):
        await car.schedule_software_update(offset_sec=60)
        mock_client.send_command.assert_called_with(
            "5YJ3E1EA1PF000001", "schedule_software_update", {"offset_sec": 60}
        )

    @pytest.mark.asyncio
    async def test_charge_port_door_open(self, car, mock_client):
        await car.charge_port_door_open()
        mock_client.send_command.assert_called_with(
            "5YJ3E1EA1PF000001", "charge_port_door_open", None
        )

    @pytest.mark.asyncio
    async def test_set_cabin_overheat_protection_off(self, car, mock_client):
        await car.set_cabin_overheat_protection("Off")
        mock_client.send_command.assert_called_with(
            "5YJ3E1EA1PF000001", "set_cabin_overheat_protection",
            {"on": False, "fan_only": False}
        )

    @pytest.mark.asyncio
    async def test_set_cabin_overheat_protection_no_ac(self, car, mock_client):
        await car.set_cabin_overheat_protection("No A/C")
        mock_client.send_command.assert_called_with(
            "5YJ3E1EA1PF000001", "set_cabin_overheat_protection",
            {"on": True, "fan_only": True}
        )

    @pytest.mark.asyncio
    async def test_set_cabin_overheat_protection_on(self, car, mock_client):
        await car.set_cabin_overheat_protection("On")
        mock_client.send_command.assert_called_with(
            "5YJ3E1EA1PF000001", "set_cabin_overheat_protection",
            {"on": True, "fan_only": False}
        )

    @pytest.mark.asyncio
    async def test_seat_heater(self, car, mock_client):
        await car.remote_seat_heater_request(3, 0)
        mock_client.send_command.assert_called_with(
            "5YJ3E1EA1PF000001", "remote_seat_heater_request",
            {"heater": 0, "level": 3}
        )

    @pytest.mark.asyncio
    async def test_seat_cooler(self, car, mock_client):
        await car.remote_seat_cooler_request(2, 1)
        mock_client.send_command.assert_called_with(
            "5YJ3E1EA1PF000001", "remote_seat_cooler_request",
            {"seat_position": 1, "seat_cooler_level": 2}
        )


class TestEmptyData:
    """Test behavior when vehicle data is missing fields."""

    def test_missing_charge_state(self, mock_client):
        car = TeslaCar({"state": "asleep"}, {"vin": "X"}, mock_client)
        assert car.battery_level is None
        assert car.charging_state is None
        assert car.charge_rate is None

    def test_missing_climate_state(self, mock_client):
        car = TeslaCar({"state": "asleep"}, {"vin": "X"}, mock_client)
        assert car.inside_temp is None
        assert car.outside_temp is None

    def test_missing_drive_state(self, mock_client):
        car = TeslaCar({"state": "asleep"}, {"vin": "X"}, mock_client)
        assert car.latitude is None
        assert car.speed is None

    def test_vin_falls_back_to_car_data(self, mock_client):
        car = TeslaCar({}, {"vin": "FALLBACK_VIN"}, mock_client)
        assert car.vin == "FALLBACK_VIN"
