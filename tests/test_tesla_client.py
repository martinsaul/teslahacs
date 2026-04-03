"""Tests for TeslaHitchClient URL construction and HTTP methods."""

import json
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from custom_components.tesla_custom.tesla_client import TeslaHitchClient


@pytest.fixture
def client():
    return TeslaHitchClient(teslahitch_url="http://teslahitch:8000")


@pytest.fixture
def mock_response():
    """Create a mock httpx.Response."""
    def _make(status_code=200, json_data=None, text=""):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = status_code
        resp.text = text
        resp.json.return_value = json_data or {}
        resp.raise_for_status = MagicMock()
        if status_code >= 400:
            resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "error", request=MagicMock(), response=resp
            )
        return resp
    return _make


class TestURLConstruction:
    """Verify every endpoint builds the correct URL."""

    @pytest.mark.asyncio
    async def test_get_config_url(self, client, mock_response):
        mock_http = AsyncMock()
        mock_http.get.return_value = mock_response(json_data={"access_token": "t"})
        mock_http.is_closed = False
        client._client = mock_http

        await client.get_config()
        mock_http.get.assert_called_with("http://teslahitch:8000/internal/ha/config")

    @pytest.mark.asyncio
    async def test_list_products_url(self, client, mock_response):
        mock_http = AsyncMock()
        mock_http.get.return_value = mock_response(json_data={"response": []})
        mock_http.is_closed = False
        client._client = mock_http

        await client.list_products()
        mock_http.get.assert_called_with("http://teslahitch:8000/internal/products")

    @pytest.mark.asyncio
    async def test_get_vehicle_data_url(self, client, mock_response):
        mock_http = AsyncMock()
        mock_http.get.return_value = mock_response(json_data={"response": {"vin": "ABC123"}})
        mock_http.is_closed = False
        client._client = mock_http

        await client.get_vehicle_data("ABC123")
        mock_http.get.assert_called_with(
            "http://teslahitch:8000/internal/vehicles/ABC123/vehicle_data"
        )

    @pytest.mark.asyncio
    async def test_get_energy_site_data_url(self, client, mock_response):
        mock_http = AsyncMock()
        mock_http.get.return_value = mock_response(json_data={"response": {}})
        mock_http.is_closed = False
        client._client = mock_http

        await client.get_energy_site_data("12345")
        mock_http.get.assert_called_with(
            "http://teslahitch:8000/internal/energy_sites/12345/live_status"
        )

    @pytest.mark.asyncio
    async def test_send_command_url_and_method(self, client, mock_response):
        """Commands must use POST to /internal/vehicles/{vin}/command/{endpoint}."""
        mock_http = AsyncMock()
        mock_http.post.return_value = mock_response(json_data={"result": True})
        mock_http.is_closed = False
        client._client = mock_http

        await client.send_command("VIN123", "wake_up")
        mock_http.post.assert_called_once()
        call_url = mock_http.post.call_args[0][0]
        assert call_url == "http://teslahitch:8000/internal/vehicles/VIN123/command/wake_up"

    @pytest.mark.asyncio
    async def test_send_command_with_body(self, client, mock_response):
        mock_http = AsyncMock()
        mock_http.post.return_value = mock_response(json_data={"result": True})
        mock_http.is_closed = False
        client._client = mock_http

        await client.send_command("VIN123", "set_charge_limit", {"percent": 80})
        call_kwargs = mock_http.post.call_args
        body = call_kwargs.kwargs.get("content") or call_kwargs[1].get("content")
        assert json.loads(body) == {"percent": 80}

    @pytest.mark.asyncio
    async def test_send_energy_command_url(self, client, mock_response):
        """Energy commands must use /internal/energy_sites/{id}/{endpoint}."""
        mock_http = AsyncMock()
        mock_http.post.return_value = mock_response(json_data={"result": True})
        mock_http.is_closed = False
        client._client = mock_http

        await client.send_energy_command("99999", "backup", {"backup_reserve_percent": 50})
        call_url = mock_http.post.call_args[0][0]
        assert call_url == "http://teslahitch:8000/internal/energy_sites/99999/backup"

    @pytest.mark.asyncio
    async def test_wake_up_uses_post(self, client, mock_response):
        """wake_up must use POST, not GET."""
        mock_http = AsyncMock()
        mock_http.post.return_value = mock_response(json_data={})
        mock_http.is_closed = False
        client._client = mock_http

        await client.wake_up("VIN123")
        mock_http.post.assert_called_once()
        # Verify GET was NOT called
        mock_http.get.assert_not_called()


class TestResponseUnwrapping:
    """Verify responses are correctly unwrapped from Tesla's response envelope."""

    @pytest.mark.asyncio
    async def test_vehicle_data_unwraps_response(self, client, mock_response):
        vehicle = {"vin": "X", "charge_state": {"battery_level": 80}}
        mock_http = AsyncMock()
        mock_http.get.return_value = mock_response(json_data={"response": vehicle})
        mock_http.is_closed = False
        client._client = mock_http

        result = await client.get_vehicle_data("X")
        assert result == vehicle
        assert result["charge_state"]["battery_level"] == 80

    @pytest.mark.asyncio
    async def test_list_products_unwraps_response(self, client, mock_response):
        products = [{"vin": "A"}, {"energy_site_id": 123}]
        mock_http = AsyncMock()
        mock_http.get.return_value = mock_response(json_data={"response": products, "count": 2})
        mock_http.is_closed = False
        client._client = mock_http

        result = await client.list_products()
        assert len(result) == 2
        assert result[0]["vin"] == "A"

    @pytest.mark.asyncio
    async def test_energy_site_data_unwraps_response(self, client, mock_response):
        live = {"solar_power": 5000, "battery_power": -1000}
        mock_http = AsyncMock()
        mock_http.get.return_value = mock_response(json_data={"response": live})
        mock_http.is_closed = False
        client._client = mock_http

        result = await client.get_energy_site_data("12345")
        assert result["solar_power"] == 5000


class TestStateManagement:
    """Verify controller state tracking methods."""

    @pytest.mark.asyncio
    async def test_polling_toggle(self, client):
        client._polling_enabled["VIN1"] = True
        assert client.get_updates(vin="VIN1") is True
        client.set_updates(vin="VIN1", value=False)
        assert client.get_updates(vin="VIN1") is False

    @pytest.mark.asyncio
    async def test_update_interval(self, client):
        assert client.get_update_interval_vin(vin="VIN1") == 660  # default
        client.set_update_interval_vin(vin="VIN1", value=120)
        assert client.get_update_interval_vin(vin="VIN1") == 120
