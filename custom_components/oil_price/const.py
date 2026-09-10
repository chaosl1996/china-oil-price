"""Constants for the China Oil Price integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "oil_price"

MANUFACTURER = "汽油价格网 qiyoujiage.com"

# 注意：该站点 https 证书在部分网络环境下校验失败，http 可正常访问。
DATA_URL = "http://www.qiyoujiage.com/{region}.shtml"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 30

# 地区列表：(站点 slug, 中文名)
# 顺序按惯例的地理分区排列，与 qiyoujiage.com 导航一致。
# 注：陕西的 slug 为 "shanxi-3"，山西为 "shanxi"。
REGIONS: list[tuple[str, str]] = [
    ("beijing", "北京"),
    ("tianjin", "天津"),
    ("hebei", "河北"),
    ("shanxi", "山西"),
    ("neimenggu", "内蒙古"),
    ("liaoning", "辽宁"),
    ("jilin", "吉林"),
    ("heilongjiang", "黑龙江"),
    ("shanghai", "上海"),
    ("jiangsu", "江苏"),
    ("zhejiang", "浙江"),
    ("anhui", "安徽"),
    ("fujian", "福建"),
    ("jiangxi", "江西"),
    ("shandong", "山东"),
    ("henan", "河南"),
    ("hubei", "湖北"),
    ("hunan", "湖南"),
    ("guangdong", "广东"),
    ("shenzhen", "深圳"),
    ("guangxi", "广西"),
    ("hainan", "海南"),
    ("chongqing", "重庆"),
    ("sichuan", "四川"),
    ("guizhou", "贵州"),
    ("yunnan", "云南"),
    ("xizang", "西藏"),
    ("shanxi-3", "陕西"),
    ("gansu", "甘肃"),
    ("qinghai", "青海"),
    ("ningxia", "宁夏"),
    ("xinjiang", "新疆"),
]
REGION_NAMES: dict[str, str] = dict(REGIONS)

DEFAULT_SCAN_INTERVAL = timedelta(hours=8)
