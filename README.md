# Tesla Custom Integration (teslaHitch Edition)

[![GitHub Release][releases-shield]][releases]
![GitHub all releases][download-all]
![GitHub release (latest by SemVer)][download-latest]
[![GitHub Activity][commits-shield]][commits]

[![License][license-shield]][license]

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

A fork of the [Tesla Custom Integration](https://github.com/alandtse/tesla) for Home Assistant, modified to work with [teslaHitch](https://github.com/martinsaul/teslaHitch) for automatic proxy and token configuration.

## What's different

The original integration requires you to manually provide a refresh token (from a third-party app), proxy URL, SSL certificate path, and Tesla developer Client ID. This fork replaces all of that with a single **teslaHitch URL** — everything else is fetched automatically.

| Original | This fork |
|----------|-----------|
| Refresh token (from Auth App for Tesla / Tesla Tokens) | Automatic (from teslaHitch OAuth) |
| Proxy URL (manual entry) | Automatic (from teslaHitch config) |
| Proxy SSL certificate path | Not needed (Traefik handles TLS) |
| Tesla developer Client ID | Automatic (from teslaHitch config) |

## Prerequisites

- A running [teslaHitch](https://github.com/martinsaul/teslaHitch) instance with completed OAuth flow
- Traefik reverse proxy serving teslaHitch and the Tesla HTTP proxy with valid TLS certificates

## Installation

1. In HACS, go to **Integrations > Explore & Add Repositories**
2. Add `https://github.com/martinsaul/teslahacs` as a custom repository
3. Install **Tesla Custom Integration**
4. Restart Home Assistant
5. Add the integration: go to **Settings > Devices & Services**, click **+**, search for **Tesla Custom Integration**

## Configuration

During setup, you only need to provide:

| Field | Description | Example |
|-------|-------------|---------|
| **teslaHitch URL** | URL of your teslaHitch instance | `https://teslahitch.home.zenithnetwork.com` |
| **Email** | Your Tesla account email | `you@example.com` |
| **Include Vehicles** | Whether to include vehicles | `true` |
| **Include Energy Sites** | Whether to include energy sites (Powerwall, etc.) | `true` |

The integration calls `{teslaHitch URL}/api/ha/config` to fetch your refresh token, client ID, and proxy URL automatically.

**Important:** Complete the Tesla OAuth flow on teslaHitch before setting up this integration. If OAuth hasn't been completed, you'll see an "invalid auth" error.

## Entities

This integration provides the following entities for vehicles:

- Binary sensors - charger connection, charging status, car online, parking brake, car asleep, and door status.
- Buttons - horn, flash lights, wake up, force data update, trigger HomeLink, and remote start.
- Climate - turn HVAC on/off, set target temperature, set preset modes (defrost, keep on, dog mode and camp mode).
- Device tracker - car location, and active route destination.
- Cover - Charger door, frunk, trunk, and windows.
- Locks - door lock, and charge port latch lock.
- Selects - seat heaters and cabin overheat protection.
- Sensors - battery level, charge rate, energy added, charger power, inside/outside temperature, odometer, estimated range, time charge complete, TPMS pressure, active route arrival time and distance to arrival.
- Switches - heated steering wheel, charger, sentry mode, polling, and valet mode.
- Update - software update

This integration provides the following entities for energy sites:

- Binary sensors - Powerwall charging and grid status.
- Selects - grid charging, export rule and operation mode.
- Sensors - solar power, grid power, load power, battery level, battery Wh remaining and backup reserve.

## Options

Tesla options are set via **Settings** -> **Devices & Services** -> **Tesla** -> **Options**.

- Seconds between polling - referred to below as the `polling_interval`.
- Wake cars on start - Whether to wake sleeping cars on Home Assistant startup.
- Polling policy - When do we actively poll the car to get updates. See [the Wiki](https://github.com/alandtse/tesla/wiki/Polling-policy) for more information.
- Sync Data from TeslaMate via MQTT - Enable syncing of Data from a TeslaMate instance via MQTT.

## Potential Battery impacts

- The `polling_interval` determines when to check if the car is awake (default: 660 seconds). Polling too frequently can keep the car awake and drain the battery.
- The car will be woken up when a command is actively sent (door unlock, HVAC, etc.).
- You can toggle the `polling switch` on/off to disable polling completely.

## Credits

Based on [alandtse/tesla](https://github.com/alandtse/tesla). Modified for use with teslaHitch.

---

[integration_blueprint]: https://github.com/custom-components/integration_blueprint
[buymecoffee]: https://www.buymeacoffee.com/alandtse
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/w/alandtse/tesla?style=for-the-badge
[commits]: https://github.com/alandtse/tesla/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license]: LICENSE
[license-shield]: https://img.shields.io/github/license/alandtse/tesla.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Martin%20Saul-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/alandtse/tesla.svg?style=for-the-badge
[releases]: https://github.com/alandtse/tesla/releases
[download-all]: https://img.shields.io/github/downloads/alandtse/tesla/total?style=for-the-badge
[download-latest]: https://img.shields.io/github/downloads/alandtse/tesla/latest/total?style=for-the-badge
[add-integration]: https://my.home-assistant.io/redirect/config_flow_start?domain=tesla_custom
[add-integration-badge]: https://my.home-assistant.io/badges/config_flow_start.svg
