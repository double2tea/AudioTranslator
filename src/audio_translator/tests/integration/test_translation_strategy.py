import unittest
import os
import time
from typing import Dict, Any, List

from audio_translator.services.business.translation.translation_manager import TranslationManager
from audio_translator.services.business.translation.cache.cache_manager import CacheManager
from audio_translator.services.business.translation.context.context_processor import ContextProcessor
from audio_translator.services.business.translation.strategies.adapters.openai_adapter import OpenAIAdapter

class TranslationStrategyIntegrationTest(unittest.TestCase):
    """集成测试翻译策略服务"""
    
    def setUp(self):
        """测试前准备"""
        self.config = {
            'default_strategy': 'openai',
            'strategies': {
                'openai': {
                    'api_key': os.environ.get('OPENAI_API_KEY', 'test_api_key'),
                    'model': 'gpt-3.5-turbo'
                }
            },
            'cache': {
                'enabled': True,
                'type': 'memory',
                'max_size': 1000
            },
            'context': {
                'preserve_patterns': [r'\{.*?\}', r'\$\w+']
            }
        }
        
        self.cache_manager = CacheManager(self.config['cache'])
        self.context_processor = ContextProcessor(self.config['context'])
        
        self.manager = TranslationManager(self.config)
        self.manager.cache_manager = self.cache_manager
        self.manager.context_processor = self.context_processor
        self.manager.initialize()
    
    def test_end_to_end_translation(self):
        """测试端到端的翻译流程"""
        # 准备测试数据
        text = "Hello world! This is a test."
        context = {'source_lang': 'en', 'target_lang': 'zh'}
        
        # 执行翻译
        result = self.manager.translate(text, strategy_name='openai', context=context)
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        self.assertNotEqual(result, text)  # 确保文本被翻译
    
    def test_cache_integration(self):
        """测试缓存集成"""
        # 准备测试数据
        text = "This is a cache test."
        context = {'source_lang': 'en', 'target_lang': 'zh'}
        
        # 执行第一次翻译（应该调用API）
        start_time = time.time()
        result1 = self.manager.translate(text, strategy_name='openai', context=context)
        first_time = time.time() - start_time
        
        # 执行第二次翻译（应该从缓存获取）
        start_time = time.time()
        result2 = self.manager.translate(text, strategy_name='openai', context=context)
        second_time = time.time() - start_time
        
        # 验证结果
        self.assertEqual(result1, result2)  # 两次结果应相同
        self.assertLess(second_time, first_time * 0.5)  # 第二次应该显著更快
        
        # 验证缓存指标
        metrics = self.manager.cache_manager.get_metrics()
        self.assertGreater(metrics['hits'], 0)  # 应该有缓存命中
        
    def test_context_processing(self):
        """测试上下文处理"""
        # 带有需要保留的模式的文本
        text = "Hello {VARIABLE} world! This is $TEST."
        context = {'source_lang': 'en', 'target_lang': 'zh'}
        
        # 执行翻译
        result = self.manager.translate(text, strategy_name='openai', context=context)
        
        # 验证保留的模式
        self.assertIn('{VARIABLE}', result)
        self.assertIn('$TEST', result)
        
    def test_multiple_strategies(self):
        """测试多策略切换"""
        if not os.environ.get('ANTHROPIC_API_KEY'):
            self.skipTest("缺少Anthropic API密钥，跳过多策略测试")
            
        # 注册一个额外的策略
        self.config['strategies']['anthropic'] = {
            'api_key': os.environ.get('ANTHROPIC_API_KEY', 'test_api_key'),
            'model': 'claude-2'
        }
        
        # 添加Anthropic适配器
        try:
            from audio_translator.services.business.translation.strategies.adapters.anthropic_adapter import AnthropicAdapter
            anthropic_adapter = AnthropicAdapter(self.config['strategies']['anthropic'])
            self.manager.register_strategy(anthropic_adapter)
        except ImportError:
            self.skipTest("AnthropicAdapter不可用，跳过多策略测试")
            
        # 测试文本
        text = "This is a multi-strategy test."
        context = {'source_lang': 'en', 'target_lang': 'zh'}
        
        # 分别使用不同策略翻译
        openai_result = self.manager.translate(text, strategy_name='openai', context=context)
        anthropic_result = self.manager.translate(text, strategy_name='anthropic', context=context)
        
        # 验证结果
        self.assertIsNotNone(openai_result)
        self.assertIsNotNone(anthropic_result)
        # 不同模型可能有不同翻译，所以不直接比较结果内容

    def test_long_text_handling(self):
        """测试长文本处理"""
        # 生成长文本
        long_text = "This is a test sentence. " * 100
        context = {'source_lang': 'en', 'target_lang': 'zh'}
        
        # 执行翻译
        result = self.manager.translate(long_text, strategy_name='openai', context=context)
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        self.assertNotEqual(result, long_text)
        # 检查翻译后的文本长度应与源文本相当
        self.assertGreater(len(result), len(long_text) * 0.5)

if __name__ == '__main__':
    unittest.main() 