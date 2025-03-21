"""
服务工厂模块

此模块提供服务工厂类，用于管理应用程序中所有的服务实例，确保服务的单例性和依赖关系管理。
服务工厂负责创建、初始化、获取和关闭服务实例，简化了服务管理的复杂性。
"""

import logging
from typing import Dict, Any, Optional, Type, Set
import importlib

from .base_service import BaseService
from .interfaces import IServiceRegistry
from ..infrastructure.file_service import FileService
from ..business.audio_service import AudioService
from ..infrastructure.config_service import ConfigService
from ..business.ucs.ucs_service import UCSService
from .service_manager_service import ServiceManagerService

from ..business.translator_service import TranslatorService
from ..business.theme_service import ThemeService
from ..api.providers.openai.openai_service import OpenAIService
from ..api.providers.anthropic.anthropic_service import AnthropicService
from ..api.providers.gemini.gemini_service import GeminiService
from ..api.providers.volc.volc_service import VolcEngineService
from ..api.providers.zhipu.zhipu_service import ZhipuAIService
from ..api.providers.alibaba.alibaba_service import AlibabaService
from ..api.providers.deepseek.deepseek_service import DeepSeekService

# 设置日志记录器
logger = logging.getLogger(__name__)

class ServiceFactory(IServiceRegistry):
    """
    服务工厂类
    
    管理应用程序中所有服务实例，确保服务的单例性和依赖关系的正确初始化。
    主要功能：
    - 创建并管理服务实例
    - 维护服务间的依赖关系
    - 提供获取服务的统一接口
    - 确保服务的正确初始化和关闭
    """
    
    # 单例实例
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
            logger.info("创建ServiceFactory单例实例")
        return cls._instance
    
    def __init__(self):
        """初始化服务工厂"""
        # 如果已存在实例，直接返回该实例
        if ServiceFactory._instance is not None and self != ServiceFactory._instance:
            logger.warning("尝试创建新的ServiceFactory实例，但已存在单例实例")
            return
            
        # 存储已创建的服务实例
        self._services: Dict[str, BaseService] = {}
        # 记录已初始化的服务
        self._initialized_services: Set[str] = set()
        # 记录服务依赖关系
        self._dependencies: Dict[str, Set[str]] = {}
        # 服务配置
        self._services_config: Dict[str, Dict[str, Any]] = {}
        
        # 注册核心服务
        self._register_core_services()
        
        logger.debug("服务工厂已创建")
        
        self._service_classes = {
            # 基础服务
            'config_service': 'audio_translator.services.infrastructure.config_service.ConfigService',
            'file_service': 'audio_translator.services.infrastructure.file_service.FileService',
            
            # 业务服务
            'audio_service': 'audio_translator.services.business.audio_service.AudioService',
            'translator_service': 'audio_translator.services.business.translator_service.TranslatorService',
            'category_service': 'audio_translator.services.business.category.category_service.CategoryService',
            'theme_service': 'audio_translator.services.business.theme_service.ThemeService',
            'ucs_service': 'audio_translator.services.business.ucs.ucs_service.UCSService',
            'naming_service': 'audio_translator.services.business.naming.naming_service.NamingService',
            'translation_manager_service': 'audio_translator.services.business.translation.translation_manager.TranslationManager',
            'service_manager_service': 'audio_translator.services.core.service_manager_service.ServiceManagerService',
            
            # API服务
            'model_service': 'audio_translator.services.api.model_service.ModelService',
            'openai_service': 'audio_translator.services.api.providers.openai.openai_service.OpenAIService',
            'anthropic_service': 'audio_translator.services.api.providers.anthropic.anthropic_service.AnthropicService',
            'gemini_service': 'audio_translator.services.api.providers.gemini.gemini_service.GeminiService',
            'alibaba_service': 'audio_translator.services.api.providers.alibaba.alibaba_service.AlibabaService',
            'zhipu_service': 'audio_translator.services.api.providers.zhipu.zhipu_service.ZhipuService',
        }
    
    def _register_core_services(self):
        """注册核心服务"""
        # 注册配置服务（无依赖）
        self._dependencies["config_service"] = set()
        
        # 注册文件服务（依赖配置服务）
        self._dependencies["file_service"] = {"config_service"}
        
        # 注册音频服务（依赖文件服务和配置服务）
        self._dependencies["audio_service"] = {"file_service", "config_service"}
        
        # 注册UCS服务（依赖配置服务）
        self._dependencies["ucs_service"] = {"config_service"}
        
        # 注册服务管理器服务（依赖配置服务）
        self._dependencies["service_manager_service"] = {"config_service"}
        
        # 注册翻译服务（依赖配置服务和UCS服务）
        self._dependencies["translator_service"] = {"config_service", "ucs_service"}
        
        # 注册分类服务（依赖配置服务）
        self._dependencies["category_service"] = {"config_service"}
        
        # 注册主题服务（依赖配置服务）
        self._dependencies["theme_service"] = {"config_service"}
        
        logger.debug("核心服务已注册")
    
    def register_service(self, service_name: str, service_instance: Any) -> bool:
        """
        注册服务实例
        
        Args:
            service_name: 服务名称
            service_instance: 服务实例
            
        Returns:
            注册是否成功
        """
        try:
            if not isinstance(service_instance, BaseService):
                logger.warning(f"注册服务失败: {service_name} 不是BaseService的实例")
                return False
                
            self._services[service_name] = service_instance
            
            # 如果服务已初始化，添加到已初始化服务集合
            if service_instance.is_available():
                self._initialized_services.add(service_name)
                
            logger.info(f"成功注册服务: {service_name}")
            return True
        except Exception as e:
            logger.error(f"注册服务失败: {service_name}, {e}")
            return False
    
    def register_service_config(self, service_name: str, service_config: Dict[str, Any]) -> bool:
        """
        注册服务配置
        
        Args:
            service_name: 服务名称
            service_config: 服务配置
            
        Returns:
            注册是否成功
        """
        try:
            self._services_config[service_name] = service_config
            logger.info(f"成功注册服务配置: {service_name}")
            return True
        except Exception as e:
            logger.error(f"注册服务配置失败: {service_name}, {e}")
            return False
    
    def get_service(self, service_name: str) -> Optional[BaseService]:
        """
        获取服务实例
        
        如果服务实例不存在，会先创建并初始化服务及其依赖。
        如果服务存在但未初始化或已关闭，会重新初始化它。
        
        Args:
            service_name: 服务名称
            
        Returns:
            服务实例，如果获取失败则返回 None
        """
        try:
            # 如果服务已存在且已初始化，直接返回
            if service_name in self._services and service_name in self._initialized_services:
                # 额外检查服务是否实际可用（可能已被关闭）
                service = self._services[service_name]
                if service and hasattr(service, 'is_available') and callable(service.is_available) and service.is_available():
                    return service
                elif service and hasattr(service, 'is_initialized') and service.is_initialized:
                    return service
            
            # 如果服务未注册且不在依赖关系中，返回 None
            if service_name not in self._dependencies and service_name not in self._services:
                logger.error(f"未注册的服务类型 '{service_name}'")
                return None
            
            # 如果服务存在但未初始化或已关闭
            if service_name in self._services:
                # 如果服务在 _initialized_services 中但实际不可用，从 _initialized_services 中移除
                service = self._services[service_name]
                is_available = False
                
                if hasattr(service, 'is_available') and callable(service.is_available):
                    is_available = service.is_available()
                elif hasattr(service, 'is_initialized'):
                    is_available = service.is_initialized
                
                if service_name in self._initialized_services and not is_available:
                    self._initialized_services.remove(service_name)
                
                # 尝试初始化服务
                if not self._initialize_service(service_name):
                    logger.error(f"初始化服务 '{service_name}' 失败")
                    return None
                return self._services[service_name]
            
            # 创建服务
            if self._create_service(service_name):
                return self._services[service_name]
            
            logger.error(f"服务 '{service_name}' 创建失败")
            return None
            
        except Exception as e:
            logger.error(f"获取服务 '{service_name}' 时发生错误: {str(e)}")
            return None
    
    def has_service(self, service_name: str) -> bool:
        """
        检查服务是否存在
        
        Args:
            service_name: 服务名称
            
        Returns:
            服务是否存在
        """
        return service_name in self._services
    
    def _create_service(self, service_name: str) -> bool:
        """
        创建服务实例
        
        Args:
            service_name: 服务名称
            
        Returns:
            创建是否成功
        """
        try:
            # 获取服务类路径
            service_class_path = self._service_classes.get(service_name)
            if not service_class_path:
                logger.error(f"未知的服务类型: {service_name}")
                return False
                
            # 动态导入服务类
            module_path, class_name = service_class_path.rsplit('.', 1)
            try:
                module = importlib.import_module(module_path)
                service_class = getattr(module, class_name)
            except (ImportError, AttributeError) as e:
                logger.error(f"导入服务类失败: {service_name}, {e}")
                return False
            
            # 获取服务配置
            config = self._services_config.get(service_name, {})
            
            # 创建服务实例
            if service_name == 'config_service':
                # 配置服务需要特殊处理，直接传递config_file参数
                config_file = config.get('config_file')
                service = service_class(config_file)
            elif service_name in ['translation_manager_service', 'service_manager_service']:
                # 这些服务需要特殊处理
                try:
                    # 首先尝试使用标准参数创建服务
                    service = service_class(config)
                except TypeError:
                    # 如果失败，尝试适配接口
                    logger.debug(f"使用特殊参数创建服务: {service_name}")
                    # 创建的服务可能需要名称参数
                    service = service_class(service_name, config)
            else:
                # 其他服务正常传递配置字典
                service = service_class(config)
            
            # 设置服务的service_factory属性，以便服务可以获取其依赖
            if hasattr(service, 'service_factory'):
                service.service_factory = self
            
            # 注册服务
            self._services[service_name] = service
            
            # 初始化服务
            if isinstance(service, BaseService):
                if service.initialize():
                    self._initialized_services.add(service_name)
                    logger.info(f"服务 '{service_name}' 初始化成功")
                else:
                    logger.error(f"服务初始化失败: {service_name}")
                    return False
            
            logger.info(f"服务创建成功: {service_name}")
            return True
        except Exception as e:
            logger.error(f"创建服务失败: {service_name}, {e}")
            return False
    
    def _initialize_service(self, service_name: str) -> bool:
        """
        初始化服务
        
        初始化指定的服务及其依赖。
        
        Args:
            service_name: 服务名称
            
        Returns:
            初始化是否成功
        """
        try:
            logger.info(f"正在初始化服务: {service_name}")
            
            # 如果服务已初始化，直接返回成功
            if service_name in self._initialized_services:
                service = self._services[service_name]
                if hasattr(service, 'is_initialized') and service.is_initialized:
                    logger.debug(f"服务 '{service_name}' 已初始化，跳过")
                    return True
                
                # 如果服务标记为已初始化但实际上没有初始化，移除标记
                self._initialized_services.remove(service_name)
            
            # 如果服务不存在，创建服务
            if service_name not in self._services:
                if not self._create_service(service_name):
                    logger.error(f"无法创建服务 '{service_name}'")
                    return False
            
            # 获取服务实例
            service = self._services[service_name]
            
            # 初始化依赖
            if service_name in self._dependencies:
                for dependency in self._dependencies[service_name]:
                    # 避免循环依赖
                    if dependency == service_name:
                        continue
                        
                    if dependency not in self._initialized_services:
                        if not self._initialize_service(dependency):
                            logger.error(f"初始化依赖 '{dependency}' 失败")
                            return False
            
            # 调用服务的初始化方法
            if hasattr(service, 'is_initialized') and service.is_initialized:
                logger.debug(f"服务 '{service_name}' 已经初始化过")
                self._initialized_services.add(service_name)
                return True
                
            # 如果服务有service_factory属性，设置为当前实例
            if hasattr(service, 'service_factory'):
                service.service_factory = self
                
            # 确保我们是单例实例
            ServiceFactory._instance = self
                
            # 调用初始化方法
            if service.initialize():
                self._initialized_services.add(service_name)
                logger.info(f"服务 '{service_name}' 初始化成功")
                return True
            else:
                logger.error(f"服务 '{service_name}' 初始化失败")
                return False
                
        except Exception as e:
            logger.error(f"初始化服务 '{service_name}' 时发生错误: {e}")
            return False
    
    def initialize_all_services(self) -> bool:
        """
        初始化所有已注册的服务
        
        Returns:
            是否全部初始化成功
        """
        success = True
        for service_name in self._dependencies.keys():
            if not self.get_service(service_name):
                logger.error(f"初始化服务 '{service_name}' 失败")
                success = False
        
        if success:
            logger.info("所有服务初始化成功")
        else:
            logger.error("部分服务初始化失败")
        
        return success
    
    def shutdown_all_services(self) -> bool:
        """
        关闭所有已初始化的服务
        
        按照依赖关系的反序关闭服务
        
        Returns:
            是否全部关闭成功
        """
        # 构建服务依赖图的反序
        reverse_deps = {}
        for service_name, deps in self._dependencies.items():
            for dep in deps:
                if dep not in reverse_deps:
                    reverse_deps[dep] = set()
                reverse_deps[dep].add(service_name)
        
        # 获取所有已初始化的服务
        services_to_shutdown = list(self._initialized_services)
        
        # 关闭服务的顺序：先关闭被依赖少的服务
        shutdown_order = []
        while services_to_shutdown:
            # 找出没有依赖的服务
            next_services = []
            for service_name in services_to_shutdown:
                if service_name not in reverse_deps or not any(dep in services_to_shutdown for dep in reverse_deps.get(service_name, set())):
                    next_services.append(service_name)
            
            if not next_services:
                # 如果存在循环依赖，直接按剩余顺序关闭
                logger.warning("服务之间可能存在循环依赖，按默认顺序关闭")
                shutdown_order.extend(services_to_shutdown)
                break
            
            # 将这些服务添加到关闭顺序中
            shutdown_order.extend(next_services)
            
            # 从待关闭列表中移除
            for service_name in next_services:
                services_to_shutdown.remove(service_name)
        
        # 按顺序关闭服务
        success = True
        for service_name in shutdown_order:
            service = self._services.get(service_name)
            if service:
                logger.info(f"正在关闭服务: {service_name}")
                if service.shutdown():
                    self._initialized_services.remove(service_name)
                    logger.info(f"服务 '{service_name}' 已关闭")
                else:
                    logger.error(f"关闭服务 '{service_name}' 失败")
                    success = False
        
        if success:
            logger.info("所有服务已关闭")
        else:
            logger.error("部分服务关闭失败")
        
        return success
    
    def get_file_service(self) -> Optional[FileService]:
        """
        获取文件服务
        
        Returns:
            文件服务实例，如果获取失败则返回 None
        """
        try:
            service = self.get_service('file_service')
            # 确保返回的是正确的类型
            if service and isinstance(service, FileService):
                return service
            else:
                # 直接从_services字典获取
                direct_service = self._services.get('file_service')
                if direct_service and isinstance(direct_service, FileService):
                    # 确保服务已初始化
                    if direct_service.is_initialized:
                        if 'file_service' not in self._initialized_services:
                            self._initialized_services.add('file_service')
                        return direct_service
                    elif self._initialize_service('file_service'):
                        return direct_service
                # 如果直接获取失败，尝试创建新服务
                logger.warning("无法获取文件服务，尝试创建新实例")
                if self._create_service('file_service'):
                    return self._services.get('file_service')
                return None
        except Exception as e:
            logger.error(f"获取文件服务失败: {e}")
            return None
    
    def get_audio_service(self) -> Optional[AudioService]:
        """
        获取音频服务
        
        Returns:
            音频服务实例，如果获取失败则返回 None
        """
        try:
            service = self.get_service('audio_service')
            # 确保返回的是正确的类型
            if service and isinstance(service, AudioService):
                return service
            else:
                # 直接从_services字典获取
                direct_service = self._services.get('audio_service')
                if direct_service and isinstance(direct_service, AudioService):
                    # 确保服务已初始化
                    if direct_service.is_initialized:
                        if 'audio_service' not in self._initialized_services:
                            self._initialized_services.add('audio_service')
                        return direct_service
                    elif self._initialize_service('audio_service'):
                        return direct_service
                # 如果直接获取失败，尝试创建新服务
                logger.warning("无法获取音频服务，尝试创建新实例")
                if self._create_service('audio_service'):
                    return self._services.get('audio_service')
                return None
        except Exception as e:
            logger.error(f"获取音频服务失败: {e}")
            return None
    
    def get_config_service(self) -> Optional[ConfigService]:
        """
        获取配置服务
        
        Returns:
            配置服务实例
        """
        service = self.get_service("config_service")
        return service if isinstance(service, ConfigService) else None
    
    def get_category_service(self) -> Optional['CategoryService']:
        """
        获取分类服务
        
        Returns:
            分类服务实例
        """
        service = self.get_service("category_service")
        # 避免循环导入
        from ..business.category.category_service import CategoryService
        return service if isinstance(service, CategoryService) else None
    
    def get_ucs_service(self) -> Optional[UCSService]:
        """
        获取UCS服务实例
        
        Returns:
            UCS服务实例，如果获取失败则返回 None
        """
        service = self.get_service("ucs_service")
        return service if isinstance(service, UCSService) else None
    
    def get_service_manager_service(self) -> Optional[ServiceManagerService]:
        """
        获取服务管理器服务实例
        
        Returns:
            服务管理器服务实例，如果获取失败则返回 None
        """
        service = self.get_service("service_manager_service")
        return service if isinstance(service, ServiceManagerService) else None
    
    def get_translator_service(self) -> Optional[TranslatorService]:
        """
        获取翻译服务
        
        Returns:
            翻译服务实例，如果获取失败则返回 None
        """
        try:
            service = self.get_service('translator_service')
            # 确保返回的是正确的类型
            if service and isinstance(service, TranslatorService):
                return service
            else:
                # 直接从_services字典获取
                direct_service = self._services.get('translator_service')
                if direct_service and isinstance(direct_service, TranslatorService):
                    # 确保服务已初始化
                    if direct_service.is_initialized:
                        if 'translator_service' not in self._initialized_services:
                            self._initialized_services.add('translator_service')
                        return direct_service
                    elif self._initialize_service('translator_service'):
                        return direct_service
                # 如果直接获取失败，尝试创建新服务
                logger.warning("无法获取翻译服务，尝试创建新实例")
                if self._create_service('translator_service'):
                    return self._services.get('translator_service')
                return None
        except Exception as e:
            logger.error(f"获取翻译服务失败: {e}")
            return None
    
    def get_all_services(self) -> Dict[str, Any]:
        """
        获取所有服务
        
        Returns:
            服务字典，键为服务名称，值为服务实例
        """
        return self._services.copy() 