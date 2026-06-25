from __future__ import annotations

from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CREATOR, DOMAIN, NAME


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entity_registry = er.async_get(hass)
    old_unique_id = f"apa_arad_customer_name_{entry.entry_id}"
    old_entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, old_unique_id
    )
    if old_entity_id:
        entity_registry.async_remove(old_entity_id)

    sensors = [
        ApaAradStatusSensor(coordinator, entry),
        ApaAradBalanceSensor(coordinator, entry),
        ApaAradLastInvoiceSensor(coordinator, entry),
        ApaAradInvoiceDateSensor(coordinator, entry),
        ApaAradInvoiceDueDateSensor(coordinator, entry),
        ApaAradConsumptionSensor(coordinator, entry),
        ApaAradIndexSensor(coordinator, entry),
        ApaAradMeterSensor(coordinator, entry),
        ApaAradUsernameSensor(coordinator, entry),
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
            "status": self.coordinator.data.get("last_invoice_status"),
        }


def _parse_portal_date(value: str | None) -> date | None:
    """Convert a portal date to a Home Assistant date value."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError:
        return None


class ApaAradInvoiceDateSensor(ApaAradBaseSensor):
    _attr_device_class = SensorDeviceClass.DATE

    @property
    def name(self) -> str:
        return f"{self._entry.title} Data emiterii"

    @property
    def unique_id(self) -> str:
        return f"apa_arad_invoice_date_{self._entry.entry_id}"

    @property
    def native_value(self) -> date | None:
        return _parse_portal_date(self.coordinator.data.get("last_invoice_date"))


class ApaAradInvoiceDueDateSensor(ApaAradBaseSensor):
    _attr_device_class = SensorDeviceClass.DATE

    @property
    def name(self) -> str:
        return f"{self._entry.title} Data scadenței"

    @property
    def unique_id(self) -> str:
        return f"apa_arad_invoice_due_date_{self._entry.entry_id}"

    @property
    def native_value(self) -> date | None:
        return _parse_portal_date(
            self.coordinator.data.get("last_invoice_due_date")
        )


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

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"period": self.coordinator.data.get("consumption_period")}

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
