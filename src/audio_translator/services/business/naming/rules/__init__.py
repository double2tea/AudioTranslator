"""
命名规则实现模块
"""
from .direct_naming_rule import DirectNamingRule
from .bilingual_naming_rule import BilingualNamingRule
from .ucs_naming_rule import UCSNamingRule
from .template_naming_rule import TemplateNamingRule

__all__ = [
    'DirectNamingRule',
    'BilingualNamingRule',
    'UCSNamingRule',
    'TemplateNamingRule',
] 