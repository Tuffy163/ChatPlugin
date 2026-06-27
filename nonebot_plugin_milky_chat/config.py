"""插件配置 — 所有配置项支持通过环境变量或 .env 文件设置"""

from typing import Any, Union
from pydantic import BaseModel, Field, field_validator


class ChatConfig(BaseModel):
    """Chat Plugin 插件配置"""

    # API 配置
    chat_api_base: str = Field(
        default="https://api.openai.com/v1",
        description="API 地址 (OpenAI 兼容格式)",
    )
    chat_api_key: str = Field(
        default="sk-xxx",
        description="API 密钥",
    )
    chat_model: str = Field(
        default="gpt-3.5-turbo",
        description="使用的模型名称",
    )
    chat_endpoint: str = Field(
        default="/chat/completions",
        description="对话 API 路径",
    )
    chat_models_endpoint: str = Field(
        default="/models",
        description="模型列表 API 路径",
    )

    # 对话配置
    chat_system_prompt: str = Field(
        default="你是一个友好、乐于助人的 AI 助手。请用简洁清晰的语言回答用户的问题。",
        description="系统提示词，定义 AI 的角色和行为",
    )

    # 白名单 (逗号分隔的 QQ群号/QQ号, 留空=不限制)
    chat_allow_groups: str = Field(
        default="",
        description="允许响应的 QQ 群号，逗号分隔。留空则不限制",
    )
    chat_allow_users: str = Field(
        default="",
        description="允许响应的 QQ 号，逗号分隔。留空则不限制",
    )

    @field_validator("chat_allow_groups", "chat_allow_users", mode="before")
    @classmethod
    def _coerce_to_str(cls, v: Any) -> str:
        return str(v) if v is not None else ""

    @property
    def allow_group_set(self) -> set[str]:
        return {x.strip() for x in self.chat_allow_groups.split(",") if x.strip()}

    @property
    def allow_user_set(self) -> set[str]:
        return {x.strip() for x in self.chat_allow_users.split(",") if x.strip()}

    class Config:
        extra = "ignore"
