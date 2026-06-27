"""The Thermoworks Cloud integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN
from .coordinator import ThermoworksCoordinator

# The list of platforms provided by this integration
PLATFORMS: list[Platform] = [Platform.SENSOR]


@dataclass
class RuntimeData:
    """Data available globally throughout the integration."""

    coordinator: ThermoworksCoordinator
    cancel_update_listener: Callable


ThermoworksConfigEntry = ConfigEntry[RuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: ThermoworksConfigEntry) -> bool:
    """Set up Thermoworks Cloud from a config entry."""
    # Initialise the coordinator that manages data updates from your api.
    # This is defined in coordinator.py
    coordinator = ThermoworksCoordinator(hass, entry)

    # Perform an initial data load from api.
    # async_config_entry_first_refresh() is special in that it does not log errors if it fails
    await coordinator.async_config_entry_first_refresh()

    # Test to see if api initialised correctly, else raise ConfigNotReady to make HA retry setup
    if not coordinator.api:
        raise ConfigEntryNotReady

    # Initialise a listener for config flow options changes.
    # See config_flow for defining an options setting that shows up as configure on the integration.
    cancel_update_listener = entry.add_update_listener(_async_update_listener)

    # Store coordinator and update listener directly on the config entry
    entry.runtime_data = RuntimeData(coordinator, cancel_update_listener)

    # Setup platforms (based on the list of entity types in PLATFORMS defined above)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Return true to denote a successful setup.
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ThermoworksConfigEntry) -> None:
    """Handle config options update."""
    # Update the coordinator scan interval dynamically without needing a full integration reload.
    coordinator = entry.runtime_data.coordinator
    coordinator.update_interval = timedelta(
        seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS)
    )


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ThermoworksConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Delete device if selected from UI."""
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ThermoworksConfigEntry) -> bool:
    """Unload a config entry.

    This is called when you remove your integration or shutdown HA.
    """

    # Remove the config options update listener
    entry.runtime_data.cancel_update_listener()

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )

    return unload_ok
