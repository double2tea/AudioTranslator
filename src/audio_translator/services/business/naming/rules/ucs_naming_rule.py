"""
UCS命名规则模块
"""
from typing import Dict, List, Any, Optional
import logging
from ..naming_rule import INamingRule

logger = logging.getLogger(__name__)


class UCSNamingRule(INamingRule):
    """
    UCS标准命名规则 - 分类ID_分类名称_描述
    UCS（Universal Category System）是一种通用分类系统
    """
    
    def __init__(self, description: str = "UCS标准 - 分类ID_分类名称_描述"):
        """
        初始化UCS命名规则
        
        Args:
            description: 规则描述
        """
        self.description = description
        self.category_service = None
    
    def set_category_service(self, category_service) -> None:
        """
        设置分类服务
        
        Args:
            category_service: 分类服务实例
        """
        self.category_service = category_service
        logger.info("已设置分类服务")
    
    def format(self, context: Dict[str, Any]) -> str:
        """
        格式化上下文为文件名
        
        Args:
            context: 命名上下文
            
        Returns:
            格式化后的文件名
        """
        category_id = context.get('category_id', 'OTHER')
        category_name = context.get('category', 'Other')
        translated = context.get('translated_name', '')
        extension = context.get('extension', '')
        
        # 尝试自动获取分类信息（如果未提供）
        if (category_id == 'OTHER' and 'original_name' in context and 
                self.category_service and hasattr(self.category_service, 'guess_category_with_fields')):
            try:
                cat_info = self.category_service.guess_category_with_fields(context['original_name'])
                category_id = cat_info.get('category_id', category_id)
                category_name = cat_info.get('category', category_name)
                logger.debug(f"自动获取分类信息: {category_id}, {category_name}")
            except Exception as e:
                logger.warning(f"获取分类信息失败: {e}")
        
        # 格式化为UCS标准格式
        return f"{category_id}_{category_name}_{translated}{extension}"
    
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