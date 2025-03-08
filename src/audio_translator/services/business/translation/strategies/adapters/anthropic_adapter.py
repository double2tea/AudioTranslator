"""
Anthropic适配器模块

将AnthropicService适配为ITranslationStrategy接口，以便在翻译管理器中使用。
"""

from typing import Dict, Any, Optional

from ..model_service_adapter import ModelServiceAdapter
from ......services.api.providers.anthropic.anthropic_service import AnthropicService

class AnthropicAdapter(ModelServiceAdapter):
    """
    Anthropic适配器
    
    将AnthropicService适配为ITranslationStrategy接口，提供Anthropic Claude模型的翻译能力。
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Anthropic适配器
        
        Args:
            config: 配置信息，包含API密钥等
        """
        # 创建Anthropic服务实例
        config = config or {}
        anthropic_service = AnthropicService(config)
        
        # 设置默认提示模板，针对Claude模型优化
        if "prompt_template" not in config:
            config["prompt_template"] = "请将以下文本翻译成中文，直接输出翻译结果，不要包含任何前缀、后缀或解释：\n\n{text}"
            
        # 设置默认描述
        if "description" not in config:
            config["description"] = "Anthropic Claude翻译服务，提供高质量自然的翻译。"
        
        # 设置默认系统消息，Claude没有系统消息，但我们可以通过用户消息开头设置角色
        if "system_message" not in config:
            config["system_message"] = "你是一个专业翻译模型。你的任务是准确翻译文本，不添加任何解释或额外内容。"
        
        # 初始化适配器
        super().__init__(anthropic_service, config)
    
    def translate(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        使用Anthropic翻译文本
        
        Args:
            text: 要翻译的文本
            context: 翻译上下文
            
        Returns:
            翻译后的文本
        """
        return super().translate(text, context)
        
    def _prepare_messages(self, prompt: str) -> list:
        """
        为Anthropic API准备消息格式
        
        Anthropic使用特殊的格式，我们需要将系统消息和提示组合成适合Claude的格式
        
        Args:
            prompt: 准备好的提示文本
            
        Returns:
            适合Anthropic API的消息列表
        """
        # Claude使用特殊的Human:/Assistant:格式
        system = self.system_message if hasattr(self, 'system_message') else ""
        if system:
            formatted_prompt = f"{system}\n\n{prompt}"
        else:
            formatted_prompt = prompt
            
        return [
            {"role": "user", "content": formatted_prompt}
        ] 