"""Sensors for the Roborock Mower integration."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import logging
import struct
from typing import Any, Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CHARGE_STATE_MAP,
    DOMAIN,
    MOW_STATE_MAP,
    STATUS_BATTERY,
    STATUS_CHARGE_STATE,
    STATUS_GPS_COORDINATE,
    STATUS_MOW_HEIGHT,
    STATUS_MOW_PROGRESS,
    STATUS_MOW_STATE,
    STATUS_NETWORK_CHANNEL,
)
from .coordinator import RoborockMowerCoordinator, RoborockMowerDevice, mower_device_id, status_value

_LOGGER = logging.getLogger(__name__)
_UNKNOWN_CODES_LOGGED: set[tuple[str, int]] = set()


def decode_gps_coordinate(value: Any) -> dict[str, Any]:
    """Decode the observed RockMow raw GPS payload."""

    if not isinstance(value, str):
        return {}

    try:
        raw = base64.b64decode(value + "=" * (-len(value) % 4))
    except (binascii.Error, ValueError):
        return {"gps_decode_error": "invalid_base64"}

    if len(raw) < 23 or raw[0:4] != b"\x08\x00\x12\x12" or raw[4] != 0x09 or raw[13] != 0x11:
        return {
            "gps_payload_bytes": len(raw),
            "gps_decode_error": "unknown_format",
        }

    latitude = struct.unpack_from("<d", raw, 5)[0]
    longitude = struct.unpack_from("<d", raw, 14)[0]
    return {
        "latitude": latitude,
        "longitude": longitude,
        "gps_payload_bytes": len(raw),
    }


def mapped_state(value: Any, mapping: dict[int, str], state_name: str) -> str | None:
    """Return a readable state while preserving unknown raw codes."""

    if value is None:
        return None
    try:
        code = int(value)
    except (TypeError, ValueError):
        return str(value)
    if code in mapping:
        return mapping[code]

    log_key = (state_name, code)
    if log_key not in _UNKNOWN_CODES_LOGGED:
        _UNKNOWN_CODES_LOGGED.add(log_key)
        _LOGGER.warning(
            "Roborock mower reported unknown %s code %s; exposing state as unknown_%s",
            state_name,
            code,
            code,
        )
    return f"unknown_{code}"


@dataclass(frozen=True, kw_only=True)
class RoborockMowerSensorEntityDescription(SensorEntityDescription):
    """Describes a Roborock mower sensor."""

    status_id: str
    value_fn: Callable[[Any], Any] = lambda value: value


SENSORS: tuple[RoborockMowerSensorEntityDescription, ...] = (
    RoborockMowerSensorEntityDescription(
        key="battery",
        name="Battery",
        status_id=STATUS_BATTERY,
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
    ),
    RoborockMowerSensorEntityDescription(
        key="mow_state",
        name="Mow state",
        status_id=STATUS_MOW_STATE,
        value_fn=lambda value: mapped_state(value, MOW_STATE_MAP, "mow_state"),
    ),
    RoborockMowerSensorEntityDescription(
        key="charge_state",
        name="Charge state",
        status_id=STATUS_CHARGE_STATE,
        value_fn=lambda value: mapped_state(value, CHARGE_STATE_MAP, "charge_state"),
    ),
    RoborockMowerSensorEntityDescription(
        key="mow_progress",
        name="Mow progress",
        status_id=STATUS_MOW_PROGRESS,
        native_unit_of_measurement=PERCENTAGE,
    ),
    RoborockMowerSensorEntityDescription(
        key="mow_height",
        name="Mow height",
        status_id=STATUS_MOW_HEIGHT,
    ),
    RoborockMowerSensorEntityDescription(
        key="gps_raw",
        name="GPS raw",
        status_id=STATUS_GPS_COORDINATE,
    ),
    RoborockMowerSensorEntityDescription(
        key="network_channel",
        name="Network channel",
        status_id=STATUS_NETWORK_CHANNEL,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Roborock mower sensors."""

    coordinator: RoborockMowerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        RoborockMowerSensor(coordinator, mower_id, description)
        for mower_id in coordinator.data
        for description in SENSORS
    )


class RoborockMowerSensor(CoordinatorEntity[RoborockMowerCoordinator], SensorEntity):
    """A read-only Roborock mower sensor."""

    entity_description: RoborockMowerSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RoborockMowerCoordinator,
        mower_id: str,
        description: RoborockMowerSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._mower_id = mower_id
        self.entity_description = description
        self._attr_unique_id = f"{mower_id}_{description.key}"

    @property
    def _mower(self) -> RoborockMowerDevice | None:
        return self.coordinator.data.get(self._mower_id)

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device registry information."""

        if self._mower is None:
            return None
        device = self._mower.device
        product = self._mower.product
        identifier = mower_device_id(device)
        return DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            manufacturer="Roborock",
            name=device.name,
            model=product.model,
            sw_version=device.fv,
            serial_number=device.sn,
        )

    @property
    def native_value(self) -> Any:
        """Return the current sensor value."""

        if self._mower is None:
            return None
        value = status_value(self._mower.device, self.entity_description.status_id)
        return self.entity_description.value_fn(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return useful debug attributes for this first integration version."""

        if self._mower is None:
            return {}
        raw_value = status_value(self._mower.device, self.entity_description.status_id)
        attrs = {
            "status_id": self.entity_description.status_id,
            "raw_value": raw_value,
            "last_cloud_update": self.coordinator.last_cloud_update,
            "last_mqtt_update": self.coordinator.last_mqtt_update,
            "last_mqtt_protocol": self.coordinator.last_mqtt_protocol,
            "last_mqtt_seen": self.coordinator.last_mqtt_seen.get(self._mower_id),
            "last_mqtt_online_hint": self.coordinator.last_mqtt_online_hint.get(self._mower_id),
            "last_mqtt_payload": self.coordinator.last_mqtt_payload.get(self._mower_id),
            "mqtt_connected": self.coordinator.mqtt_connected,
            "mqtt_subscribed": self.coordinator.mqtt_subscribed.get(self._mower_id),
            "last_mqtt_error": self.coordinator.last_mqtt_error,
            "last_update_attempt": self.coordinator.last_update_attempt,
            "last_rate_limit": self.coordinator.last_rate_limit,
            "last_status_change": self.coordinator.last_status_change.get(self._mower_id),
            "last_static_status_update": self.coordinator.last_static_status_update.get(self._mower_id),
            "product_name": self._mower.product.name,
            "product_model": self._mower.product.model,
        }
        if self.entity_description.status_id == STATUS_GPS_COORDINATE:
            attrs.update(decode_gps_coordinate(raw_value))
        return attrs
