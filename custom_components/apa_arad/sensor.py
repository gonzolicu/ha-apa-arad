from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ApaAradStatusSensor(coordinator)
    ])


class ApaAradStatusSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Apa Arad Status"
    _attr_unique_id = "apa_arad_status"

    @property
    def native_value(self):
        if self.coordinator.data:
            return "Connected"
        return "Unavailable"
