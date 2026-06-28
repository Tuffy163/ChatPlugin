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
    chat_system_prompt_file: str = Field(
        default="",
        description="系统提示词文件路径 (完整路径)。从此文件读取系统提示词，留空则不使用提示词",
    )
    chat_temperature: Optional[float] = Field(
        default=None,
        description="Temperature 参数，控制回复的随机性 (0.0~2.0)。留空则不设置，使用 API 默认值",
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

    # === 提示词解析 ===

    @property
    def resolved_system_prompt(self) -> str:
        """获取系统提示词。从 CHAT_SYSTEM_PROMPT_FILE 读取，留空则不使用提示词"""
        file_path = self.chat_system_prompt_file.strip()
        if not file_path:
            return ""
        try:
            from pathlib import Path
            path = Path(file_path)
            if path.is_file():
                try:
                    return path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    return path.read_text()  # 回退系统默认编码 (如 GBK)
            logger.warning(f"CHAT_SYSTEM_PROMPT_FILE 指定的文件不存在: {file_path}")
        except Exception as e:
            logger.warning(f"读取 CHAT_SYSTEM_PROMPT_FILE 失败 ({file_path}): {e}")
        return ""

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
