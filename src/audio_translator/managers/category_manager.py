"""
分类管理器模块 - 负责音效文件分类的管理和操作

此模块提供了CategoryManager类，用于管理音效文件的分类。
主要功能包括：
1. 加载和管理分类数据
2. 根据文件名智能猜测分类
3. 提供分类选择对话框
4. 处理文件的分类和移动
"""

import os
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import csv
import shutil
from typing import Dict, List, Tuple, Optional, Any, Union
import threading
import queue
import time
from dataclasses import dataclass
from functools import lru_cache

# 导入自定义对话框
from ..gui.dialogs.category_selection_dialog import CategorySelectionDialog
from ..gui.dialogs.auto_categorize_dialog import AutoCategorizeDialog

# 设置日志记录器
logger = logging.getLogger(__name__)

@dataclass
class Category:
    """分类数据结构"""
    cat_id: str
    name_zh: str
    name_en: str
    subcategory: str = ""
    subcategory_zh: str = ""
    synonyms_en: List[str] = None
    synonyms_zh: List[str] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.synonyms_en is None:
            self.synonyms_en = []
        if self.synonyms_zh is None:
            self.synonyms_zh = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'CatID': self.cat_id,
            'Category': self.name_en,
            'Category_zh': self.name_zh,
            'subcategory': self.subcategory,
            'subcategory_zh': self.subcategory_zh,
            'synonyms_en': self.synonyms_en,
            'synonyms_zh': self.synonyms_zh
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Category':
        """从字典创建分类对象"""
        return cls(
            cat_id=data.get('CatID', ''),
            name_en=data.get('Category', ''),
            name_zh=data.get('Category_zh', ''),
            subcategory=data.get('subcategory', ''),
            subcategory_zh=data.get('subcategory_zh', ''),
            synonyms_en=data.get('synonyms_en', []),
            synonyms_zh=data.get('synonyms_zh', [])
        )


