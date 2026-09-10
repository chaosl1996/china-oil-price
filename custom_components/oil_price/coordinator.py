"""Coordinator that polls qiyoujiage.com once and shares the result."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OilPriceData, async_fetch_oil_price
from .const import MANUFACTURER

_LOGGER = logging.getLogger(__name__)


class OilPriceCoordinator(DataUpdateCoordinator[OilPriceData]):
    """所有实体共享一个协调器，每次更新只请求一次网页。"""

    def __init__(self, hass: HomeAssistant, region: str, scan_interval: timedelta) -> None:
        self.region = region
        super().__init__(
            hass,
            _LOGGER,
            name=f"{MANUFACTURER} ({region})",
            update_interval=scan_interval,
        )

    async def _async_update_data(self) -> OilPriceData:
        session = async_get_clientsession(self.hass)
        try:
            data = await async_fetch_oil_price(session, self.region)
        except (ConnectionError, ValueError) as err:
            raise UpdateFailed(str(err)) from err
        _LOGGER.debug(
            "油价更新完成: %s prices=%s next=%s trend=%s",
            data.region_name,
            data.prices,
            data.next_adjustment,
            data.trend,
        )
        return data
