"""
分类数据结构模块

此模块定义了分类数据的统一结构，用于在各个组件间传递分类信息。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any

@dataclass
class Category:
    """
    分类数据结构
    
    统一的分类数据结构，用于在服务层和UI层之间传递分类信息。
    提供了分类数据的基本属性和转换方法。
    
    Attributes:
        cat_id: 分类ID
        name_en: 英文分类名称
        name_zh: 中文分类名称
        subcategory: 英文子分类名称
        subcategory_zh: 中文子分类名称
        synonyms_en: 英文同义词列表
        synonyms_zh: 中文同义词列表
        parent_id: 父分类ID，为空表示根分类
    """
    cat_id: str
    name_en: str
    name_zh: str
    subcategory: str = ""
    subcategory_zh: str = ""
    synonyms_en: List[str] = field(default_factory=list)
    synonyms_zh: List[str] = field(default_factory=list)
    parent_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            分类数据的字典表示
        """
        return {
            'CatID': self.cat_id,
            'Category': self.name_en,
            'Category_zh': self.name_zh,
            'subcategory': self.subcategory,
            'subcategory_zh': self.subcategory_zh,
            'synonyms_en': self.synonyms_en,
            'synonyms_zh': self.synonyms_zh,
            'parent_id': self.parent_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Category':
        """
        从字典创建分类对象
        
        Args:
            data: 分类数据字典
            
        Returns:
            分类对象
        """
        # 处理同义词列表(可能是JSON字符串或者列表)
        synonyms_en = data.get('synonyms_en', data.get('synonyms', []))
        synonyms_zh = data.get('synonyms_zh', [])
        
        # 如果是字符串，尝试解析为JSON
        if isinstance(synonyms_en, str):
            try:
                import json
                synonyms_en = json.loads(synonyms_en)
            except Exception as e:
                import logging
                logging.warning(f"解析英文同义词失败: {e}, 值: {synonyms_en}")
                # 分割字符串作为备选方案
                if ',' in synonyms_en:
                    synonyms_en = [s.strip() for s in synonyms_en.split(',')]
                else:
                    synonyms_en = []
        
        # 如果是字符串，尝试解析为JSON
        if isinstance(synonyms_zh, str):
            try:
                import json
                synonyms_zh = json.loads(synonyms_zh)
            except Exception as e:
                import logging
                logging.warning(f"解析中文同义词失败: {e}, 值: {synonyms_zh}")
                # 分割字符串作为备选方案
                if ',' in synonyms_zh:
                    synonyms_zh = [s.strip() for s in synonyms_zh.split(',')]
                else:
                    synonyms_zh = []
        
        return cls(
            cat_id=data.get('CatID', ''),
            name_en=data.get('Category', ''),
            name_zh=data.get('Category_zh', ''),
            subcategory=data.get('subcategory', ''),
            subcategory_zh=data.get('subcategory_zh', ''),
            synonyms_en=synonyms_en,
            synonyms_zh=synonyms_zh,
            parent_id=data.get('parent_id', '')
        )
    
    def get_full_name_en(self) -> str:
        """
        获取完整英文名称
        
        Returns:
            包含子分类的完整英文名称
        """
        if self.subcategory:
            return f"{self.name_en} - {self.subcategory}"
        return self.name_en
    
    def get_full_name_zh(self) -> str:
        """
        获取完整中文名称
        
        Returns:
            包含子分类的完整中文名称
        """
        if self.subcategory_zh:
            return f"{self.name_zh} - {self.subcategory_zh}"
        return self.name_zh
    
    def get_display_name(self, language: str = 'zh') -> str:
        """
        获取显示名称
        
        Args:
            language: 语言，'zh'表示中文，其他表示英文
            
        Returns:
            适合显示的分类名称
        """
        if language == 'zh':
            return self.get_full_name_zh()
        return self.get_full_name_en()
    
    def get_naming_fields(self) -> Dict[str, str]:
        """
        获取用于命名的字段
        
        Returns:
            适用于命名规则的字段字典
        """
        return {
            'category_id': self.cat_id,
            'category': self.name_en,
            'category_zh': self.name_zh,
            'subcategory': self.subcategory,
            'subcategory_zh': self.subcategory_zh,
            'full_category': self.get_full_name_en(),
            'full_category_zh': self.get_full_name_zh()
        } 