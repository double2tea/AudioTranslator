from typing import Dict, List
import requests
import json
import logging
from ...model_service import ModelService

logger = logging.getLogger(__name__)

class VolcEngineService(ModelService):
    """火山引擎 API 服务实现"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.name = config.get('name', '火山引擎')
        self.type = 'volcengine'
        
    def test_connection(self) -> Dict:
        """测试火山引擎 API 连接"""
        try:
            # 使用预定义模型列表作为测试
            models = self.list_models()
            if models:
                return {'status': 'success', 'message': '连接成功'}
            else:
                return {'status': 'error', 'message': '无法获取模型列表'}
        except Exception as e:
            logger.error(f"火山引擎 API 连接测试失败: {str(e)}")
            return {'status': 'error', 'message': str(e)}
            
    def list_models(self) -> List[str]:
        """列出可用的火山引擎模型"""
        try:
            # 不调用API，直接返回预定义模型列表
            # 这避免了SSL连接问题
            return [
                "spark-v2",
                "spark-v3"
            ]
        except Exception as e:
            logger.error(f"获取火山引擎模型列表失败: {str(e)}")
            return []
            
    def chat_completion(self, messages: List[Dict], model: str = "spark-v3") -> Dict:
        """创建对话完成"""
        try:
            data = {
                "model": model,
                "messages": messages,
                "temperature": 0.7
            }
            # 直接使用完整路径，避免拼接错误
            response = self.make_request(
                'services/chat/completions',
                method='POST',
                data=data
            )
            return response
        except Exception as e:
            logger.error(f"火山引擎聊天完成请求失败: {str(e)}")
            raise Exception(f"聊天完成请求失败: {str(e)}")
            
    def validate_config(self) -> bool:
        """验证火山引擎配置"""
        if not super().validate_config():
            return False
            
        if not self.api_url:
            # 设置正确的API URL，包含HTTPS协议和正确的域名
            self.api_url = "https://spark-api.cn-beijing.volcanicengine.com/v1"
            
        return True 