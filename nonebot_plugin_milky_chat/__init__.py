"""nonebot-plugin-milky-chat — NoneBot AI 聊天插件

内置 ChatClient，支持:
- 多 API 配置与运行时切换
- OpenAI / Anthropic 双协议自动适配
- 模型选择 (每 API 独立追踪)
- 系统提示词

命令:
    @bot <任意消息>       — 直接对话 (单轮, 无上下文)
    @bot /model [名称]    — 查看可用模型 / 切换模型
    @bot /api [名称]      — 查看可用 API / 切换 API
    @bot /help           — 查看帮助

配置方式:
    .env 中设置 CHAT_APIS (JSON 列表)，每项含 name/type/base/key/model
    详见 .env.example
"""

from nonebot import get_driver, logger
from nonebot.plugin import PluginMetadata

from .config import ChatConfig
from .adapter import ChatClient

# ---- 插件元数据 ----
__plugin_meta__ = PluginMetadata(
    name="Milky Chat",
    description="AI 对话插件，支持 OpenAI/Anthropic 双协议，多 API 运行时切换",
    usage="@bot <消息> — 直接对话\n@bot /model — 查看/切换模型\n@bot /api — 查看/切换 API\n@bot /help — 帮助",
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
        chat_apis=getattr(nb_config, "chat_apis", ""),
        chat_default_api=getattr(nb_config, "chat_default_api", ""),
        chat_system_prompt_file=getattr(nb_config, "chat_system_prompt_file", ""),
        chat_vision_enabled=getattr(nb_config, "chat_vision_enabled", True),
        chat_allow_groups=getattr(nb_config, "chat_allow_groups", ""),
        chat_allow_users=getattr(nb_config, "chat_allow_users", ""),
    )

    client = ChatClient(config)

    from . import commands as cmds
    cmds.client = client

    if client.configured:
        apis = client.api_list
        logger.info(
            f"Milky Chat 插件已启动 | {len(apis)} 个 API: "
            + ", ".join(f"{a['name']}({a['type']})" for a in apis)
            + f" | 当前: {client.current_api_name}/{client.current_model}"
        )
    else:
        logger.warning("Milky Chat 插件已启动 | ⚠️ 未配置 CHAT_APIS，请检查 .env")


@driver.on_shutdown
async def on_shutdown():
    """插件关闭时清理资源"""
    global client
    if client:
        await client.close()
        logger.info("Milky Chat 插件已关闭")
