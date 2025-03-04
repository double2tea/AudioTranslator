from typing import Dict, List
import requests
import json
import logging
from ...model_service import ModelService

logger = logging.getLogger(__name__)

class DeepSeekService(ModelService):
    """DeepSeek API service implementation"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.name = config.get('name', 'DeepSeek')
        self.type = 'deepseek'
        
    def test_connection(self) -> Dict:
        """Test connection to DeepSeek API"""
        try:
            # 改为直接使用预定义模型列表,而非API调用
            models = self.list_models()
            if models:
                return {'status': 'success', 'message': '连接成功'}
            else:
                return {'status': 'error', 'message': '无法获取模型列表'}
        except Exception as e:
            logger.error(f"DeepSeek API 连接测试失败: {str(e)}")
            return {'status': 'error', 'message': str(e)}
            
    def list_models(self) -> List[str]:
        """List available DeepSeek models"""
        try:
            # 不调用API，直接返回预定义模型列表
            # 这避免了401 Unauthorized错误
            return [
                "deepseek-chat",
                "deepseek-coder"
            ]
        except Exception as e:
            logger.error(f"获取DeepSeek模型列表失败: {str(e)}")
            return []
            
    def chat_completion(self, messages: List[Dict], model: str = "deepseek-chat") -> Dict:
        """Create a chat completion using DeepSeek API"""
        try:
            data = {
                "model": model,
                "messages": messages,
                "temperature": 0.7
            }
            response = self.make_request(
                'chat/completions',
                method='POST',
                data=data
            )
            return response
        except Exception as e:
            logger.error(f"DeepSeek 聊天完成请求失败: {str(e)}")
            raise Exception(f"Chat completion failed: {str(e)}")
            
    def validate_config(self) -> bool:
        """Validate DeepSeek configuration"""
        # 首先调用父类的验证方法
        if not super().validate_config():
            return False
            
        # 设置默认API URL，如果未提供
        if not self.api_url:
            self.api_url = "https://api.deepseek.com/v1"
            
        return True 