"""通用工具函数"""

import hashlib
import re
from datetime import UTC, datetime
from typing import Any


def calculate_md5(content: bytes) -> str:
    """计算内容的 MD5 值"""
    return hashlib.md5(content).hexdigest()


def calculate_md5_from_file(file_path: str) -> str:
    """计算文件的 MD5 值"""
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()


def calculate_sha256(content: bytes) -> str:
    """计算内容的 SHA256 值"""
    return hashlib.sha256(content).hexdigest()


def format_amount(amount: float) -> str:
    """格式化金额显示"""
    if amount >= 10000:
        wan = amount / 10000
        return f"{wan:.2f}万元"
    return f"{amount:.2f}元"


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def now_utc() -> datetime:
    """获取当前 UTC 时间"""
    return datetime.now(UTC)


def now_local() -> datetime:
    """获取当前本地时间"""
    return datetime.now()


def sanitize_filename(filename: str) -> str:
    """清理文件名中的非法字符"""
    return re.sub(r'[<>:"/\\|?*]', "_", filename)


def extract_chinese_name(text: str) -> str | None:
    """从文本中提取中文姓名（简单实现）"""
    patterns = [
        r"甲方[：:]\s*([\u4e00-\u9fa5]{2,4})",
        r"乙方[：:]\s*([\u4e00-\u9fa5]{2,4})",
        r"供方[：:]\s*([\u4e00-\u9fa5]{2,4})",
        r"需方[：:]\s*([\u4e00-\u9fa5]{2,4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def extract_amount(text: str) -> float | None:
    """从文本中提取金额"""
    patterns = [
        r"合同(?:总)?金额[：:]\s*([\d,]+\.?\d*)\s*元",
        r"(?:人民币|CNY|￥)\s*([\d,]+\.?\d*)\s*元",
        r"([\d,]+\.?\d*)\s*万元",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            amount_str = match.group(1).replace(",", "")
            amount = float(amount_str)
            if "万" in match.group(0):
                amount *= 10000
            return amount
    return None


def snake_to_camel(snake_str: str) -> str:
    """蛇形命名转驼峰命名"""
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def camel_to_snake(camel_str: str) -> str:
    """驼峰命名转蛇形命名"""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", camel_str).lower()


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + suffix


def mask_sensitive(text: str, visible_start: int = 3, visible_end: int = 4, mask_char: str = "*") -> str:
    """脱敏处理"""
    if len(text) <= visible_start + visible_end:
        return mask_char * len(text)
    return text[:visible_start] + mask_char * (len(text) - visible_start - visible_end) + text[-visible_end:]


def safe_json_loads(text: str, default: Any = None) -> Any:
    """安全 JSON 解析"""
    import json

    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: Any = None) -> str:
    """安全 JSON 序列化"""
    import json

    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return default if default is not None else "{}"


def batch_list(items: list, batch_size: int = 100):
    """将列表分批"""
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def retry_with_backoff(max_retries: int = 5, base_delay: float = 1.0, max_delay: float = 30.0):
    import asyncio
    import random
    from functools import wraps

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2**attempt) + random.uniform(0, 1), max_delay)
                        await asyncio.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


def is_valid_date(date_str: str) -> bool:
    """验证日期字符串是否有效"""
    try:
        from datetime import datetime
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def parse_date(date_str: str) -> datetime:
    """解析日期字符串"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as err:
        raise ValueError(f"无效的日期格式: {date_str}") from err
