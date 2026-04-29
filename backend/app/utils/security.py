import struct
from typing import Optional, Tuple

MAGIC_NUMBERS = {
    "image/jpeg": [
        (b"\xFF\xD8\xFF\xDB", 0),
        (b"\xFF\xD8\xFF\xE0", 0),
        (b"\xFF\xD8\xFF\xE1", 0),
        (b"\xFF\xD8\xFF\xE2", 0),
        (b"\xFF\xD8\xFF\xE3", 0),
        (b"\xFF\xD8\xFF\xE8", 0),
    ],
    "image/png": [
        (b"\x89PNG\r\n\x1a\n", 0),
    ],
    "image/webp": [
        (b"RIFF", 0),
        (b"WEBP", 8),
    ],
    "video/mp4": [
        (b"\x00\x00\x00\x18ftypmp4", 0),
        (b"\x00\x00\x00\x20ftypmp4", 0),
        (b"\x00\x00\x00\x18ftypisom", 0),
        (b"\x00\x00\x00\x20ftypisom", 0),
        (b"\x00\x00\x00\x18ftypavc1", 0),
    ],
    "video/avi": [
        (b"RIFF", 0),
        (b"AVI ", 8),
    ],
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}

ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


def validate_magic_number(file_content: bytes, expected_type: str) -> bool:
    """
    通过魔数验证文件类型

    Args:
        file_content: 文件字节内容
        expected_type: 期望的 MIME 类型

    Returns:
        True 如果魔数匹配，False 否则
    """
    if expected_type not in MAGIC_NUMBERS:
        return True

    for magic_bytes, offset in MAGIC_NUMBERS[expected_type]:
        if len(file_content) >= offset + len(magic_bytes):
            if file_content[offset:offset + len(magic_bytes)] == magic_bytes:
                return True

    return False


def get_file_type_by_magic(file_content: bytes) -> Optional[str]:
    """
    通过魔数检测文件实际类型

    Args:
        file_content: 文件字节内容

    Returns:
        检测到的 MIME 类型，未知返回 None
    """
    for mime_type, magic_pairs in MAGIC_NUMBERS.items():
        for magic_bytes, offset in magic_pairs:
            if len(file_content) >= offset + len(magic_bytes):
                if file_content[offset:offset + len(magic_bytes)] == magic_bytes:
                    return mime_type
    return None


def validate_file_security(
    file_content: bytes,
    filename: str,
    expected_type: str
) -> Tuple[bool, str]:
    """
    综合文件安全验证

    Args:
        file_content: 文件字节内容
        filename: 文件名
        expected_type: 期望的 MIME 类型

    Returns:
        (是否安全, 错误信息)
    """
    import os

    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        return False, f"不支持的文件扩展名: {ext}"

    if expected_type.startswith("image/") and ext not in IMAGE_EXTENSIONS:
        return False, f"文件扩展名与图片类型不匹配"

    if expected_type.startswith("video/") and ext not in VIDEO_EXTENSIONS:
        return False, f"文件扩展名与视频类型不匹配"

    if not validate_magic_number(file_content, expected_type):
        detected_type = get_file_type_by_magic(file_content)
        if detected_type:
            return False, f"文件内容与声明类型不符，实际为 {detected_type}"
        return False, "无法识别的文件格式"

    return True, ""
