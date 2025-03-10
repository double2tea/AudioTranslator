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
        """解析英文同义词字符串"""
        if not synonyms_str:
            return []
            
        try:
            # 尝试解析为JSON
            if synonyms_str.startswith('[') and synonyms_str.endswith(']'):
                try:
                    import json
                    return json.loads(synonyms_str)
                except json.JSONDecodeError:
                    logging.warning(f"解析同义词JSON失败: {synonyms_str}")
                    
            # 如果不是JSON格式，按逗号分割
            if ',' in synonyms_str:
                return [s.strip() for s in synonyms_str.split(',') if s.strip()]
                
            # 如果没有逗号，按空格分割
            return [s.strip() for s in synonyms_str.split() if s.strip()]
                
        except Exception as e:
            logging.error(f"解析英文同义词失败: {e}, 原始数据: {synonyms_str}")
            return []

    def _parse_synonyms_zh(self, synonyms_str: str) -> List[str]:
        """解析中文同义词字符串"""
        if not synonyms_str:
            return []
            
        try:
            # 尝试解析为JSON
            if synonyms_str.startswith('[') and synonyms_str.endswith(']'):
                try:
                    import json
                    return json.loads(synonyms_str)
                except json.JSONDecodeError:
                    logging.warning(f"解析中文同义词JSON失败: {synonyms_str}")
                    
            # 如果不是JSON格式，按逗号分割
            if ',' in synonyms_str:
                return [s.strip() for s in synonyms_str.split(',') if s.strip()]
                
            # 如果没有逗号，按空格分割
            return [s.strip() for s in synonyms_str.split() if s.strip()]
                
        except Exception as e:
            logging.error(f"解析中文同义词失败: {e}, 原始数据: {synonyms_str}")
            return []

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
        根据分类名称查找分类信息
        
        Args:
            name: 分类名称
            
        Returns:
            分类信息，如果找不到则返回None
        """
        # 先尝试精确匹配
        for cat_id, cat_info in self._categories_cache.items():
            if cat_info.get('name') == name or cat_info.get('name_zh') == name:
                return cat_info
        
        # 尝试不区分大小写的匹配
        name_lower = name.lower()
        for cat_id, cat_info in self._categories_cache.items():
            if cat_info.get('name', '').lower() == name_lower or cat_info.get('name_zh', '') == name:
                return cat_info
        
        # 没有找到匹配项
        return None
        
    def guess_category(self, text: str) -> str:
        """
        根据文本内容猜测最匹配的分类ID
        
        Args:
            text: 需要分类的文本，通常是文件名或关键词
            
        Returns:
            最匹配的分类ID，如果未找到合适分类则返回"SFXMisc"
        """
        if not text or not self._categories_cache:
            return "SFXMisc"
            
        # 清理和处理输入文本
        text = text.lower()
        words = text.split()
        
        # 评分结果格式: {cat_id: score}
        scores = {}
        
        # 对每个分类进行评分
        for cat_id, cat_info in self._categories_cache.items():
            score = 0
            
            # 获取分类和子分类名称
            category = cat_info.get('name', '').lower()
            subcategory = cat_info.get('subcategory', '').lower()
            
            # 获取同义词
            synonyms = cat_info.get('synonyms', [])
            synonyms = [s.lower() for s in synonyms]
            
            # 中文名称
            category_zh = cat_info.get('name_zh', '')
            subcategory_zh = cat_info.get('subcategory_zh', '')
            
            # 1. 检查分类名称完全匹配
            if category in words:
                score += 25
                
                # 如果是第一个词，加分
                if words and words[0] == category:
                    score += 10
            
            # 2. 检查子分类名称完全匹配
            if subcategory and subcategory in words:
                score += 35
                
                # 如果分类和子分类都匹配且顺序正确
                if category in words:
                    idx_cat = words.index(category)
                    idx_sub = words.index(subcategory)
                    if idx_sub > idx_cat:
                        score += 20  # 顺序正确加分
            
            # 3. 检查同义词匹配
            for synonym in synonyms:
                if synonym in words:
                    score += 15
                    break
            
            # 4. 检查中文匹配
            if category_zh and any(category_zh in word for word in words):
                score += 10
            
            if subcategory_zh and any(subcategory_zh in word for word in words):
                score += 15
            
            # 5. 检查部分匹配
            for word in words:
                # 部分匹配分类名称
                if len(word) > 3 and word in category:
                    score += 5
                
                # 部分匹配子分类名称
                if subcategory and len(word) > 3 and word in subcategory:
                    score += 8
                
                # 部分匹配同义词
                for synonym in synonyms:
                    if len(word) > 3 and word in synonym:
                        score += 3
                        break
            
            # 记录得分
            scores[cat_id] = score
        
        # 找出得分最高的分类
        best_cat_id = max(scores.items(), key=lambda x: x[1])[0] if scores else "SFXMisc"
        
        # 如果最高分太低，返回默认分类
        if scores.get(best_cat_id, 0) < 10:
            return "SFXMisc"
            
        return best_cat_id 