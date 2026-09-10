<div align="center">

<img src="logo.png" alt="China Oil Price" width="160"/>

# China Oil Price · 中国油价

**为 Home Assistant 提供国内各省市成品油零售价与下次调价预测**

数据来源：[汽油价格网 qiyoujiage.com](https://www.qiyoujiage.com)
适配 Home Assistant 2024.4 及以上版本（已适配 2025.6+）

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
![Version](https://img.shields.io/badge/version-2.1.0-E60012)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

## ✨ 特性

- 🗺️ **32 个省市下拉选择**：配置时直接选择地区（含中文名），无需手动输入拼音 slug
- 📊 **结构化传感器**：92# / 95# / 98# 汽油与 0# 柴油为纯数值（单位：元/升），可直接参与统计图表与自动化
- ⏰ **下次调价时间**：以时间戳传感器提供（站点“X月X日24时”已换算为精确时刻），调价方向与预测幅度写入属性
- 🔁 **单请求协调器**：所有实体共享一个 `DataUpdateCoordinator`，每次刷新只请求网页一次
- 🏷️ **唯一 ID + 设备归组**：实体可在 UI 中改名、分配区域，同一地区的 5 个传感器归属同一设备
- 🌐 **中英双语**：配置界面与实体名称均有简体中文 / English 翻译
- 🔌 **零额外依赖**：纯正则解析，无需安装 beautifulsoup4 / lxml
- ⚙️ **可配置刷新间隔**：集成选项中可调整（1–48 小时，默认 8 小时）
- ➕ **支持多地区**：可同时添加多个省市，分别建卡对比
- 💠 **集成图标**：内置 `brand/` 目录，HA 2026.3+ 直接显示宝石花图标（旧版本通过官方 brands 服务生效）

## 📦 安装

### HACS（推荐）

1. HACS → Integrations → 右上角 ⋮ → **Custom repositories**
2. 仓库地址填入本仓库 URL，类别选择 **Integration**
3. 搜索并安装 **China Oil Price 中国油价**
4. 重启 Home Assistant

### 手动安装

将 `custom_components/oil_price/` 整个目录复制到 HA 配置目录下的 `custom_components/`，重启 Home Assistant。

## ⚙️ 配置

**设置 → 设备与服务 → 添加集成 → 搜索 "China Oil Price"**

| 字段 | 说明 |
|------|------|
| 地区 | 下拉选择省市（北京、江苏、广东……） |
| 设备名称 | 留空则自动命名为「地区名 + 油价」，如「甘肃油价」 |

同一地区不可重复添加；如需其他地区，在集成页面再次添加即可。

## 📡 实体

以「甘肃油价」为例（实体 ID 由 HA 按设备名自动生成，可在实体信息中查看）：

| 实体 | 说明 | 示例值 |
|------|------|--------|
| `sensor.gan_su_you_jie_92_gasoline` | 92号汽油 | `8.09` 元/升 |
| `sensor.gan_su_you_jie_95_gasoline` | 95号汽油 | `8.63` 元/升 |
| `sensor.gan_su_you_jie_98_gasoline` | 98号汽油 | `9.20` 元/升 |
| `sensor.gan_su_you_jie_0_diesel` | 0号柴油 | `7.66` 元/升 |
| `sensor.gan_su_you_jie_next_price_adjustment` | 下次调价时间 | `2026-09-11T16:00:00+00:00` |

所有传感器都带有以下属性（时间为北京时间，可直接用 `as_datetime` 处理）：

| 属性 | 说明 | 示例 |
|------|------|------|
| `下次调价时间` | 下次调价窗口（站点“24 时”即该日次日凌晨） | `2026-09-12T00:00:00+08:00` |
| `调价方向` | 上调 / 下调 / 搁浅 | `上调` |
| `预计调整幅度` | 结构化幅度 | `260元/吨（0.20-0.24元/升）` |
| `预测原文` | 数据源站点预测文案原话 | `目前预计上调油价260元/吨…` |
| `数据更新时间` | 本次抓取时间 | `2026-09-11T00:41:06+08:00` |

## 🤖 自动化示例

调价前一天晚上 8 点提醒：

```yaml
automation:
  - alias: 油价调整提醒
    trigger:
      - platform: time
        at: "20:00:00"
    condition:
      - condition: template
        value_template: >
          {% set next = state_attr('sensor.gan_su_you_jie_next_price_adjustment', '下次调价时间') | as_datetime %}
          {{ next is not none and 0 < (next - now()).total_seconds() < 86400 }}
    action:
      - service: notify.notify
        data:
          title: "⚠️ 明天油价调整"
          message: >
            方向：{{ state_attr('sensor.gan_su_you_jie_next_price_adjustment', '调价方向') }}
            预计：{{ state_attr('sensor.gan_su_you_jie_next_price_adjustment', '预计调整幅度') }}
```

> 请将示例中的实体 ID 替换为你自己的（配置 → 设备与服务 → 中国油价 → 实体）。

## ❓ 常见问题

**价格多久更新一次？**
国内成品油调价窗口约每 10 个工作日一次（发改委调价）。集成默认每 8 小时拉取一次，足够及时；可在集成选项中调整。

**为什么实体显示「不可用」？**
通常是数据源网站暂时无法访问或改版。集成会在下个刷新周期自动重试；若长时间不可用请提 Issue。

**集成列表里为什么不显示宝石花图标？**
- HA **2026.3+**：集成自带 `brand/` 目录，直接生效（如仍显示旧图标，强制刷新浏览器缓存）。
- HA **2026.3 以下**：图标来自官方 [brands](https://github.com/home-assistant/brands) 服务，本集成的图标已通过 [PR #11139](https://github.com/home-assistant/brands/pull/11139) 提交，合并后自动生效。

**与原版 [zhoujunn/oil-price-hacs](https://github.com/zhoujunn/oil-price-hacs) 的关系？**
本项目在原版思路上重构：新增协调器架构、唯一 ID、设备归组、地区下拉选择、时间戳调价实体、实体翻译与选项流，并移除了 BeautifulSoup 依赖。感谢原作者 @zhoujunn 的开创工作。

## 📄 许可证

[MIT](LICENSE)

Logo「宝石花」版权归中国石油天然气集团有限公司所有，本仓库仅将其用作油价数据来源的标识，与中国石油天然气集团有限公司无隶属或合作关系，如有侵权请联系删除。
