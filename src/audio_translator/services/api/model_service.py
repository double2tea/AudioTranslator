from typing import Dict, List, Optional, Any
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
        
        # 更新模型相关配置
        if 'models' in config:
            self.models = config.get('models', [])
        if 'current_model' in config:
            self.current_model = config.get('current_model', '')
        
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
            
    def add_custom_model(self, model_data: Dict[str, Any]) -> bool:
        """
        添加自定义模型到服务
        
        Args:
            model_data: 模型数据字典，必须包含name字段
            
        Returns:
            添加是否成功
        """
        if not model_data or not isinstance(model_data, dict) or 'name' not in model_data:
            logging.error("添加自定义模型失败：模型数据无效")
            return False
            
        # 确保模型有is_custom标记
        model_data['is_custom'] = True
        
        # 检查是否已存在同名模型
        if isinstance(self.models, list):
            for model in self.models:
                if isinstance(model, dict) and model.get('name') == model_data['name']:
                    logging.warning(f"模型 '{model_data['name']}' 已存在")
                    return False
                elif isinstance(model, str) and model == model_data['name']:
                    logging.warning(f"模型 '{model_data['name']}' 已存在")
                    return False
                    
            # 添加到模型列表
            self.models.append(model_data)
        else:
            # 如果models不是列表，创建新列表
            self.models = [model_data]
            
        return True
        
    def remove_model(self, model_name: str) -> bool:
        """
        从服务中移除模型
        
        Args:
            model_name: 要移除的模型名称
            
        Returns:
            移除是否成功
        """
        if not model_name or not isinstance(self.models, list):
            return False
            
        original_length = len(self.models)
        
        # 移除匹配的模型
        new_models = []
        for model in self.models:
            if isinstance(model, dict) and model.get('name') != model_name:
                new_models.append(model)
            elif isinstance(model, str) and model != model_name:
                new_models.append(model)
                
        # 更新模型列表
        self.models = new_models
        
        # 如果当前模型是被删除的模型，需要更新当前模型
        if self.current_model == model_name:
            if self.models and len(self.models) > 0:
                if isinstance(self.models[0], dict) and 'name' in self.models[0]:
                    self.current_model = self.models[0]['name']
                elif isinstance(self.models[0], str):
                    self.current_model = self.models[0]
            else:
                self.current_model = ''
                
        # 检查是否移除了模型
        return len(self.models) < original_length 