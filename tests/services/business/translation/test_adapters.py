"""
翻译策略适配器测试模块

测试各种模型服务适配器的正确实现。
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import importlib.util
import logging

# 禁用日志输出，避免测试时的噪音
logging.disable(logging.CRITICAL)

class TestAdapters(unittest.TestCase):
    """翻译策略适配器测试类"""
    
    def test_adapter_files_exist(self):
        """测试适配器文件是否存在"""
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 
                                                '../../../../src/audio_translator/services/business/translation/strategies/adapters'))
        
        expected_files = [
            'openai_adapter.py',
            'anthropic_adapter.py',
            'gemini_adapter.py',
            'alibaba_adapter.py',
            'zhipu_adapter.py',
            'volc_adapter.py',
            'deepseek_adapter.py',
            '__init__.py'
        ]
        
        for file in expected_files:
            file_path = os.path.join(base_path, file)
            self.assertTrue(os.path.exists(file_path), f"文件不存在: {file}")
    
    def test_init_imports(self):
        """测试__init__.py是否正确导入了所有适配器"""
        init_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 
                                               '../../../../src/audio_translator/services/business/translation/strategies/adapters/__init__.py'))
        
        with open(init_path, 'r') as f:
            content = f.read()
        
        expected_imports = [
            'from .openai_adapter import OpenAIAdapter',
            'from .anthropic_adapter import AnthropicAdapter',
            'from .gemini_adapter import GeminiAdapter',
            'from .alibaba_adapter import AlibabaAdapter',
            'from .zhipu_adapter import ZhipuAdapter',
            'from .volc_adapter import VolcAdapter',
            'from .deepseek_adapter import DeepSeekAdapter'
        ]
        
        for imp in expected_imports:
            self.assertIn(imp, content, f"缺少导入: {imp}")
        
        self.assertIn('__all__', content, "缺少__all__定义")
        
        # 检查__all__中是否包含所有适配器
        expected_classes = [
            'OpenAIAdapter',
            'AnthropicAdapter',
            'GeminiAdapter',
            'AlibabaAdapter',
            'ZhipuAdapter',
            'VolcAdapter',
            'DeepSeekAdapter'
        ]
        
        for cls in expected_classes:
            self.assertIn(cls, content, f"__all__中缺少: {cls}")
    
    def test_adapter_structure(self):
        """测试适配器文件结构是否正确"""
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 
                                                '../../../../src/audio_translator/services/business/translation/strategies/adapters'))
        
        adapters = {
            'openai_adapter.py': 'OpenAIAdapter',
            'anthropic_adapter.py': 'AnthropicAdapter',
            'gemini_adapter.py': 'GeminiAdapter',
            'alibaba_adapter.py': 'AlibabaAdapter',
            'zhipu_adapter.py': 'ZhipuAdapter',
            'volc_adapter.py': 'VolcAdapter',
            'deepseek_adapter.py': 'DeepSeekAdapter'
        }
        
        for file, class_name in adapters.items():
            file_path = os.path.join(base_path, file)
            with open(file_path, 'r') as f:
                content = f.read()
            
            # 检查类定义
            self.assertIn(f"class {class_name}(ModelServiceAdapter):", content, 
                         f"文件 {file} 中缺少类定义: {class_name}")
            
            # 检查必要的方法
            required_methods = [
                'def __init__',
                'def translate',
            ]
            
            for method in required_methods:
                self.assertIn(method, content, f"文件 {file} 中缺少方法: {method}")

if __name__ == '__main__':
    unittest.main() 