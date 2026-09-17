"""工具包：Agent 可调用的所有工具"""

from elpis.tools.file_tools import read_file, write_file, list_directory
from elpis.tools.shell_tools import run_shell_command

# 所有可用工具的列表，直接传给 create_agent
ALL_TOOLS = [read_file, write_file, list_directory, run_shell_command]

__all__ = ["ALL_TOOLS", "read_file", "write_file", "list_directory", "run_shell_command"]
