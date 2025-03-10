"""
服务集成测试模块

测试AudioTranslator应用程序中各个服务之间的协同工作。
主要验证：
1. 服务依赖关系的正确初始化
2. 服务之间的数据传递
3. 服务配置的正确加载和应用
4. 服务生命周期的正确管理
"""

import unittest
import sys
import os
from pathlib import Path
import logging
from typing import Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入测试工具
from tests.integration.test_utils import TestEnvironment, create_test_env

# 导入核心服务
from src.audio_translator.services.core.service_factory import ServiceFactory
from src.audio_translator.services.infrastructure.config_service import ConfigService
from src.audio_translator.services.infrastructure.file_service import FileService
from src.audio_translator.services.business.audio_service import AudioService
from src.audio_translator.services.business.translator_service import TranslatorService

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServiceIntegrationTest(unittest.TestCase):
    """服务集成测试类"""
    
    def setUp(self):
        """测试准备"""
        # 创建测试环境
        self.test_env = create_test_env()
        
        # 获取配置文件路径
        self.config_file = self.test_env.setup_config()
        
        # 初始化服务工厂
        self.service_factory = ServiceFactory()
        
        # 配置服务工厂 - 确保传递的是文件路径而不是字典
        self.service_factory.register_service_config('config_service', {
            'config_file': str(self.config_file),
        })
        
        # 配置文件服务，确保使用测试环境的数据目录
        self.service_factory.register_service_config('file_service', {
            'app_data_dir': str(self.test_env.data_dir)
        })
        
        # 初始化所有服务
        self.service_factory.initialize_all_services()
    
    def tearDown(self):
        """测试清理"""
        # 关闭所有服务
        if hasattr(self, 'service_factory'):
            self.service_factory.shutdown_all_services()
        
        # 清理测试环境
        if hasattr(self, 'test_env'):
            self.test_env.cleanup()
    
    def test_config_service_initialization(self):
        """测试配置服务的初始化"""
        # 获取配置服务
        config_service = self.service_factory.get_service('config_service')
        
        # 验证服务初始化
        self.assertIsNotNone(config_service, "配置服务初始化失败")
        self.assertTrue(config_service.is_available(), "配置服务未处于可用状态")
        
        # 验证配置数据
        app_lang = config_service.get('app.language')
        self.assertEqual(app_lang, 'zh-CN', "配置值加载错误")
    
    def test_file_service_initialization(self):
        """测试文件服务的初始化"""
        # 获取文件服务
        file_service = self.service_factory.get_service('file_service')
        
        # 验证服务初始化
        self.assertIsNotNone(file_service, "文件服务初始化失败")
        self.assertTrue(file_service.is_available(), "文件服务未处于可用状态")
        
        # 验证数据目录设置
        data_dir = file_service.get_data_dir()
        self.assertIsNotNone(data_dir, "数据目录未设置")
        self.assertTrue(os.path.exists(data_dir), "数据目录不存在")
    
    def test_audio_service_initialization(self):
        """测试音频服务的初始化"""
        # 获取音频服务
        audio_service = self.service_factory.get_service('audio_service')
        
        # 验证服务初始化
        self.assertIsNotNone(audio_service, "音频服务初始化失败")
        self.assertTrue(audio_service.is_available(), "音频服务未处于可用状态")
        
        # 验证文件服务依赖
        self.assertIsNotNone(audio_service.file_service, "音频服务缺少文件服务依赖")
    
    def test_translator_service_initialization(self):
        """测试翻译服务的初始化"""
        # 获取翻译服务
        translator_service = self.service_factory.get_service('translator_service')
        
        # 验证服务初始化
        self.assertIsNotNone(translator_service, "翻译服务初始化失败")
        self.assertTrue(translator_service.is_available(), "翻译服务未处于可用状态")
        
        # 验证依赖
        self.assertIsNotNone(translator_service.config_service, "翻译服务缺少配置服务依赖")
        self.assertIsNotNone(translator_service.ucs_service, "翻译服务缺少UCS服务依赖")
    
    def test_service_dependency_chain(self):
        """测试服务依赖链"""
        # 按顺序获取服务，验证依赖链
        config_service = self.service_factory.get_service('config_service')
        file_service = self.service_factory.get_service('file_service')
        audio_service = self.service_factory.get_service('audio_service')
        translator_service = self.service_factory.get_service('translator_service')
        
        # 验证所有服务都正确初始化
        self.assertTrue(config_service.is_available(), "配置服务未初始化")
        self.assertTrue(file_service.is_available(), "文件服务未初始化")
        self.assertTrue(audio_service.is_available(), "音频服务未初始化")
        self.assertTrue(translator_service.is_available(), "翻译服务未初始化")
    
    def test_config_propagation(self):
        """测试配置变更传播"""
        # 获取服务
        config_service = self.service_factory.get_service('config_service')
        
        # 设置测试配置值
        test_key = 'app.test_value'
        test_value = 'integration_test_value'
        config_service.set(test_key, test_value)
        
        # 验证配置值已设置
        self.assertEqual(config_service.get(test_key), test_value, "配置值设置失败")
        
        # 获取翻译服务
        translator_service = self.service_factory.get_service('translator_service')
        
        # 验证配置值传播到翻译服务
        self.assertEqual(
            translator_service.config_service.get(test_key), 
            test_value,
            "配置值未正确传播到翻译服务"
        )
    
    def test_service_lifecycle(self):
        """测试服务生命周期"""
        # 获取音频服务
        audio_service = self.service_factory.get_service('audio_service')
        
        # 验证初始状态
        self.assertTrue(audio_service.is_available(), "音频服务初始状态应该是可用的")
        
        # 关闭服务
        self.assertTrue(audio_service.shutdown(), "音频服务关闭失败")
        self.assertFalse(audio_service.is_available(), "音频服务关闭后仍然显示为可用")
        
        # 重新获取服务（这将触发重新初始化）
        audio_service = self.service_factory.get_service('audio_service')
        self.assertTrue(audio_service.is_available(), "音频服务重新初始化后应该是可用的")

if __name__ == '__main__':
    unittest.main() 