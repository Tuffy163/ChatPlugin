"""插件配置 — 所有配置项支持通过环境变量或 .env 文件设置"""

from typing import Optional
from pydantic import BaseModel, Field


class ChatConfig(BaseModel):
    """Milky Chat 插件配置"""

    # API 配置
    milky_api_base: str = Field(
        default="https://api.openai.com/v1",
        description="API 地址 (OpenAI 兼容格式)",
    )
    milky_api_key: str = Field(
        default="sk-xxx",
        description="API 密钥",
    )
    milky_model: str = Field(
        default="gpt-3.5-turbo",
        description="使用的模型名称",
    )

    # 对话配置
    milky_system_prompt: str = Field(
        default="你是一个友好、乐于助人的 AI 助手。请用简洁清晰的语言回答用户的问题。",
        description="系统提示词，定义 AI 的角色和行为",
    )

    # 白名单 (逗号分隔的 QQ群号/QQ号, 留空=不限制)
    milky_allow_groups: str = Field(
        default="",
        description="允许响应的 QQ 群号，逗号分隔。留空则不限制",
    )
    milky_allow_users: str = Field(
        default="",
        description="允许响应的 QQ 号，逗号分隔。留空则不限制",
    )

    @property
    def allow_group_set(self) -> set[str]:
        return {x.strip() for x in self.milky_allow_groups.split(",") if x.strip()}

    @property
    def allow_user_set(self) -> set[str]:
        return {x.strip() for x in self.milky_allow_users.split(",") if x.strip()}

    # 额外配置
    milky_extra_body: Optional[dict] = Field(
        default=None,
        description="额外的请求体参数，用于传递给 API 的自定义参数",
    )

    class Config:
        # 允许从环境变量读取，自动转换 MILKY_API_BASE -> milky_api_base
        # NoneBot 的 Config 或 python-dotenv 负责加载 .env
        extra = "ignore"
