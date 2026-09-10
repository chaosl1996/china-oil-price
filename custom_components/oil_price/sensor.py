"""Sensors for the China Oil Price integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import TZ_CHINA
from .const import DOMAIN, MANUFACTURER, REGION_NAMES
from .coordinator import OilPriceCoordinator

# (油价键, translation_key, 图标)
OIL_TYPES: list[tuple[str, str, str]] = [
    ("92", "gasoline_92", "mdi:gas-station"),
    ("95", "gasoline_95", "mdi:gas-station"),
    ("98", "gasoline_98", "mdi:gas-station"),
    ("0", "diesel_0", "mdi:gas-station"),
]


def _as_beijing(value: datetime | None) -> datetime | None:
    """UTC 时间转北京时间，便于属性直接阅读。"""
    if value is None:
        return None
    return value.astimezone(TZ_CHINA)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up oil price sensors from a config entry."""
    coordinator: OilPriceCoordinator = hass.data[DOMAIN][entry.entry_id]
    region_name = REGION_NAMES.get(coordinator.region, coordinator.region)

    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data["name"],
        manufacturer=MANUFACTURER,
        model=f"{region_name}成品油零售价",
        entry_type=DeviceEntryType.SERVICE,
    )

    entities: list[SensorEntity] = [
        OilPriceSensor(coordinator, entry, device_info, oil_key, translation_key, icon)
        for oil_key, translation_key, icon in OIL_TYPES
    ]
    entities.append(NextAdjustmentSensor(coordinator, entry, device_info))
    async_add_entities(entities)


class _OilPriceBaseEntity(CoordinatorEntity[OilPriceCoordinator], SensorEntity):
    """公共部分：唯一 ID、设备信息与共享属性。"""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OilPriceCoordinator,
        entry: ConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = device_info

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """所有实体共享的调价信息属性（时间均为北京时间）。"""
        data = self.coordinator.data
        amount = data.forecast_ton
        if data.forecast_liter:
            amount = (
                f"{amount}（{data.forecast_liter}）" if amount else data.forecast_liter
            )
        return {
            "下次调价时间": _as_beijing(data.next_adjustment),
            "调价方向": data.trend,
            "预计调整幅度": amount,
            "预测原文": data.forecast,
            "数据更新时间": _as_beijing(data.fetched_at),
        }


class OilPriceSensor(_OilPriceBaseEntity):
    """单个油品的零售价，单位 元/升。"""

    def __init__(
        self,
        coordinator: OilPriceCoordinator,
        entry: ConfigEntry,
        device_info: DeviceInfo,
        oil_key: str,
        translation_key: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, entry, device_info)
        self._oil_key = oil_key
        self._attr_translation_key = translation_key
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}-oil-{oil_key}"
        self._attr_native_unit_of_measurement = "元/升"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 2

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.prices.get(self._oil_key)


class NextAdjustmentSensor(_OilPriceBaseEntity):
    """下次油价调整时间（北京时间 24 时，即次日凌晨）。"""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "next_adjustment"
    _attr_icon = "mdi:gas-station"

    def __init__(
        self,
        coordinator: OilPriceCoordinator,
        entry: ConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator, entry, device_info)
        self._attr_unique_id = f"{entry.entry_id}-next-adjustment"

    @property
    def native_value(self):
        return self.coordinator.data.next_adjustment
