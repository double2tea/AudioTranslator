"""
分类服务模块

此模块提供了音效文件分类的管理和操作功能。
CategoryService 作为服务层组件，提供了分类数据的加载、查询、匹配和管理功能。
"""

import os
import logging
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Set
from collections import defaultdict
from functools import lru_cache

from ...core.base_service import BaseService
from ...core.service_factory import ServiceFactory
from .category import Category
from .category_utils import (
    normalize_text, 
    calculate_text_similarity, 
    calculate_category_match_score,
    filter_categories_by_keyword,
    create_category_path
)

# 设置日志记录器
logger = logging.getLogger(__name__)

class CategoryService(BaseService):
    """
    分类服务
    
    提供音效文件分类的管理和操作功能，包括分类数据的加载、查询、匹配和管理。
    主要功能：
    - 加载和保存分类数据
    - 分类查询和过滤
    - 根据文件名智能猜测分类
    - 分类路径创建和管理
    - 提供命名规则所需的分类字段
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化分类服务
        
        Args:
            config: 服务配置
        """
        super().__init__('category_service', config)
        
        # 分类数据存储
        self.categories: Dict[str, Category] = {}
        
        # 数据目录和文件路径
        self.data_dir = None
        self.categories_file = None
        
        # 匹配缓存
        self._match_cache: Dict[str, str] = {}
        
        # 评分规则常量
        self.SCORE_RULES = {
            'EXACT_CATEGORY_SUBCATEGORY': 110,  # 精确匹配分类和子分类
            'EXACT_CATEGORY_SUBCATEGORY_REVERSE': 100,  # 精确匹配分类和子分类（反序）
            'EXACT_SUBCATEGORY_SYNONYM': 90,  # 精确匹配子分类同义词
            'EXACT_CATEGORY_SYNONYM': 60,  # 精确匹配分类同义词
            'PARTIAL_SUBCATEGORY': 40,  # 部分匹配子分类
            'PARTIAL_CATEGORY': 25,  # 部分匹配分类
            'PARTIAL_SYNONYM': 30,  # 部分匹配同义词
            'CHINESE_MATCH': 15,  # 中文匹配
            'POSITION_FIRST_WORD': 20,  # 首词匹配加分
            'POSITION_EXACT_ORDER': 10,  # 精确顺序匹配加分
        }
    
    def initialize(self) -> bool:
        """
        初始化服务
        
        加载配置和分类数据
        
        Returns:
            初始化是否成功
        """
        try:
            # 初始化路径配置
            self._initialize_paths()
            
            # 加载分类数据
            self._load_categories()
            
            # 初始化成功
            self.is_initialized = True
            logger.info("分类服务初始化成功")
            return True
        except Exception as e:
            logger.error(f"分类服务初始化失败: {e}")
            return False
    
    def _initialize_paths(self):
        """初始化路径配置"""
        # 获取ConfigService进行路径配置
        try:
            config_service = ServiceFactory.get_instance().get_service('config_service')
            if config_service:
                self.data_dir = Path(config_service.get_data_dir())
                self.categories_file = self.data_dir / "categories" / "_categorylist.csv"
                # 确保目录存在
                os.makedirs(self.data_dir / "categories", exist_ok=True)
            else:
                # 默认路径
                self.data_dir = Path('data')
                self.categories_file = self.data_dir / "categories" / "_categorylist.csv"
                # 确保目录存在
                os.makedirs(self.data_dir / "categories", exist_ok=True)
                
            logger.debug(f"分类文件路径: {self.categories_file}")
        except Exception as e:
            logger.error(f"初始化路径配置失败: {e}")
            # 使用默认路径
            self.data_dir = Path('data')
            self.categories_file = self.data_dir / "categories" / "_categorylist.csv"
            # 确保目录存在
            os.makedirs(self.data_dir / "categories", exist_ok=True)
    
    def _load_categories(self):
        """从CSV文件加载分类数据"""
        if not self.categories_file or not self.categories_file.exists():
            logger.warning(f"分类文件不存在: {self.categories_file}")
            return
        
        try:
            self.categories.clear()
            
            with open(self.categories_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 创建Category对象并添加到字典
                    cat = Category.from_dict(row)
                    self.categories[cat.cat_id] = cat
            
            logger.info(f"成功加载 {len(self.categories)} 个分类")
        except Exception as e:
            logger.error(f"加载分类数据失败: {e}")
            self.categories = {}
    
    def save_categories(self) -> bool:
        """
        保存分类数据到CSV文件
        
        Returns:
            保存是否成功
        """
        if not self.categories_file:
            logger.error("未设置分类文件路径")
            return False
        
        try:
            # 确保目录存在
            os.makedirs(self.categories_file.parent, exist_ok=True)
            
            with open(self.categories_file, 'w', encoding='utf-8', newline='') as f:
                # 定义CSV字段
                fields = ['CatID', 'Category', 'Category_zh', 'subcategory', 'subcategory_zh', 'synonyms_en', 'synonyms_zh']
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                
                # 写入分类数据
                for cat in self.categories.values():
                    row_dict = cat.to_dict()
                    # 处理列表类型数据为CSV兼容格式
                    row_dict['synonyms_en'] = json.dumps(row_dict['synonyms_en'], ensure_ascii=False)
                    row_dict['synonyms_zh'] = json.dumps(row_dict['synonyms_zh'], ensure_ascii=False)
                    writer.writerow(row_dict)
            
            logger.info(f"成功保存 {len(self.categories)} 个分类到 {self.categories_file}")
            return True
        except Exception as e:
            logger.error(f"保存分类数据失败: {e}")
            return False
    
    def get_all_categories(self) -> Dict[str, Category]:
        """
        获取所有分类
        
        Returns:
            分类字典，键为分类ID，值为分类对象
        """
        return self.categories.copy()
    
    def get_category(self, cat_id: str) -> Optional[Category]:
        """
        获取指定分类
        
        Args:
            cat_id: 分类ID
            
        Returns:
            分类对象，不存在则返回None
        """
        return self.categories.get(cat_id)
    
    def add_category(self, category: Category) -> bool:
        """
        添加分类
        
        Args:
            category: 分类对象
            
        Returns:
            添加是否成功
        """
        try:
            # 检查分类ID是否已存在
            if category.cat_id in self.categories:
                logger.warning(f"分类ID已存在: {category.cat_id}")
                return False
            
            # 添加分类
            self.categories[category.cat_id] = category
            
            # 保存分类数据
            self.save_categories()
            
            logger.info(f"成功添加分类: {category.cat_id}")
            return True
        except Exception as e:
            logger.error(f"添加分类失败: {e}")
            return False
    
    def update_category(self, cat_id: str, category: Category) -> bool:
        """
        更新分类
        
        Args:
            cat_id: 要更新的分类ID
            category: 新的分类对象
            
        Returns:
            更新是否成功
        """
        try:
            # 检查分类ID是否存在
            if cat_id not in self.categories:
                logger.warning(f"分类ID不存在: {cat_id}")
                return False
            
            # 更新分类
            self.categories[cat_id] = category
            
            # 如果分类ID发生变化，需要处理
            if cat_id != category.cat_id:
                # 删除旧的ID
                del self.categories[cat_id]
                # 添加新的ID
                self.categories[category.cat_id] = category
            
            # 保存分类数据
            self.save_categories()
            
            # 清除匹配缓存
            self._match_cache.clear()
            
            logger.info(f"成功更新分类: {cat_id} -> {category.cat_id}")
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
            # 检查分类ID是否存在
            if cat_id not in self.categories:
                logger.warning(f"分类ID不存在: {cat_id}")
                return False
            
            # 删除分类
            del self.categories[cat_id]
            
            # 保存分类数据
            self.save_categories()
            
            # 清除匹配缓存
            self._match_cache.clear()
            
            logger.info(f"成功删除分类: {cat_id}")
            return True
        except Exception as e:
            logger.error(f"删除分类失败: {e}")
            return False
    
    def filter_categories(self, keyword: str) -> Dict[str, Category]:
        """
        根据关键字过滤分类
        
        Args:
            keyword: 关键字
            
        Returns:
            过滤后的分类字典
        """
        return filter_categories_by_keyword(self.categories, keyword)
    
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
        
        # 如果没有分类数据，返回默认分类
        if not self.categories:
            return 'OTHER'
        
        # 规范化文件名
        filename_lower = normalize_text(filename)
        
        best_match = None
        max_score = 0
        
        # 遍历所有分类
        for cat_id, category in self.categories.items():
            # 计算分数
            score, reasons = calculate_category_match_score(filename, category)
            
            # 更新最佳匹配
            if score > max_score:
                max_score = score
                best_match = cat_id
                logger.debug(f"新的最佳匹配: {cat_id}, 分数: {score}, 原因: {reasons}")
        
        # 如果找到匹配
        if best_match:
            # 缓存结果
            self._match_cache[filename] = best_match
            return best_match
        
        # 如果没有匹配，返回默认分类
        return 'OTHER'
    
    def get_naming_fields(self, cat_id: str) -> Dict[str, Any]:
        """
        获取用于命名的分类字段
        
        Args:
            cat_id: 分类ID
            
        Returns:
            包含命名所需字段的字典
        """
        # 如果是默认分类或找不到分类
        if cat_id == 'OTHER' or cat_id not in self.categories:
            return {
                'category_id': 'OTHER',
                'category': 'Other',
                'category_zh': '其他',
                'full_category': 'Other',
                'full_category_zh': '其他'
            }
        
        # 获取分类对象
        category = self.categories[cat_id]
        
        # 返回命名字段
        return category.get_naming_fields()
    
    def guess_category_with_fields(self, filename: str) -> Dict[str, Any]:
        """
        猜测分类并返回命名所需字段
        
        Args:
            filename: 文件名
            
        Returns:
            包含命名所需字段的字典
        """
        cat_id = self.guess_category(filename)
        return self.get_naming_fields(cat_id)
    
    def create_category_directories(self, base_path: str) -> bool:
        """
        创建分类目录结构
        
        Args:
            base_path: 基础路径
            
        Returns:
            创建是否成功
        """
        try:
            # 确保基础路径存在
            os.makedirs(base_path, exist_ok=True)
            
            # 获取所有一级分类ID
            top_level_cats = {cat_id.split('_')[0] for cat_id in self.categories.keys()}
            
            # 创建一级分类目录
            for top_cat in top_level_cats:
                os.makedirs(os.path.join(base_path, top_cat), exist_ok=True)
            
            # 创建二级分类目录
            for cat_id in self.categories.keys():
                cat_path = create_category_path(cat_id, base_path)
                os.makedirs(cat_path, exist_ok=True)
            
            logger.info(f"成功创建分类目录结构: {base_path}")
            return True
        except Exception as e:
            logger.error(f"创建分类目录结构失败: {e}")
            return False
    
    def get_category_path(self, cat_id: str, base_path: str) -> str:
        """
        获取分类路径
        
        Args:
            cat_id: 分类ID
            base_path: 基础路径
            
        Returns:
            分类路径
        """
        return create_category_path(cat_id, base_path)
    
    def move_file_to_category(self, file_path: str, cat_id: str, base_path: str) -> Optional[str]:
        """
        将文件移动到分类目录
        
        Args:
            file_path: 文件路径
            cat_id: 分类ID
            base_path: 基础路径
            
        Returns:
            移动后的文件路径，失败则返回None
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return None
            
            # 获取分类路径
            cat_path = self.get_category_path(cat_id, base_path)
            
            # 确保分类目录存在
            os.makedirs(cat_path, exist_ok=True)
            
            # 构建目标路径
            file_name = os.path.basename(file_path)
            target_path = os.path.join(cat_path, file_name)
            
            # 检查目标文件是否已存在
            if os.path.exists(target_path):
                logger.warning(f"目标文件已存在: {target_path}")
                # 添加数字后缀
                name, ext = os.path.splitext(file_name)
                counter = 1
                while os.path.exists(target_path):
                    target_path = os.path.join(cat_path, f"{name}_{counter}{ext}")
                    counter += 1
            
            # 移动文件
            import shutil
            shutil.move(file_path, target_path)
            
            logger.info(f"成功移动文件: {file_path} -> {target_path}")
            return target_path
        except Exception as e:
            logger.error(f"移动文件失败: {e}")
            return None
    
    def get_categories_for_ui(self, search_term: str = "", language: str = "zh") -> List[Dict[str, Any]]:
        """
        获取用于UI显示的分类列表
        
        Args:
            search_term: 搜索关键字
            language: 语言，'zh'表示中文，其他表示英文
            
        Returns:
            分类列表，每项包含UI显示所需的字段
        """
        # 过滤分类
        filtered_categories = self.filter_categories(search_term) if search_term else self.categories
        
        # 构建UI数据
        ui_categories = []
        for cat_id, category in filtered_categories.items():
            ui_categories.append({
                'id': cat_id,
                'display_name': category.get_display_name(language),
                'name_en': category.name_en,
                'name_zh': category.name_zh,
                'subcategory': category.subcategory,
                'subcategory_zh': category.subcategory_zh,
                'synonyms_en': category.synonyms_en,
                'synonyms_zh': category.synonyms_zh
            })
        
        # 按ID排序
        ui_categories.sort(key=lambda x: x['id'])
        
        return ui_categories 