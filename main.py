"""
My Agent 启动入口
在 VSCode 中直接运行此文件即可启动 Agent：
    右键 -> Run Python File in Terminal
    或点击右上角的运行按钮
"""

import sys
from pathlib import Path

# 项目根目录加入 Python 路径，确保 elpis 包可被导入
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 切换工作目录到项目根目录，确保 Agent 的工作目录正确
import os
os.chdir(project_root)

if __name__ == "__main__":
    from elpis.cli import main
    main()
