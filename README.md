# nonebot-plugin-milky-chat

> NoneBot AI 聊天插件，基于 **nonebot-adapter-milky** 协议，@机器人即可对话，支持 OpenAI / Anthropic 双协议，多 API 运行时切换。

## ✨ 特性

- 🔌 **ChatClient** — 封装 OpenAI / Anthropic API 的异步通信层
- 🎛️ **多 API 支持** — 配置多个 API 提供商，QQ 端一键切换
- 🔄 **双协议适配** — `type: openai` / `type: anthropic`，自动匹配 endpoint、认证头、请求格式
- 🤖 **QQ 端切换模型** — 无需重启，命令即可切换模型（每 API 独立追踪）
- 📝 **自定义系统提示词** — 自由定义 AI 角色和行为
- 📌 **@触发回复** — 仅在 @机器人 时回复，单轮对话

## ⚙️ 配置

在 NoneBot 项目的 `.env` 文件中添加以下配置:

### API 配置 (CHAT_APIS)

```env
# JSON 列表，每项字段说明见下表
CHAT_APIS=[{"name":"OpenAI","type":"openai","base":"https://api.openai.com","key":"sk-xxx","model":"gpt-4o"},{"name":"Claude","type":"anthropic","base":"https://api.anthropic.com","key":"sk-ant-xxx","model":"claude-sonnet-4-6"}]

# 默认使用的 API (可选，留空=使用第一个)
CHAT_DEFAULT_API=OpenAI
```

每项字段:

| 字段 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | ✅ | - | API 显示名称，用于 `/api <名称>` 切换 |
| `type` | ✅ | - | 协议类型: `openai` 或 `anthropic` |
| `base` | ✅ | - | API 地址 (不含路径，如 `https://api.openai.com`) |
| `key` | ✅ | - | API 密钥 |
| `model` | ✅ | - | 该 API 的默认模型 |

### 协议自动适配

只需指定 `type`，代码自动处理所有差异:

| | `type: openai` | `type: anthropic` |
|------|------|------|
| Chat endpoint | `/v1/chat/completions` | `/v1/messages` |
| Models 端点 | `/v1/models` | 不支持 |
| 认证 | `Bearer` | `x-api-key` + `anthropic-version` |
| System prompt | messages 中 `role:system` | 顶层 `system` 字段 |
| 请求格式 | `{"model":..., "messages":...}` | + `"max_tokens": 4096` |
| 响应解析 | `choices[0].message.content` | `content[].text` (跳过 thinking 块) |
| 流式 SSE | `data: {"choices":[{"delta":...}]}` | `data: {"type":"content_block_delta","delta":{"text":"..."}}` |

> 💡 切换 API 时以上所有配置一起生效，无需手动设置 endpoint。

### 通用配置

```env
# 系统提示词 (可选)
CHAT_SYSTEM_PROMPT=你是一个友好、乐于助人的 AI 助手。请用简洁清晰的语言回答用户的问题。

# 允许响应的 QQ 群号，逗号分隔 (可选，留空=所有群)
CHAT_ALLOW_GROUPS=

# 允许响应的 QQ 号，逗号分隔 (可选，留空=所有人)
CHAT_ALLOW_USERS=
```

## 🚀 使用

### 启动 Bot

```bash
nb run
```

### 命令列表

| 用法 | 说明 |
|------|------|
| `@bot <任意消息>` | 直接对话，单轮无上下文 |
| `@bot /model` | 查看当前 API 可用模型列表 |
| `@bot /model <名称>` | 切换当前 API 的模型 |
| `@bot /api` | 查看可用 API 列表 |
| `@bot /api <名称>` | 切换到指定 API |
| `@bot /help` | 查看帮助 |

### 对话示例

```
User: @bot 你好
Bot:  你好！我是 AI 助手，有什么可以帮助你的吗？

User: @bot /api
Bot:  当前 API: OpenAI (openai)
      模型: gpt-4o

      可用 API (2):
        ● OpenAI (openai) — https://api.openai.com [gpt-4o]
        ○ Claude (anthropic) — https://api.anthropic.com [claude-sonnet-4-6]

      使用 @bot /api <名称> 切换

User: @bot /api Claude
Bot:  ✅ 已切换 API 为: Claude
         类型: anthropic
         模型: claude-sonnet-4-6
         地址: https://api.anthropic.com

User: @bot /model
Bot:  当前模型: Claude/claude-sonnet-4-6
      无法获取可用模型列表（当前 API 不支持或网络错误）

User: @bot /model claude-opus-4-8
Bot:  ✅ 已切换模型为: Claude/claude-opus-4-8

User: @bot /help
Bot:  🤖 Milky Chat 帮助:
      ━━━━━━━━━━━━━━
      @bot <消息>          直接对话 (单轮)
      @bot /model          查看可用模型
      @bot /model <名称>    切换模型
      @bot /api            查看可用 API
      @bot /api <名称>       切换 API
      @bot /help           查看此帮助
      ...
```

## 🏗️ 架构

```
nonebot_plugin_milky_chat/
├── __init__.py      # 插件入口，生命周期管理
├── adapter.py       # ChatClient — OpenAI + Anthropic 双协议通信层
├── config.py        # 配置模型 (Pydantic, ApiType enum + ApiProfile)
└── commands.py      # 命令处理器 (chat/model/api/help)
```
