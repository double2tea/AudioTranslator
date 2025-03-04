from typing import Dict, List, Any
import requests
import json
from ...model_service import ModelService

class AnthropicService(ModelService):
    """Anthropic API service implementation"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.name = config.get('name', 'Anthropic')
        self.type = 'anthropic'
        
    def test_connection(self) -> Dict:
        """Test connection to Anthropic API"""
        try:
            # Try to create a simple completion as a connection test
            data = {
                "model": "claude-2",
                "prompt": "\n\nHuman: Hello\n\nAssistant:",
                "max_tokens_to_sample": 10
            }
            response = self.make_request(
                'complete',
                method='POST',
                data=data
            )
            return {'status': 'success', 'message': '连接成功'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
            
    def list_models(self) -> List[str]:
        """List available Anthropic models"""
        # Anthropic doesn't have a models list endpoint
        # Return hardcoded list of known models
        return [
            "claude-2",
            "claude-instant-1",
            "claude-2.1"
        ]
        
    def chat_completion(self, messages: List[Dict], model: str = "claude-2") -> Dict:
        """Create a chat completion"""
        try:
            # Convert messages to Anthropic format
            prompt = ""
            for msg in messages:
                role = msg['role']
                content = msg['content']
                if role == 'user':
                    prompt += f"\n\nHuman: {content}"
                elif role == 'assistant':
                    prompt += f"\n\nAssistant: {content}"
                    
            prompt += "\n\nAssistant:"
            
            data = {
                "model": model,
                "prompt": prompt,
                "max_tokens_to_sample": 1000,
                "temperature": 0.7
            }
            
            response = self.make_request(
                'complete',
                method='POST',
                data=data
            )
            
            # Convert response to OpenAI-like format
            return {
                'choices': [{
                    'message': {
                        'role': 'assistant',
                        'content': response.get('completion', '')
                    }
                }]
            }
        except Exception as e:
            raise Exception(f"Chat completion failed: {str(e)}")
            
    def validate_config(self) -> bool:
        """Validate Anthropic configuration"""
        if not super().validate_config():
            return False
            
        if not self.api_url:
            self.api_url = "https://api.anthropic.com/v1"
            
        return True
        
    def make_request(self, endpoint: str, method: str = 'GET', data: Dict = None) -> Dict:
        """Make HTTP request to Anthropic API"""
        url = f"{self.api_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
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
            raise Exception(f"API request failed: {str(e)}") 