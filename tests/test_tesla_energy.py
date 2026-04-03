"""Tests for EnergySite property accessors and command methods."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.tesla_custom.tesla_energy import (
    EnergySite,
    RESOURCE_TYPE_BATTERY,
    RESOURCE_TYPE_SOLAR,
    GRID_ACTIVE,
)


SAMPLE_PRODUCT_DATA = {
    "energy_site_id": 99999,
    "resource_type": "battery",
    "site_name": "My Powerwall",
    "version": "24.12.1",
    "default_real_mode": "self_consumption",
    "backup_reserve_percent": 20,
    "components": {
        "load_meter": True,
        "solar": True,
        "grid_charging": True,
        "customer_preferred_export_rule": "pv_only",
    },
}

SAMPLE_LIVE_DATA = {
    "solar_power": 5000.0,
    "grid_power": -1000.0,
    "load_power": 3500.0,
    "battery_power": -500.0,
    "percentage_charged": 85.0,
    "energy_left": 10000.0,
    "grid_status": "Active",
    "backup_reserve_percent": 20,
}


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.send_energy_command = AsyncMock(return_value={"result": True})
    return client


@pytest.fixture
def site(mock_client):
    return EnergySite(SAMPLE_PRODUCT_DATA.copy(), SAMPLE_LIVE_DATA.copy(), mock_client)


class TestIdentity:
    def test_energysite_id(self, site):
        assert site.energysite_id == "99999"

    def test_site_name(self, site):
        assert site.site_name == "My Powerwall"

    def test_resource_type(self, site):
        assert site.resource_type == "battery"

    def test_version(self, site):
        assert site.version == "24.12.1"


class TestLiveData:
    def test_solar_power(self, site):
        assert site.solar_power == 5000.0

    def test_grid_power(self, site):
        assert site.grid_power == -1000.0

    def test_load_power(self, site):
        assert site.load_power == 3500.0

    def test_battery_power(self, site):
        assert site.battery_power == -500.0

    def test_percentage_charged(self, site):
        assert site.percentage_charged == 85.0

    def test_energy_left(self, site):
        assert site.energy_left == 10000.0

    def test_grid_status(self, site):
        assert site.grid_status == GRID_ACTIVE

    def test_backup_reserve_percent(self, site):
        assert site.backup_reserve_percent == 20


class TestComponents:
    def test_has_load_meter(self, site):
        assert site.has_load_meter is True

    def test_has_solar(self, site):
        assert site.has_solar is True

    def test_grid_charging(self, site):
        assert site.grid_charging is True

    def test_export_rule(self, site):
        assert site.export_rule == "pv_only"

    def test_operation_mode(self, site):
        assert site.operation_mode == "self_consumption"


class TestCommands:
    """Verify energy site commands use send_energy_command (not send_command)."""

    @pytest.mark.asyncio
    async def test_set_reserve_percent(self, site, mock_client):
        await site.set_reserve_percent(30)
        mock_client.send_energy_command.assert_called_with(
            "99999", "backup", {"backup_reserve_percent": 30}
        )

    @pytest.mark.asyncio
    async def test_set_operation_mode(self, site, mock_client):
        await site.set_operation_mode("autonomous")
        mock_client.send_energy_command.assert_called_with(
            "99999", "operation", {"default_real_mode": "autonomous"}
        )

    @pytest.mark.asyncio
    async def test_set_export_rule(self, site, mock_client):
        await site.set_export_rule("battery_ok")
        mock_client.send_energy_command.assert_called_with(
            "99999", "grid_import_export",
            {"customer_preferred_export_rule": "battery_ok"}
        )

    @pytest.mark.asyncio
    async def test_set_grid_charging_on(self, site, mock_client):
        await site.set_grid_charging(True)
        mock_client.send_energy_command.assert_called_with(
            "99999", "grid_import_export",
            {"disallow_charge_from_grid_with_solar_installed": False}
        )

    @pytest.mark.asyncio
    async def test_set_grid_charging_off(self, site, mock_client):
        await site.set_grid_charging(False)
        mock_client.send_energy_command.assert_called_with(
            "99999", "grid_import_export",
            {"disallow_charge_from_grid_with_solar_installed": True}
        )

    @pytest.mark.asyncio
    async def test_commands_do_not_use_vehicle_endpoint(self, site, mock_client):
        """Energy commands must NOT use send_command (vehicle endpoint)."""
        await site.set_reserve_percent(50)
        # send_command should never be called for energy sites
        assert not hasattr(mock_client, 'send_command') or \
            not mock_client.send_command.called


class TestConstants:
    def test_resource_type_battery(self):
        assert RESOURCE_TYPE_BATTERY == "battery"

    def test_resource_type_solar(self):
        assert RESOURCE_TYPE_SOLAR == "solar"

    def test_grid_active(self):
        assert GRID_ACTIVE == "Active"


class TestEmptyData:
    def test_missing_live_data(self, mock_client):
        site = EnergySite(SAMPLE_PRODUCT_DATA, {}, mock_client)
        assert site.solar_power == 0.0
        assert site.grid_status == "Unknown"
        assert site.percentage_charged == 0.0
