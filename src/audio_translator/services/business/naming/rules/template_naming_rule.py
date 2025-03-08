"""
模板命名规则模块
"""
from typing import Dict, List, Any, Optional
import logging
import re
from ..naming_rule import INamingRule
from ..template_processor import TemplateProcessor

logger = logging.getLogger(__name__)


class TemplateNamingRule(INamingRule):
    """
    模板命名规则 - 使用自定义模板格式化文件名
    """
    
    def __init__(self, template: str, description: str = None):
        """
        初始化模板命名规则
        
        Args:
            template: 模板字符串，例如 "{category_id}_{translated_name}"
            description: 规则描述，如果为None则自动生成
        """
        self.template = template
        self.description = description or f"模板规则 - {template}"
        self.template_processor = TemplateProcessor()
        self._required_fields = self._extract_required_fields(template)
    
    def _extract_required_fields(self, template: str) -> List[str]:
        """
        从模板中提取必填字段
        
        Args:
            template: 模板字符串
            
        Returns:
            必填字段名称列表
        """
        fields = self.template_processor.extract_fields(template)
        # 添加扩展名字段（如果模板中没有包含）
        if 'extension' not in fields:
            fields.append('extension')
        return fields
    
    def format(self, context: Dict[str, Any]) -> str:
        """
        格式化上下文为文件名
        
        Args:
            context: 命名上下文
            
        Returns:
            格式化后的文件名
        """
        try:
            # 使用模板处理器处理模板
            result = self.template_processor.process_template(self.template, context)
            
            # 添加扩展名（如果模板中没有包含）
            if '{extension}' not in self.template:
                result += context.get('extension', '')
                
            # 清理文件名
            return self.template_processor.sanitize_filename(result)
        except Exception as e:
            logger.error(f"模板格式化失败: {e}")
            return f"模板错误_{context.get('original_name', 'unknown')}"
    
    def get_required_fields(self) -> List[str]:
        """
        获取规则所需的必填字段
        
        Returns:
            必填字段名称列表
        """
        return self._required_fields
    
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
    
    def set_template(self, template: str) -> bool:
        """
        设置新的模板
        
        Args:
            template: 新的模板字符串
            
        Returns:
            设置是否成功
        """
        if not self.template_processor.validate_template(template):
            logger.error(f"模板验证失败: {template}")
            return False
            
        self.template = template
        self._required_fields = self._extract_required_fields(template)
        return True 