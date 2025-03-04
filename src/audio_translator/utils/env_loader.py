"""
环境变量加载工具。
允许从.env文件加载环境变量。
"""
import os
import logging
from pathlib import Path
from typing import Optional, Dict

class EnvLoader:
    """环境变量加载器"""
    
    @staticmethod
    def load_dotenv(env_file: Optional[str] = None) -> bool:
        """
        从.env文件加载环境变量
        
        Args:
            env_file: 环境变量文件路径，默认为项目根目录下的.env文件
            
        Returns:
            bool: 是否成功加载
        """
        if env_file is None:
            # 尝试从当前目录、项目根目录查找.env文件
            possible_paths = [
                '.env',
                '../.env', 
                '../../.env',
                str(Path.home() / '.audio_translator.env')
            ]
            
            for path in possible_paths:
                if os.path.isfile(path):
                    env_file = path
                    break
        
        if not env_file or not os.path.isfile(env_file):
            logging.warning(f"未找到.env文件")
            return False
            
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 移除引号
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                        
                    os.environ[key] = value
                    
            logging.info(f"从 {env_file} 加载了环境变量")
            return True
            
        except Exception as e:
            logging.error(f"加载环境变量文件 {env_file} 失败: {str(e)}")
            return False
    
    @staticmethod
    def get_env(key: str, default: str = '') -> str:
        """
        获取环境变量值
        
        Args:
            key: 环境变量名
            default: 默认值
            
        Returns:
            str: 环境变量值
        """
        return os.environ.get(key, default)
        
    @staticmethod
    def parse_env_vars(config: Dict) -> Dict:
        """
        解析配置中的环境变量引用
        
        Args:
            config: 配置字典
            
        Returns:
            Dict: 解析后的配置
        """
        if not isinstance(config, dict):
            return config
            
        result = {}
        for key, value in config.items():
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]
                result[key] = os.environ.get(env_var, '')
                if not result[key]:
                    logging.warning(f"环境变量 {env_var} 未设置或为空")
            elif isinstance(value, dict):
                result[key] = EnvLoader.parse_env_vars(value)
            elif isinstance(value, list):
                result[key] = [
                    EnvLoader.parse_env_vars(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
                
        return result 