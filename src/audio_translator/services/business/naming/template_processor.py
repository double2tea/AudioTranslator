"""
模板处理器模块，负责解析和处理命名模板
"""
from typing import Dict, List, Any, Optional
import re
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


class TemplateProcessor:
    """
    模板处理器，负责解析和处理命名模板
    """
    
    def __init__(self):
        """初始化模板处理器"""
        self.template_cache = {}
    
    def process_template(self, template: str, context: Dict[str, Any]) -> str:
        """
        处理模板
        
        Args:
            template: 模板字符串，格式如 "{category_id}_{translated_name}"
            context: 命名上下文
            
        Returns:
            处理后的字符串
        """
        try:
            # 使用字符串格式化
            return template.format(**context)
        except KeyError as e:
            logger.error(f"模板处理失败，缺少字段: {e}")
            return f"模板错误_{e}"
        except Exception as e:
            logger.error(f"模板处理异常: {e}")
            return f"模板异常_{str(e)[:20]}"
    
    @lru_cache(maxsize=100)
    def extract_fields(self, template: str) -> List[str]:
        """
        从模板中提取字段
        
        Args:
            template: 模板字符串
            
        Returns:
            字段名称列表
        """
        # 匹配{field_name}格式的字段
        pattern = r'\{([a-zA-Z0-9_]+)\}'
        return re.findall(pattern, template)
    
    def validate_template(self, template: str) -> bool:
        """
        验证模板格式是否正确
        
        Args:
            template: 模板字符串
            
        Returns:
            模板是否有效
        """
        try:
            # 尝试使用空字典格式化，检查语法
            dummy_context = {}
            for field in self.extract_fields(template):
                dummy_context[field] = f"test_{field}"
            self.process_template(template, dummy_context)
            return True
        except Exception as e:
            logger.error(f"模板验证失败: {e}")
            return False
    
    def is_template(self, text: str) -> bool:
        """
        检查文本是否是模板
        
        Args:
            text: 要检查的文本
            
        Returns:
            是否是模板
        """
        return '{' in text and '}' in text and self.extract_fields(text)
    
    def sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除不允许的字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            清理后的文件名
        """
        # 替换Windows和类Unix系统不允许的字符
        invalid_chars = r'[<>:"/\\|?*\x00-\x1F]'
        return re.sub(invalid_chars, '_', filename) 