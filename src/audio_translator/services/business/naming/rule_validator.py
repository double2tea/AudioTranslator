"""
规则验证器模块，用于验证命名规则和上下文
"""
from typing import Dict, List, Any, Tuple, Optional
import logging
from .naming_rule import INamingRule

logger = logging.getLogger(__name__)


class RuleValidator:
    """
    规则验证器，负责验证命名规则和上下文
    """
    
    def validate_rule(self, rule: INamingRule) -> bool:
        """
        验证命名规则是否有效
        
        Args:
            rule: 命名规则实例
            
        Returns:
            规则是否有效
        """
        # 检查规则是否实现了所有必要的方法
        required_methods = ['format', 'get_required_fields', 'validate']
        for method in required_methods:
            if not hasattr(rule, method) or not callable(getattr(rule, method)):
                logger.error(f"规则验证失败，缺少方法: {method}")
                return False
        return True
    
    def validate_context(self, rule: INamingRule, context: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证上下文是否满足规则要求
        
        Args:
            rule: 命名规则实例
            context: 命名上下文
            
        Returns:
            (是否有效, 缺失字段列表)
        """
        required_fields = rule.get_required_fields()
        missing_fields = [field for field in required_fields if field not in context]
        return len(missing_fields) == 0, missing_fields
    
    def suggest_fixes(self, rule: INamingRule, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        为无效上下文建议修复方案
        
        Args:
            rule: 命名规则实例
            context: 命名上下文
            
        Returns:
            修复后的上下文副本
        """
        is_valid, missing_fields = self.validate_context(rule, context)
        if is_valid:
            return context.copy()
        
        # 创建上下文的副本
        fixed_context = context.copy()
        
        # 为每个缺失字段添加默认值
        for field in missing_fields:
            if field == 'original_name' and 'translated_name' in context:
                fixed_context[field] = context['translated_name']
            elif field == 'translated_name' and 'original_name' in context:
                fixed_context[field] = context['original_name']
            elif field == 'extension' and 'original_name' in context:
                # 尝试从原始文件名中提取扩展名
                original = context['original_name']
                if '.' in original:
                    fixed_context[field] = '.' + original.split('.')[-1]
                else:
                    fixed_context[field] = ''
            else:
                fixed_context[field] = f"unknown_{field}"
        
        return fixed_context 