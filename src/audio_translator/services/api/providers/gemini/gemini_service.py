from typing import Dict, List
import requests
import json
from ...model_service import ModelService

class GeminiService(ModelService):
    """Google Gemini API service implementation"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.name = config.get('name', 'Gemini')
        self.type = 'gemini'
        
    def test_connection(self) -> Dict:
        """Test connection to Gemini API"""
        try:
            # Try to generate content as a connection test
            data = {
                "contents": [{
                    "parts": [{
                        "text": "Hello"
                    }]
                }]
            }
            response = self.make_request(
                f'models/gemini-pro:generateContent?key={self.api_key}',
                method='POST',
                data=data
            )
            return {'status': 'success', 'message': '连接成功'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
            
    def list_models(self) -> List[str]:
        """List available Gemini models"""
        # Gemini currently has a fixed set of models
        return [
            "gemini-pro",
            "gemini-pro-vision"
        ]
        
    def chat_completion(self, messages: List[Dict], model: str = "gemini-pro") -> Dict:
        """Create a chat completion"""
        try:
            # Convert messages to Gemini format
            contents = []
            for msg in messages:
                role = msg['role']
                content = msg['content']
                
                # Map roles to Gemini format
                if role == 'user':
                    contents.append({
                        "role": "user",
                        "parts": [{"text": content}]
                    })
                elif role == 'assistant':
                    contents.append({
                        "role": "model",
                        "parts": [{"text": content}]
                    })
                    
            data = {
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 1024,
                }
            }
            
            response = self.make_request(
                f'models/{model}:generateContent?key={self.api_key}',
                method='POST',
                data=data
            )
            
            # Convert response to OpenAI-like format
            generated_text = ""
            if 'candidates' in response:
                for candidate in response['candidates']:
                    if 'content' in candidate:
                        for part in candidate['content'].get('parts', []):
                            if 'text' in part:
                                generated_text += part['text']
                                
            return {
                'choices': [{
                    'message': {
                        'role': 'assistant',
                        'content': generated_text
                    }
                }]
            }
        except Exception as e:
            raise Exception(f"Chat completion failed: {str(e)}")
            
    def validate_config(self) -> bool:
        """Validate Gemini configuration"""
        if not super().validate_config():
            return False
            
        if not self.api_url:
            self.api_url = "https://generativelanguage.googleapis.com/v1"
            
        return True
        
    def make_request(self, endpoint: str, method: str = 'GET', data: Dict = None) -> Dict:
        """Make HTTP request to Gemini API"""
        url = f"{self.api_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {
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
            raise Exception(f"API request failed: {str(e)}") 