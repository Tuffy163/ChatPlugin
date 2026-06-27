"""nonebot-plugin-milky-chat — NoneBot AI 聊天插件

内置 ChatClient，支持自定义:
- 对话 API 地址 (OpenAI 兼容格式)
- 模型选择
- 系统提示词

命令:
    @bot <任意消息>       — 直接对话 (单轮, 无上下文)
    @bot /model [名称]    — 查看可用模型 / 切换模型
    @bot /help           — 查看帮助

配置方式:
    环境变量 / .env 文件，前缀 CHAT_
    详见 .env.example
"""

from nonebot import get_driver, logger
from nonebot.plugin import PluginMetadata

from .config import ChatConfig
from .adapter import ChatClient

# ---- 插件元数据 ----
__plugin_meta__ = PluginMetadata(
    name="Milky Chat",
    description="AI 对话插件，支持自定义 API、模型和提示词",
    usage="@bot <消息> — 直接对话\n@bot /model — 查看/切换模型\n@bot /help — 帮助",
    type="application",
    homepage="https://github.com/example/nonebot-plugin-milky-chat",
    config=ChatConfig,
    supported_adapters=None,
)

# ---- 全局实例 ----
config: ChatConfig = ChatConfig()  # type: ignore
client: ChatClient = None  # type: ignore

# ---- 生命周期 ----

driver = get_driver()


@driver.on_startup
async def on_startup():
    """插件启动时初始化 client"""
    global client, config

    nb_config = driver.config

    config = ChatConfig(
        chat_api_base=getattr(nb_config, "chat_api_base", "https://api.openai.com/v1"),
        chat_api_key=getattr(nb_config, "chat_api_key", "sk-xxx"),
        chat_model=getattr(nb_config, "chat_model", "gpt-3.5-turbo"),
        chat_system_prompt=getattr(
            nb_config,
            "chat_system_prompt",
            "你是一个友好、乐于助人的 AI 助手。请用简洁清晰的语言回答用户的问题。",
        ),
        chat_allow_groups=getattr(nb_config, "chat_allow_groups", ""),
        chat_allow_users=getattr(nb_config, "chat_allow_users", ""),
        chat_endpoint=getattr(nb_config, "chat_endpoint", "/chat/completions"),
        chat_models_endpoint=getattr(nb_config, "chat_models_endpoint", "/models"),
    )

    client = ChatClient(config)

    import nonebot_plugin_milky_chat.commands as cmds
    cmds.client = client

    logger.info(f"Milky Chat 插件已启动 | API: {config.chat_api_base} | 模型: {config.chat_model}")


@driver.on_shutdown
async def on_shutdown():
    """插件关闭时清理资源"""
    global client
    if client:
        await client.close()
        logger.info("Milky Chat 插件已关闭")
