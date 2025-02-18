import os
import json
import logging
import copy
import requests
from typing import Dict

class ConfigChangeEvent:
    def __init__(self, key, old_value, new_value):
        self.key = key
        self.old_value = old_value
        self.new_value = new_value

class Config:
    """简化的配置管理类"""
    def __init__(self):
        self.config_file = "config.json"
        self._listeners = []  # 初始化监听器列表
        self._config = self._get_default_config()
        self._load_config()

    def get_chinese_description_prompt(self) -> str:
        """获取中文描述提示词"""
        return """作为音效设计师，请用3-9个中文字简短描述这个音效。要求：
1. 不加"音效"、"声音"等词
2. 不用语气词（的了着过）
3. 用拟声和描述性词语

示例：
water_stream -> 溪水潺潺
metal_impact -> 金属撞击
human_male_laugh -> 男性大笑

请直接返回翻译：{text}"""

    def get_ucs_prompt(self):
        """获取默认的 UCS 提示词模板"""
        return """You are a professional audio filename translator. Your task is to translate English audio filenames into Chinese, following these rules:
1. Keep translations concise and accurate
2. Focus on the core meaning of the sound effect
3. Use descriptive Chinese terms
4. Avoid filler words
5. Maximum 4 Chinese characters

Examples:
- bang -> 轰鸣
- crackle -> 爆裂
- swoosh -> 疾呼
- thump -> 重击
- screech -> 咆哮

Translate this: {text}"""

    def get_bilingual_description_prompt(self) -> str:
        """获取双语音效描述提示词"""
        return """As a sound effect expert, provide both English and Chinese descriptions for this sound effect.
Keep English under 25 characters and Chinese between 3-9 characters.

Focus on describing:
1. Sound source (what makes the sound)
2. Action/state (what's happening)
3. Quality/characteristics (how it sounds)

Examples:
- human_male_ah_question -> (male vocal question, 男声困惑询问)
- error_tonal -> (error alert tone, 电子错误提示)
- click_blip -> (sharp click blip, 清脆按键声)
- cloth_nylon_movement -> (nylon cloth movement, 尼龙布料摩擦)
- metal_door_slam -> (heavy metal door slam, 金属重门砰响)
- footstep_concrete -> (footsteps on concrete, 混凝土脚步)

Format: Return exactly two lines:
1. English: [english description]
2. Chinese: [chinese description]

Describe: {text}"""

    def get_prompt_templates(self) -> Dict[str, str]:
        """获取所有 prompt 模板"""
        return {
            "通用翻译": self.get_ucs_prompt(),
            "中文描述": self.get_chinese_description_prompt(),
            "双语音效描述": self.get_bilingual_description_prompt()
        }

    def _get_default_config(self):
        """获取默认配置"""
        return {
            # 基础UI配置
            "UI_THEME": "dark",
            "COLORS": {
                'bg_dark': '#1E1E1E',
                'bg_light': '#2D2D2D',
                'fg': '#FFFFFF',
                'accent': '#007ACC'
            },
            
            # 翻译服务配置
            "TRANSLATION_SERVICE": "zhipu",
            "TRANSLATION_SERVICES": {
                # 智谱 API
                "zhipu": {
                    "name": "智谱 API",
                    "enabled": True,
                    "api_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                    "api_key": "",
                    "models": [
                        {"name": "glm-4", "description": "GLM-4 最新版"},
                        {"name": "glm-4v", "description": "GLM-4 视觉版"},
                        {"name": "glm-3-turbo", "description": "GLM-3 涡轮增压版"},
                        {"name": "chatglm_turbo", "description": "ChatGLM Turbo"}
                    ],
                    "current_model": "glm-4",
                    "prompts": self.get_prompt_templates(),
                    "current_prompt": "双语音效描述"
                },

                # 百炼 API
                "bailian": {
                    "name": "百炼 API",
                    "enabled": True,
                    "api_url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                    "api_key": "",
                    "models": [
                        {"name": "qwen-turbo", "description": "通义千问-涡轮增压版"},
                        {"name": "deepseek-r1", "description": ""},
                        {"name": "deepseek-v3", "description": ""}
                    ],
                    "current_model": "qwen-turbo",
                    "prompt_template": self.get_ucs_prompt(),
                    "chinese_description_prompt": self.get_chinese_description_prompt(),
                    "custom_prompt": False,
                    "messages_format": True,
                    "response_path": "output.text",
                    "request_format": {
                        "model": "{model}",
                        "input": {
                            "messages": [
                                {"role": "system", "content": "{prompt}"},
                                {"role": "user", "content": "{text}"}
                            ]
                        },
                        "parameters": {
                            "result_format": "message"
                        }
                    },
                    "prompts": self.get_prompt_templates(),
                    "current_prompt": "双语音效描述"
                },

                # NVIDIA API
                "nvidia": {
                    "name": "NVIDIA API",
                    "enabled": True,
                    "api_url": "https://api.nvcf.nvidia.com/v1/chat/completions",
                    "api_key": "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",
                    "models": [
                        {"name": "mixtral-8x7b", "description": "Mixtral 8x7B"},
                        {"name": "llama2-70b", "description": "Llama 2 70B"},
                        {"name": "yi-34b", "description": "Yi 34B"}
                    ],
                    "current_model": "mixtral-8x7b",
                    "prompt_template": self.get_ucs_prompt(),
                    "chinese_description_prompt": self.get_chinese_description_prompt(),
                    "custom_prompt": False,
                    "messages_format": True,
                    "response_path": "choices[0].message.content",
                    "prompts": self.get_prompt_templates(),
                    "current_prompt": "双语音效描述"
                },

                # 硅基流动 API
                "moonshot": {
                    "name": "硅基流动 API",
                    "enabled": True,
                    "api_url": "https://api.moonshot.cn/v1/chat/completions",
                    "api_key": "sk-nssnanjqfjnthtsonpamhgulwzorpeavzccqdfcqlhmgqsqu",
                    "models": [
                        {"name": "moonshot-v1-8k", "description": "Moonshot V1 8K"},
                        {"name": "moonshot-v1-32k", "description": "Moonshot V1 32K"},
                        {"name": "moonshot-v1-128k", "description": "Moonshot V1 128K"}
                    ],
                    "current_model": "moonshot-v1-8k",
                    "prompt_template": self.get_ucs_prompt(),
                    "chinese_description_prompt": self.get_chinese_description_prompt(),
                    "custom_prompt": False,
                    "messages_format": True,
                    "response_path": "choices[0].message.content"
                },

                # 通义千问 API
                "dashscope": {
                    "name": "通义千问 API",
                    "enabled": True,
                    "api_url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                    "api_key": "",
                    "models": [
                        {"name": "qwen-max", "description": "通义千问-最强版"},
                        {"name": "qwen-max-1201", "description": "通义千问-最强版(旧版)"},
                        {"name": "qwen-plus", "description": "通义千问-增强版"},
                        {"name": "qwen-turbo", "description": "通义千问-涡轮增压版"},
                        {"name": "qwen-1.8b-chat", "description": "通义千问-轻量版"}
                    ],
                    "current_model": "qwen-turbo",
                    "prompt_template": self.get_ucs_prompt(),
                    "chinese_description_prompt": self.get_chinese_description_prompt(),
                    "custom_prompt": False,
                    "messages_format": True,
                    "response_path": "output.text",
                    "request_format": {
                        "model": "{model}",
                        "input": {
                            "messages": [
                                {"role": "system", "content": "{prompt}"},
                                {"role": "user", "content": "{text}"}
                            ]
                        }
                    }
                },

                # DeepSeek API
                "DeepSeek": {
                    "name": "deepseek-r1",
                    "enabled": True,
                    "api_url": "https://api.deepseek.com/v1/chat/completions",
                    "api_key": "",
                    "headers": {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer {api_key}"
                    },
                    "models": [
                        {"name": "deepseek-chat", "description": "DeepSeek Chat"}
                    ],
                    "current_model": "deepseek-chat",
                    "prompt_template": self.get_ucs_prompt(),
                    "chinese_description_prompt": self.get_chinese_description_prompt(),
                    "custom_prompt": False,
                    "messages_format": True,
                    "response_path": "choices[0].message.content"
                },

                # OpenRouter API
                "openrouter": {
                    "name": "OpenRouter API",
                    "enabled": True,
                    "api_url": "https://openrouter.ai/api/v1/chat/completions",
                    "api_key": "",
                    "headers": {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer {api_key}",
                        "HTTP-Referer": "https://your-app-domain.com",
                        "X-Title": "Audio Translator"
                    },
                    "models": [
                        {"name": "anthropic/claude-3-opus", "description": "Claude 3 Opus"},
                        {"name": "anthropic/claude-3-sonnet", "description": "Claude 3 Sonnet"}
                    ],
                    "current_model": "anthropic/claude-3-opus",
                    "prompt_template": """You are a professional audio filename translator. Your task is to translate English audio filenames into Chinese, following these rules:
1. Keep translations concise and accurate
2. Focus on the core meaning of the sound effect
3. Use descriptive Chinese terms
4. Avoid filler words
5. Maximum 4 Chinese characters

Examples:
- bang -> 轰鸣
- crackle -> 爆裂
- swoosh -> 疾呼
- thump -> 重击
- screech -> 咆哮

Translate this: {text}""",
                    "custom_prompt": False,
                    "messages_format": True,
                    "response_path": "choices[0].message.content",
                    "request_format": {
                        "model": "{model}",
                        "messages": [
                            {"role": "system", "content": "{prompt}"},
                            {"role": "user", "content": "{text}"}
                        ],
                        "temperature": 0.3,
                        "route": "default",
                        "stream": False
                    }
                }
            },

            # 提示词模板
            "PROMPT_TEMPLATES": {
                "默认UCS提示词": self.get_ucs_prompt(),
                "中文描述提示词": self.get_chinese_description_prompt()
            },

            # 文件配置
            "FILE_CONFIG": {
                "formats": [".wav", ".mp3", ".ogg", ".flac"],
                "max_length": 100
            }
        }

    def get(self, key, default=None):
        """获取配置值"""
        return self._config.get(key, default)

    def set(self, key, value):
        """设置配置值"""
        self._config[key] = value
        self.save()

    def save(self):
        """保存配置"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, ensure_ascii=False, indent=4)

    def _load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    if self._validate_config(user_config):
                        self._config = user_config
                    else:
                        self._config = self._get_default_config()
            else:
                self._config = self._get_default_config()
            self.save()
        except Exception as e:
            logging.error(f"加载配置失败: {e}")
            self._config = self._get_default_config()
            self.save()

    def _validate_config(self, config):
        """验证配置是否完整"""
        if not isinstance(config, dict):
            return False
        
        required_fields = [
            "TRANSLATION_SERVICE",
            "TRANSLATION_SERVICES",
            "PROMPT_TEMPLATES"
        ]
        
        # 检查必需字段
        for field in required_fields:
            if field not in config:
                return False
        
        # 检查服务配置
        services = config.get("TRANSLATION_SERVICES", {})
        if not services:
            return False
        
        # 检查当前选中的服务是否存在
        current_service = config.get("TRANSLATION_SERVICE")
        if current_service not in services:
            return False
        
        return True

    def _merge_config(self, user_config):
        """合并用户配置和默认配置"""
        if not isinstance(user_config, dict):
            return
            
        for key, value in user_config.items():
            if key in self._config:
                if isinstance(self._config[key], dict) and isinstance(value, dict):
                    self._merge_dict(self._config[key], value)
                else:
                    self._config[key] = copy.deepcopy(value)

    def _merge_dict(self, target, source):
        """递归合并字典"""
        for key, value in source.items():
            if key in target:
                if isinstance(target[key], dict) and isinstance(value, dict):
                    self._merge_dict(target[key], value)
                else:
                    target[key] = copy.deepcopy(value)
            else:
                target[key] = copy.deepcopy(value)

    def _update_config(self, user_config):
        """更新配置"""
        self._config.update(user_config)

    def copy(self):
        """返回配置的深拷贝"""
        return copy.deepcopy(self._config)

    def validate_api_keys(self):
        """验证所有启用的服务是否都配置了API密钥"""
        services = self._config.get("TRANSLATION_SERVICES", {})
        for service_id, service in services.items():
            if service.get("enabled", True) and not service.get("api_key"):
                return False
        return True

    def reset_to_default(self):
        """重置为默认配置"""
        self._config = self._get_default_config()
        self.save()

    def _check_and_update_config(self):
        """检查并更新配置版本"""
        if not self._validate_config(self._config):
            logging.warning("配置文件不完整，重置为默认配置")
            self.reset_to_default()
            return
            
        # 在这里添加版本更新逻辑
        config_version = self._config.get("version", "1.0.0")
        if config_version != self.version:
            logging.info(f"配置版本从 {config_version} 更新到 {self.version}")
            self._config["version"] = self.version
            self.save()

    def get_ui_config(self):
        """获取UI相关配置"""
        return {
            'colors': self.get_colors(),
            'fonts': {
                'default': ('Arial', 10),
                'heading': ('Arial', 12, 'bold'),
                'monospace': ('Courier', 10)
            },
            'padding': {
                'small': 5,
                'medium': 10,
                'large': 15
            },
            'window': {
                'min_width': 800,
                'min_height': 600,
                'default_width': 1280,
                'default_height': 800
            }
        }
        
    def get_translation_config(self):
        """获取翻译相关配置"""
        return {
            'batch_size': 10,  # 批量翻译数量
            'timeout': 30,     # API超时时间
            'retry_times': 3,  # 重试次数
            'cache_size': 1000 # 翻译缓存大小
        }
        
    def get_file_config(self):
        """获取文件处理相关配置"""
        return {
            'supported_formats': ['.wav', '.mp3', '.ogg', '.flac'],
            'max_filename_length': 100,
            'default_category': 'SFXMisc',
            'category_folder_template': '{cat_id}_{cat_name}'
        }
        
    def get_logging_config(self):
        """获取日志配置"""
        return {
            'level': 'DEBUG',
            'format': '%(asctime)s - %(levelname)s - %(message)s',
            'file': 'audio_translator.log',
            'max_size': 1024 * 1024,  # 1MB
            'backup_count': 5
        }

    def get_category_config(self):
        """获取分类相关配置"""
        return {
            'data_file': 'data/_categorylist.csv',
            'auto_categorize': True,
            'use_subcategory': True,
            'match_weights': {
                'cat_id': 4,
                'name': 3,
                'subcategory': 3,
                'synonym': 2
            }
        }

    def validate_config(self):
        """验证配置完整性"""
        required_fields = [
            'TRANSLATION_SERVICE',
            'TRANSLATION_SERVICES',
            'PROMPT_TEMPLATES',
            'UI_THEME',
            'COLORS'
        ]
        
        for field in required_fields:
            if field not in self._config:
                return False
            
        return True

    def migrate_config(self):
        """配置版本迁移"""
        current_version = self._config.get('version', '1.0.0')
        if current_version != self.version:
            # 执行迁移逻辑
            if current_version == '1.0.0':
                self._migrate_to_1_0_1()
            
            self._config['version'] = self.version
            self.save()

    def _migrate_to_1_0_1(self):
        """迁移到1.0.1版本"""
        # 添加新配置项
        if 'UI_THEME' not in self._config:
            self._config['UI_THEME'] = 'dark'
        
        # 更新服务配置结构
        services = self._config.get('TRANSLATION_SERVICES', {})
        for service in services.values():
            if 'headers' not in service:
                service['headers'] = {
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {service.get('api_key', '')}"
                }

    def export_config(self, filepath):
        """导出配置到文件"""
        try:
            # 移除敏感信息
            config = self.copy()
            for service in config['TRANSLATION_SERVICES'].values():
                service['api_key'] = '******'
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            
            return True
        except Exception as e:
            logging.error(f"导出配置失败: {e}")
            return False

    def import_config(self, filepath):
        """从文件导入配置"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                new_config = json.load(f)
            
            # 验证导入的配置
            if not self._validate_imported_config(new_config):
                raise ValueError("导入的配置格式无效")
            
            # 保留原有的敏感信息
            for service_id, service in new_config['TRANSLATION_SERVICES'].items():
                if service_id in self._config['TRANSLATION_SERVICES']:
                    service['api_key'] = self._config['TRANSLATION_SERVICES'][service_id]['api_key']
            
            self._config = new_config
            self.save()
            return True
        except Exception as e:
            logging.error(f"导入配置失败: {e}")
            return False

    def add_listener(self, callback):
        """添加配置变更监听器"""
        self._listeners.append(callback)
        
    def remove_listener(self, callback):
        """移除配置变更监听器"""
        if callback in self._listeners:
            self._listeners.remove(callback)
            
    def _notify_listeners(self, event):
        """通知所有监听器"""
        for listener in self._listeners:
            try:
                listener(event)
            except Exception as e:
                logging.error(f"配置监听器执行失败: {e}")

    def test_connection(self):
        """测试API连接"""
        try:
            # 设置更长的超时时间
            timeout = 30
            
            # 添加重试机制
            for attempt in range(3):  # 最多重试3次
                try:
                    response = requests.post(
                        self.api_url,
                        headers=self.headers,
                        json=self.data,
                        timeout=timeout
                    )
                    return response
                    
                except requests.Timeout:
                    if attempt < 2:  # 如果不是最后一次尝试
                        logging.warning(f"连接超时，正在进行第{attempt+2}次尝试...")
                        timeout += 10  # 每次增加超时时间
                        continue
                    raise
                    
                except requests.RequestException as e:
                    logging.error(f"API请求失败: {e}")
                    raise
                    
        except Exception as e:
            logging.error(f"测试连接失败: {e}")
            raise
