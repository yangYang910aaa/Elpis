"""记忆模块

管理 Agent 的短期记忆和长期记忆。

短期记忆（Short-term Memory）：
- 当前对话的历史消息
- 自动截断/摘要超长对话，防止上下文爆炸
- 对应文件：short_term.py

长期记忆（Long-term Memory）：
- 跨会话记住用户偏好、历史事实
- 存储在文件或数据库中
- 对应文件：long_term.py（未来添加）

未来可以加：
- short_term.py：对话历史管理，自动摘要
- long_term.py：用户画像、偏好记忆
- memory_store.py：记忆存储后端（JSON/SQLite/向量数据库）
"""
