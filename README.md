# ActivityPush

GsCore 插件：多游戏活动 / 版本查询与到期提醒。

支持 **崩坏：星穹铁道、原神、绝区零、鸣潮、异环、明日方舟：终末地** 六款游戏。

> 数据来自第三方公开接口，非官方接口；仅用于查询与提醒，不涉及账号登录。

## 功能

- **活动查询**：查询当前版本与全部活动，含起止时间、剩余天数，输出图片卡片。
- **版本查询**：当前版本号 / 版本名 / 版本起止时间。
- **个人提醒**：创建活动到期提醒，活动剩余 3 / 2 / 1 天时在群里 @ 你；也可以让 AI 直接创建。
- **群级推送**：群里开启后，活动临近结束时自动推送汇总。
- **AI 可调用**：所有查询 / 提醒能力注册为 AI 工具；开启 GsCore AI Core 后，AI 可以直接调用。
- **定时缓存**：默认每 6 小时拉取一次活动数据并落盘缓存。

## 环境要求

- Python >= 3.11
- GsCore 上游 `0.11.x`（主目标），或 `AthenaHibou/gsuid_core` 的 `main`（基于 `0.10.7` + 定制补丁）
- AI Core 可选；不开启时，用户命令仍然可用，只是 AI 工具不会注册

> 上游当前基线为 `0.11.2`；`AthenaHibou/gsuid_core` 的 `main` 基于 `0.10.7` + 定制补丁，AI Core 行为可能与上游不同。0.10.7 早期快照可能没有 `covers/aliases`；缺少时插件通常仍能加载，但 AI 召回会下降。

## 安装

### 方式一：core 安装插件（收录到插件列表后）

```text
安装插件ActivityPush
```

### 方式二：手动 clone

```bash
cd gsuid_core/gsuid_core/plugins
git clone https://github.com/AthenaHibou/ActivityPush
```

然后重启 Core。

## 命令

指令关键字可以在 Web 控制台的「插件配置」中修改，默认 `>`。

| 命令 | 说明 |
|---|---|
| `>活动查询 <游戏> [关键词]` | 查询活动列表，例如 `>活动查询 原神` |
| `>版本查询 <游戏>` | 查询版本信息，例如 `>版本查询 星铁` |
| `>活动提醒 <游戏> <活动名>` | 创建个人到期提醒 |
| `>我的提醒` | 列出自己的提醒 |
| `>关闭活动提醒 <活动名>` | 关闭提醒 |
| `>开启活动推送` / `>关闭活动推送` | 群级到期推送开关 |
| `>活动帮助` | 输出帮助图 |

支持的游戏标识：`sr` / `ys` / `zzz` / `ww` / `nte` / `ef`，也支持中文名和常见别名。

## 配置

在 Web 控制台「插件配置」中修改：

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `command_keyword` | `>` | 命令前缀，修改后需重启 Core |
| `api_base` | `https://starrailassistant.top/api/v1` | StarRailAssistant API 地址 |
| `fetch_interval` | `360` | 定时拉取间隔（分钟） |
| `remind_days` | `["3","2","1"]` | 触发提醒的剩余天数 |
| `enable_group_push` | `true` | 群级到期推送 |
| `enable_user_remind` | `true` | 个人提醒 |
| `enable_game_sr` / `ys` / `zzz` / `ww` / `nte` / `ef` | `true` | 各游戏开关 |

运行数据保存在 `data/ActivityPush/`，不会提交到仓库。

## AI 工具

开启 AI Core 后注册以下工具：

- `query_activities(game, keyword="")`
- `query_version(game)`
- `create_activity_reminder(game, activity_name)`
- `close_activity_reminder(activity_name="")`
- `list_my_reminders()`

示例：直接对机器人说「原神这周还有什么活动」「原神的某某活动快结束了提醒我」。

## 数据源与致谢

- [StarRailAssistant 公开 API](https://starrailassistant.top/public-api/)：活动 / 版本主数据。
- `https://ef-cal.mogujun.icu/api/v1/events`：终末地版本日历。
- 本项目与上述服务、游戏官方均无隶属关系；接口结构或可用性变化可能导致查询失败。

## 兼容性

- **主目标**：上游 `Genshin-bots/gsuid_core` 的 `master`，当前为 `0.11.2`。
- **Fork 目标**：`AthenaHibou/gsuid_core` 的 `main`，基于 `0.10.7` + 定制补丁；AI Core 行为可能与上游不同。
- 代码按上游 `0.11.2` 的 API 编写；导入与关键符号已做过静态对照，实际运行仍取决于 AI Core 配置和数据库状态。
- 使用了 `ai_tools` 的 `covers` / `aliases` 元数据；旧核心没有这些参数时会被忽略，不影响基本命令，但 AI 召回会下降。
- 使用了 `BaseModel` / `GsAdminModel` 的 Web 后台注册；如果核心数据库或后台 API 有破坏性变更，需要同步适配。

## License

GPL-3.0-or-later。见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。
