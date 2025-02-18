# ucs_parser.py

import os
import sys
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import csv
import time

# 添加依赖检查和安装
try:
    import pandas as pd
except ImportError:
    try:
        import subprocess
        print("正在安装必要的依赖包 pandas，请稍候...")
        
        # 使用当前 Python 解释器的路径安装
        python_executable = sys.executable
        subprocess.check_call([python_executable, "-m", "pip", "install", "pandas", "openpyxl"])
        
        # 重新导入
        import pandas as pd
        
    except Exception as e:
        error_msg = (f"无法安装必要的依赖包: {str(e)}\n"
                    f"请手动运行: {python_executable} -m pip install pandas openpyxl")
        print(error_msg)
        raise

class UCSParser:
    """UCS 标准解析器,用于处理 UCS v8.2.1 的分类和翻译"""
    
    def __init__(self, data_dir=None):
        # 配置日志
        self.logger = logging.getLogger('UCSParser')
        self.logger.setLevel(logging.DEBUG)
        
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
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent / "data"
        self.categories_file = self.data_dir / "_categorylist.csv"
        self.translations_file = self.data_dir / "ucs_translations.csv"
        
        # 主缓存
        self._categories_cache = {}
        self._translations_cache = {}
        
        # 二级缓存（用于快速查找）
        self._name_to_id_cache = {}  # 名称到ID的映射
        self._synonym_to_id_cache = {}  # 同义词到ID的映射
        self._subcategory_to_id_cache = {}  # 子类别到ID的映射
        
        # 初始化
        start_time = time.time()
        self._init_data()
        self._load_data()
        self._stats['load_time'] = time.time() - start_time
        
        self.logger.info(f"初始化完成，加载耗时: {self._stats['load_time']:.2f}秒")
        self.logger.info(f"已加载 {len(self._categories_cache)} 个分类")
        self.logger.info(f"已加载 {len(self._translations_cache)} 个翻译")
    
    def _init_data(self):
        """初始化基础数据"""
        try:
            if not self.categories_file.exists():
                raise FileNotFoundError(f"分类文件不存在: {self.categories_file}")
            
            if not self.translations_file.exists():
                self.logger.warning(f"翻译文件不存在，将创建新文件: {self.translations_file}")
                with open(self.translations_file, 'w', encoding='utf-8') as f:
                    f.write("source,target\n")
                    
        except Exception as e:
            self.logger.error(f"初始化数据失败: {str(e)}")
            raise
    
    def _load_data(self):
        """加载所有数据"""
        try:
            # 读取分类数据
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
                            self.logger.warning(f"第{row_num}行: 跳过空的CatID")
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
                        
                        # 记录详细日志
                        self.logger.debug(f"加载分类: {cat_id}")
                        self.logger.debug(f"  - 英文名称: {category_data['name']}")
                        self.logger.debug(f"  - 中文名称: {category_data['name_zh']}")
                        self.logger.debug(f"  - 同义词: {synonyms}")
                        self.logger.debug(f"  - 中文同义词: {synonyms_zh}")
                        
                    except Exception as e:
                        self.logger.error(f"处理第{row_num}行时出错: {str(e)}")
                        continue
            
            # 读取翻译数据
            self._load_translations()
            
        except Exception as e:
            self.logger.error(f"加载数据失败: {str(e)}")
            raise
    
    def _parse_synonyms(self, synonyms_str: str) -> list:
        """解析英文同义词"""
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
    
    def _parse_synonyms_zh(self, synonyms_str: str) -> list:
        """解析中文同义词"""
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
    
    def _update_secondary_caches(self, cat_id: str, category_data: dict):
        """更新二级缓存"""
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
    
    def _load_translations(self):
        """加载翻译数据"""
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
                                self.logger.warning(f"第{row_num}行: 跳过空的翻译")
                                continue
                            
                            self._translations_cache[source] = target
                            
                            # 添加单词变体（只处理英文单词）
                            if source.isascii():
                                self._add_word_variants(source, target)
                            
                            self.logger.debug(f"加载翻译: {source} -> {target}")
                            
                        except Exception as e:
                            self.logger.error(f"处理翻译第{row_num}行时出错: {str(e)}")
                            continue
                            
        except Exception as e:
            self.logger.error(f"加载翻译数据失败: {str(e)}")
            raise
    
    def _add_word_variants(self, source: str, target: str):
        """添加单词变体到翻译缓存"""
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
    
    def get_category(self, cat_id: str) -> Optional[dict]:
        """获取分类信息"""
        self._stats['total_queries'] += 1
        cat_id = cat_id.upper()
        
        if cat_id in self._categories_cache:
            self._stats['cache_hits'] += 1
            return self._categories_cache[cat_id]
        
        self._stats['cache_misses'] += 1
        return None
    
    def get_translation(self, text: str) -> Optional[str]:
        """获取翻译"""
        self._stats['total_queries'] += 1
        text = text.lower()
        
        if text in self._translations_cache:
            self._stats['translation_hits'] += 1
            return self._translations_cache[text]
        
        self._stats['translation_misses'] += 1
        return None
    
    def add_translation(self, source: str, target: str):
        """添加新的翻译"""
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
            
            self.logger.info(f"添加新翻译: {source} -> {target}")
            
        except Exception as e:
            self.logger.error(f"添加翻译失败: {str(e)}")
            raise
    
    def get_stats(self) -> dict:
        """获取性能统计信息"""
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
            'translation_hit_rate': f"{translation_hit_rate:.2f}%"
        }
    
    def __str__(self) -> str:
        """返回解析器状态的字符串表示"""
        stats = self.get_stats()
        return (
            f"UCS解析器状态:\n"
            f"- 加载耗时: {stats['load_time']:.2f}秒\n"
            f"- 分类数量: {len(self._categories_cache)}\n"
            f"- 翻译数量: {len(self._translations_cache)}\n"
            f"- 缓存命中率: {stats['cache_hit_rate']}\n"
            f"- 翻译命中率: {stats['translation_hit_rate']}"
        )
