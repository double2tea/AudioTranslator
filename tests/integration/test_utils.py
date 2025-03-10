"""
集成测试工具模块

提供集成测试中需要的辅助功能，包括测试环境设置、Mock数据生成等。
"""

import os
import tempfile
import shutil
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestEnvironment:
    """测试环境管理类，负责创建和清理测试环境"""
    
    def __init__(self):
        """初始化测试环境"""
        self.temp_dir = tempfile.mkdtemp(prefix="audio_translator_test_")
        self.data_dir = Path(self.temp_dir) / "data"
        self.config_dir = Path(self.temp_dir) / "config"
        self.categories_dir = self.data_dir / "categories"
        self.samples_dir = self.data_dir / "samples"
        
        # 创建目录结构
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.categories_dir, exist_ok=True)
        os.makedirs(self.samples_dir, exist_ok=True)
        
        logger.info(f"测试环境创建: {self.temp_dir}")
    
    def setup_config(self, config: Optional[Dict[str, Any]] = None) -> Path:
        """
        设置配置文件
        
        Args:
            config: 配置数据，如果为None则使用默认配置
            
        Returns:
            配置文件路径
        """
        config_file = self.config_dir / "app_config.json"
        
        # 默认配置
        default_config = {
            "app": {
                "data_dir": str(self.data_dir),
                "language": "zh-CN",
                "debug": True,
                "offline_mode": False
            },
            "translation": {
                "api_key": "test_key",
                "model": "test_model",
                "timeout": 5,
                "temperature": 0.3,
                "cache_enabled": True
            },
            "ui": {
                "theme": "system",
                "font_size": 12,
                "show_welcome": True
            }
        }
        
        # 合并配置
        if config:
            self._deep_update(default_config, config)
        
        # 写入配置文件
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"配置文件创建: {config_file}")
        return config_file
    
    def setup_categories(self, count: int = 10) -> Path:
        """
        设置分类数据
        
        Args:
            count: 创建的分类数量
            
        Returns:
            分类文件路径
        """
        categories_file = self.categories_dir / "_categorylist.csv"
        
        # 创建简单的分类数据
        with open(categories_file, 'w', encoding='utf-8') as f:
            # 写入CSV头
            f.write("CatID,Category,Category_zh,subcategory,subcategory_zh,synonyms_en,synonyms_zh\n")
            
            # 写入样本分类
            for i in range(1, count + 1):
                cat_id = f"C{i:03d}"
                category = f"Category{i}"
                category_zh = f"分类{i}"
                subcategory = f"Subcat{i}"
                subcategory_zh = f"子分类{i}"
                synonyms_en = json.dumps([f"syn_{i}_1", f"syn_{i}_2"])
                synonyms_zh = json.dumps([f"同义词_{i}_1", f"同义词_{i}_2"])
                
                line = f"{cat_id},{category},{category_zh},{subcategory},{subcategory_zh},{synonyms_en},{synonyms_zh}\n"
                f.write(line)
        
        logger.info(f"分类文件创建: {categories_file}")
        return categories_file
    
    def setup_sample_audio_files(self, count: int = 5) -> List[Path]:
        """
        创建样本音频文件（实际上只是空文件）
        
        Args:
            count: 文件数量
            
        Returns:
            文件路径列表
        """
        files = []
        extensions = ['mp3', 'wav', 'flac', 'ogg', 'aiff']
        
        for i in range(1, count + 1):
            ext = extensions[i % len(extensions)]
            file_path = self.samples_dir / f"test_audio_{i}.{ext}"
            
            # 创建空文件
            with open(file_path, 'w') as f:
                pass
            
            files.append(file_path)
        
        logger.info(f"创建了 {len(files)} 个样本音频文件")
        return files
    
    def cleanup(self):
        """清理测试环境"""
        try:
            shutil.rmtree(self.temp_dir)
            logger.info(f"测试环境已清理: {self.temp_dir}")
        except Exception as e:
            logger.error(f"清理测试环境失败: {e}")
    
    def _deep_update(self, source: Dict, updates: Dict) -> None:
        """
        深度更新字典
        
        Args:
            source: 源字典
            updates: 更新内容
        """
        for key, value in updates.items():
            if key in source and isinstance(source[key], dict) and isinstance(value, dict):
                self._deep_update(source[key], value)
            else:
                source[key] = value

def create_test_env() -> TestEnvironment:
    """
    创建测试环境
    
    Returns:
        测试环境实例
    """
    env = TestEnvironment()
    env.setup_config()
    env.setup_categories()
    env.setup_sample_audio_files()
    return env 