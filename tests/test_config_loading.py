#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置加载测试脚本

此脚本用于测试新的配置加载路径是否正常工作，确保系统使用项目级配置。
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from src.audio_translator.services.infrastructure.config_service import ConfigService
from src.audio_translator.services.business.translation.strategies.strategy_registry import StrategyRegistry
from src.audio_translator.services.business.translation.strategies.dynamic_strategy_loader import DynamicStrategyLoader

def test_config_service():
    """测试配置服务加载路径"""
    logger.info("=== 测试配置服务加载路径 ===")
    
    # 创建配置服务实例
    config_service = ConfigService()
    config_service.initialize()
    
    # 获取配置文件路径
    config_file = config_service.config_file
    config_dir = config_service.config_dir
    
    logger.info(f"配置文件路径: {config_file}")
    logger.info(f"配置目录路径: {config_dir}")
    
    # 验证配置文件路径是否指向项目级配置
    expected_path = Path(__file__).parent.parent / "src" / "config"
    actual_path = Path(config_dir)
    
    if expected_path.resolve() == actual_path.resolve():
        logger.info("✅ 配置服务使用正确的项目级配置目录")
    else:
        logger.error(f"❌ 配置目录不匹配: 期望 {expected_path}, 实际 {actual_path}")
    
    # 检查配置文件是否存在
    if config_file.exists():
        logger.info(f"✅ 配置文件存在: {config_file}")
    else:
        logger.error(f"❌ 配置文件不存在: {config_file}")
    
    return config_service

def test_strategies_loading():
    """测试策略加载路径"""
    logger.info("\n=== 测试策略加载路径 ===")
    
    # 创建策略注册表
    registry = StrategyRegistry()
    
    # 创建策略加载器
    loader = DynamicStrategyLoader(registry)
    
    # 打印配置目录
    logger.info(f"策略配置目录: {loader.config_dir}")
    
    # 验证配置目录是否指向项目级配置
    expected_path = Path(__file__).parent.parent / "src" / "config"
    actual_path = Path(loader.config_dir)
    
    if expected_path.resolve() == actual_path.resolve():
        logger.info("✅ 策略加载器使用正确的项目级配置目录")
    else:
        logger.error(f"❌ 策略配置目录不匹配: 期望 {expected_path}, 实际 {actual_path}")
    
    # 加载策略配置
    num_loaded = loader.load_from_config()
    logger.info(f"从配置文件加载了 {num_loaded} 个策略")
    
    # 检查加载的策略
    strategies = loader.get_loaded_strategies()
    if strategies:
        logger.info(f"✅ 成功加载策略: {', '.join(strategies.keys())}")
        
        # 检查默认策略 - 不尝试通过registry获取
        # 由于我们没有StrategyRegistry.get_default_strategy_name方法，我们检查策略配置
        try:
            # 我们可以尝试从加载器的配置中获取默认策略
            import json
            config_file = os.path.join(loader.config_dir, 'strategies.json')
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                default_strategy = config.get('default_strategy', '')
                
            logger.info(f"配置中的默认策略: {default_strategy}")
            
            if default_strategy == "zhipu_glm4":
                logger.info("✅ 默认策略设置正确")
            else:
                logger.warning(f"⚠️ 默认策略不是预期的 'zhipu_glm4', 而是 '{default_strategy}'")
        except Exception as e:
            logger.error(f"❌ 检查默认策略时出错: {e}")
    else:
        logger.error("❌ 未加载任何策略")
    
    return registry, loader

if __name__ == "__main__":
    # 测试配置服务
    config_service = test_config_service()
    
    # 测试策略加载
    registry, loader = test_strategies_loading()
    
    # 总结
    logger.info("\n=== 测试总结 ===")
    logger.info("测试完成。如果没有错误消息，则配置加载功能工作正常。")
    logger.info("现在可以安全地移除内部配置目录。") 