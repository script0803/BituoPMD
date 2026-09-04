# BituoPMD for Home Assistant

An optimized fork of
[`script0803/BituoPMD`](https://github.com/script0803/BituoPMD) for Bituo
SPM/SDM power monitoring devices.

This fork keeps the original `bituopmd` integration domain, config-entry data,
device identifiers, and entity unique IDs. It can replace V1.0.4 without
re-adding devices or changing existing entity IDs.

## What is improved

- One shared coordinator per device instead of separate sensor and switch
  polling loops.
- Fully asynchronous HTTP through Home Assistant's shared client.
- A five-second timeout on every device request so an offline meter cannot
  stall startup or reload.
- Clean unload behavior with no orphaned background tasks.
- Polling interval stored in the Home Assistant config entry instead of a JSON
  file inside `custom_components`.
- Native options and reconfigure flows for polling interval and IP changes.
- Missing data returns `unavailable`, never a fabricated zero.
- Correct HA units and classes, including RSSI in dBm and current-unbalance as
  a percentage rather than a power factor.
- Reliable three-phase totals derived when current firmware omits them:
  current, average current, average line-to-neutral voltage, active/reactive/
  apparent power, forward energy, and reverse energy.
- Secured compatibility panel: administrator-only configuration actions,
  configured devices only, explicit action allowlists, and bounded requests.
- HACS, hassfest, Ruff, syntax, and unit-test workflows.

## Supported devices

The upstream integration documents support for:

- SPM01-xxEW
- SPM02-xxEW
- SDM01-EWx
- SDM02-EW

The optimized code is designed around the same local HTTP API and preserves
relay support for models that advertise it.

## Install with HACS

1. Open HACS.
2. Open the menu and choose **Custom repositories**.
3. Add `https://github.com/kkangg1/BituoPMD` as category
   **Integration**.
4. Download `BituoPMD`.
5. Restart Home Assistant.

To add a new device, go to **Settings → Devices & services → Add
integration**, search for `BituoPMD`, and enter its fixed IP address. Home
Assistant native Zeroconf discovery is also supported.

## Replace upstream V1.0.4

Create a Home Assistant backup first. Then install this repository through
HACS over the existing `custom_components/bituopmd` directory and restart Home
Assistant. Existing entries and entity IDs are retained.

After restart, verify:

- every BituoPMD config entry is `Loaded`;
- metering entities update;
- existing dashboards and automations resolve their old entity IDs;
- the system log contains no `bituopmd` errors.

The previous V1.0.4 component should be kept as a rollback archive until the
new version has run successfully.

## Polling interval

Open the integration entry and choose **Configure**. The supported range is
5–3600 seconds. The default remains 5 seconds for compatibility. With several
meters, 10–30 seconds usually reduces LAN and recorder load without affecting
normal energy dashboards.

The legacy service remains available for panel compatibility:

```yaml
action: bituopmd.set_frequency
data:
  device_id: 192.0.2.10
  frequency: 15
```

`192.0.2.10` is a documentation-only TEST-NET address, not a real device.

## Privacy and security

The integration communicates directly with configured devices on the local
network. The repository and tests contain no installation-specific IP
addresses, serial numbers, config-entry IDs, device-registry IDs, or real
meter readings.

The sidebar panel can change device Wi-Fi, MQTT, Modbus, and firmware settings.
It is therefore visible only to Home Assistant administrators. The proxy
rejects unknown hosts and actions.

## Development

Run the local checks:

```bash
python -m compileall -q custom_components tests
python -m unittest discover -s tests
node --check custom_components/bituopmd/www/bituo_panel.js
ruff check .
ruff format --check .
```

GitHub Actions additionally run HACS and hassfest validation.

## Attribution and licensing

This repository is a fork of the work by
[`@Script0803`](https://github.com/script0803). The upstream repository does
not currently include a license file. No new license is asserted by this
fork; upstream authorship and applicable rights remain unchanged.
