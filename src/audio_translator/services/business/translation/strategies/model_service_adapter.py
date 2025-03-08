"""
模型服务适配器模块

此模块提供了将ModelService适配为ITranslationStrategy的适配器基类。
适配器模式使得不同的API服务可以统一使用翻译策略接口。
"""

import logging
import time
from typing import Dict, List, Any, Optional

from .....core.interfaces import ITranslationStrategy
from .....services.api.model_service import ModelService

# 设置日志记录器
logger = logging.getLogger(__name__)

class ModelServiceAdapter(ITranslationStrategy):
    """
    模型服务适配器
    
    将ModelService适配为ITranslationStrategy，使得各种API服务
    可以统一通过翻译策略接口使用。
    """
    
    def __init__(self, model_service: ModelService, config: Optional[Dict[str, Any]] = None):
        """
        初始化适配器
        
        Args:
            model_service: 要适配的模型服务
            config: 适配器配置
        """
        self.model_service = model_service
        self.config = config or {}
        
        # 性能指标
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0,
            "total_response_time": 0
        }
        
        # 翻译提示模板
        self.prompt_template = config.get("prompt_template", "请将以下文本翻译成中文: \n\n{text}")
        
        # 系统消息
        self.system_message = config.get("system_message", "你是一个专业的翻译引擎，请直接输出翻译结果，不要有任何解释或附加信息。")
    
    def get_name(self) -> str:
        """
        获取策略名称
        
        Returns:
            策略名称
        """
        return self.model_service.name
    
    def get_description(self) -> str:
        """
        获取策略描述
        
        Returns:
            策略描述
        """
        description = self.config.get("description")
        if description:
            return description
        return f"{self.model_service.name} 翻译策略"
    
    def get_provider_type(self) -> str:
        """
        获取提供商类型
        
        Returns:
            提供商类型
        """
        return self.model_service.type
    
    def translate(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        翻译文本
        
        Args:
            text: 要翻译的文本
            context: 翻译上下文
            
        Returns:
            翻译后的文本
        """
        try:
            start_time = time.time()
            self.metrics["total_requests"] += 1
            
            # 处理上下文
            ctx = context or {}
            
            # 根据上下文调整提示文本
            prompt = self._build_prompt(text, ctx)
            
            # 准备消息
            messages = self._prepare_messages(prompt)
            
            # 选择模型
            model = self.config.get("model") or self.model_service.get_default_model()
            
            # 执行翻译
            result = self.model_service.chat_completion(messages, model)
            
            # 提取翻译结果
            translated = self._extract_response(result)
            
            # 更新指标
            end_time = time.time()
            response_time = end_time - start_time
            self.metrics["successful_requests"] += 1
            self.metrics["total_response_time"] += response_time
            if self.metrics["successful_requests"] > 0:
                self.metrics["average_response_time"] = self.metrics["total_response_time"] / self.metrics["successful_requests"]
            
            return translated
        except Exception as e:
            logger.error(f"翻译失败: {str(e)}")
            self.metrics["failed_requests"] += 1
            # 返回原文
            return text
    
    def batch_translate(self, texts: List[str], context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        批量翻译文本
        
        Args:
            texts: 要翻译的文本列表
            context: 翻译上下文
            
        Returns:
            翻译后的文本列表
        """
        results = []
        for text in texts:
            results.append(self.translate(text, context))
        return results
    
    def test_connection(self) -> Dict[str, Any]:
        """
        测试连接状态
        
        Returns:
            连接状态信息
        """
        try:
            result = self.model_service.test_connection()
            return result
        except Exception as e:
            logger.error(f"测试连接失败: {str(e)}")
            return {
                "status": "error",
                "message": f"连接测试失败: {str(e)}"
            }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        获取配置模式描述
        
        Returns:
            描述配置项的结构和验证规则的字典
        """
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "模型名称"
                },
                "prompt_template": {
                    "type": "string",
                    "description": "提示模板，使用{text}作为占位符"
                },
                "system_message": {
                    "type": "string",
                    "description": "系统消息"
                },
                "description": {
                    "type": "string",
                    "description": "策略描述"
                }
            }
        }
    
    def update_config(self, config: Dict[str, Any]) -> bool:
        """
        更新策略配置
        
        Args:
            config: 新的配置信息
            
        Returns:
            更新是否成功
        """
        try:
            self.config.update(config)
            
            # 更新提示模板
            if "prompt_template" in config:
                self.prompt_template = config["prompt_template"]
            
            # 更新系统消息
            if "system_message" in config:
                self.system_message = config["system_message"]
            
            logger.info(f"更新配置成功: {self.get_name()}")
            return True
        except Exception as e:
            logger.error(f"更新配置失败: {str(e)}")
            return False
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        获取策略能力信息
        
        Returns:
            描述策略支持的能力和限制的字典
        """
        return {
            "supports_batch": True,
            "max_batch_size": 50,
            "supports_async": False,
            "requires_api_key": True,
            "supported_languages": ["en", "zh", "ja", "ko", "fr", "de", "es", "ru"],
            "provider_type": self.get_provider_type()
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        获取策略性能指标
        
        Returns:
            描述策略性能指标的字典
        """
        return self.metrics.copy()
    
    def _build_prompt(self, text: str, context: Dict[str, Any]) -> str:
        """
        构建提示文本
        
        Args:
            text: 原始文本
            context: 上下文
            
        Returns:
            提示文本
        """
        # 使用模板替换文本
        prompt = self.prompt_template.replace("{text}", text)
        
        # 处理其他上下文字段
        for key, value in context.items():
            placeholder = "{" + key + "}"
            if placeholder in prompt:
                prompt = prompt.replace(placeholder, str(value))
        
        return prompt
    
    def _prepare_messages(self, prompt: str) -> List[Dict[str, str]]:
        """
        准备聊天消息
        
        Args:
            prompt: 提示文本
            
        Returns:
            消息列表
        """
        messages = []
        
        # 添加系统消息
        if self.system_message:
            messages.append({
                "role": "system",
                "content": self.system_message
            })
        
        # 添加用户消息
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        return messages
    
    def _extract_response(self, response: Dict[str, Any]) -> str:
        """
        从响应中提取文本
        
        Args:
            response: API响应
            
        Returns:
            提取的文本
        """
        try:
            # 提取返回的消息内容
            if "choices" in response and len(response["choices"]) > 0:
                choice = response["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"].strip()
                elif "text" in choice:
                    return choice["text"].strip()
            
            # 处理不同的响应格式
            if "output" in response:
                return response["output"].strip()
            
            if "content" in response:
                return response["content"].strip()
            
            # 如果无法提取内容，记录错误并返回空字符串
            logger.warning(f"无法从响应中提取内容: {response}")
            return ""
        except Exception as e:
            logger.error(f"提取响应内容失败: {str(e)}")
            return "" 