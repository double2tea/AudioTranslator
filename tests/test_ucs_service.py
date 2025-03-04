#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UCSService 测试模块

测试UCSService的各项功能，包括：
- 初始化和关闭
- 分类查询
- 翻译查询
- 翻译添加
"""

import unittest
import os
import sys
import logging
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到模块搜索路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.audio_translator.services.ucs_service import UCSService

# 配置日志
logging.basicConfig(level=logging.DEBUG)


class TestUCSService(unittest.TestCase):
    """UCSService 测试类"""

    def setUp(self):
        """测试前设置"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建测试数据文件
        self.create_test_files()
        
        # 创建 UCSService 实例
        config = {"data_dir": str(self.data_dir)}
        self.ucs_service = UCSService(config)
        
        # 初始化服务
        result = self.ucs_service.initialize()
        self.assertTrue(result, "初始化 UCSService 失败")

    def tearDown(self):
        """测试后清理"""
        # 关闭服务
        self.ucs_service.shutdown()
        
        # 删除临时目录
        shutil.rmtree(self.temp_dir)

    def create_test_files(self):
        """创建测试数据文件"""
        # 创建分类文件
        categories_content = (
            "CatID,Category,Category_zh,SubCategory,SubCategory_zh,Synonyms - Comma Separated,Synonyms_zh\n"
            "AA01,Fruit,水果,Apple,苹果,apple|fruit,苹果|水果\n"
            "AA02,Fruit,水果,Banana,香蕉,banana,香蕉\n"
            "BB01,Vehicle,交通工具,Car,汽车,car|automobile,汽车|轿车\n"
            "BB02,Vehicle,交通工具,Bus,公交车,bus,公共汽车|巴士\n"
        )
        
        category_file = self.data_dir / "_categorylist.csv"
        with open(category_file, 'w', encoding='utf-8') as f:
            f.write(categories_content)
        
        # 创建翻译文件
        translations_content = (
            "source,target\n"
            "apple,苹果\n"
            "fruit,水果\n"
            "banana,香蕉\n"
            "car,汽车\n"
            "bus,公交车\n"
        )
        
        translations_file = self.data_dir / "ucs_translations.csv"
        with open(translations_file, 'w', encoding='utf-8') as f:
            f.write(translations_content)

    def test_category_query(self):
        """测试分类查询"""
        # 测试通过ID查询
        category = self.ucs_service.get_category("AA01")
        self.assertIsNotNone(category, "未找到分类 AA01")
        self.assertEqual(category['name'], "Fruit", "分类名称不匹配")
        self.assertEqual(category['subcategory'], "Apple", "子分类名称不匹配")
        
        # 测试通过名称查询
        category = self.ucs_service.find_category_by_name("apple")
        self.assertIsNotNone(category, "未找到分类 apple")
        self.assertEqual(category['name'], "Fruit", "分类名称不匹配")
        
        # 测试通过中文名称查询
        category = self.ucs_service.find_category_by_name("苹果")
        self.assertIsNotNone(category, "未找到分类 苹果")
        self.assertEqual(category['name_zh'], "水果", "中文分类名称不匹配")

    def test_translation_query(self):
        """测试翻译查询"""
        # 测试基本翻译
        translation = self.ucs_service.get_translation("apple")
        self.assertEqual(translation, "苹果", "翻译不匹配")
        
        # 测试不存在的翻译
        translation = self.ucs_service.get_translation("orange")
        self.assertIsNone(translation, "不应该找到翻译")

    def test_add_translation(self):
        """测试添加翻译"""
        # 添加新翻译
        result = self.ucs_service.add_translation("orange", "橙子")
        self.assertTrue(result, "添加翻译失败")
        
        # 验证添加成功
        translation = self.ucs_service.get_translation("orange")
        self.assertEqual(translation, "橙子", "添加的翻译不匹配")
        
        # 验证文件更新
        translations_file = self.data_dir / "ucs_translations.csv"
        with open(translations_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("orange,橙子", content, "翻译未写入文件")

    def test_get_stats(self):
        """测试获取统计信息"""
        # 先进行一些查询以产生统计数据
        self.ucs_service.get_category("AA01")
        self.ucs_service.get_translation("apple")
        self.ucs_service.get_translation("unknown")
        
        # 获取统计信息
        stats = self.ucs_service.get_stats()
        
        # 验证统计数据
        self.assertEqual(stats['categories_count'], 4, "分类数量不匹配")
        self.assertEqual(stats['translations_count'], 5, "翻译数量不匹配")
        self.assertGreater(stats['cache_hits'], 0, "缓存命中数应大于0")
        self.assertGreater(stats['translation_misses'], 0, "翻译未命中数应大于0")


if __name__ == "__main__":
    unittest.main() 