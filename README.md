# nonebot-plugin-milky-chat

> NoneBot AI 聊天插件，基于 **nonebot-adapter-milky** 协议，@机器人即可对话，支持自定义 API、模型和提示词。

## ✨ 特性

- 🔌 **ChatClient** — 封装 OpenAI 兼容 API 的异步通信层
- 🎛️ **自定义 API 地址** — 支持任何 OpenAI 兼容接口（OpenAI、DeepSeek、通义千问、Ollama 等）
- 🤖 **QQ 端切换模型** — 无需重启，命令即可切换模型
- 📝 **自定义系统提示词** — 自由定义 AI 角色和行为
- 📌 **@触发回复** — 仅在 @机器人 时回复，单轮对话

## ⚙️ 配置

在 NoneBot 项目的 `.env` 文件中添加以下配置:

```env
# API 地址 (必填，支持任何 OpenAI 兼容接口)
CHAT_API_BASE=https://api.openai.com/v1

# API 密钥 (必填)
CHAT_API_KEY=sk-your-api-key-here

# 模型名称 (可选，默认 gpt-3.5-turbo)
CHAT_MODEL=gpt-3.5-turbo

# 对话 endpoint (可选，默认 /chat/completions)
CHAT_ENDPOINT=/chat/completions

# 模型列表 endpoint (可选，默认 /models)
CHAT_MODELS_ENDPOINT=/models

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
| `@bot /model` | 查看可用模型列表 |
| `@bot /model <名称>` | 切换模型 |
| `@bot /help` | 查看帮助 |

### 对话示例

```
User: @bot 你好
Bot:  你好！我是 AI 助手，有什么可以帮助你的吗？

User: @bot 帮我写一个 Python 快速排序
Bot:  [返回快速排序代码...]

User: @bot /model
Bot:  当前模型: gpt-3.5-turbo
      可用模型 (API 查询) (3):
        • gpt-3.5-turbo
        • gpt-4
        • gpt-4o

User: @bot /model gpt-4o
Bot:  ✅ 已切换模型为: gpt-4o

User: @bot /help
Bot:  🤖 Milky Chat 帮助:
      ━━━━━━━━━━━━━━
      @bot <消息>          直接对话 (单轮)
      @bot /model          查看可用模型
      @bot /model <名称>    切换模型
      @bot /help           查看此帮助
      ...
```

## 🏗️ 架构

```
nonebot_plugin_milky_chat/
├── __init__.py      # 插件入口，生命周期管理
├── adapter.py       # ChatClient — OpenAI 兼容 API 通信层
├── config.py        # 配置模型 (Pydantic)
└── commands.py      # 命令处理器
```

