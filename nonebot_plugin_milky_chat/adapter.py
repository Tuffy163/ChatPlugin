"""ChatClient — 封装 OpenAI 兼容 API 的异步 HTTP 通信层"""

from typing import Optional
import httpx

from .config import ChatConfig


class ChatClient:
    """AI 对话客户端

    封装与 OpenAI 兼容 API 的通信，支持:
    - 自定义 base_url 和 api_key
    - 自定义模型和参数
    - 流式/非流式响应
    """

    def __init__(self, config: ChatConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建持久化的 httpx 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.chat_api_base.rstrip("/"),
                headers={
                    "Authorization": f"Bearer {self.config.chat_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(60.0),
            )
        return self._client

    async def chat(self, messages: list[dict]) -> str:
        """发送消息并返回 AI 回复文本"""
        client = await self._get_client()

        body = {
            "model": self.config.chat_model,
            "messages": messages,
        }

        response = await client.post(self.config.chat_endpoint, json=body)
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def chat_stream(self, messages: list[dict]):
        """流式发送消息，逐块 yield 回复文本"""
        client = await self._get_client()

        body = {
            "model": self.config.chat_model,
            "messages": messages,
            "stream": True,
        }

        async with client.stream("POST", self.config.chat_endpoint, json=body) as response:
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

    async def list_models(self) -> list[str]:
        """获取 API 可用模型列表"""
        client = await self._get_client()
        try:
            response = await client.get(self.config.chat_models_endpoint)
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
