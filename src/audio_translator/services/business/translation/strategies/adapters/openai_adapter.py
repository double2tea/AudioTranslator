"""
OpenAI适配器模块

将OpenAIService适配为ITranslationStrategy接口，以便在翻译管理器中使用。
"""

from typing import Dict, Any, Optional

from ..model_service_adapter import ModelServiceAdapter
from ......services.api.providers.openai.openai_service import OpenAIService

class OpenAIAdapter(ModelServiceAdapter):
    """
    OpenAI适配器
    
    将OpenAIService适配为ITranslationStrategy接口，提供OpenAI翻译能力。
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化OpenAI适配器
        
        Args:
            config: 配置信息，包含API密钥等
        """
        # 创建OpenAI服务实例
        config = config or {}
        openai_service = OpenAIService(config)
        
        # 设置默认提示模板
        if "prompt_template" not in config:
            config["prompt_template"] = "请将以下文本翻译成中文，直接输出翻译结果，无需解释：\n\n{text}"
            
        # 设置默认描述
        if "description" not in config:
            config["description"] = "OpenAI翻译服务，基于GPT模型提供高质量的翻译。"
        
        # 设置默认系统消息
        if "system_message" not in config:
            config["system_message"] = "你是专业的翻译模型，专注于准确翻译文本。请直接提供翻译结果，不要添加解释或其他内容。"
        
        # 初始化适配器
        super().__init__(openai_service, config)
    
    def translate(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        使用OpenAI翻译文本
        
        Args:
            text: 要翻译的文本
            context: 翻译上下文
            
        Returns:
            翻译后的文本
        """
        return super().translate(text, context) 