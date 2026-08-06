"""Binary sensors for the Roborock Mower integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RoborockMowerCoordinator, RoborockMowerDevice, mower_device_id


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Roborock mower binary sensors."""

    coordinator: RoborockMowerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(RoborockMowerOnlineBinarySensor(coordinator, mower_id) for mower_id in coordinator.data)


class RoborockMowerOnlineBinarySensor(CoordinatorEntity[RoborockMowerCoordinator], BinarySensorEntity):
    """Roborock mower online status."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_has_entity_name = True
    _attr_name = "Online"

    def __init__(self, coordinator: RoborockMowerCoordinator, mower_id: str) -> None:
        """Initialize the binary sensor."""

        super().__init__(coordinator)
        self._mower_id = mower_id
        self._attr_unique_id = f"{mower_id}_online"

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
    def is_on(self) -> bool | None:
        """Return whether the mower is online."""

        return self.coordinator.is_mower_online(self._mower_id)
