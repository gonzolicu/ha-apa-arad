from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        ApaAradStatusSensor(coordinator, entry),
        ApaAradBalanceSensor(coordinator, entry),
        ApaAradLastInvoiceSensor(coordinator, entry),
        ApaAradConsumptionSensor(coordinator, entry),
        ApaAradMeterSensor(coordinator, entry),
    ]

    async_add_entities(sensors)


class ApaAradBaseSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and bool(self.coordinator.data)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=NAME,
            manufacturer="Compania de Apa Arad",
        )


class ApaAradStatusSensor(ApaAradBaseSensor):
    @property
    def name(self) -> str:
        return f"{self._entry.title} Status"

    @property
    def unique_id(self) -> str:
        return f"apa_arad_status_{self._entry.entry_id}"

    @property
    def native_value(self) -> str:
        if self.coordinator.data:
            return "Conectat"
        return "Indisponibil"


class ApaAradBalanceSensor(ApaAradBaseSensor):
    @property
    def name(self) -> str:
        return f"{self._entry.title} Sold"

    @property
    def unique_id(self) -> str:
        return f"apa_arad_balance_{self._entry.entry_id}"

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.get("balance")

    @property
    def unit_of_measurement(self) -> str:
        return "RON"


class ApaAradLastInvoiceSensor(ApaAradBaseSensor):
    @property
    def name(self) -> str:
        return f"{self._entry.title} Ultima factura"

    @property
    def unique_id(self) -> str:
        return f"apa_arad_last_invoice_{self._entry.entry_id}"

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.get("last_invoice")


class ApaAradConsumptionSensor(ApaAradBaseSensor):
    @property
    def name(self) -> str:
        return f"{self._entry.title} Consum"

    @property
    def unique_id(self) -> str:
        return f"apa_arad_consumption_{self._entry.entry_id}"

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.get("consumption_last_period")

    @property
    def unit_of_measurement(self) -> str:
        return "m3"


class ApaAradMeterSensor(ApaAradBaseSensor):
    @property
    def name(self) -> str:
        return f"{self._entry.title} Contor"

    @property
    def unique_id(self) -> str:
        return f"apa_arad_meter_{self._entry.entry_id}"

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.get("meter_number")
