"""
命名规则接口模块，定义命名规则接口和通用功能
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class INamingRule(ABC):
    """
    命名规则接口，所有命名规则必须实现此接口
    """
    
    @abstractmethod
    def format(self, context: Dict[str, Any]) -> str:
        """
        格式化上下文为文件名
        
        Args:
            context: 命名上下文，包含原文件名、翻译名、分类信息等
            
        Returns:
            格式化后的文件名
        """
        pass
    
    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """
        获取规则所需的必填字段
        
        Returns:
            必填字段名称列表
        """
        pass
    
    @abstractmethod
    def validate(self, context: Dict[str, Any]) -> bool:
        """
        验证上下文是否符合规则需求
        
        Args:
            context: 命名上下文
            
        Returns:
            是否有效
        """
        pass
    
    def get_name(self) -> str:
        """
        获取规则名称
        
        Returns:
            规则名称
        """
        return self.__class__.__name__.replace('NamingRule', '')
    
    def get_description(self) -> str:
        """
        获取规则描述
        
        Returns:
            规则描述
        """
        return f"{self.get_name()} Naming Rule" 