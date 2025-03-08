"""
DeepSeek适配器模块

将DeepSeekService适配为ITranslationStrategy接口，以便在翻译管理器中使用。
"""

from typing import Dict, Any, Optional, List
import logging

from ..model_service_adapter import ModelServiceAdapter
from ......services.api.providers.deepseek.deepseek_service import DeepSeekService

# 设置日志记录器
logger = logging.getLogger(__name__)

class DeepSeekAdapter(ModelServiceAdapter):
    """
    DeepSeek适配器
    
    将DeepSeekService适配为ITranslationStrategy接口，提供DeepSeek模型的翻译能力。
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化DeepSeek适配器
        
        Args:
            config: 配置信息，包含API密钥等
        """
        # 创建DeepSeek服务实例
        config = config or {}
        deepseek_service = DeepSeekService(config)
        
        # 设置默认提示模板，针对DeepSeek模型优化
        if "prompt_template" not in config:
            config["prompt_template"] = "请将以下文本翻译成简体中文，只需提供翻译结果，不要添加任何解释、注释或其他内容：\n\n{text}"
            
        # 设置默认描述
        if "description" not in config:
            config["description"] = "DeepSeek翻译服务，基于先进的大语言模型提供高质量翻译。"
        
        # 设置默认系统消息
        if "system_message" not in config:
            config["system_message"] = "你是一位精通多种语言的翻译专家。请将文本准确翻译成简体中文，只输出翻译结果，不要添加任何其他内容。"
        
        # 设置默认模型
        if "model" not in config:
            config["model"] = "deepseek-chat"
            
        # 初始化适配器
        super().__init__(deepseek_service, config)
    
    def translate(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        使用DeepSeek翻译文本
        
        Args:
            text: 要翻译的文本
            context: 翻译上下文
            
        Returns:
            翻译后的文本
        """
        return super().translate(text, context)
        
    def get_capabilities(self) -> Dict[str, Any]:
        """
        获取DeepSeek翻译能力信息
        
        Returns:
            描述翻译能力的字典
        """
        capabilities = super().get_capabilities()
        # 添加DeepSeek特有的能力描述
        capabilities.update({
            "supports_chinese_optimization": True,
            "provider_region": "中国",
            "specialized_domains": ["技术", "科学", "学术", "编程"],
            "supports_code_translation": True,
            "max_input_tokens": 8192
        })
        return capabilities
    
    def _extract_response(self, response: Dict[str, Any]) -> str:
        """
        从DeepSeek响应中提取翻译结果
        
        Args:
            response: DeepSeek API的原始响应
            
        Returns:
            提取的翻译文本
        """
        try:
            # DeepSeek的响应格式
            if 'choices' in response and len(response['choices']) > 0:
                choice = response['choices'][0]
                if 'message' in choice and 'content' in choice['message']:
                    return choice['message']['content'].strip()
            
            # 尝试通用提取方法            
            return super()._extract_response(response)
        except Exception as e:
            logger.error(f"从DeepSeek响应中提取文本失败: {e}")
            return "" 