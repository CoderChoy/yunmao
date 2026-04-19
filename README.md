# Yun Mao

![Yun Mao logo](custom_components/yunmao/brand/logo.png)

Yun Mao is a Home Assistant custom integration for Yun Mao local gateways. It exposes local lights and covers through a config flow and keeps stable identifiers where possible, which helps existing Node-RED automations continue to work after upgrades.

## Features

- Local TCP control and status updates over the gateway network interface
- Home Assistant config flow setup
- Light and cover entities created from one gateway entry
- Compatibility-oriented device and entity identifiers

## Install with HACS

1. Open HACS and add this repository as a custom repository:
   `https://github.com/CoderChoy/yunmao`
2. Choose repository type `Integration`.
3. Download `Yun Mao` from HACS.
4. Restart Home Assistant.
5. Go to `Settings > Devices & Services > Add Integration`, then add `Yun Mao`.

Direct HACS link:
https://my.home-assistant.io/redirect/hacs_repository/?owner=CoderChoy&repository=yunmao&category=integration

## Configuration

The integration currently targets a single Yun Mao gateway. During setup, enter the gateway IP address. The integration will then create the light and cover entities defined in the repository's built-in device map.

Default local ports used by the gateway:

- `8888`: request/command channel
- `21688`: push status updates

## Add Devices

Do not add the integration again when you pair a new device to the same gateway. This integration uses a single gateway entry, so clicking `Add Integration` again will correctly show the Home Assistant `single_instance_allowed` message.

To add a new device under the existing gateway:

1. Pair the device with the Yun Mao gateway first.
2. Update [custom_components/yunmao/const.py](custom_components/yunmao/const.py) with the new device mapping.
3. Restart Home Assistant or reload the integration.

Current mapping types:

- Light: `YunMaoLightDescription("书房灯", "FFFF301B977BXXXX", 1)`
- Dual light: `YunMaoLightDescription("客厅灯", "MAC_A", 1, "MAC_B", 4)`
- Cover: `YunMaoCoverDescription("书房窗帘", "00124B00XXXXXXXX")`

Required fields:

- Lights need `name`, `mac`, and `pos`
- Dual-channel lights can also define `secondary_mac` and `secondary_pos`
- Covers need `name` and `mac`

Keep names stable once published. The integration reuses device names as stable identifiers where possible to avoid breaking existing Home Assistant entities or Node-RED flows.

## Upgrades

Release notes for HACS upgrades come from GitHub Releases:
https://github.com/CoderChoy/yunmao/releases

Before installing an update:

1. Read the latest release notes for breaking changes or migration notes.
2. Update from HACS.
3. Restart Home Assistant.

If an update changes gateway behavior, entity model, or migration expectations, the release notes should call that out explicitly.

## Troubleshooting

- If the integration does not appear in `Add Integration`, clear the browser cache and restart Home Assistant once.
- If setup fails, confirm the gateway IP is reachable from Home Assistant and that the local ports above are open.
- For bug reports, include the Home Assistant version, integration version, and relevant logs.

## Support

- Issues: https://github.com/CoderChoy/yunmao/issues
- Releases: https://github.com/CoderChoy/yunmao/releases
