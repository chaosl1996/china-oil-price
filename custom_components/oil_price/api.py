"""Client for fetching and parsing oil prices from qiyoujiage.com.

解析不依赖 BeautifulSoup，仅用正则处理页面中两个稳定的区块：

1. ``<div id="youjia">`` 内的若干 ``<dl><dt>江苏92#汽油</dt><dd>7.41</dd></dl>``
2. 紧随其后的调价信息区块，如::

    下次油价12月4日24时调整<br/>
    <span>目前预计上调35元/吨(未达到上调标准)，大家相互转告油价上涨中</span>
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import aiohttp

from .const import DATA_URL, REQUEST_TIMEOUT, USER_AGENT

_LOGGER = logging.getLogger(__name__)

TZ_CHINA = ZoneInfo("Asia/Shanghai")

_DL_RE = re.compile(r"<dl[^>]*>(.*?)</dl>", re.S)
_DT_RE = re.compile(r"<dt[^>]*>(.*?)</dt>", re.S)
_DD_RE = re.compile(r"<dd[^>]*>(.*?)</dd>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(r"<script.*?</script>", re.S | re.I)
_BR_RE = re.compile(r"<br\s*/?>", re.I)
_OIL_NO_RE = re.compile(r"(\d{1,2})\s*#")
_PRICE_RE = re.compile(r"\d+(?:\.\d+)?")
_ADJUST_RE = re.compile(
    r"下次?油价\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*24\s*时(?:前后)?调整"
)
_SPAN_RE = re.compile(r"<span[^>]*>(.*?)</span>", re.S)

_TREND_UP_RE = re.compile(r"上调|上涨|涨幅")
_TREND_DOWN_RE = re.compile(r"下调|下跌|跌幅")
# 涨跌幅度，如 “260元/吨” “60元/吨-70元/吨” “0.20元/升-0.24元/升”
_RANGE_TON_RE = re.compile(
    r"\d+(?:\.\d+)?元/吨(?:\s*[-~至到]\s*\d+(?:\.\d+)?元/吨)?"
)
_RANGE_LITER_RE = re.compile(
    r"\d+(?:\.\d+)?元/升(?:\s*[-~至到]\s*\d+(?:\.\d+)?元/升)?"
)


def _norm_range(text: str) -> str:
    """“0.20元/升-0.24元/升” → “0.20-0.24元/升”，去掉重复单位。"""
    return re.sub(r"(元/[吨升])\s*[-~至到]\s*(?=\d)", "-", text)


@dataclass
class OilPriceData:
    """一次抓取得到的全部数据。"""

    region: str
    # 油品编号 -> 单价（元/升），键为 "92" / "95" / "98" / "0"
    prices: dict[str, float] = field(default_factory=dict)
    # 下次调价时间（北京时间 24 时，即次日凌晨，已转 UTC）
    next_adjustment: datetime | None = None
    # 调价方向：上调 / 下调 / 搁浅
    trend: str | None = None
    # 调价预测原文（站点文案）
    forecast: str | None = None
    # 结构化的预测幅度，如 “260元/吨” “0.20-0.24元/升”
    forecast_ton: str | None = None
    forecast_liter: str | None = None
    fetched_at: datetime | None = None

    @property
    def region_name(self) -> str:
        from .const import REGION_NAMES  # 局部导入避免循环

        return REGION_NAMES.get(self.region, self.region)


def _decode(raw: bytes) -> str:
    """按优先级尝试解码，兼容 UTF-8（BOM）与 GBK 系老页面。"""
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _parse_next_adjustment(text: str) -> datetime | None:
    """从 “下次油价12月4日24时调整” 推断具体时间。

    站点只给出月/日，按“最近的未来一次出现”推断年份；
    “24 时”即该日 24:00，等价于次日 00:00（北京时间），返回 UTC。
    """
    match = _ADJUST_RE.search(text)
    if match is None:
        return None
    month, day = int(match.group(1)), int(match.group(2))
    now = datetime.now(TZ_CHINA)
    for year in (now.year, now.year + 1):
        try:
            # “24 时”即该日结束的时刻（次日凌晨 0 点），用它判断是否属于未来
            effective = datetime(year, month, day, tzinfo=TZ_CHINA) + timedelta(days=1)
        except ValueError:  # 如 2 月 29 日
            continue
        if effective > now:
            return effective.astimezone(timezone.utc)
    return None


def _parse_forecast(text: str) -> str | None:
    """提取调价预测文案（含涨跌方向的第一个句子）。"""
    for span in _SPAN_RE.finditer(text):
        content = _TAG_RE.sub("", span.group(1)).strip()
        if _TREND_UP_RE.search(content) or _TREND_DOWN_RE.search(content):
            return content
    # 兜底：调价时间之后的纯文本里找
    match = _ADJUST_RE.search(text)
    if match:
        chunk = _TAG_RE.sub(" ", text[match.end(): match.end() + 400])
        for line in (part.strip() for part in chunk.split()):
            if _TREND_UP_RE.search(line) or _TREND_DOWN_RE.search(line):
                return line
    return None


def parse_html(region: str, html: str) -> OilPriceData:
    """把页面解析为结构化数据。"""
    data = OilPriceData(
        region=region, fetched_at=datetime.now(TZ_CHINA).astimezone(timezone.utc)
    )

    for dl in _DL_RE.finditer(html):
        dt_match = _DT_RE.search(dl.group(1))
        dd_match = _DD_RE.search(dl.group(1))
        if dt_match is None or dd_match is None:
            continue
        oil_no = _OIL_NO_RE.search(_TAG_RE.sub("", dt_match.group(1)))
        price = _PRICE_RE.search(_TAG_RE.sub("", dd_match.group(1)))
        if oil_no is None or price is None:
            continue
        data.prices[oil_no.group(1)] = float(price.group(0))

    if not data.prices:
        raise ValueError("未能在页面中解析到任何油价数据")

    data.next_adjustment = _parse_next_adjustment(html)
    data.forecast = _parse_forecast(html)
    source = data.forecast or html
    if ton := _RANGE_TON_RE.search(source):
        data.forecast_ton = _norm_range(ton.group(0))
    if liter := _RANGE_LITER_RE.search(source):
        data.forecast_liter = _norm_range(liter.group(0))
    if data.forecast:
        data.trend = (
            "上调"
            if _TREND_UP_RE.search(data.forecast)
            else "下调"
            if _TREND_DOWN_RE.search(data.forecast)
            else "搁浅"
        )
    return data


async def async_fetch_oil_price(
    session: aiohttp.ClientSession, region: str
) -> OilPriceData:
    """抓取并解析指定地区的油价页面。"""
    url = DATA_URL.format(region=region)
    headers = {"User-Agent": USER_AGENT}
    try:
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        ) as response:
            response.raise_for_status()
            raw = await response.read()
    except (aiohttp.ClientError, TimeoutError) as err:
        raise ConnectionError(f"请求油价页面失败: {url}") from err

    try:
        return parse_html(region, _decode(raw))
    except ValueError as err:
        raise ValueError(f"解析油价页面失败: {url}") from err
