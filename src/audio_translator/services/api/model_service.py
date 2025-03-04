from typing import Dict, List, Optional
import requests
import json
import logging
from abc import ABC, abstractmethod
import os

class ModelService(ABC):
    """Base class for AI model services"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # 从环境变量读取API密钥（如果配置值以 ${ENV_VAR} 格式提供）
        api_key = config.get('api_key', '')
        if isinstance(api_key, str) and api_key.startswith('${') and api_key.endswith('}'):
            env_var = api_key[2:-1]
            self.api_key = os.environ.get(env_var, '')
            if not self.api_key:
                logging.warning(f"环境变量 {env_var} 未设置或为空")
        else:
            self.api_key = api_key
            
        self.api_url = config.get('api_url', '')
        self.enabled = config.get('enabled', True)
        self.models = config.get('models', [])
        self.name = config.get('name', '')
        self.service_id = config.get('service_id', '')
        self.type = config.get('type', '')
        
        # 处理current_model
        self.current_model = config.get('current_model', '')
        # 如果没有current_model但有models列表，使用第一个模型
        if not self.current_model and self.models and len(self.models) > 0:
            try:
                if isinstance(self.models[0], dict) and 'name' in self.models[0]:
                    self.current_model = self.models[0]['name']
                elif isinstance(self.models[0], str):
                    self.current_model = self.models[0]
            except (IndexError, KeyError) as e:
                logging.warning(f"无法从models列表获取current_model: {e}")
        
    @abstractmethod
    def test_connection(self) -> Dict:
        """Test the connection to the model service"""
        pass
        
    @abstractmethod
    def list_models(self) -> List[str]:
        """List available models from the service"""
        pass
        
    def validate_config(self) -> bool:
        """Validate the service configuration"""
        if not self.api_key:
            logging.error(f"{self.name}: API key is required")
            return False
        if not self.api_url:
            logging.error(f"{self.name}: API URL is required")
            return False
        return True
        
    def update_config(self, config: Dict) -> None:
        """Update service configuration"""
        self.config.update(config)
        self.api_key = config.get('api_key', self.api_key)
        self.api_url = config.get('api_url', self.api_url)
        self.enabled = config.get('enabled', self.enabled)
        self.models = config.get('models', self.models)
        self.current_model = config.get('current_model', self.current_model)
        
    def to_dict(self) -> Dict:
        """Convert service configuration to dictionary"""
        return {
            'name': self.name,
            'type': self.type,
            'service_id': self.service_id,
            'api_key': self.api_key,
            'api_url': self.api_url,
            'enabled': self.enabled,
            'models': self.models,
            'current_model': self.current_model
        }
        
    def make_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict:
        """Make HTTP request to the service API"""
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
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"{self.name} API request failed: {str(e)}")
            raise 