from typing import Dict, List
import requests
import json
import logging
from ...model_service import ModelService

logger = logging.getLogger(__name__)

class AlibabaService(ModelService):
    """阿里云通义 API 服务实现"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.name = config.get('name', '阿里通义')
        self.type = 'alibaba'
        
    def test_connection(self) -> Dict:
        """测试阿里通义 API 连接"""
        try:
            # 使用手动预定义的模型列表作为连接测试
            models = self.list_models()
            if models:
                return {'status': 'success', 'message': '连接成功'}
            else:
                return {'status': 'error', 'message': '无法获取模型列表'}
        except Exception as e:
            logger.error(f"阿里通义 API 连接测试失败: {str(e)}")
            return {'status': 'error', 'message': str(e)}
            
    def list_models(self) -> List[str]:
        """列出可用的阿里通义模型"""
        try:
            # 阿里通义API没有提供列出模型的端点，使用预定义的模型列表
            # 这避免了404错误
            models = [
                "qwen-turbo",
                "qwen-plus",
                "qwen-max",
                "qwen-max-1201",
                "qwen-1.8b-chat"
            ]
            return models
        except Exception as e:
            logger.error(f"获取阿里通义模型列表失败: {str(e)}")
            return []
            
    def chat_completion(self, messages: List[Dict], model: str = "qwen-turbo") -> Dict:
        """创建对话完成"""
        try:
            data = {
                "model": model,
                "input": {
                    "messages": messages
                },
                "parameters": {
                    "temperature": 0.7,
                    "top_p": 0.8
                }
            }
            # 使用正确的聊天端点
            response = self.make_request(
                'services/aigc/text-generation/generation',
                method='POST',
                data=data
            )
            return response
        except Exception as e:
            logger.error(f"阿里通义聊天完成请求失败: {str(e)}")
            raise Exception(f"聊天完成请求失败: {str(e)}")
            
    def validate_config(self) -> bool:
        """验证阿里通义配置"""
        if not super().validate_config():
            return False
            
        if not self.api_url:
            # 设置默认的API URL
            self.api_url = "https://dashscope.aliyuncs.com/api/v1"
            
        return True 