"""命令处理器 — @bot 触发，单轮对话，支持群/用户白名单。
适配器无关: 不 import 任何特定协议，通过 getattr 检测 event 属性。"""

from nonebot import on_command, on_message
from nonebot.rule import Rule
from nonebot.adapters import Event, Message
from nonebot.exception import FinishedException
from nonebot.params import CommandArg
from nonebot.log import logger

from .adapter import ChatClient

# ---- 全局实例 (由 __init__.py 初始化) ----
client: ChatClient = None  # type: ignore


# ---- 自定义规则: to_me + 白名单 ----

def _extract_ids(event: Event) -> tuple[str, str]:
    """适配器无关地提取 (用户ID, 群号)。群号取不到时为 ""。

    - 用户ID: 优先 NoneBot 标准的 event.get_user_id()（所有适配器都实现）
    - 群号: 优先 OneBot 风格的 event.group_id；
            否则取 Milky 的 event.data.peer_id（仅当 message_scene == "group"）
    """
    try:
        uid = event.get_user_id()
    except Exception:
        uid = str(getattr(event, "user_id", "") or "")

    gid = str(getattr(event, "group_id", "") or "")
    if not gid:
        data = getattr(event, "data", None)
        if data is not None and getattr(data, "message_scene", None) == "group":
            gid = str(getattr(data, "peer_id", "") or "")

    return uid, gid


async def _chat_rule(event: Event) -> bool:
    """只有 @bot 且 在白名单内（若设置了白名单）才响应"""
    if not event.is_tome():
        return False

    group_set = client.config.allow_group_set
    user_set = client.config.allow_user_set
    if not group_set and not user_set:
        return True

    uid, gid = _extract_ids(event)

    if gid:
        return gid in group_set or uid in user_set
    else:
        return uid in user_set


CHAT_RULE = Rule(_chat_rule)


# ---- 注册 ----

model_cmd = on_command("model", rule=CHAT_RULE, priority=1, block=True)
help_cmd = on_command("help", rule=CHAT_RULE, priority=1, block=True)
chat_handler = on_message(rule=CHAT_RULE, priority=10, block=True)


# ---- 处理器 ----

async def _get_models() -> list[str]:
    """从 API 获取可用模型列表"""
    return await client.list_models()


@chat_handler.handle()
async def handle_chat(event: Event):
    """@bot 任意消息直接对话，单轮无上下文"""
    user_msg = event.get_plaintext().strip()

    if not user_msg:
        await chat_handler.finish("@我有什么事吗？直接说就行~")
        return

    messages = [
        {"role": "system", "content": client.config.chat_system_prompt},
        {"role": "user", "content": user_msg},
    ]

    try:
        reply = await client.chat(messages)
        await chat_handler.finish(reply)
    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"Milky API 调用失败: {e}")
        await chat_handler.finish(f"抱歉，AI 服务暂时不可用: {type(e).__name__}")


@model_cmd.handle()
async def handle_model(arg: Message = CommandArg()):
    """@bot /model [名称] — 无参数查看模型列表，有参数切换"""
    model_name = arg.extract_plain_text().strip()

    if not model_name:
        current = client.config.chat_model
        models = await _get_models()

        if models:
            lines = "\n".join(f"  • {m}" for m in models[:20])
            extra = "" if len(models) <= 20 else f"\n  ... 还有 {len(models) - 20} 个"
            source = "(API 查询)"
            await model_cmd.finish(
                f"当前模型: {current}\n\n可用模型 {source} ({len(models)}):\n{lines}{extra}"
            )
        else:
            await model_cmd.finish(
                f"当前模型: {current}\n\n无法获取可用模型列表（API 不支持或网络错误）"
            )
        return

    client.config.chat_model = model_name
    await model_cmd.finish(f"✅ 已切换模型为: {model_name}")


@help_cmd.handle()
async def handle_help():
    """@bot /help — 查看帮助"""
    models = await _get_models()
    model_list_str = ", ".join(models[:6]) if models else "取决于 API"

    await help_cmd.finish(
        f"🤖 Milky Chat 帮助:\n"
        f"━━━━━━━━━━━━━━\n"
        f"@bot <消息>          直接对话 (单轮)\n"
        f"@bot /model          查看可用模型\n"
        f"@bot /model <名称>    切换模型\n"
        f"@bot /help           查看此帮助\n"
        f"━━━━━━━━━━━━━━\n"
        f"当前模型: {client.config.chat_model}\n"
        f"可选模型: {model_list_str}"
    )
