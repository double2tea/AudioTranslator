"""
分类服务模块

此模块提供了音效文件分类的管理和操作功能。
CategoryService 作为服务层组件，提供了分类数据的加载、查询、匹配和管理功能。
"""

import os
import logging
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass
from functools import lru_cache

from ..core.base_service import BaseService

# 设置日志记录器
logger = logging.getLogger(__name__)

@dataclass
class Category:
    """分类数据结构"""
    cat_id: str
    name_en: str
    name_zh: str
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
            'synonyms': self.synonyms_en,
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
            synonyms_en=data.get('synonyms', []),
            synonyms_zh=data.get('synonyms_zh', [])
        )


class CategoryService(BaseService):
    """
    分类服务类
    
    负责音效文件分类的管理和操作，提供分类数据的加载、查询、匹配和管理功能。
    
    Attributes:
        categories: 分类数据字典，键为分类ID，值为Category对象
        match_cache: 文件名到分类ID的匹配缓存
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化分类服务
        
        Args:
            data_dir: 数据目录路径，如果为None则使用默认路径
        """
        super().__init__("category_service")
        
        # 设置数据目录
        self.data_dir = Path(data_dir) if data_dir else Path('data')
        self.categories_file = self.data_dir / "_categorylist.csv"
        
        # 初始化分类数据
        self.categories: Dict[str, Category] = {}
        
        # 初始化缓存
        self._match_cache: Dict[str, str] = {}
        
        # 评分规则常量
        self.SCORE_RULES = {
            'EXACT_CATEGORY_SUBCATEGORY': 110,      # Category + SubCategory 完全匹配（正确顺序）
            'EXACT_CATEGORY_SUBCATEGORY_REVERSE': 100,  # Category + SubCategory 完全匹配（反序）
            'EXACT_SUBCATEGORY_SYNONYM': 90,        # SubCategory + Synonym 完全匹配
            'EXACT_CATEGORY_SYNONYM': 60,           # Category + Synonym 完全匹配
            'PARTIAL_SUBCATEGORY': 40,              # SubCategory 部分匹配
            'PARTIAL_CATEGORY': 25,                 # Category 部分匹配
            'PARTIAL_SYNONYM': 30,                  # Synonym 部分匹配
            'CHINESE_MATCH': 15,                    # 中文匹配
            'POSITION_FIRST_WORD': 20,              # 首词匹配额外加分
            'POSITION_EXACT_ORDER': 10,             # 精确顺序匹配额外加分
        }
    
    def initialize(self) -> bool:
        """
        初始化分类服务
        
        加载分类数据并初始化缓存。
        
        Returns:
            初始化是否成功
        """
        try:
            # 加载分类数据
            self.load_categories()
            
            self.is_initialized = True
            logger.info("分类服务初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"分类服务初始化失败: {e}")
            return False
    
    def shutdown(self) -> bool:
        """
        关闭分类服务
        
        清理资源并保存数据。
        
        Returns:
            关闭是否成功
        """
        try:
            # 清理缓存
            self._match_cache.clear()
            
            logger.info("分类服务已关闭")
            return True
            
        except Exception as e:
            logger.error(f"分类服务关闭失败: {e}")
            return False
    
    def load_categories(self) -> None:
        """
        从CSV文件加载分类数据
        
        从data/_categorylist.csv文件加载分类数据，并存储在categories字典中。
        如果加载失败，会记录错误日志。
        """
        try:
            # 检查文件是否存在
            if not self.categories_file.exists():
                logger.error(f"分类文件不存在: {self.categories_file}")
                return
                
            # 读取CSV文件
            with open(self.categories_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    cat_id = row.get('CatID', '').strip()
                    
                    if not cat_id:
                        continue
                        
                    # 处理同义词列表
                    synonyms_en = []
                    synonyms_zh = []
                    
                    # 提取英文同义词
                    synonyms_str = row.get('Synonyms - Comma Separated', '')
                    if synonyms_str:
                        synonyms_en = [s.strip().lower() for s in synonyms_str.split(',') if s.strip()]
                    
                    # 提取中文同义词
                    synonyms_zh_str = row.get('Synonyms_zh', '')
                    if synonyms_zh_str:
                        synonyms_zh = [s.strip() for s in synonyms_zh_str.split('、') if s.strip()]
                    
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
    
    def get_category(self, cat_id: str) -> Optional[Dict[str, Any]]:
        """
        获取分类信息
        
        Args:
            cat_id: 分类ID
            
        Returns:
            分类信息字典，如果不存在则返回None
        """
        if cat_id in self.categories:
            return self.categories[cat_id].to_dict()
        return None
    
    def get_all_categories(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有分类
        
        Returns:
            所有分类的字典，键为分类ID，值为分类信息字典
        """
        return {cat_id: category.to_dict() for cat_id, category in self.categories.items()}
    
    @lru_cache(maxsize=1000)
    def guess_category(self, filename: str) -> str:
        """
        根据文件名智能猜测分类ID
        
        Args:
            filename: 文件名
            
        Returns:
            最匹配的分类ID
        """
        # 检查缓存
        if filename in self._match_cache:
            return self._match_cache[filename]
        
        # 预处理文件名
        filename_lower = filename.lower().replace('_', ' ')
        
        best_match = None
        max_score = 0
        
        # 遍历所有分类
        for cat_id, category in self.categories.items():
            score = 0
            
            # 检查英文同义词
            for synonym in category.synonyms_en:
                if synonym.lower() in filename_lower:
                    score += self.SCORE_RULES['PARTIAL_SYNONYM']
            
            # 检查中文同义词
            for synonym in category.synonyms_zh:
                if synonym in filename:
                    score += self.SCORE_RULES['CHINESE_MATCH']
            
            # 检查分类名称
            if category.name_en.lower() in filename_lower:
                score += self.SCORE_RULES['PARTIAL_CATEGORY']
                
            if category.name_zh in filename:
                score += self.SCORE_RULES['CHINESE_MATCH']
            
            # 检查子分类名称
            if category.subcategory and category.subcategory.lower() in filename_lower:
                score += self.SCORE_RULES['PARTIAL_SUBCATEGORY']
                
            if category.subcategory_zh and category.subcategory_zh in filename:
                score += self.SCORE_RULES['CHINESE_MATCH']
            
            # 检查分类ID
            if cat_id.lower() in filename_lower:
                score += self.SCORE_RULES['EXACT_CATEGORY_SUBCATEGORY']
            
            # 更新最佳匹配
            if score > max_score:
                max_score = score
                best_match = cat_id
        
        # 如果找到匹配
        if best_match:
            # 缓存结果
            self._match_cache[filename] = best_match
            return best_match
        
        # 如果没有匹配，返回默认分类
        return 'OTHER'
    
    def search_categories(self, query: str) -> Dict[str, Dict[str, Any]]:
        """
        搜索分类
        
        Args:
            query: 搜索关键词
            
        Returns:
            匹配的分类字典，键为分类ID，值为分类信息字典
        """
        if not query:
            return self.get_all_categories()
        
        query = query.lower()
        results = {}
        
        for cat_id, category in self.categories.items():
            # 检查分类ID
            if query in cat_id.lower():
                results[cat_id] = category.to_dict()
                continue
                
            # 检查分类名称
            if query in category.name_en.lower() or query in category.name_zh:
                results[cat_id] = category.to_dict()
                continue
                
            # 检查子分类名称
            if (category.subcategory and query in category.subcategory.lower()) or \
               (category.subcategory_zh and query in category.subcategory_zh):
                results[cat_id] = category.to_dict()
                continue
                
            # 检查同义词
            found = False
            for synonym in category.synonyms_en:
                if query in synonym.lower():
                    results[cat_id] = category.to_dict()
                    found = True
                    break
                    
            if found:
                continue
                
            for synonym in category.synonyms_zh:
                if query in synonym:
                    results[cat_id] = category.to_dict()
                    break
        
        return results
    
    def create_category_folder(self, cat_id: str, base_path: Path) -> Path:
        """
        创建分类文件夹
        
        Args:
            cat_id: 分类ID
            base_path: 基础路径
            
        Returns:
            创建的文件夹路径
        """
        category = self.get_category(cat_id)
        if not category:
            # 如果找不到分类，使用默认值
            folder_name = f"{cat_id}_其他"
        else:
            folder_name = f"{cat_id}_{category['Category_zh']}"
        
        # 创建分类文件夹
        folder_path = base_path / folder_name
        folder_path.mkdir(exist_ok=True)
        
        return folder_path
    
    def create_subcategory_folder(self, cat_id: str, category_folder: Path) -> Optional[Path]:
        """
        创建子分类文件夹
        
        Args:
            cat_id: 分类ID
            category_folder: 分类文件夹路径
            
        Returns:
            创建的子分类文件夹路径，如果没有子分类则返回None
        """
        category = self.get_category(cat_id)
        if not category or not category['subcategory'] or not category['subcategory_zh']:
            return None
        
        # 创建子分类文件夹
        subcategory_folder = category_folder / f"{category['subcategory']}_{category['subcategory_zh']}"
        subcategory_folder.mkdir(exist_ok=True)
        
        return subcategory_folder
    
    def add_category(self, category_data: Dict[str, Any]) -> bool:
        """
        添加新分类
        
        Args:
            category_data: 分类数据
            
        Returns:
            添加是否成功
        """
        try:
            cat_id = category_data.get('CatID', '').strip()
            if not cat_id:
                logger.error("添加分类失败：缺少分类ID")
                return False
            
            # 创建分类对象
            category = Category.from_dict(category_data)
            
            # 存储分类
            self.categories[cat_id] = category
            
            # 保存到文件
            self._save_categories()
            
            logger.info(f"成功添加分类: {cat_id}")
            return True
            
        except Exception as e:
            logger.error(f"添加分类失败: {e}")
            return False
    
    def update_category(self, cat_id: str, category_data: Dict[str, Any]) -> bool:
        """
        更新分类
        
        Args:
            cat_id: 分类ID
            category_data: 分类数据
            
        Returns:
            更新是否成功
        """
        try:
            if cat_id not in self.categories:
                logger.error(f"更新分类失败：分类ID不存在 {cat_id}")
                return False
            
            # 创建分类对象
            category = Category.from_dict(category_data)
            
            # 更新分类
            self.categories[cat_id] = category
            
            # 保存到文件
            self._save_categories()
            
            # 清除缓存
            self._match_cache.clear()
            
            logger.info(f"成功更新分类: {cat_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新分类失败: {e}")
            return False
    
    def delete_category(self, cat_id: str) -> bool:
        """
        删除分类
        
        Args:
            cat_id: 分类ID
            
        Returns:
            删除是否成功
        """
        try:
            if cat_id not in self.categories:
                logger.error(f"删除分类失败：分类ID不存在 {cat_id}")
                return False
            
            # 删除分类
            del self.categories[cat_id]
            
            # 保存到文件
            self._save_categories()
            
            # 清除缓存
            self._match_cache.clear()
            
            logger.info(f"成功删除分类: {cat_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除分类失败: {e}")
            return False
    
    def _save_categories(self) -> bool:
        """
        保存分类数据到CSV文件
        
        Returns:
            保存是否成功
        """
        try:
            # 确保目录存在
            self.categories_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 准备CSV数据
            fieldnames = [
                'CatID', 'Category', 'Category_zh', 
                'SubCategory', 'SubCategory_zh',
                'Synonyms - Comma Separated', 'Synonyms_zh'
            ]
            
            rows = []
            for cat_id, category in self.categories.items():
                row = {
                    'CatID': category.cat_id,
                    'Category': category.name_en,
                    'Category_zh': category.name_zh,
                    'SubCategory': category.subcategory,
                    'SubCategory_zh': category.subcategory_zh,
                    'Synonyms - Comma Separated': ', '.join(category.synonyms_en),
                    'Synonyms_zh': '、'.join(category.synonyms_zh)
                }
                rows.append(row)
            
            # 写入CSV文件
            with open(self.categories_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            
            logger.info(f"成功保存分类数据到 {self.categories_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存分类数据失败: {e}")
            return False
    
    def clear_cache(self) -> None:
        """清除缓存"""
        self._match_cache.clear()
        # 清除lru_cache缓存
        self.guess_category.cache_clear()
        logger.info("分类匹配缓存已清除") 