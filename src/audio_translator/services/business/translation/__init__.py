"""
翻译服务模块

此模块包含所有与翻译相关的服务、策略和工具。
主要包括：
- 翻译管理器
- 翻译策略接口和实现
- 命名规则接口和实现
"""

from .translation_manager import TranslationManager

__all__ = ["TranslationManager"] 