"""
UCS服务模块

此模块提供UCS标准解析服务，用于处理UCS v8.2.1的分类和翻译。
服务提供分类查询、翻译查询和翻译添加等功能。
"""

import os
import sys
import logging
import time
import csv
from pathlib import Path
from typing import Dict, List, Optional, Any

from ...core.base_service import BaseService

class UCSService(BaseService):
    """
    UCS服务类

    提供UCS标准解析功能，包括分类查询、翻译查询和翻译添加等服务。
    支持多语言分类和翻译，主要用于处理UCS v8.2.1标准。

    Attributes:
        data_dir: 数据目录
        categories_file: 分类文件路径
        translations_file: 翻译文件路径
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化UCS服务

        Args:
            config: 服务配置
        """
        super().__init__("ucs_service", config)
        
        # 性能统计
        self._stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'translation_hits': 0,
            'translation_misses': 0,
            'load_time': 0,
            'total_queries': 0
        }
        
        # 如果没有提供data_dir，使用默认路径
        self.data_dir = None
        self.categories_file = None
        self.translations_file = None
        
        # 主缓存
        self._categories_cache = {}
        self._translations_cache = {}
        
        # 二级缓存（用于快速查找）
        self._name_to_id_cache = {}    # 名称到ID的映射
        self._synonym_to_id_cache = {} # 同义词到ID的映射
        self._subcategory_to_id_cache = {} # 子类别到ID的映射

    def initialize(self) -> bool:
        """
        初始化UCS服务

        加载分类和翻译数据，建立缓存。

        Returns:
            初始化是否成功
        """
        try:
            # 设置数据目录
            if 'data_dir' in self.config:
                self.data_dir = Path(self.config['data_dir'])
            else:
                # 使用默认路径
                self.data_dir = Path(os.getcwd()) / "data"
            
            self.categories_file = self.data_dir / "_categorylist.csv"
            self.translations_file = self.data_dir / "ucs_translations.csv"
            
            # 初始化基础数据
            if not self._init_data():
                return False
            
            # 加载数据
            start_time = time.time()
            if not self._load_data():
                return False
            self._stats['load_time'] = time.time() - start_time
            
            logging.info(f"UCS服务初始化完成，加载耗时: {self._stats['load_time']:.2f}秒")
            logging.info(f"已加载 {len(self._categories_cache)} 个分类")
            logging.info(f"已加载 {len(self._translations_cache)} 个翻译")
            
            self.is_initialized = True
            return True
            
        except Exception as e:
            logging.error(f"初始化UCS服务失败: {str(e)}")
            self.is_initialized = False
            return False

    def _init_data(self) -> bool:
        """
        初始化基础数据
        
        检查数据文件是否存在，如不存在则创建。
        
        Returns:
            初始化是否成功
        """
        try:
            if not self.data_dir.exists():
                self.data_dir.mkdir(parents=True, exist_ok=True)
                logging.info(f"创建数据目录: {self.data_dir}")
            
            if not self.categories_file.exists():
                logging.error(f"分类文件不存在: {self.categories_file}")
                return False
            
            if not self.translations_file.exists():
                logging.warning(f"翻译文件不存在，将创建新文件: {self.translations_file}")
                with open(self.translations_file, 'w', encoding='utf-8') as f:
                    f.write("source,target\n")
            
            return True
                    
        except Exception as e:
            logging.error(f"初始化基础数据失败: {str(e)}")
            return False

    def _load_data(self) -> bool:
        """
        加载所有数据
        
        加载分类和翻译数据，建立主缓存和二级缓存。
        
        Returns:
            加载是否成功
        """
        try:
            # 读取分类数据
            if not self._load_categories():
                return False
            
            # 读取翻译数据
            if not self._load_translations():
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"加载数据失败: {str(e)}")
            return False

    def _load_categories(self) -> bool:
        """
        加载分类数据
        
        从CSV文件加载分类数据，建立主缓存和二级缓存。
        
        Returns:
            加载是否成功
        """
        try:
            with open(self.categories_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # 验证必需的列
                required_columns = {'CatID', 'Category', 'Category_zh', 'SubCategory', 'SubCategory_zh'}
                columns = set(reader.fieldnames)
                missing_columns = required_columns - columns
                if missing_columns:
                    raise ValueError(f"CSV文件缺少必需的列: {', '.join(missing_columns)}")
                
                for row_num, row in enumerate(reader, start=2):  # 从2开始计数（考虑标题行）
                    try:
                        # 标准化CatID（转换为大写）
                        cat_id = row['CatID'].strip().upper()
                        if not cat_id:
                            logging.warning(f"第{row_num}行: 跳过空的CatID")
                            continue
                        
                        # 处理同义词
                        synonyms = self._parse_synonyms(row.get('Synonyms - Comma Separated', ''))
                        synonyms_zh = self._parse_synonyms_zh(row.get('Synonyms_zh', ''))
                        
                        # 构建分类数据
                        category_data = {
                            'name': row['Category'].strip(),
                            'name_zh': row['Category_zh'].strip(),
                            'subcategory': row['SubCategory'].strip(),
                            'subcategory_zh': row['SubCategory_zh'].strip(),
                            'synonyms': synonyms,
                            'synonyms_zh': synonyms_zh
                        }
                        
                        # 更新主缓存
                        self._categories_cache[cat_id] = category_data
                        
                        # 更新二级缓存
                        self._update_secondary_caches(cat_id, category_data)
                        
                    except Exception as e:
                        logging.error(f"处理分类第{row_num}行时出错: {str(e)}")
                        continue
            
            return True
            
        except Exception as e:
            logging.error(f"加载分类数据失败: {str(e)}")
            return False

    def _parse_synonyms(self, synonyms_str: str) -> List[str]:
        """
        解析英文同义词
        
        Args:
            synonyms_str: 同义词字符串，多个同义词用分隔符分隔
            
        Returns:
            同义词列表
        """
        synonyms = []
        if synonyms_str.strip():
            # 支持多种分隔符
            for sep in [',', ';', '|']:
                if sep in synonyms_str:
                    synonyms.extend([s.strip().lower() for s in synonyms_str.split(sep) if s.strip()])
                    break
            else:
                synonyms = [synonyms_str.strip().lower()]
        return list(dict.fromkeys(synonyms))  # 去重

    def _parse_synonyms_zh(self, synonyms_str: str) -> List[str]:
        """
        解析中文同义词
        
        Args:
            synonyms_str: 同义词字符串，多个同义词用分隔符分隔
            
        Returns:
            同义词列表
        """
        synonyms = []
        if synonyms_str.strip():
            # 支持多种中文分隔符
            for sep in ['、', '，', '|']:
                if sep in synonyms_str:
                    synonyms.extend([s.strip() for s in synonyms_str.split(sep) if s.strip()])
                    break
            else:
                synonyms = [synonyms_str.strip()]
        return list(dict.fromkeys(synonyms))  # 去重

    def _update_secondary_caches(self, cat_id: str, category_data: Dict[str, Any]):
        """
        更新二级缓存
        
        Args:
            cat_id: 分类ID
            category_data: 分类数据
        """
        # 名称映射
        self._name_to_id_cache[category_data['name'].lower()] = cat_id
        self._name_to_id_cache[category_data['name_zh']] = cat_id
        
        # 子类别映射
        self._subcategory_to_id_cache[category_data['subcategory'].lower()] = cat_id
        self._subcategory_to_id_cache[category_data['subcategory_zh']] = cat_id
        
        # 同义词映射
        for synonym in category_data['synonyms']:
            self._synonym_to_id_cache[synonym.lower()] = cat_id
        for synonym in category_data['synonyms_zh']:
            self._synonym_to_id_cache[synonym] = cat_id

    def _load_translations(self) -> bool:
        """
        加载翻译数据
        
        从CSV文件加载翻译数据，建立翻译缓存。
        
        Returns:
            加载是否成功
        """
        try:
            if self.translations_file.exists():
                with open(self.translations_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    
                    if set(reader.fieldnames) != {'source', 'target'}:
                        raise ValueError("翻译文件格式错误，应包含'source'和'target'列")
                    
                    for row_num, row in enumerate(reader, start=2):
                        try:
                            source = row['source'].strip().lower()
                            target = row['target'].strip()
                            
                            if not source or not target:
                                logging.warning(f"第{row_num}行: 跳过空的翻译")
                                continue
                            
                            self._translations_cache[source] = target
                            
                            # 添加单词变体（只处理英文单词）
                            if source.isascii():
                                self._add_word_variants(source, target)
                                
                        except Exception as e:
                            logging.error(f"处理翻译第{row_num}行时出错: {str(e)}")
                            continue
            
            return True
                            
        except Exception as e:
            logging.error(f"加载翻译数据失败: {str(e)}")
            return False

    def _add_word_variants(self, source: str, target: str):
        """
        添加单词变体到翻译缓存
        
        处理常见的单词变化形式，如复数、进行时、过去时等。
        
        Args:
            source: 源单词
            target: 目标翻译
        """
        # 处理常见的单词变化形式
        if source.endswith('s'):
            self._translations_cache[source[:-1]] = target
        if source.endswith('ing'):
            self._translations_cache[source[:-3]] = target
            if len(source) > 4 and source[-4] == source[-5]:  # 处理双写字母，如running->run
                self._translations_cache[source[:-4]] = target
        if source.endswith('ed'):
            self._translations_cache[source[:-2]] = target
            if len(source) > 3 and source[-3] == source[-4]:  # 处理双写字母，如stopped->stop
                self._translations_cache[source[:-3]] = target

    def get_category(self, cat_id: str) -> Optional[Dict[str, Any]]:
        """
        获取分类信息
        
        根据分类ID获取分类详细信息。
        
        Args:
            cat_id: 分类ID
            
        Returns:
            分类信息，如果不存在则返回None
        """
        self._stats['total_queries'] += 1
        cat_id = cat_id.upper()
        
        if cat_id in self._categories_cache:
            self._stats['cache_hits'] += 1
            return self._categories_cache[cat_id]
        
        self._stats['cache_misses'] += 1
        return None

    def get_translation(self, text: str) -> Optional[str]:
        """
        获取翻译
        
        根据源文本获取目标翻译。
        
        Args:
            text: 源文本
            
        Returns:
            目标翻译，如果不存在则返回None
        """
        self._stats['total_queries'] += 1
        text = text.lower()
        
        if text in self._translations_cache:
            self._stats['translation_hits'] += 1
            return self._translations_cache[text]
        
        self._stats['translation_misses'] += 1
        return None

    def add_translation(self, source: str, target: str) -> bool:
        """
        添加新的翻译
        
        将新的翻译添加到缓存和文件中。
        
        Args:
            source: 源文本
            target: 目标翻译
            
        Returns:
            添加是否成功
        """
        try:
            if not source or not target:
                raise ValueError("源文本和目标文本不能为空")
            
            source = source.lower().strip()
            target = target.strip()
            
            # 更新缓存
            self._translations_cache[source] = target
            
            # 添加单词变体
            if source.isascii():
                self._add_word_variants(source, target)
            
            # 更新文件
            with open(self.translations_file, 'a', encoding='utf-8') as f:
                f.write(f"{source},{target}\n")
            
            logging.info(f"添加新翻译: {source} -> {target}")
            return True
            
        except Exception as e:
            logging.error(f"添加翻译失败: {str(e)}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        获取性能统计信息
        
        Returns:
            性能统计信息
        """
        total_queries = self._stats['total_queries']
        if total_queries > 0:
            cache_hit_rate = (self._stats['cache_hits'] / total_queries) * 100
            translation_hit_rate = (self._stats['translation_hits'] / total_queries) * 100
        else:
            cache_hit_rate = 0
            translation_hit_rate = 0
            
        return {
            **self._stats,
            'cache_hit_rate': f"{cache_hit_rate:.2f}%",
            'translation_hit_rate': f"{translation_hit_rate:.2f}%",
            'categories_count': len(self._categories_cache),
            'translations_count': len(self._translations_cache)
        }

    def shutdown(self) -> bool:
        """
        关闭UCS服务
        
        清理资源，关闭服务。
        
        Returns:
            关闭是否成功
        """
        try:
            # 清空缓存
            self._categories_cache.clear()
            self._translations_cache.clear()
            self._name_to_id_cache.clear()
            self._synonym_to_id_cache.clear()
            self._subcategory_to_id_cache.clear()
            
            # 重置统计信息
            self._stats = {
                'cache_hits': 0,
                'cache_misses': 0,
                'translation_hits': 0,
                'translation_misses': 0,
                'load_time': 0,
                'total_queries': 0
            }
            
            logging.info("UCS服务已关闭")
            self.is_initialized = False
            return True
            
        except Exception as e:
            logging.error(f"关闭UCS服务失败: {str(e)}")
            return False

    def find_category_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        根据名称查找分类
        
        支持英文名称、中文名称和同义词查找。
        
        Args:
            name: 分类名称
            
        Returns:
            分类信息，如果不存在则返回None
        """
        name = name.lower() if name.isascii() else name
        
        # 直接从名称缓存查找
        if name in self._name_to_id_cache:
            cat_id = self._name_to_id_cache[name]
            return self.get_category(cat_id)
        
        # 从同义词缓存查找
        if name in self._synonym_to_id_cache:
            cat_id = self._synonym_to_id_cache[name]
            return self.get_category(cat_id)
        
        # 从子类别缓存查找
        if name in self._subcategory_to_id_cache:
            cat_id = self._subcategory_to_id_cache[name]
            return self.get_category(cat_id)
        
        return None 