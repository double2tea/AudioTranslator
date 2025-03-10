"""
分类管理器模块 - 负责音效文件分类的UI管理和操作

此模块提供了CategoryManager类，用于管理音效文件分类的UI相关功能。
主要功能包括：
1. 提供分类选择对话框
2. 处理分类UI交互
3. 处理文件的分类和移动
"""

import os
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import shutil
from typing import Dict, List, Tuple, Optional, Any, Union

# 导入自定义对话框
from ..gui.dialogs.category_selection_dialog import CategorySelectionDialog
from ..gui.dialogs.auto_categorize_dialog import AutoCategorizeDialog
from ..services.business.category import Category

# 设置日志记录器
logger = logging.getLogger(__name__)

class CategoryManager:
    """
    分类管理器
    
    负责音效文件分类的UI管理和操作，作为UI层和服务层之间的桥梁。
    主要功能：
    - 提供分类选择对话框
    - 管理分类UI交互
    - 处理文件的分类和移动操作
    """
    
    def __init__(self, parent: tk.Tk):
        """
        初始化分类管理器
        
        Args:
            parent: 父窗口
        """
        self.parent = parent
        
        # 分类服务
        self.category_service = None
        
        # UI变量
        self.auto_categorize_var = tk.BooleanVar(value=False)
        self.use_subcategory_var = tk.BooleanVar(value=True)
    
    def set_category_service(self, category_service):
        """
        设置分类服务
        
        Args:
            category_service: 分类服务实例
        """
        self.category_service = category_service
    
    def show_category_dialog(self, files: List[str]) -> Optional[Dict[str, Any]]:
        """
        显示分类选择对话框
        
        Args:
            files: 文件列表
            
        Returns:
            用户选择的分类信息，取消则返回None
        """
        if not self.category_service:
            logger.error("分类服务未设置")
            messagebox.showerror("错误", "分类服务未初始化")
            return None
        
        # 获取所有分类
        categories = self.category_service.get_categories_for_ui()
        
        # 创建并显示对话框
        dialog = CategorySelectionDialog(
            self.parent,
            categories=categories,
            files=files
        )
        
        return dialog.show()
    
    def start_auto_categorize(self, files: List[str], base_path: Union[str, Path]) -> List[str]:
        """
        开始自动分类处理
        
        Args:
            files: 文件列表
            base_path: 基础路径
            
        Returns:
            成功分类的文件列表
        """
        if not self.category_service:
            logger.error("分类服务未设置")
            messagebox.showerror("错误", "分类服务未初始化")
            return []
        
        # 确保基础路径存在
        if isinstance(base_path, str):
            base_path = Path(base_path)
        os.makedirs(base_path, exist_ok=True)
        
        # 创建并显示自动分类对话框
        dialog = AutoCategorizeDialog(
            self.parent,
            files=files,
            category_service=self.category_service,
            base_path=str(base_path)
        )
        
        return dialog.show() or []
    
    def categorize_files(self, files: List[str], 
                        category_id: str, 
                        base_path: Union[str, Path]) -> List[str]:
        """
        将文件分类到指定分类
        
        Args:
            files: 文件列表
            category_id: 分类ID
            base_path: 基础路径
            
        Returns:
            成功分类的文件列表
        """
        if not self.category_service:
            logger.error("分类服务未设置")
            messagebox.showerror("错误", "分类服务未初始化")
            return []
        
        # 确保基础路径存在
        if isinstance(base_path, str):
            base_path = Path(base_path)
        os.makedirs(base_path, exist_ok=True)
        
        # 移动文件
        moved_files = []
        for file_path in files:
            try:
                target_path = self.category_service.move_file_to_category(
                    file_path, 
                    category_id, 
                    str(base_path)
                )
                if target_path:
                    moved_files.append(target_path)
            except Exception as e:
                logger.error(f"移动文件失败: {file_path}, {e}")
        
        return moved_files
    
    def guess_category(self, filename: str) -> str:
        """
        根据文件名猜测分类ID
        
        Args:
            filename: 文件名
            
        Returns:
            分类ID
        """
        if not self.category_service:
            logger.error("分类服务未设置")
            return 'OTHER'
        
        return self.category_service.guess_category(filename)
    
    def create_category_directories(self, base_path: Union[str, Path]) -> bool:
        """
        创建分类目录结构
        
        Args:
            base_path: 基础路径
            
        Returns:
            创建是否成功
        """
        if not self.category_service:
            logger.error("分类服务未设置")
            messagebox.showerror("错误", "分类服务未初始化")
            return False
        
        # 确保基础路径存在
        if isinstance(base_path, str):
            base_path = Path(base_path)
        os.makedirs(base_path, exist_ok=True)
        
        return self.category_service.create_category_directories(str(base_path))
    
    def search_categories(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索分类
        
        Args:
            keyword: 关键字
            
        Returns:
            匹配的分类列表
        """
        if not self.category_service:
            logger.error("分类服务未设置")
            return []
        
        # 过滤分类
        filtered_categories = self.category_service.filter_categories(keyword)
        
        # 转换为UI格式
        return self.category_service.get_categories_for_ui(keyword)
    
    def get_category_display_name(self, cat_id: str, language: str = "zh") -> str:
        """
        获取分类显示名称
        
        Args:
            cat_id: 分类ID
            language: 语言，'zh'表示中文，其他表示英文
            
        Returns:
            分类显示名称
        """
        if not self.category_service:
            logger.error("分类服务未设置")
            return cat_id
        
        # 获取分类
        category = self.category_service.get_category(cat_id)
        if not category:
            return cat_id
        
        # 获取显示名称
        return category.get_display_name(language)
    
    def is_valid_category(self, cat_id: str) -> bool:
        """
        检查分类ID是否有效
        
        Args:
            cat_id: 分类ID
            
        Returns:
            是否有效
        """
        if not self.category_service:
            logger.error("分类服务未设置")
            return False
        
        return cat_id in self.category_service.get_all_categories()
    
    def get_all_categories(self) -> Dict[str, Any]:
        """
        获取所有分类
        
        Returns:
            所有分类的字典，键为分类ID，值为分类对象
        """
        if not self.category_service:
            logger.error("分类服务未设置")
            return {}
        
        return self.category_service.get_all_categories()
    
    def get_subcategories(self, parent_id: str) -> Dict[str, Any]:
        """
        获取子分类
        
        Args:
            parent_id: 父分类ID
            
        Returns:
            子分类的字典，键为分类ID，值为分类对象
        """
        if not self.category_service:
            logger.error("分类服务未设置")
            return {}
        
        return self.category_service.get_subcategories(parent_id) 