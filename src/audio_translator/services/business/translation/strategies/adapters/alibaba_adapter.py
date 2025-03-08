"""
Alibaba适配器模块

将AlibabaService适配为ITranslationStrategy接口，以便在翻译管理器中使用。
"""

from typing import Dict, Any, Optional, List
import logging

from ..model_service_adapter import ModelServiceAdapter
from ......services.api.providers.alibaba.alibaba_service import AlibabaService

# 设置日志记录器
logger = logging.getLogger(__name__)

class AlibabaAdapter(ModelServiceAdapter):
    """
    阿里通义适配器
    
    将AlibabaService适配为ITranslationStrategy接口，提供阿里云通义模型的翻译能力。
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化阿里通义适配器
        
        Args:
            config: 配置信息，包含API密钥等
        """
        # 创建阿里通义服务实例
        config = config or {}
        alibaba_service = AlibabaService(config)
        
        # 设置默认提示模板，针对通义千问模型优化
        if "prompt_template" not in config:
            config["prompt_template"] = "请将以下文本准确翻译成简体中文，只需直接返回翻译结果：\n\n{text}"
            
        # 设置默认描述
        if "description" not in config:
            config["description"] = "阿里云通义千问翻译服务，提供专业、准确的中文本地化翻译。"
        
        # 设置默认系统消息
        if "system_message" not in config:
            config["system_message"] = "你是通义千问翻译助手，请准确翻译用户提供的文本，直接给出翻译结果，无需解释或附加内容。"
        
        # 设置默认模型
        if "model" not in config:
            config["model"] = "qwen-max"
            
        # 初始化适配器
        super().__init__(alibaba_service, config)
    
    def translate(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        使用阿里通义翻译文本
        
        Args:
            text: 要翻译的文本
            context: 翻译上下文
            
        Returns:
            翻译后的文本
        """
        return super().translate(text, context)
        
    def get_capabilities(self) -> Dict[str, Any]:
        """
        获取阿里通义翻译能力信息
        
        Returns:
            描述翻译能力的字典
        """
        capabilities = super().get_capabilities()
        # 添加阿里特有的能力描述
        capabilities.update({
            "supports_chinese_optimization": True,
            "provider_region": "中国",
            "specialized_domains": ["技术", "商业", "音频", "游戏"]
        })
        return capabilities
    
    def _extract_response(self, response: Dict[str, Any]) -> str:
        """
        从阿里通义响应中提取翻译结果
        
        Args:
            response: 阿里通义API的原始响应
            
        Returns:
            提取的翻译文本
        """
        try:
            # 阿里通义的响应格式
            if 'output' in response and 'text' in response['output']:
                return response['output']['text'].strip()
            
            # 尝试通用提取方法
            return super()._extract_response(response)
        except Exception as e:
            logger.error(f"从阿里通义响应中提取文本失败: {e}")
            return "" 