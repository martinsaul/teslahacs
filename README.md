# Tesla Custom Integration

[![GitHub Release][releases-shield]][releases]
![GitHub all releases][download-all]
![GitHub release (latest by SemVer)][download-latest]
[![GitHub Activity][commits-shield]][commits]

[![License][license-shield]][license]

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

A Tesla integration for Home Assistant, powered by [teslaHitch](https://github.com/martinsaul/teslaHitch). All Tesla API communication goes through teslaHitch -- no direct Tesla API calls, no token management.

## How it works

This integration talks exclusively to teslaHitch's HTTP API on port 8000:

- **`/internal/products`** -- discovers vehicles and energy sites
- **`/internal/vehicles/{vin}/vehicle_data`** -- fetches vehicle state
- **`/internal/vehicles/{vin}/command/{cmd}`** -- sends commands (lock, charge, climate, etc.)
- **`/internal/ha/config`** -- gets tokens and proxy configuration

teslaHitch handles all OAuth, token refresh, and certificate management. You never need to manually provide tokens, proxy URLs, or client IDs.

## Prerequisites

- A running [teslaHitch](https://github.com/martinsaul/teslaHitch) instance with completed OAuth flow
- The teslaHitch trusted port (8000) must be reachable from Home Assistant

## Installation

1. In HACS, go to **Integrations > Explore & Add Repositories**
2. Add `https://github.com/martinsaul/teslahacs` as a custom repository
3. Install **Tesla Custom Integration**
4. Restart Home Assistant
5. Go to **Settings > Devices & Services**, click **+**, search for **Tesla Custom Integration**

## Configuration

During setup, enter:

| Field | Description | Example |
|-------|-------------|---------|
| **teslaHitch URL** | URL of teslaHitch's trusted port | `http://teslahitch:8000` |
| **Email** | Your Tesla account email | `you@example.com` |
| **Include Vehicles** | Include vehicles | `true` |
| **Include Energy Sites** | Include Powerwall/solar | `true` |

**Important:** Complete the OAuth flow on teslaHitch (`/internal/auth`) before setting up this integration.

## Entities

### Vehicles

| Platform | Entities |
|----------|----------|
| binary_sensor | Charger connected, charging, car online, asleep, parking brake, doors, windows, scheduled charging/departure, user present |
| button | Horn, flash lights, wake up, force data update, HomeLink, remote start, emissions test |
| climate | HVAC on/off, target temperature, presets (defrost, keep, dog, camp), bioweapon mode |
| cover | Charger door, frunk, trunk, windows |
| device_tracker | Car location, active route destination |
| lock | Door lock, charge port latch |
| number | Charge limit, charging amps |
| select | Seat heaters/coolers, heated steering wheel, cabin overheat protection |
| sensor | Battery, charge rate, energy added, charger power, range, odometer, temperature, TPMS, arrival time, distance to arrival, polling interval |
| switch | Heated steering, sentry mode, charger, polling, valet mode |
| text | TeslaMate ID |
| update | Software update |

### Energy Sites

| Platform | Entities |
|----------|----------|
| binary_sensor | Battery charging, grid status |
| number | Backup reserve |
| select | Grid charging, export rule, operation mode |
| sensor | Solar/grid/load/battery power, battery level, battery remaining, backup reserve |

## Options

Configure via **Settings > Devices & Services > Tesla > Options**:

- **Polling interval** -- seconds between updates (default: 660, min: 10)
- **Wake on start** -- wake sleeping cars when HA starts
- **Polling policy** -- when to actively poll (normal / connected / always)
- **TeslaMate** -- sync data from TeslaMate via MQTT

## Architecture

```
teslahacs
    |
    |-- TeslaHitchClient (tesla_client.py)
    |     calls teslaHitch /internal/* endpoints
    |
    |-- TeslaCar (tesla_car.py)
    |     wraps raw vehicle_data, exposes properties + command methods
    |
    |-- EnergySite (tesla_energy.py)
    |     wraps raw energy site data, exposes properties + command methods
    |
    |-- TeslaDataUpdateCoordinator (__init__.py)
    |     polls teslaHitch, updates TeslaCar/EnergySite in-place
    |
    |-- Entity platforms (sensor.py, switch.py, climate.py, ...)
          read from TeslaCar/EnergySite, send commands through them
```

As of v4.0.0, the `teslajsonpy` library has been completely removed. The three modules above (`tesla_client.py`, `tesla_car.py`, `tesla_energy.py`) replace it entirely.

## Troubleshooting

### "invalid auth" during setup

Complete the OAuth flow on teslaHitch first: visit `http://<teslahitch-host>:8000/internal/auth`.

### "cannot connect" during setup

Ensure the teslaHitch URL points to port 8000 (the trusted port). All `/internal/*` endpoints are blocked on port 8080.

### Integration stops updating

Check teslaHitch is running and healthy (`/health` endpoint). The integration will automatically reload on auth errors (401/403).

---

[commits-shield]: https://img.shields.io/github/commit-activity/w/martinsaul/teslahacs?style=for-the-badge
[commits]: https://github.com/martinsaul/teslahacs/commits/dev
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license]: LICENSE
[license-shield]: https://img.shields.io/github/license/martinsaul/teslahacs.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40martinsaul-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/martinsaul/teslahacs.svg?style=for-the-badge
[releases]: https://github.com/martinsaul/teslahacs/releases
[download-all]: https://img.shields.io/github/downloads/martinsaul/teslahacs/total?style=for-the-badge
[download-latest]: https://img.shields.io/github/downloads/martinsaul/teslahacs/latest/total?style=for-the-badge
