from typing import Dict, List, Optional
import requests
import json
import logging
from ...model_service import ModelService

logger = logging.getLogger(__name__)

class ZhipuAIService(ModelService):
    """智谱 AI 服务实现"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.name = config.get('name', '智谱AI')
        self.type = 'zhipuai'
        self.available_models = []
        
    def test_connection(self) -> Dict:
        """测试智谱 AI API 连接"""
        try:
            # 尝试列出模型作为连接测试
            models = self.list_models()
            if models:
                return {'status': 'success', 'message': '连接成功'}
            else:
                return {'status': 'error', 'message': '无法获取模型列表'}
        except Exception as e:
            logger.error(f"智谱 API 连接测试失败: {str(e)}")
            return {'status': 'error', 'message': str(e)}
            
    def list_models(self) -> List[str]:
        """列出可用的智谱模型"""
        try:
            # 由于智谱API v4版本不提供model/list端点，我们手动返回支持的模型列表
            self.available_models = [
                "glm-4",
                "glm-4-plus", 
                "glm-4-0520", 
                "glm-4-air", 
                "glm-4-airx", 
                "glm-4-long", 
                "glm-4-flashx", 
                "glm-4-flash",
                "glm-3-turbo"
            ]
            return self.available_models
        except Exception as e:
            logger.error(f"获取智谱模型列表失败: {str(e)}")
            return []
            
    def chat_completion(self, messages: List[Dict], model: str = "glm-4") -> Dict:
        """创建智谱AI聊天完成"""
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
            logger.error(f"智谱聊天完成请求失败: {str(e)}")
            raise Exception(f"聊天完成请求失败: {str(e)}")
            
    def validate_config(self) -> bool:
        """验证智谱AI配置"""
        if not super().validate_config():
            return False
            
        if not self.api_url:
            # 设置默认的API URL - 更新为最新v4版本API
            self.api_url = "https://open.bigmodel.cn/api/paas/v4"
            
        return True 

    def make_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict:
        """发送请求到智谱 AI API"""
        url = f"{self.api_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"不支持的 HTTP 方法: {method}")
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"智谱 API 请求失败: {str(e)}")
            raise Exception(f"API 请求失败: {str(e)}") 