class CategoryManager:
    """音效文件分类管理器"""
    
    # 深色主题配色
    COLORS = {
        'bg_dark': '#1E1E1E',      # 主背景色
        'bg_light': '#2D2D2D',     # 次要背景
        'fg': '#FFFFFF',           # 主文本色
        'fg_dim': '#AAAAAA',       # 次要文本
        'accent': '#007ACC',       # 强调色
        'border': '#3D3D3D',       # 边框色
        'hover': '#3D3D3D',        # 悬停色
        'selected': '#094771'      # 选中色
    }
    
    def __init__(self, parent: tk.Tk):
        """
        初始化分类管理器
        
        Args:
            parent: 父窗口对象
        """
        self.parent = parent
        self.categories: Dict[str, Category] = {}
        self.load_categories()
        
        # 自动分类选项
        self.auto_categorize_var = tk.BooleanVar(value=False)
        
        # 使用子分类选项
        self.use_subcategory_var = tk.BooleanVar(value=True)
        
        # 缓存匹配结果
        self._match_cache: Dict[str, str] = {}
        
        # 创建工作队列和线程
        self._work_queue = queue.Queue()
        self._worker_thread = None
        self._stop_event = threading.Event()
        
    def load_categories(self) -> None:
        """
        从CSV文件加载分类数据
        
        从data/_categorylist.csv文件加载分类数据，并存储在categories字典中。
        如果加载失败，会记录错误日志。
        """
        try:
            # 获取CSV文件路径
            csv_path = Path('data') / '_categorylist.csv'
            
            if not csv_path.exists():
                logger.error(f"分类文件不存在: {csv_path}")
                return
                
            # 读取CSV文件
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    cat_id = row.get('CatID', '').strip()
                    
                    if not cat_id:
                        continue
                        
                    # 处理同义词列表
                    synonyms_en = []
                    synonyms_zh = []
                    
                    # 提取英文同义词
                    for i in range(1, 6):
                        syn_key = f'Synonym{i}'
                        if syn_key in row and row[syn_key].strip():
                            synonyms_en.append(row[syn_key].strip().lower())
                    
                    # 提取中文同义词
                    for i in range(1, 6):
                        syn_key = f'Synonym{i}_zh'
                        if syn_key in row and row[syn_key].strip():
                            synonyms_zh.append(row[syn_key].strip())
                    
                    # 创建分类对象
                    category = Category(
                        cat_id=cat_id,
                        name_en=row.get('Category', '').strip(),
                        name_zh=row.get('Category_zh', '').strip(),
                        subcategory=row.get('SubCategory', '').strip(),
                        subcategory_zh=row.get('SubCategory_zh', '').strip(),
                        synonyms_en=synonyms_en,
                        synonyms_zh=synonyms_zh
                    )
                    
                    # 存储分类
                    self.categories[cat_id] = category
                    
            logger.info(f"成功加载 {len(self.categories)} 个分类")
            
        except Exception as e:
            logger.error(f"加载分类数据失败: {e}")
    
    def guess_category(self, filename: str) -> Dict[str, Any]:
        """
        根据文件名智能猜测分类
        
        Args:
            filename: 文件名
            
        Returns:
            包含猜测分类信息的字典
        """
        # 检查缓存
        if filename in self._match_cache:
            cat_id = self._match_cache[filename]
            return self.get_category_by_id(cat_id)
        
        # 预处理文件名
        filename_lower = filename.lower().replace('_', ' ')
        
        best_match = None
        max_matches = 0
        
        # 遍历所有分类
        for cat_id, category in self.categories.items():
            matches = 0
            
            # 检查英文同义词
            for synonym in category.synonyms_en:
                if synonym.lower() in filename_lower:
                    matches += 2
            
            # 检查中文同义词
            for synonym in category.synonyms_zh:
                if synonym in filename:
                    matches += 2
            
            # 检查分类名称
            if category.name_en.lower() in filename_lower:
                matches += 3
                
            if category.name_zh in filename:
                matches += 3
            
            # 检查子分类名称
            if category.subcategory and category.subcategory.lower() in filename_lower:
                matches += 2
                
            if category.subcategory_zh and category.subcategory_zh in filename:
                matches += 2
            
            # 检查分类ID
            if cat_id.lower() in filename_lower:
                matches += 4
            
            # 更新最佳匹配
            if matches > max_matches:
                max_matches = matches
                best_match = cat_id
        
        # 如果找到匹配
        if best_match:
            # 缓存结果
            self._match_cache[filename] = best_match
            return self.get_category_by_id(best_match)
        
        # 如果没有匹配，返回默认分类
        return {
            'CatID': 'OTHER',
            'Category': 'Other',
            'Category_zh': '其他',
            'subcategory': '',
            'subcategory_zh': ''
        }
    
    def show_category_dialog(self, files: List[str]) -> Optional[Dict[str, Any]]:
        """
        显示分类选择对话框
        
        Args:
            files: 文件路径列表
            
        Returns:
            选择的分类信息，如果取消则返回None
        """
        dialog = CategorySelectionDialog(
            self.parent, 
            self.categories,
            files=files
        )
        
        # 显示对话框并获取结果
        result = dialog.show()
        return result
    
    def get_category_by_id(self, cat_id: str) -> Dict[str, Any]:
        """
        根据分类ID获取分类信息
        
        Args:
            cat_id: 分类ID
            
        Returns:
            分类信息字典
        """
        if cat_id in self.categories:
            return self.categories[cat_id].to_dict()
        
        # 如果找不到分类，返回默认分类
        return {
            'CatID': 'OTHER',
            'Category': 'Other',
            'Category_zh': '其他',
            'subcategory': '',
            'subcategory_zh': ''
        }
    
    def create_category_folder(self, category: Dict[str, Any], base_path: Path) -> Path:
        """
        创建分类文件夹
        
        Args:
            category: 分类信息
            base_path: 基础路径
            
        Returns:
            创建的文件夹路径
        """
        cat_id = category.get('CatID', '')
        cat_zh = category.get('Category_zh', '')
        
        # 创建分类文件夹
        category_folder = base_path / f"{cat_id}_{cat_zh}"
        category_folder.mkdir(exist_ok=True)
        
        return category_folder
    
    def move_files_to_category(self, files: List[str], category: Dict[str, Any], 
                              base_path: Union[str, Path]) -> List[str]:
        """
        将文件移动到分类文件夹
        
        Args:
            files: 文件路径列表
            category: 分类信息
            base_path: 基础路径
            
        Returns:
            成功移动的文件路径列表
        """
        if not files or not category:
            return []
        
        # 确保base_path是Path对象
        if isinstance(base_path, str):
            base_path = Path(base_path)
        
        # 创建分类文件夹
        category_folder = self.create_category_folder(category, base_path)
        
        # 如果需要使用子分类
        subcategory = category.get('subcategory', '')
        subcategory_zh = category.get('subcategory_zh', '')
        
        if subcategory and subcategory_zh:
            sub_folder = category_folder / f"{subcategory}_{subcategory_zh}"
            sub_folder.mkdir(exist_ok=True)
            target_folder = sub_folder
        else:
            target_folder = category_folder
        
        # 移动文件
        moved_files = []
        
        for file_path in files:
            try:
                # 获取文件名
                file_path = Path(file_path)
                filename = file_path.name
                
                # 生成目标路径
                target_path = target_folder / filename
                
                # 如果目标文件已存在，生成唯一文件名
                if target_path.exists():
                    base_name = target_path.stem
                    extension = target_path.suffix
                    counter = 1
                    
                    while True:
                        new_name = f"{base_name}_{counter}{extension}"
                        target_path = target_folder / new_name
                        
                        if not target_path.exists():
                            break
                            
                        counter += 1
                
                # 移动文件
                shutil.move(str(file_path), str(target_path))
                moved_files.append(str(target_path))
                
                logger.info(f"文件已移动: {file_path} -> {target_path}")
                
            except Exception as e:
                logger.error(f"移动文件失败 {file_path}: {e}")
        
        return moved_files
    
    def start_auto_categorize(self, files: List[str], base_path: Union[str, Path]) -> List[str]:
        """
        开始自动分类处理
        
        Args:
            files: 文件路径列表
            base_path: 基础路径
            
        Returns:
            成功移动的文件路径列表
        """
        dialog = AutoCategorizeDialog(
            self.parent,
            files=files,
            category_manager=self,
            base_path=base_path
        )
        
        # 显示对话框并获取结果
        result = dialog.show()
        return result or []
    
    def get_auto_categorize_var(self) -> tk.BooleanVar:
        """
        获取自动分类选项变量
        
        Returns:
            自动分类选项变量
        """
        return self.auto_categorize_var
    
    def get_use_subcategory_var(self) -> tk.BooleanVar:
        """
        获取使用子分类选项变量
        
        Returns:
            使用子分类选项变量
        """
        return self.use_subcategory_var
    
    def get_all_categories(self) -> Dict[str, Category]:
        """
        获取所有分类
        
        Returns:
            所有分类的字典
        """
        return self.categories
    
    def search_categories(self, query: str) -> Dict[str, Category]:
        """
        搜索分类
        
        Args:
            query: 搜索关键词
            
        Returns:
            匹配的分类字典
        """
        if not query:
            return self.categories
        
        query = query.lower()
        results = {}
        
        for cat_id, category in self.categories.items():
            # 检查分类ID
            if query in cat_id.lower():
                results[cat_id] = category
                continue
                
            # 检查分类名称
            if query in category.name_en.lower() or query in category.name_zh:
                results[cat_id] = category
                continue
                
            # 检查子分类名称
            if (category.subcategory and query in category.subcategory.lower()) or \
               (category.subcategory_zh and query in category.subcategory_zh):
                results[cat_id] = category
                continue
                
            # 检查同义词
            found = False
            for synonym in category.synonyms_en:
                if query in synonym.lower():
                    results[cat_id] = category
                    found = True
                    break
                    
            if found:
                continue
                
            for synonym in category.synonyms_zh:
                if query in synonym:
                    results[cat_id] = category
                    break
        
        return results
    
    def clear_cache(self) -> None:
        """清除缓存"""
        self._match_cache.clear()
        logger.info("分类匹配缓存已清除") 