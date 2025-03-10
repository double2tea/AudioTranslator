from typing import Dict, List, Any, Optional
import time

from src.audio_translator.services.business.translation.strategies.base_strategy import ITranslationStrategy

class SimpleCustomStrategy(ITranslationStrategy):
    """
    简单的自定义翻译策略，用于演示
    将文本翻译成特定的格式，不调用实际的翻译API
    """
    
    def __init__(self):
        """初始化自定义策略"""
        self.config = {
            "prefix": "[翻译] ",
            "suffix": " [END]",
            "translation_delay": 0.5  # 模拟翻译延迟（秒）
        }
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0
        }
        
    def get_name(self) -> str:
        """获取策略名称"""
        return "simple_custom"
        
    def get_description(self) -> str:
        """获取策略描述"""
        return "简单的自定义翻译策略，用于演示插件机制"
        
    def get_provider_type(self) -> str:
        """获取提供商类型"""
        return "custom"
        
    def translate(self, text: str, context: Dict[str, Any] = None) -> str:
        """
        翻译文本
        
        Args:
            text: 要翻译的文本
            context: 上下文信息
            
        Returns:
            翻译后的文本
        """
        start_time = time.time()
        self.metrics["total_requests"] += 1
        
        try:
            # 模拟翻译延迟
            time.sleep(self.config.get("translation_delay", 0.5))
            
            # 获取目标语言
            context = context or {}
            target_lang = context.get("target_lang", "zh")
            
            # 根据目标语言模拟翻译
            if target_lang == "zh":
                translation = f"{self.config.get('prefix', '')}这是一个自定义翻译: {text}{self.config.get('suffix', '')}"
            elif target_lang == "en":
                translation = f"{self.config.get('prefix', '')}This is a custom translation: {text}{self.config.get('suffix', '')}"
            elif target_lang == "ja":
                translation = f"{self.config.get('prefix', '')}これはカスタム翻訳です: {text}{self.config.get('suffix', '')}"
            else:
                translation = f"{self.config.get('prefix', '')}Custom translation for '{target_lang}': {text}{self.config.get('suffix', '')}"
                
            # 更新指标
            self.metrics["successful_requests"] += 1
            elapsed_time = time.time() - start_time
            self._update_response_time(elapsed_time)
            
            return translation
        except Exception as e:
            self.metrics["failed_requests"] += 1
            raise
            
    def batch_translate(self, texts: List[str], context: Dict[str, Any] = None) -> List[str]:
        """
        批量翻译文本
        
        Args:
            texts: 要翻译的文本列表
            context: 上下文信息
            
        Returns:
            翻译后的文本列表
        """
        return [self.translate(text, context) for text in texts]
        
    def test_connection(self) -> Dict[str, Any]:
        """
        测试连接
        
        Returns:
            连接状态信息
        """
        return {
            "status": "success",
            "message": "自定义策略不需要外部连接"
        }
        
    def get_config_schema(self) -> Dict[str, Any]:
        """
        获取配置模式
        
        Returns:
            配置模式字典
        """
        return {
            "type": "object",
            "properties": {
                "prefix": {
                    "type": "string",
                    "title": "翻译前缀",
                    "description": "添加到翻译结果前的文本",
                    "default": "[翻译] "
                },
                "suffix": {
                    "type": "string",
                    "title": "翻译后缀",
                    "description": "添加到翻译结果后的文本",
                    "default": " [END]"
                },
                "translation_delay": {
                    "type": "number",
                    "title": "模拟延迟",
                    "description": "模拟翻译延迟（秒）",
                    "minimum": 0,
                    "maximum": 10,
                    "default": 0.5
                }
            }
        }
        
    def update_config(self, config: Dict[str, Any]) -> bool:
        """
        更新配置
        
        Args:
            config: 新的配置字典
            
        Returns:
            更新是否成功
        """
        try:
            self.config.update(config)
            return True
        except Exception:
            return False
            
    def get_capabilities(self) -> Dict[str, Any]:
        """
        获取能力
        
        Returns:
            能力字典
        """
        return {
            "supports_batch": True,
            "max_text_length": 10000,
            "languages": ["en", "zh", "ja", "fr", "es", "de", "it", "ru"],
            "features": ["custom_prefix", "custom_suffix"]
        }
        
    def get_metrics(self) -> Dict[str, Any]:
        """
        获取指标
        
        Returns:
            指标字典
        """
        return self.metrics
        
    def _update_response_time(self, response_time: float) -> None:
        """
        更新平均响应时间
        
        Args:
            response_time: 响应时间（秒）
        """
        total_requests = self.metrics["successful_requests"] + self.metrics["failed_requests"]
        if total_requests == 1:
            self.metrics["average_response_time"] = response_time
        else:
            avg = self.metrics["average_response_time"]
            self.metrics["average_response_time"] = avg * 0.9 + response_time * 0.1 