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

## Token Management

This integration delegates **all token management to teslaHitch**. This is critical because Tesla uses refresh token rotation — every refresh invalidates the previous refresh token. If both teslahacs and teslaHitch refresh independently, they invalidate each other and auth is lost.

How it works:

- **teslaHitch** proactively refreshes access tokens every 2 hours via a scheduled job. Tokens always have ~8 hours of remaining life.
- **teslahacs** re-fetches fresh tokens from teslaHitch's `/api/ha/config` endpoint 30 minutes before the current access token expires.
- If the underlying `teslajsonpy` library refreshes independently (which can happen in edge cases), teslahacs **immediately overrides** those tokens with authoritative ones from teslaHitch.
- On 403 errors from the Tesla API, teslahacs automatically attempts token recovery from teslaHitch before giving up.

You should never need to re-authenticate unless the refresh token itself expires (90 days of inactivity).

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

The integration calls `{teslaHitch URL}/api/ha/config` to fetch your access token, refresh token, client ID, and proxy URL automatically.

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

## Troubleshooting

### "invalid auth" during setup

Complete the Tesla OAuth flow on teslaHitch first. Visit `http://<teslahitch-admin-host>/internal/auth` to authenticate.

### Auth keeps getting lost

This was fixed in v3.29.0. The root causes were:

1. teslaHitch returned stale expiration timestamps, causing teslahacs to think tokens were already expired
2. teslahacs (via teslajsonpy) refreshed directly with Tesla, triggering refresh token rotation
3. This invalidated teslaHitch's stored refresh token, breaking all future refreshes

The fix ensures teslaHitch is the sole token authority and teslahacs always gets fresh tokens from teslaHitch rather than refreshing independently.

### "teslajsonpy refreshed independently" warning

This warning means the underlying Tesla API library tried to refresh tokens on its own. teslahacs automatically overrides these tokens with authoritative ones from teslaHitch. The warning is informational — if it appears frequently, check that teslaHitch's scheduled refresh is running (look for `Scheduled proactive token refresh completed` in teslaHitch logs).

### 403 errors from Tesla API

teslahacs automatically attempts token recovery from teslaHitch on 403 errors. If recovery fails, check:
- teslaHitch is running and accessible
- The OAuth session is still valid (not expired after 90 days)
- Re-authenticate on teslaHitch if needed

## Credits

Originally built by [Alan Tse (@alandtse)](https://github.com/alandtse/tesla) as the Tesla Custom Integration for Home Assistant. This fork modifies the integration for use with [teslaHitch](https://github.com/martinsaul/teslaHitch). All upstream issues should be reported to the [original repository](https://github.com/alandtse/tesla); issues specific to the teslaHitch integration should be reported [here](https://github.com/martinsaul/teslahacs/issues).

---

[integration_blueprint]: https://github.com/custom-components/integration_blueprint
[buymecoffee]: https://www.buymeacoffee.com/alandtse
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/w/martinsaul/teslahacs?style=for-the-badge
[commits]: https://github.com/martinsaul/teslahacs/commits/dev
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license]: LICENSE
[license-shield]: https://img.shields.io/github/license/martinsaul/teslahacs.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40martinsaul-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/martinsaul/teslahacs.svg?style=for-the-badge
[releases]: https://github.com/martinsaul/teslahacs/releases
[download-all]: https://img.shields.io/github/downloads/martinsaul/teslahacs/total?style=for-the-badge
[download-latest]: https://img.shields.io/github/downloads/martinsaul/teslahacs/latest/total?style=for-the-badge
[add-integration]: https://my.home-assistant.io/redirect/config_flow_start?domain=tesla_custom
[add-integration-badge]: https://my.home-assistant.io/badges/config_flow_start.svg
