"""
直接翻译规则模块
"""
from typing import Dict, List, Any
from ..naming_rule import INamingRule


class DirectNamingRule(INamingRule):
    """
    直接翻译规则 - 使用翻译结果作为文件名
    """
    
    def __init__(self, description: str = "直接翻译 - 使用翻译结果作为文件名"):
        """
        初始化直接翻译规则
        
        Args:
            description: 规则描述
        """
        self.description = description
    
    def format(self, context: Dict[str, Any]) -> str:
        """
        格式化翻译结果为文件名
        
        Args:
            context: 命名上下文
            
        Returns:
            格式化后的文件名
        """
        translated = context.get('translated_name', '')
        extension = context.get('extension', '')
        return f"{translated}{extension}"
    
    def get_required_fields(self) -> List[str]:
        """
        获取规则所需的必填字段
        
        Returns:
            必填字段名称列表
        """
        return ['translated_name', 'extension']
    
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