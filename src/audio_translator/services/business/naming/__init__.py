"""
命名服务模块，提供文件命名规则管理和应用功能
"""
from .naming_service import NamingService
from .naming_rule import INamingRule
from .rule_registry import RuleRegistry
from .rule_validator import RuleValidator
from .template_processor import TemplateProcessor
from .rules import (
    DirectNamingRule,
    BilingualNamingRule,
    UCSNamingRule,
    TemplateNamingRule,
)

__all__ = [
    'NamingService',
    'INamingRule',
    'RuleRegistry',
    'RuleValidator',
    'TemplateProcessor',
    'DirectNamingRule',
    'BilingualNamingRule',
    'UCSNamingRule',
    'TemplateNamingRule',
] 