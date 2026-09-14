"""文件操作工具：读文件、写文件、列目录"""

from pathlib import Path
from langchain_core.tools import tool
from mirage.config import settings


def _resolve_path(file_path: str) -> Path:
    """将相对路径解析为工作目录下的绝对路径，并做安全检查"""
    p = Path(file_path)
    if not p.is_absolute():
        p = settings.workspace_path / p
    resolved = p.resolve()

    # 安全：禁止跳出工作目录（防止 ../ 穿越）
    try:
        resolved.relative_to(settings.workspace_path.resolve())
    except ValueError:
        raise PermissionError(f"路径超出工作目录范围: {file_path}")

    return resolved


@tool
def read_file(file_path: str) -> str:
    """读取文本文件的内容。用于查看已有文件的代码或文本。

    Args:
        file_path: 要读取的文件路径（相对工作目录或绝对路径）

    Returns:
        文件的文本内容
    """
    p = _resolve_path(file_path)
    if not p.exists():
        return f"错误：文件不存在 - {file_path}"
    if not p.is_file():
        return f"错误：不是文件 - {file_path}"
    try:
        content = p.read_text(encoding="utf-8")
        # 大文件截断，防止上下文爆炸
        if len(content) > 10000:
            content = content[:10000] + "\n... (文件过长，已截断)"
        return content
    except UnicodeDecodeError:
        return f"错误：文件不是文本格式（可能是二进制文件）- {file_path}"
    except Exception as e:
        return f"读取文件失败: {e}"


@tool
def write_file(file_path: str, content: str) -> str:
    """写入内容到文件，会覆盖已有文件。用于创建新文件或修改文件内容。

    Args:
        file_path: 要写入的文件路径
        content: 要写入的完整文本内容

    Returns:
        操作结果描述
    """
    p = _resolve_path(file_path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"成功写入文件: {file_path} ({len(content)} 字符)"
    except Exception as e:
        return f"写入文件失败: {e}"


@tool
def list_directory(dir_path: str = ".") -> str:
    """列出指定目录中的文件和子目录。用于了解项目结构。

    Args:
        dir_path: 要列出的目录路径，默认为当前工作目录

    Returns:
        目录内容的格式化列表
    """
    p = _resolve_path(dir_path)
    if not p.exists():
        return f"错误：目录不存在 - {dir_path}"
    if not p.is_dir():
        return f"错误：不是目录 - {dir_path}"

    try:
        entries = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        lines = [f"目录: {dir_path}", "=" * 40]
        for entry in entries:
            if entry.name.startswith("."):
                continue  # 跳过隐藏文件
            if entry.is_dir():
                lines.append(f"  [DIR]  {entry.name}/")
            else:
                size = entry.stat().st_size
                lines.append(f"  [FILE] {entry.name}  ({size} bytes)")
        if len(lines) == 2:
            lines.append("  (空目录)")
        return "\n".join(lines)
    except Exception as e:
        return f"列出目录失败: {e}"
