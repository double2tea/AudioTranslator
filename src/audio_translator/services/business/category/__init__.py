"""
分类服务模块

此模块提供了音频文件分类相关的功能，包括分类数据结构和管理服务。
主要组件包括：
1. Category类：分类数据结构
2. CategoryService：分类管理服务
3. 辅助工具函数
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set

@dataclass
class Category:
    """
    分类数据结构
    
    表示一个音频文件分类，包含ID、名称、同义词等信息。
    支持转换为UI和存储格式的方法。
    """
    cat_id: str
    name_zh: str
    name_en: str
    subcategory: str = ""
    subcategory_zh: str = ""
    synonyms_en: List[str] = field(default_factory=list)
    synonyms_zh: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    parent_id: str = ""
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def get_display_name(self, language: str = "zh") -> str:
        """
        获取分类的显示名称
        
        Args:
            language: 语言代码，'zh'表示中文，其他表示英文
            
        Returns:
            分类显示名称
        """
        if language == "zh" and self.name_zh:
            return self.name_zh
        return self.name_en or self.cat_id
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式（存储格式）
        
        Returns:
            分类的字典表示
        """
        return {
            'CatID': self.cat_id,
            'Category': self.name_en,
            'Category_zh': self.name_zh,
            'SubCategory': self.subcategory,
            'SubCategory_zh': self.subcategory_zh,
            'parent_id': self.parent_id,
            'synonyms_en': self.synonyms_en,
            'synonyms_zh': self.synonyms_zh,
            'keywords': self.keywords,
            **self.custom_fields
        }
    
    def to_ui_dict(self) -> Dict[str, Any]:
        """
        转换为UI字典格式
        
        Returns:
            用于UI显示的字典表示
        """
        return {
            'id': self.cat_id,
            'name_zh': self.name_zh,
            'name_en': self.name_en,
            'subcategory': self.subcategory,
            'subcategory_zh': self.subcategory_zh,
            'parent_id': self.parent_id,
            'synonyms_zh': self.synonyms_zh,
            'synonyms_en': self.synonyms_en,
            'keywords': self.keywords,
            'display_name': self.get_display_name()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Category':
        """
        从字典创建分类对象
        
        Args:
            data: 包含分类数据的字典
            
        Returns:
            创建的Category对象
        """
        # 提取标准字段
        standard_fields = {
            'cat_id': data.get('CatID', ''),
            'name_en': data.get('Category', ''),
            'name_zh': data.get('Category_zh', ''),
            'subcategory': data.get('SubCategory', ''),
            'subcategory_zh': data.get('SubCategory_zh', ''),
            'parent_id': data.get('parent_id', ''),
            'synonyms_en': data.get('synonyms_en', []),
            'synonyms_zh': data.get('synonyms_zh', []),
            'keywords': data.get('keywords', [])
        }
        
        # 提取自定义字段
        custom_fields = {}
        for key, value in data.items():
            if key not in ['CatID', 'Category', 'Category_zh', 'SubCategory', 
                           'SubCategory_zh', 'parent_id', 'synonyms_en', 
                           'synonyms_zh', 'keywords']:
                custom_fields[key] = value
                
        # 创建分类对象
        category = cls(**standard_fields)
        category.custom_fields = custom_fields
        
        return category
    
    def get_search_terms(self) -> Set[str]:
        """
        获取所有可搜索的术语
        
        Returns:
            包含分类ID、名称和同义词的集合
        """
        terms = {
            self.cat_id.lower(), 
            self.name_en.lower(), 
            self.name_zh
        }
        
        # 添加子分类名称
        if self.subcategory:
            terms.add(self.subcategory.lower())
        if self.subcategory_zh:
            terms.add(self.subcategory_zh)
            
        # 添加同义词
        terms.update([s.lower() for s in self.synonyms_en])
        terms.update(self.synonyms_zh)
        
        # 添加关键词
        terms.update([k.lower() for k in self.keywords])
        
        # 移除空字符串
        if '' in terms:
            terms.remove('')
            
        return terms
        
    def matches_keyword(self, keyword: str, threshold: float = 0.0) -> bool:
        """
        检查分类是否匹配关键词
        
        Args:
            keyword: 要匹配的关键词
            threshold: 相似度阈值，用于模糊匹配
            
        Returns:
            是否匹配
        """
        # 标准化关键词
        keyword = keyword.lower()
        
        # 精确匹配
        if threshold <= 0:
            if (keyword in self.cat_id.lower() or
                keyword in self.name_en.lower() or
                keyword in self.name_zh.lower() or
                keyword in [s.lower() for s in self.synonyms_en] or
                keyword in self.synonyms_zh or
                (self.subcategory and keyword in self.subcategory.lower()) or
                (self.subcategory_zh and keyword in self.subcategory_zh.lower())):
                return True
            return False
            
        # 模糊匹配需要导入模块
        from ..category.category_utils import calculate_text_similarity
        
        # 检查每个可匹配字段
        search_terms = self.get_search_terms()
        
        for term in search_terms:
            similarity = calculate_text_similarity(keyword, term)
            if similarity >= threshold:
                return True
                
        return False

from .category_service import CategoryService
from .category_utils import (
    normalize_text, 
    calculate_text_similarity,
    calculate_category_match_score,
    filter_categories_by_keyword,
    create_category_path
)

__all__ = [
    'Category',
    'CategoryService',
    'normalize_text',
    'calculate_text_similarity',
    'calculate_category_match_score',
    'filter_categories_by_keyword',
    'create_category_path'
] 