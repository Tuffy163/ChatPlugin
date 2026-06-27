"""ChatClient — 封装 OpenAI / Anthropic API 的异步 HTTP 通信层，支持多 API 运行时切换"""

from typing import Optional
import httpx

from .config import ApiType, ApiProfile, ChatConfig

# ---- 协议常量 ----

ENDPOINT_MAP = {
    ApiType.openai: {
        "chat": "/v1/chat/completions",
        "models": "/v1/models",
    },
    ApiType.anthropic: {
        "chat": "/v1/messages",
        "models": None,  # Anthropic 不支持 /models 端点
    },
}

ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MAX_TOKENS = 4096


class ChatClient:
    """AI 对话客户端

    支持 OpenAI 和 Anthropic 两种协议，统一接口:
    - 多 API 配置与运行时切换
    - 每 API 独立追踪模型选择
    - 流式/非流式响应
    - 根据 type 自动匹配 endpoint、认证头、请求/响应格式
    """

    def __init__(self, config: ChatConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

        # 每 API 独立追踪的模型: {api_name: model_name}
        self._per_api_models: dict[str, str] = {}

        # 当前 API 设置
        self._current_api_name: str = ""
        self._current_type: ApiType = ApiType.openai
        self._current_base: str = ""
        self._current_key: str = ""
        self._current_chat_endpoint: str = ""
        self._current_models_endpoint: Optional[str] = None

        # 初始化
        profile = config.get_active_profile()
        if profile:
            self._apply_profile(profile)
        else:
            # 无 API 配置时给一个占位，实际调用会报友好错误
            self._current_api_name = "__unconfigured__"
            self._current_base = ""

    # ---- 模型管理 ----

    @property
    def current_model(self) -> str:
        """当前 API 正在使用的模型"""
        if self._current_api_name and self._current_api_name in self._per_api_models:
            return self._per_api_models[self._current_api_name]
        profile = self.config.get_profile(self._current_api_name)
        if profile:
            return profile.model
        return ""

    @current_model.setter
    def current_model(self, value: str):
        """设置当前 API 的模型"""
        if self._current_api_name:
            self._per_api_models[self._current_api_name] = value

    # ---- API 管理 ----

    @property
    def current_api_name(self) -> str:
        """当前 API 名称"""
        return self._current_api_name

    @property
    def current_api_base(self) -> str:
        """当前 API 地址"""
        return self._current_base

    @property
    def current_api_type(self) -> ApiType:
        """当前 API 协议类型"""
        return self._current_type

    @property
    def api_list(self) -> list[dict]:
        """可用 API 列表，含每 API 当前模型"""
        profiles = self.config.api_profiles
        return [
            {
                "name": p.name,
                "type": p.type.value,
                "base": p.base,
                "model": self._per_api_models.get(p.name, p.model),
            }
            for p in profiles
        ]

    @property
    def has_multi_api(self) -> bool:
        """是否配置了多 API"""
        return len(self.config.api_profiles) > 0

    @property
    def configured(self) -> bool:
        """是否已正确配置（至少有一个 API profile）"""
        return self.has_multi_api and self._current_base != ""

    def _apply_profile(self, profile: ApiProfile) -> None:
        """应用 API profile 到当前设置"""
        self._current_api_name = profile.name
        self._current_type = profile.type
        self._current_base = profile.base.rstrip("/")
        self._current_key = profile.key

        endpoints = ENDPOINT_MAP.get(profile.type, ENDPOINT_MAP[ApiType.openai])
        self._current_chat_endpoint = endpoints["chat"]
        self._current_models_endpoint = endpoints.get("models")

        # 首次加载时保留 profile 默认模型
        if profile.name not in self._per_api_models:
            self._per_api_models[profile.name] = profile.model

    async def switch_api(self, name: str) -> bool:
        """切换到指定 API。成功返回 True，找不到返回 False"""
        profile = self.config.get_profile(name)
        if not profile:
            return False

        # 关闭旧连接 (协议类型可能不同，需要重建)
        if self._client is not None:
            await self._client.aclose()
            self._client = None

        self._apply_profile(profile)
        return True

    # ---- HTTP 客户端 ----

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或重建 httpx 客户端 (根据 type 自动配置认证头)"""
        if self._client is None:
            headers = {"Content-Type": "application/json"}

            if self._current_type == ApiType.anthropic:
                headers["x-api-key"] = self._current_key
                headers["anthropic-version"] = ANTHROPIC_VERSION
            else:
                headers["Authorization"] = f"Bearer {self._current_key}"

            self._client = httpx.AsyncClient(
                base_url=self._current_base,
                headers=headers,
                timeout=httpx.Timeout(60.0),
            )
        return self._client

    # ---- API 调用 ----

    async def chat(self, messages: list[dict]) -> str:
        """发送消息并返回 AI 回复文本"""
        if not self.configured:
            return "⚠️ 插件未配置 API，请在 .env 中设置 CHAT_APIS"

        if self._current_type == ApiType.anthropic:
            return await self._chat_anthropic(messages)
        else:
            return await self._chat_openai(messages)

    async def _chat_openai(self, messages: list[dict]) -> str:
        """OpenAI 协议: POST /v1/chat/completions"""
        client = await self._get_client()
        body = {
            "model": self.current_model,
            "messages": messages,
        }
        response = await client.post(self._current_chat_endpoint, json=body)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def _chat_anthropic(self, messages: list[dict]) -> str:
        """Anthropic 协议: POST /v1/messages"""
        client = await self._get_client()

        # Anthropic: system 是顶层字段，messages 中不能有 role=system
        system_prompt: Optional[str] = None
        user_messages: list[dict] = []
        for m in messages:
            if m["role"] == "system":
                system_prompt = m["content"]
            else:
                user_messages.append(m)

        body: dict = {
            "model": self.current_model,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "messages": user_messages,
        }
        if system_prompt:
            body["system"] = system_prompt

        response = await client.post(self._current_chat_endpoint, json=body)
        response.raise_for_status()
        data = response.json()

        # 从 content 数组中找 type=text 的块 (兼容 thinking 块)
        for block in data.get("content", []):
            if block.get("type") == "text":
                return block["text"]

        raise RuntimeError("响应中没有 text 块")

    async def chat_stream(self, messages: list[dict]):
        """流式发送消息，逐块 yield 回复文本"""
        if not self.configured:
            yield "⚠️ 插件未配置 API，请在 .env 中设置 CHAT_APIS"
            return

        if self._current_type == ApiType.anthropic:
            async for chunk in self._chat_stream_anthropic(messages):
                yield chunk
        else:
            async for chunk in self._chat_stream_openai(messages):
                yield chunk

    async def _chat_stream_openai(self, messages: list[dict]):
        """OpenAI 协议: SSE 流式"""
        client = await self._get_client()
        body = {
            "model": self.current_model,
            "messages": messages,
            "stream": True,
        }
        async with client.stream("POST", self._current_chat_endpoint, json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[len("data: "):]
                    if data_str.strip() == "[DONE]":
                        break
                    import json
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    async def _chat_stream_anthropic(self, messages: list[dict]):
        """Anthropic 协议: SSE 流式"""
        client = await self._get_client()

        # 分离 system prompt
        system_prompt: Optional[str] = None
        user_messages: list[dict] = []
        for m in messages:
            if m["role"] == "system":
                system_prompt = m["content"]
            else:
                user_messages.append(m)

        body: dict = {
            "model": self.current_model,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "messages": user_messages,
            "stream": True,
        }
        if system_prompt:
            body["system"] = system_prompt

        import json

        async with client.stream("POST", self._current_chat_endpoint, json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[len("data: "):]
                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    if event.get("type") == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                yield text
                    elif event.get("type") == "message_stop":
                        break

    async def list_models(self) -> list[str]:
        """获取当前 API 的可用模型列表 (GET /v1/models)"""
        if not self.configured or self._current_models_endpoint is None:
            return []

        client = await self._get_client()
        try:
            response = await client.get(self._current_models_endpoint)
            response.raise_for_status()
            data = response.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
