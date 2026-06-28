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
api_cmd = on_command("api", rule=CHAT_RULE, priority=1, block=True)
help_cmd = on_command("help", rule=CHAT_RULE, priority=1, block=True)
chat_handler = on_message(rule=CHAT_RULE, priority=10, block=True)


# ---- 处理器 ----


async def _get_models() -> list[str]:
    """从当前 API 获取可用模型列表"""
    return await client.list_models()


def _model_label() -> str:
    """生成当前模型显示文本，多 API 时显示 API名/模型"""
    if len(client.api_list) > 1:
        return f"{client.current_api_name}/{client.current_model}"
    return client.current_model


def _build_reply(event: Event, text: str):
    """构建引用回复消息。Milky 适配器用 MessageSegment.reply() 构造"""
    from nonebot.adapters.milky.message import MessageSegment as MilkySeg

    msg_id = getattr(event, "message_id", None)
    if msg_id is not None:
        return MilkySeg.reply(msg_id) + MilkySeg.text(text)
    return text


@chat_handler.handle()
async def handle_chat(event: Event):
    """@bot 任意消息直接对话，单轮无上下文；支持图文混排"""
    # 按消息段原始顺序遍历，保持图文交错顺序
    content: list[dict] = []
    for seg in event.message:
        if seg.type == "text":
            text = seg.data.get("text", "").strip()
            if text:
                content.append({"type": "text", "text": text})
        elif seg.type == "image" and client.config.chat_vision_enabled:
            if seg.data.get("sub_type") != "sticker":
                url = seg.data.get("temp_url", "")
                if url:
                    content.append({"type": "image_url", "image_url": {"url": url}})

    if not content:
        await chat_handler.finish(_build_reply(event, "@我有什么事吗？直接说就行~"))
        return

    # 有图片时确保至少有一个 text 块（API 要求）
    has_image = any(b.get("type") == "image_url" for b in content)
    if has_image:
        has_text = any(b.get("type") == "text" for b in content)
        if not has_text:
            content.insert(0, {"type": "text", "text": "请描述这张图片的内容"})

    # 纯文本一条: 用字符串保持兼容；多模态: 用数组
    if len(content) == 1 and content[0]["type"] == "text":
        user_content: str | list[dict] = content[0]["text"]
    else:
        user_content = content

    system_prompt = client.config.resolved_system_prompt
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_content})

    try:
        reply = await client.chat(messages)
        await chat_handler.finish(_build_reply(event, reply))
    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"API 调用失败: {e}")
        await chat_handler.finish(_build_reply(event, "抱歉，AI 服务暂时不可用，请稍后再试。"))


@model_cmd.handle()
async def handle_model(event: Event, arg: Message = CommandArg()):
    """@bot /model [名称] — 无参数查看模型列表，有参数切换"""
    model_name = arg.extract_plain_text().strip()

    if not model_name:
        current = _model_label()
        models = await _get_models()

        if models:
            lines = "\n".join(f"  • {m}" for m in models)
            await model_cmd.finish(
                _build_reply(event, f"当前模型: {current}\n\n可用模型 (API 查询) ({len(models)}):\n{lines}")
            )
        else:
            await model_cmd.finish(
                _build_reply(event, f"当前模型: {current}\n\n无法获取可用模型列表（当前 API 不支持或网络错误）")
            )
        return

    client.current_model = model_name
    current = _model_label()
    await model_cmd.finish(_build_reply(event, f"✅ 已切换模型为: {current}"))


@api_cmd.handle()
async def handle_api(event: Event, arg: Message = CommandArg()):
    """@bot /api [名称] — 无参数查看 API 列表，有参数切换 API"""
    api_name = arg.extract_plain_text().strip()

    if not client.configured:
        await api_cmd.finish(
            _build_reply(
                event,
                "⚠️ 插件未配置 API。\n"
                "请在 .env 中设置 CHAT_APIS，例如:\n"
                '[{"name":"OpenAI","type":"openai","base":"https://api.openai.com","key":"sk-xxx","model":"gpt-4o"}]',
            )
        )
        return

    if not api_name:
        # 查看 API 列表
        current = client.current_api_name
        apis = client.api_list
        lines = "\n".join(
            f"  {'●' if a['name'] == current else '○'} {a['name']} ({a['type']}) [{a['model']}]"
            for a in apis
        )
        await api_cmd.finish(
            _build_reply(
                event,
                f"当前 API: {current} ({client.current_api_type.value})\n"
                f"模型: {client.current_model}\n\n"
                f"可用 API ({len(apis)}):\n{lines}\n\n"
                f"使用 @bot /api <名称> 切换",
            )
        )
        return

    # 切换 API
    success = await client.switch_api(api_name)
    if success:
        await api_cmd.finish(
            _build_reply(
                event,
                f"✅ 已切换 API 为: {client.current_api_name}\n"
                f"   类型: {client.current_api_type.value}\n"
                f"   模型: {client.current_model}",
            )
        )
    else:
        names = ", ".join(a["name"] for a in client.api_list)
        await api_cmd.finish(_build_reply(event, f"❌ 未找到 API「{api_name}」。可用: {names}"))


@help_cmd.handle()
async def handle_help(event: Event):
    """@bot /help — 查看帮助"""

    await help_cmd.finish(
        _build_reply(
            event,
            "🤖 Milky Chat 帮助:\n"
            "━━━━━━━━━━━━━━\n"
            "@bot <消息>          直接对话 (单轮)\n"
            "@bot <图片>          识图分析\n"
            "@bot <文字+图片>      图文对话\n"
            "@bot /model          查看可用模型\n"
            "@bot /model <名称>    切换模型\n"
            "@bot /api            查看可用 API\n"
            "@bot /api <名称>       切换 API\n"
            "@bot /help           查看此帮助\n"
            "━━━━━━━━━━━━━━",
        )
    )
