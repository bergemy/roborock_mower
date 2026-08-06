# Roborock Mower

![Roborock Mower unofficial integration logo](../../assets/roborock_mower_logo.svg)

Read-only Home Assistant custom integration for Roborock RockMow Z1 / Z115.

Version 0.2 uses Roborock MQTT/DPS push as the primary status source and keeps `get_home_data_v3(user_data)` as a slow cloud fallback.

## Supported device

The integration looks for Roborock devices where:

- `product.category` is `roborock.mower`
- tested model: `roborock.mower.a235`
- product name: `RockMow Z1`

Other mower models are not blocked, but they are not tested.

## Install

1. Copy `custom_components/roborock_mower` to your Home Assistant config folder:

   ```text
   <config>/custom_components/roborock_mower
   ```

2. Restart Home Assistant.
3. Go to **Settings** -> **Devices & services** -> **Add integration**.
4. Search for **Roborock Mower**.
5. Enter the Roborock account e-mail address.
6. Enter the Roborock e-mail code.

The Roborock e-mail code normally expires after 15 minutes. The integration stores the returned session/token data, so a new code is only needed if Home Assistant starts a reauth flow.

## Entities

The integration creates one main entity per mower:

- `lawn_mower.<device>`

It also creates these read-only status entities:

- `sensor.<device>_battery`
- `sensor.<device>_mow_state`
- `sensor.<device>_charge_state`
- `sensor.<device>_mow_progress`
- `sensor.<device>_mow_height`
- `sensor.<device>_gps_raw`
- `sensor.<device>_network_channel`
- `binary_sensor.<device>_online`

All entities are linked to the same Home Assistant device. Unique IDs use DUID, with SN as fallback.

## Status source

MQTT protocol `102` DPS updates are applied immediately. Cloud polling runs every 15 minutes as fallback/resynchronization.

MQTT protocol `500` online/offline messages are treated as weak hints. Offline is delayed for 5 minutes because RockMow can briefly report false/true when Wi-Fi coverage is poor. Any fresh DPS update marks the mower online again.

Binary/map-like MQTT protocols `301` and `702` are logged at debug level only. They are not decoded in this integration yet.

## Known RockMow DPS

| ID | Field |
| --- | --- |
| 120 | `error_code` |
| 121 | `battery` |
| 122 | `mow_type` |
| 123 | `mow_state` |
| 124 | `mapping_type` |
| 125 | `mapping_state` |
| 126 | `ota_state` |
| 127 | `charge_state` |
| 129 | `charge_type` |
| 132 | `mow_start_type` |
| 133 | `mow_eff_mode` |
| 134 | `mow_height` |
| 135 | `mow_direction_angle` |
| 138 | `offline_status` |
| 139 | `mow_progress` |
| 142 | `gps_coordinate` |
| 143 | `off_dock_no_task_status` |
| 144 | `afs_status` |
| 145 | `network_channel` |

Known `mow_state` mappings:

- `0` = `idle`
- `55` = `area_mowing`
- `56` = `edge_mowing`
- `57` = `moving_to_area`
- `61` = `returning_to_charge_low_battery`
- `76` = `transit`

Unknown values are preserved as `unknown_<code>` and the raw value is available in entity attributes.

## Debug logging

```yaml
logger:
  logs:
    custom_components.roborock_mower: debug
```

Useful attributes include:

- `last_mqtt_update`
- `last_mqtt_protocol`
- `last_mqtt_seen`
- `last_mqtt_online_hint`
- `last_mqtt_payload`
- `last_cloud_update`
- `last_rate_limit`

Diagnostics redact sensitive values such as `localKey`, `duid`, `sn`, `token`, and `rriot`.

## Not implemented yet

No commands are implemented in this version. Future button/action support may use these mower DPS command IDs once the command payloads are verified safely:

- start = 201
- dock = 202
- pause = 203
- resume = 204
- stop = 205

No map, zone, or area-name decoding is implemented yet.
