"""
基础服务抽象类模块

此模块定义了应用程序服务的基本接口和功能，为所有服务提供一个统一的基类。
服务是应用程序的核心功能单元，负责执行特定的业务逻辑。
"""

import abc
import logging
from typing import Any, Dict, Optional

# 设置日志记录器
logger = logging.getLogger(__name__)

class BaseService(abc.ABC):
    """
    服务基类
    
    为应用程序中的所有服务组件提供基本接口和功能。
    服务组件负责应用程序的业务逻辑，如文件处理、音频处理、翻译等。
    
    Attributes:
        name: 服务名称
        config: 服务配置
        is_initialized: 服务是否已初始化
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化服务
        
        Args:
            name: 服务名称
            config: 服务配置
        """
        self.name = name
        self.config = config or {}
        self.is_initialized = False
        logger.debug(f"创建服务: {name}")
    
    @abc.abstractmethod
    def initialize(self) -> bool:
        """
        初始化服务
        
        子类必须实现此方法以进行服务特定的初始化工作。
        
        Returns:
            初始化是否成功
        """
        pass
    
    def shutdown(self) -> bool:
        """
        关闭服务
        
        执行必要的清理工作，以便安全地关闭服务。
        
        Returns:
            关闭是否成功
        """
        logger.debug(f"关闭服务: {self.name}")
        self.is_initialized = False
        return True
    
    def get_name(self) -> str:
        """
        获取服务名称
        
        Returns:
            服务名称
        """
        return self.name
    
    def is_available(self) -> bool:
        """
        检查服务是否可用
        
        Returns:
            服务是否可用
        """
        return self.is_initialized
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取服务配置
        
        Returns:
            服务配置
        """
        return self.config
    
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """
        更新服务配置
        
        Args:
            new_config: 新的配置项
            
        Returns:
            配置更新是否成功
        """
        try:
            self.config.update(new_config)
            logger.debug(f"更新服务配置: {self.name}")
            return True
        except Exception as e:
            logger.error(f"更新服务配置失败: {e}")
            return False 