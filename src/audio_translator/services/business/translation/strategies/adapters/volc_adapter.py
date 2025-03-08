"""
火山引擎适配器模块

将VolcEngineService适配为ITranslationStrategy接口，以便在翻译管理器中使用。
"""

from typing import Dict, Any, Optional, List
import logging

from ..model_service_adapter import ModelServiceAdapter
from ......services.api.providers.volc.volc_service import VolcEngineService

# 设置日志记录器
logger = logging.getLogger(__name__)

class VolcAdapter(ModelServiceAdapter):
    """
    火山引擎适配器
    
    将VolcEngineService适配为ITranslationStrategy接口，提供火山引擎讯飞星火模型的翻译能力。
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化火山引擎适配器
        
        Args:
            config: 配置信息，包含API密钥等
        """
        # 创建火山引擎服务实例
        config = config or {}
        volc_service = VolcEngineService(config)
        
        # 设置默认提示模板，针对星火模型优化
        if "prompt_template" not in config:
            config["prompt_template"] = "请你充当翻译专家，将以下文本翻译成简体中文，直接给出翻译结果，不需要解释：\n\n{text}"
            
        # 设置默认描述
        if "description" not in config:
            config["description"] = "火山引擎讯飞星火翻译服务，提供专业的中文本地化翻译。"
        
        # 设置默认系统消息
        if "system_message" not in config:
            config["system_message"] = "你是一位专业的翻译助手，负责将文本准确翻译成中文。请直接提供翻译结果，不需要解释或添加额外内容。"
        
        # 设置默认模型
        if "model" not in config:
            config["model"] = "spark-v3"
            
        # 初始化适配器
        super().__init__(volc_service, config)
    
    def translate(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        使用火山引擎翻译文本
        
        Args:
            text: 要翻译的文本
            context: 翻译上下文
            
        Returns:
            翻译后的文本
        """
        return super().translate(text, context)
        
    def get_capabilities(self) -> Dict[str, Any]:
        """
        获取火山引擎翻译能力信息
        
        Returns:
            描述翻译能力的字典
        """
        capabilities = super().get_capabilities()
        # 添加火山引擎特有的能力描述
        capabilities.update({
            "supports_chinese_optimization": True,
            "provider_region": "中国",
            "specialized_domains": ["技术", "生活", "媒体", "娱乐"],
            "response_speed": "快速",
            "supports_streaming": True
        })
        return capabilities
    
    def _extract_response(self, response: Dict[str, Any]) -> str:
        """
        从火山引擎响应中提取翻译结果
        
        Args:
            response: 火山引擎API的原始响应
            
        Returns:
            提取的翻译文本
        """
        try:
            # 火山引擎的响应格式
            if 'choices' in response and len(response['choices']) > 0:
                choice = response['choices'][0]
                if 'message' in choice and 'content' in choice['message']:
                    return choice['message']['content'].strip()
            
            # 尝试通用提取方法            
            return super()._extract_response(response)
        except Exception as e:
            logger.error(f"从火山引擎响应中提取文本失败: {e}")
            return "" 