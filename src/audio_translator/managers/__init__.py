"""
音频翻译器管理器包

此包包含应用程序的各种管理器类，用于处理文件、类别和其他资源。
"""

from .file_manager import FileManager
from .category_manager import CategoryManager

__all__ = ['FileManager', 'CategoryManager']
