"""
翻译策略基础接口模块

该模块导入并重新导出ITranslationStrategy接口，用于向后兼容。
策略实现应该直接继承此接口。
"""

from ....core.interfaces import ITranslationStrategy

# 重新导出接口，以便插件可以导入
__all__ = ['ITranslationStrategy'] 