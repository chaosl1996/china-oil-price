# 我给 Home Assistant 重写了一个中国油价集成

> 从一个"能用但很糙"的自定义集成出发，聊聊 HA 集成开发的正确姿势：协调器、唯一 ID、实体翻译，以及一次"集成图标为什么不显示"的深挖。

## 起因

家里的 Home Assistant 一直挂着一个中国油价集成（[zhoujunn/oil-price-hacs](https://github.com/zhoujunn/oil-price-hacs)，数据源是汽油价格网 qiyoujiage.com），功能上没问题，但用起来总有点别扭：

- **信息是散的**：92#/95#/98#/0# 柴油四五个实体各自抓一次网页，"下次调价"实体更是把站点文案正则拼成一坨字符串塞进 state；
- **状态不是数据**：油价是 `"8.68元/升"` 这样的字符串，想做历史曲线、做"涨价了提醒"都得先解析文本；
- **体验粗糙**：配置要手输 `jiangsu` 这种拼音 slug，输错一个字母就 404。

于是动手重写，也就是 [china-oil-price](https://github.com/chaosl1996/china-oil-price)。

## 架构：一个协调器，五类传感器

老版本每个传感器独立抓网页，一次刷新 5 个请求。新版本用 `DataUpdateCoordinator` 把抓取收敛成一份共享数据：

```python
class OilPriceCoordinator(DataUpdateCoordinator[OilPriceData]):
    async def _async_update_data(self) -> OilPriceData:
        session = async_get_clientsession(self.hass)
        try:
            return await async_fetch_oil_price(session, self.region)
        except (ConnectionError, ValueError) as err:
            raise UpdateFailed(str(err)) from err
```

所有实体继承 `CoordinatorEntity`，天然共享缓存、统一可用性状态。这是 HA 官方推荐的模式，也是自定义集成和"玩具"的分水岭之一。

页面解析没有引入 BeautifulSoup——两个目标区块（价格表、调价信息框）结构多年稳定，几十行正则就够了，manifest 的 `requirements` 保持为空，安装零负担。

## 两个值得记的坑

### 1. "X月X日24时调整"怎么变成时间戳

站点只给"下次油价9月11日24时调整"，要变成可计算的时间需要两步推理：

- **"24 时"就是该日的 24:00**，等价于次日凌晨 0 点。直觉上容易写成当天 00:00，那样"今天 24 时调价"会被判定成过去时；
- 站点不给年份，按**"未来最近一次出现"**推断：先试今年，比现在早就用明年。

```python
for year in (now.year, now.year + 1):
    effective = datetime(year, month, day, tzinfo=TZ_CHINA) + timedelta(days=1)
    if effective > now:
        return effective.astimezone(timezone.utc)
```

调价窗口每 10 个工作日一次，年份推断出错概率极低，但一旦遇到月初边界就会诡异地差一年——上线第一天就撞上了，顺手修掉。

### 2. 集成图标为什么不显示

给集成配了漂亮的 `icon.png`，结果 HA 集成列表里还是个拼图。翻 HA 2025.9 的前端编译产物才发现：**图标 URL 是写死的** `https://brands.home-assistant.io/{域名}/icon.png`，本地文件只对 HACS 商店页生效。

而 HA 新版（2026.3+）已经改了机制：内置 `brands` 组件，前端从本机 `/api/brands/integration/{域名}/icon.png` 取图，后端直接读集成目录下的 `brand/` 子文件夹。所以现在是双保险：

- 集成里内置 `brand/` 目录（新版 HA 开箱即用）；
- 同时往 [home-assistant/brands](https://github.com/home-assistant/brands) 提了 PR（旧版本 HA 走 CDN，合并后同样生效）。

## 数据模型：让文案变成字段

站点调价框的原文长这样：

> 目前预计上调油价260元/吨(0.20元/升-0.24元/升)，大家相互转告油价又涨了。

对人是文案，对自动化是噪声。解析时拆成结构化字段，原文保留备查：

| 属性 | 值 |
|------|-----|
| `下次调价时间` | `2026-09-12T00:00:00+08:00` |
| `调价方向` | `上调` |
| `预计调整幅度` | `260元/吨（0.20-0.24元/升）` |
| `预测原文` | 目前预计上调油价260元/吨… |

于是"调价前夜提醒"的自动化干净得像样多了：

```yaml
condition:
  - condition: template
    value_template: >
      {% set next = state_attr('sensor.gan_su_you_jie_next_price_adjustment',
                              '下次调价时间') | as_datetime %}
      {{ next is not none and 0 < (next - now()).total_seconds() < 86400 }}
```

## 安装

HACS 添加自定义仓库 `https://github.com/chaosl1996/china-oil-price`，类别选 Integration，搜索安装即可。配置时下拉选省市、名称留空自动生成，32 个地区随便加。

## 结语

重写的全部代码就是 `custom_components/oil_price/` 下十个文件：协调器、API 解析、配置流、传感器、翻译。没有一行BeautifulSoup，没有一次多余的请求，但对 HA 的实体注册表、统计、自动化都足够友好。

"能用"和"好用"之间的距离，往往就是把这些细节补齐的过程。

---

*数据来源：[汽油价格网](https://www.qiyoujiage.com) · 感谢原作者 [@zhoujunn](https://github.com/zhoujunn)*
