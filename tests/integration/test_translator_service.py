"""
翻译服务集成测试模块

测试AudioTranslator应用程序的翻译服务功能。
主要验证：
1. 翻译服务的初始化和配置加载
2. 翻译功能的正确运行
3. 翻译缓存机制的有效性
4. 与UCS服务的协同工作
"""

import unittest
import sys
import os
from pathlib import Path
import logging
from typing import Dict, Any
from unittest.mock import MagicMock, patch

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入测试工具
from tests.integration.test_utils import TestEnvironment, create_test_env

# 导入核心服务
from src.audio_translator.services.core.service_factory import ServiceFactory
from src.audio_translator.services.business.translator_service import TranslatorService

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TranslatorServiceTest(unittest.TestCase):
    """翻译服务测试类"""
    
    def setUp(self):
        """测试准备"""
        # 创建测试环境
        self.test_env = create_test_env()
        
        # 获取配置文件路径
        self.config_file = self.test_env.setup_config({
            'translation': {
                'api_key': 'test_api_key',
                'model': 'test_model',
                'timeout': 5,
                'temperature': 0.3,
                'cache_enabled': True
            }
        })
        
        # 初始化服务工厂
        self.service_factory = ServiceFactory()
        
        # 配置服务工厂
        self.service_factory.register_service_config('config_service', {
            'config_file': str(self.config_file),
        })
        
        # 初始化所有服务
        self.service_factory.initialize_all_services()
        
        # 获取翻译服务
        self.translator_service = self.service_factory.get_service('translator_service')
        
        # 确保翻译服务初始化成功
        self.assertIsNotNone(self.translator_service, "翻译服务初始化失败")
    
    def tearDown(self):
        """测试清理"""
        # 关闭所有服务
        if hasattr(self, 'service_factory'):
            self.service_factory.shutdown_all_services()
        
        # 清理测试环境
        if hasattr(self, 'test_env'):
            self.test_env.cleanup()
    
    def test_translation_cache(self):
        """测试翻译缓存机制"""
        # 模拟翻译API调用
        original_translate = self.translator_service._translate_with_api
        self.translator_service._translate_with_api = MagicMock(return_value="测试翻译结果")
        
        # 第一次调用，应该使用API
        result1 = self.translator_service._translate_with_retries("Test content")
        self.assertEqual(result1, "测试翻译结果", "翻译结果不匹配")
        self.translator_service._translate_with_api.assert_called_once()
        
        # 重置模拟对象
        self.translator_service._translate_with_api.reset_mock()
        
        # 第二次调用相同内容，应该使用缓存
        result2 = self.translator_service._translate_with_retries("Test content")
        self.assertEqual(result2, "测试翻译结果", "缓存翻译结果不匹配")
        self.translator_service._translate_with_api.assert_not_called()
        
        # 恢复原始方法
        self.translator_service._translate_with_api = original_translate
    
    def test_filename_translation(self):
        """测试文件名翻译功能"""
        # 模拟翻译API调用
        with patch.object(self.translator_service, '_translate_with_api', return_value="测试"):
            # 测试文件名翻译
            result = self.translator_service.translate_filename("test_sound.wav")
            
            # 验证结果包含翻译结果
            self.assertIsInstance(result, dict, "翻译结果应该是字典")
            self.assertIn('translation', result, "翻译结果应包含'translation'键")
            self.assertEqual(result['translation'], "测试", "翻译结果不匹配")
            self.assertEqual(result['chinese_name'], "测试", "中文名称不匹配")
    
    def test_offline_mode(self):
        """测试离线模式"""
        # 开启离线模式
        self.translator_service.set_offline_mode(True)
        
        # 模拟翻译API调用
        self.translator_service._translate_with_api = MagicMock(return_value="这不应该被调用")
        
        # 尝试翻译，应该使用缓存或返回原始文本
        result = self.translator_service._translate_with_retries("Test content")
        
        # 验证API未被调用
        self.translator_service._translate_with_api.assert_not_called()
        
        # 关闭离线模式
        self.translator_service.set_offline_mode(False)
    
    def test_translation_with_ucs(self):
        """测试与UCS服务的集成"""
        # 获取UCS服务
        ucs_service = self.service_factory.get_service('ucs_service')
        self.assertIsNotNone(ucs_service, "UCS服务初始化失败")
        
        # 添加测试翻译到UCS服务
        test_en = "Test UCS Integration"
        test_zh = "测试UCS集成"
        ucs_service.add_translation(test_en, test_zh)
        
        # 模拟翻译API调用，如果UCS集成正常应该不会被调用
        with patch.object(self.translator_service, '_translate_with_api', return_value="这不应该被调用"):
            # 尝试翻译UCS已有的文本
            result = self.translator_service._translate_with_retries(test_en)
            
            # 验证结果使用UCS中的翻译
            self.assertEqual(result, test_zh, "未使用UCS中的翻译")

if __name__ == '__main__':
    unittest.main() 