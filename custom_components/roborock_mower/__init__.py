"""The Roborock Mower integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import RoborockMowerCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Roborock Mower from a config entry."""

    coordinator = RoborockMowerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_start_mqtt()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: RoborockMowerCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_stop_mqtt()
    return unload_ok


# TODO: Add read-write button entities later when command handling is understood:
# start = 201, dock = 202, pause = 203, resume = 204, stop = 205.
