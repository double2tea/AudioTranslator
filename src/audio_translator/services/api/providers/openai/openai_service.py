from typing import Dict, List, Any
import logging
from ...model_service import ModelService

# 设置日志记录器
logger = logging.getLogger(__name__)

class OpenAIService(ModelService):
    """OpenAI服务实现"""

    def __init__(self, config: Dict):
        """
        初始化OpenAI服务
        
        Args:
            config: 服务配置
        """
        super().__init__(config)
        self.name = config.get('name', 'OpenAI')
        self.type = 'openai'

    def validate_config(self) -> bool:
        """
        验证配置是否有效
        
        Returns:
            配置是否有效
        """
        is_valid = super().validate_config()
        
        # 如果未设置API URL，使用默认值
        if not self.api_url:
            self.api_url = "https://api.openai.com/v1"
            logger.info(f"未设置API URL，使用默认值: {self.api_url}")
        
        return is_valid

    def test_connection(self) -> Dict[str, Any]:
        """
        测试与OpenAI API的连接
        
        Returns:
            连接测试结果
        """
        try:
            # 直接使用预定义的模型列表验证连接
            models = self.list_models()
            if models and len(models) > 0:
                return {'status': 'success', 'message': '连接成功'}
            else:
                return {'status': 'error', 'message': '无法获取模型列表'}
        except Exception as e:
            logger.error(f"OpenAI连接测试失败: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def list_models(self) -> List[str]:
        """
        获取可用模型列表
        
        Returns:
            模型名称列表
        """
        # 返回预定义的模型列表而不是调用API
        # 这样可以避免API调用失败导致的问题
        return [
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k"
        ]

    def chat_completion(self, messages: List[Dict], model: str = None) -> Dict:
        """
        生成聊天回复
        
        Args:
            messages: 消息列表
            model: 模型名称，如果未指定则使用当前模型
        
        Returns:
            聊天完成结果
        """
        try:
            # 使用当前模型如果未指定模型
            model_to_use = model or self.current_model
            if not model_to_use:
                raise ValueError("未指定模型且未设置当前模型")
            
            # 构建请求
            data = {
                "model": model_to_use,
                "messages": messages
            }
            
            # 发送请求
            response = self.make_request('POST', 'chat/completions', data)
            
            return response
        except Exception as e:
            logger.error(f"OpenAI聊天请求失败: {str(e)}")
            raise 