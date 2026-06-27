#!/usr/bin/env python3
"""NoneBot 启动入口 — Milky Chat Plugin 示例

依赖:
    pip install nonebot-adapter-milky

协议端 (选其一):
    - Lagrange.Milky
    - LLOneBot
"""

import nonebot
from nonebot.adapters.milky import Adapter as MilkyAdapter

nonebot.init()

# 注册 Milky 协议适配器
nonebot.get_driver().register_adapter(MilkyAdapter)

# 加载插件 (自动发现 nonebot_plugin_milky_chat)
nonebot.load_builtin_plugins()

if __name__ == "__main__":
    nonebot.run()
