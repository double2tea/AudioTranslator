"""
智谱AI适配器模块

将ZhipuAIService适配为ITranslationStrategy接口，以便在翻译管理器中使用。
"""

from typing import Dict, Any, Optional, List
import logging

from ..model_service_adapter import ModelServiceAdapter
from ......services.api.providers.zhipu.zhipu_service import ZhipuAIService

# 设置日志记录器
logger = logging.getLogger(__name__)

class ZhipuAdapter(ModelServiceAdapter):
    """
    智谱AI适配器
    
    将ZhipuAIService适配为ITranslationStrategy接口，提供智谱AI模型的翻译能力。
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化智谱AI适配器
        
        Args:
            config: 配置信息，包含API密钥等
        """
        # 创建智谱AI服务实例
        config = config or {}
        zhipu_service = ZhipuAIService(config)
        
        # 设置默认提示模板，针对智谱GLM模型优化
        if "prompt_template" not in config:
            config["prompt_template"] = "请将以下文本翻译成简体中文，只返回翻译结果，不要添加解释、注释或其他内容：\n\n{text}"
            
        # 设置默认描述
        if "description" not in config:
            config["description"] = "智谱GLM翻译服务，提供高质量的中文翻译，特别适合技术内容翻译。"
        
        # 设置默认系统消息
        if "system_message" not in config:
            config["system_message"] = "你是一个专业的文本翻译助手，基于GLM模型。请准确翻译用户提供的文本，只返回翻译结果，不添加任何额外内容。"
        
        # 设置默认模型
        if "model" not in config:
            config["model"] = "glm-4"
            
        # 初始化适配器
        super().__init__(zhipu_service, config)
    
    def translate(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        使用智谱AI翻译文本
        
        Args:
            text: 要翻译的文本
            context: 翻译上下文
            
        Returns:
            翻译后的文本
        """
        return super().translate(text, context)
        
    def get_capabilities(self) -> Dict[str, Any]:
        """
        获取智谱AI翻译能力信息
        
        Returns:
            描述翻译能力的字典
        """
        capabilities = super().get_capabilities()
        # 添加智谱特有的能力描述
        capabilities.update({
            "supports_chinese_optimization": True,
            "provider_region": "中国",
            "specialized_domains": ["技术", "学术", "科学", "金融"],
            "max_input_tokens": 8192 if "glm-4-long" in self.config.get("model", "") else 4096
        })
        return capabilities
    
    def _extract_response(self, response: Dict[str, Any]) -> str:
        """
        从智谱AI响应中提取翻译结果
        
        Args:
            response: 智谱AI API的原始响应
            
        Returns:
            提取的翻译文本
        """
        try:
            # 智谱GLM的响应格式
            if 'choices' in response and len(response['choices']) > 0:
                choice = response['choices'][0]
                if 'content' in choice and len(choice['content']) > 0:
                    for item in choice['content']:
                        if item.get('type') == 'text' and 'text' in item:
                            return item['text'].strip()
            
            # 尝试通用提取方法            
            return super()._extract_response(response)
        except Exception as e:
            logger.error(f"从智谱AI响应中提取文本失败: {e}")
            return "" 