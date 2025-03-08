"""
上下文处理器模块

此模块提供翻译上下文的处理功能，包括上下文构建、增强和验证。
"""

import logging
import os
from typing import Dict, Any, Optional, List

# 设置日志记录器
logger = logging.getLogger(__name__)

class ContextProcessor:
    """
    上下文处理器
    
    处理翻译上下文，提供上下文构建、增强和验证功能。
    主要功能：
    - 构建基础上下文
    - 增强上下文（添加分类信息等）
    - 验证上下文
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化上下文处理器
        
        Args:
            config: 处理器配置
        """
        self.config = config or {}
        
        # 依赖服务
        self.category_service = None
        self.ucs_service = None
    
    def set_category_service(self, category_service):
        """
        设置分类服务
        
        Args:
            category_service: 分类服务实例
        """
        self.category_service = category_service
    
    def set_ucs_service(self, ucs_service):
        """
        设置UCS服务
        
        Args:
            ucs_service: UCS服务实例
        """
        self.ucs_service = ucs_service
    
    def build_context(self, file_path: str) -> Dict[str, Any]:
        """
        构建基础上下文
        
        Args:
            file_path: 文件路径
            
        Returns:
            基础上下文
        """
        # 提取文件信息
        file_name = os.path.basename(file_path)
        name, ext = os.path.splitext(file_name)
        
        # 构建基础上下文
        context = {
            'original_name': name,
            'extension': ext,
            'file_path': file_path,
            'file_name': file_name,
            'directory': os.path.dirname(file_path)
        }
        
        return context
    
    def enhance_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        增强上下文
        
        添加分类信息、UCS信息等
        
        Args:
            context: 基础上下文
            
        Returns:
            增强后的上下文
        """
        # 复制上下文
        enhanced = context.copy()
        
        # 添加分类信息
        if self.category_service and 'original_name' in context:
            try:
                cat_info = self.category_service.guess_category_with_fields(context['original_name'])
                if cat_info:
                    enhanced.update(cat_info)
            except Exception as e:
                logger.warning(f"获取分类信息失败: {e}")
        
        # 添加UCS信息
        if self.ucs_service and 'original_name' in context:
            try:
                ucs_info = self.ucs_service.get_ucs_info(context['original_name'])
                if ucs_info:
                    enhanced['ucs'] = ucs_info
            except Exception as e:
                logger.warning(f"获取UCS信息失败: {e}")
        
        return enhanced
    
    def validate_context(self, context: Dict[str, Any], required_fields: List[str]) -> bool:
        """
        验证上下文
        
        检查上下文是否包含所有必需字段
        
        Args:
            context: 上下文
            required_fields: 必需字段列表
            
        Returns:
            验证是否通过
        """
        return all(field in context for field in required_fields)
    
    def fill_missing_fields(self, context: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        """
        填充缺失字段
        
        Args:
            context: 上下文
            required_fields: 必需字段列表
            
        Returns:
            填充后的上下文
        """
        # 复制上下文
        filled = context.copy()
        
        for field in required_fields:
            if field not in filled:
                # 特殊字段处理
                if field.startswith('category') and self.category_service and 'original_name' in context:
                    # 尝试获取分类信息
                    cat_info = self.category_service.guess_category_with_fields(context['original_name'])
                    if cat_info:
                        filled.update(cat_info)
                        continue
                
                # 添加默认值
                filled[field] = f"未知{field}"
        
        return filled 