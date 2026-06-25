from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CREATOR, DOMAIN, NAME


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        ApaAradStatusSensor(coordinator, entry),
        ApaAradBalanceSensor(coordinator, entry),
        ApaAradLastInvoiceSensor(coordinator, entry),
        ApaAradConsumptionSensor(coordinator, entry),
        ApaAradIndexSensor(coordinator, entry),
        ApaAradMeterSensor(coordinator, entry),
        ApaAradUsernameSensor(coordinator, entry),
        ApaAradCustomerNameSensor(coordinator, entry),
        ApaAradAddressSensor(coordinator, entry),
    ]

    async_add_entities(sensors)


class ApaAradBaseSensor(CoordinatorEntity, SensorEntity):
    _attr_attribution = ATTRIBUTION

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
            manufacturer=CREATOR,
            model="Compania de Apa Arad cloud account",
            configuration_url="https://myarad.croscloud.com/crosweb",
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
    _attr_native_unit_of_measurement = "RON"

    @property
    def name(self) -> str:
        return f"{self._entry.title} Sold"

    @property
    def unique_id(self) -> str:
        return f"apa_arad_balance_{self._entry.entry_id}"

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.get("balance")

class ApaAradLastInvoiceSensor(ApaAradBaseSensor):
    _attr_native_unit_of_measurement = "RON"

    @property
    def name(self) -> str:
        return f"{self._entry.title} Ultima factura"

    @property
    def unique_id(self) -> str:
        return f"apa_arad_last_invoice_{self._entry.entry_id}"

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.get("last_invoice")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "invoice_number": self.coordinator.data.get("last_invoice_number"),
            "invoice_date": self.coordinator.data.get("last_invoice_date"),
            "due_date": self.coordinator.data.get("last_invoice_due_date"),
            "status": self.coordinator.data.get("last_invoice_status"),
        }


class ApaAradConsumptionSensor(ApaAradBaseSensor):
    _attr_native_unit_of_measurement = "m³"

    @property
    def name(self) -> str:
        return f"{self._entry.title} Consum"

    @property
    def unique_id(self) -> str:
        return f"apa_arad_consumption_{self._entry.entry_id}"

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.get("consumption_last_period")

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

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "contract": self.coordinator.data.get("contract_number"),
            "self_reading_code": self.coordinator.data.get("self_reading_code"),
        }


class ApaAradIndexSensor(ApaAradBaseSensor):
    @property
    def name(self) -> str:
        return f"{self._entry.title} Ultimul index"

    @property
    def unique_id(self) -> str:
        return f"apa_arad_latest_index_{self._entry.entry_id}"

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.get("latest_index")


class ApaAradUsernameSensor(ApaAradBaseSensor):
    @property
    def name(self) -> str:
        return f"{self._entry.title} Utilizator"

    @property
    def unique_id(self) -> str:
        return f"apa_arad_username_{self._entry.entry_id}"

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.get("username")


class ApaAradCustomerNameSensor(ApaAradBaseSensor):
    @property
    def name(self) -> str:
        return f"{self._entry.title} Titular"

    @property
    def unique_id(self) -> str:
        return f"apa_arad_customer_name_{self._entry.entry_id}"

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.get("customer_name")


class ApaAradAddressSensor(ApaAradBaseSensor):
    @property
    def name(self) -> str:
        return f"{self._entry.title} Adresă"

    @property
    def unique_id(self) -> str:
        return f"apa_arad_address_{self._entry.entry_id}"

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.get("service_address")
