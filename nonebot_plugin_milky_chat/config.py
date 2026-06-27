"""插件配置 — 所有配置项支持通过环境变量或 .env 文件设置"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator
from nonebot.log import logger


class ApiType(str, Enum):
    """API 协议类型，自动匹配 endpoint 和认证方式"""
    openai = "openai"
    anthropic = "anthropic"


class ApiProfile(BaseModel):
    """单个 API 端点配置"""

    name: str = Field(description="API 显示名称，用于 /api <名称> 切换")
    type: ApiType = Field(default=ApiType.openai, description="API 协议类型: openai / anthropic")
    base: str = Field(description="API 地址 (不含路径，如 https://api.openai.com)")
    key: str = Field(description="API 密钥")
    model: str = Field(description="默认模型")

class ChatConfig(BaseModel):
    """Chat Plugin 插件配置"""

    # === 多 API 配置 ===
    chat_apis: str = Field(
        default="",
        description=(
            'API 配置列表 (JSON), 每项: name, type (openai/anthropic), base, key, model.\n'
            '例如: [{"name":"OpenAI","type":"openai","base":"https://api.openai.com","key":"sk-xxx","model":"gpt-4o"}]'
        ),
    )
    chat_default_api: str = Field(
        default="",
        description="默认使用的 API 名称 (需在 chat_apis 中定义), 留空=使用第一个",
    )

    # === 对话配置 ===
    chat_system_prompt: str = Field(
        default="你是一个友好、乐于助人的 AI 助手。请用简洁清晰的语言回答用户的问题。",
        description="系统提示词，定义 AI 的角色和行为",
    )

    # === 功能开关 ===
    chat_vision_enabled: bool = Field(
        default=True,
        description="是否启用识图功能 (将图片发送给 AI 分析)",
    )

    # === 白名单 ===
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

    @field_validator("chat_apis", mode="before")
    @classmethod
    def _coerce_chat_apis(cls, v: Any) -> str:
        """兼容 NoneBot 自动解析 JSON 为 list 的情况"""
        if v is None or v == "":
            return ""
        if isinstance(v, str):
            return v
        if isinstance(v, (list, tuple)):
            import json
            return json.dumps(v, ensure_ascii=False)
        return str(v)

    # === 白名单辅助 ===

    @property
    def allow_group_set(self) -> set[str]:
        return {x.strip() for x in self.chat_allow_groups.split(",") if x.strip()}

    @property
    def allow_user_set(self) -> set[str]:
        return {x.strip() for x in self.chat_allow_users.split(",") if x.strip()}

    # === 多 API 辅助 ===

    @property
    def api_profiles(self) -> list[ApiProfile]:
        """解析 chat_apis JSON，返回 API 配置列表。解析失败或为空时返回 []"""
        if not self.chat_apis or not self.chat_apis.strip():
            return []
        try:
            import json

            data = json.loads(self.chat_apis)
            if not isinstance(data, list):
                logger.warning(f"CHAT_APIS 应为 JSON 列表格式，当前类型: {type(data).__name__}")
                return []
            return [ApiProfile(**item) for item in data]
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"CHAT_APIS 配置解析失败: {e}\n原始值: {self.chat_apis}")
            return []

    def get_active_profile(self) -> Optional[ApiProfile]:
        """获取当前应激活的 API profile。无配置时返回 None"""
        profiles = self.api_profiles
        if not profiles:
            return None
        if self.chat_default_api:
            for p in profiles:
                if p.name == self.chat_default_api:
                    return p
        return profiles[0]

    def get_profile(self, name: str) -> Optional[ApiProfile]:
        """按名称查找 API profile"""
        for p in self.api_profiles:
            if p.name == name:
                return p
        return None

    class Config:
        extra = "ignore"
