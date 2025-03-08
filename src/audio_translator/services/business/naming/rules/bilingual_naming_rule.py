"""
双语命名规则模块
"""
from typing import Dict, List, Any
from ..naming_rule import INamingRule


class BilingualNamingRule(INamingRule):
    """
    双语规则 - 原文件名 + 分隔符 + 翻译名称
    """
    
    def __init__(self, separator: str = " - ", description: str = "双语模式 - 原文件名+分隔符+翻译结果"):
        """
        初始化双语命名规则
        
        Args:
            separator: 分隔符
            description: 规则描述
        """
        self.separator = separator
        self.description = description
    
    def format(self, context: Dict[str, Any]) -> str:
        """
        格式化翻译结果为文件名
        
        Args:
            context: 命名上下文
            
        Returns:
            格式化后的文件名
        """
        original = context.get('original_name', '')
        translated = context.get('translated_name', '')
        extension = context.get('extension', '')
        
        # 确保原始文件名不含扩展名
        if '.' in original and not extension:
            name_parts = original.rsplit('.', 1)
            original = name_parts[0]
            if len(name_parts) > 1:
                extension = '.' + name_parts[1]
            
        return f"{original}{self.separator}{translated}{extension}"
    
    def get_required_fields(self) -> List[str]:
        """
        获取规则所需的必填字段
        
        Returns:
            必填字段名称列表
        """
        return ['original_name', 'translated_name', 'extension']
    
    def validate(self, context: Dict[str, Any]) -> bool:
        """
        验证上下文是否符合规则需求
        
        Args:
            context: 命名上下文
            
        Returns:
            是否有效
        """
        return all(field in context for field in self.get_required_fields())
    
    def get_description(self) -> str:
        """
        获取规则描述
        
        Returns:
            规则描述
        """
        return self.description
    
    def set_separator(self, separator: str) -> None:
        """
        设置分隔符
        
        Args:
            separator: 新的分隔符
        """
        self.separator = separator 