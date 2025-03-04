"""
音频翻译器服务包

此包包含应用程序的核心服务层，提供以下基础服务：
- BaseService: 服务基类，定义了所有服务的通用接口
- FileService: 提供文件系统操作服务
- AudioService: 提供音频处理服务
- ConfigService: 提供配置管理服务
- UCSService: 提供UCS标准解析服务
- ServiceManagerService: 提供翻译服务管理服务
- ServiceFactory: 服务工厂，管理所有服务实例
"""

from .core.base_service import BaseService
from .infrastructure.file_service import FileService
from .business.audio_service import AudioService
from .infrastructure.config_service import ConfigService
from .business.ucs.ucs_service import UCSService
from .core.service_manager_service import ServiceManagerService
from .core.service_factory import ServiceFactory

__all__ = [
    'BaseService',
    'FileService',
    'AudioService',
    'ConfigService',
    'UCSService',
    'ServiceManagerService',
    'ServiceFactory',
]
