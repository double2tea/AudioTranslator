"""
Gemini适配器模块

将GeminiService适配为ITranslationStrategy接口，以便在翻译管理器中使用。
"""

from typing import Dict, Any, Optional, List

from ..model_service_adapter import ModelServiceAdapter
from ......services.api.providers.gemini.gemini_service import GeminiService

class GeminiAdapter(ModelServiceAdapter):
    """
    Gemini适配器
    
    将GeminiService适配为ITranslationStrategy接口，提供Google Gemini模型的翻译能力。
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Gemini适配器
        
        Args:
            config: 配置信息，包含API密钥等
        """
        # 创建Gemini服务实例
        config = config or {}
        gemini_service = GeminiService(config)
        
        # 设置默认提示模板，针对Gemini模型优化
        if "prompt_template" not in config:
            config["prompt_template"] = "请将以下文本准确翻译成简体中文，直接返回翻译结果而不添加任何解释或引号：\n\n{text}"
            
        # 设置默认描述
        if "description" not in config:
            config["description"] = "Google Gemini翻译服务，利用先进的AI模型提供高质量翻译。"
        
        # 设置默认系统消息，Gemini没有真正的系统消息
        if "system_message" not in config:
            config["system_message"] = "你是一个专业的翻译助手。请直接提供准确的翻译，不要添加任何额外说明或解释。"
        
        # 初始化适配器
        super().__init__(gemini_service, config)
    
    def translate(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        使用Gemini翻译文本
        
        Args:
            text: 要翻译的文本
            context: 翻译上下文
            
        Returns:
            翻译后的文本
        """
        return super().translate(text, context)
        
    def _prepare_messages(self, prompt: str) -> List[Dict[str, Any]]:
        """
        为Gemini API准备消息格式
        
        Args:
            prompt: 准备好的提示文本
            
        Returns:
            适合Gemini API的消息列表
        """
        # Gemini使用contents格式，需要调整角色映射
        system = self.system_message if hasattr(self, 'system_message') else ""
        
        messages = []
        if system:
            # Gemini没有系统消息，但我们可以作为用户消息的一部分发送
            messages.append({
                "role": "user",
                "content": system
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        return messages
        
    def _extract_response(self, response: Dict[str, Any]) -> str:
        """
        从Gemini响应中提取翻译结果
        
        Args:
            response: Gemini API的原始响应
            
        Returns:
            提取的翻译文本
        """
        try:
            # Gemini的响应格式与其他模型不同
            if 'candidates' in response and len(response['candidates']) > 0:
                candidate = response['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    if len(parts) > 0 and 'text' in parts[0]:
                        return parts[0]['text'].strip()
            
            # 如果无法解析特定格式，尝试更通用的方法
            return super()._extract_response(response)
        except Exception as e:
            logger.error(f"从Gemini响应中提取文本失败: {e}")
            return "" 