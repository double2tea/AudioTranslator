"""
服务注册辅助模块

此模块提供了手动注册和初始化特定服务的功能，
特别是针对那些通过正常机制无法注册的服务。
"""

import logging
from typing import Dict, Any, Optional

# 导入服务工厂
from .core.service_factory import ServiceFactory

# 导入需要手动注册的服务
from .business.translation.translation_manager import TranslationManager
from .business.naming.naming_service import NamingService
from .infrastructure.config_service import ConfigService
from .business.category.category_service import CategoryService

# 设置日志记录器
logger = logging.getLogger(__name__)

def register_config_service(service_factory: ServiceFactory, config: Optional[Dict[str, Any]] = None) -> bool:
    """
    手动注册并初始化ConfigService服务
    
    Args:
        service_factory: 服务工厂实例
        config: 服务配置
        
    Returns:
        注册是否成功
    """
    try:
        # 创建ConfigService实例
        service_name = 'config_service'
        service = ConfigService(config)
        
        # 注册服务
        service_factory._services[service_name] = service
        
        # 初始化服务
        if service.initialize():
            service_factory._initialized_services.add(service_name)
            logger.info(f"手动注册的服务 '{service_name}' 初始化成功")
            # 设置单例实例，确保其他服务可以通过 get_instance() 获取到相同的实例
            ServiceFactory._instance = service_factory
            return True
        else:
            logger.error(f"手动注册的服务 '{service_name}' 初始化失败")
            return False
    
    except Exception as e:
        logger.error(f"手动注册ConfigService服务失败: {e}")
        return False

def register_translation_manager(service_factory: ServiceFactory, config: Optional[Dict[str, Any]] = None) -> bool:
    """
    手动注册并初始化TranslationManager服务
    
    Args:
        service_factory: 服务工厂实例
        config: 服务配置
        
    Returns:
        注册是否成功
    """
    try:
        # 创建TranslationManager实例
        service_name = 'translation_manager_service'
        service = TranslationManager(config)
        
        # 设置服务工厂
        service.service_factory = service_factory
        
        # 注册服务
        service_factory._services[service_name] = service
        
        # 初始化服务
        if service.initialize():
            service_factory._initialized_services.add(service_name)
            logger.info(f"手动注册的服务 '{service_name}' 初始化成功")
            return True
        else:
            logger.error(f"手动注册的服务 '{service_name}' 初始化失败")
            return False
    
    except Exception as e:
        logger.error(f"手动注册TranslationManager服务失败: {e}")
        return False

def register_naming_service(service_factory: ServiceFactory, config: Optional[Dict[str, Any]] = None) -> bool:
    """
    手动注册并初始化NamingService服务
    
    Args:
        service_factory: 服务工厂实例
        config: 服务配置
        
    Returns:
        注册是否成功
    """
    try:
        # 创建NamingService实例
        service_name = 'naming_service'
        service = NamingService(config)
        
        # 设置服务工厂
        service.service_factory = service_factory
        
        # 注册服务
        service_factory._services[service_name] = service
        
        # 初始化服务
        if service.initialize():
            service_factory._initialized_services.add(service_name)
            logger.info(f"手动注册的服务 '{service_name}' 初始化成功")
            return True
        else:
            logger.error(f"手动注册的服务 '{service_name}' 初始化失败")
            return False
    
    except Exception as e:
        logger.error(f"手动注册NamingService服务失败: {e}")
        return False

def register_category_service(service_factory: ServiceFactory, config: Optional[Dict[str, Any]] = None) -> bool:
    """
    手动注册并初始化CategoryService服务
    
    Args:
        service_factory: 服务工厂实例
        config: 服务配置
        
    Returns:
        注册是否成功
    """
    try:
        # 确保config_service已经初始化
        if not service_factory.has_service('config_service') or 'config_service' not in service_factory._initialized_services:
            logger.error("CategoryService依赖于ConfigService，但ConfigService未初始化")
            return False
            
        # 创建CategoryService实例
        service_name = 'category_service'
        service = CategoryService(config)
        
        # 设置服务工厂，确保CategoryService可以访问到正确的服务工厂实例
        if hasattr(service, 'service_factory'):
            service.service_factory = service_factory
        
        # 注册服务
        service_factory._services[service_name] = service
        
        # 初始化服务前，确保ServiceFactory._instance已设置为当前service_factory
        # 这样CategoryService在初始化时通过ServiceFactory.get_instance()获取的就是当前实例
        old_instance = ServiceFactory._instance
        ServiceFactory._instance = service_factory
        
        # 初始化服务
        success = service.initialize()
        
        # 恢复原来的实例（如果需要）
        if old_instance is not None and old_instance is not service_factory:
            ServiceFactory._instance = old_instance
        
        if success:
            service_factory._initialized_services.add(service_name)
            logger.info(f"手动注册的服务 '{service_name}' 初始化成功")
            return True
        else:
            logger.error(f"手动注册的服务 '{service_name}' 初始化失败")
            return False
    
    except Exception as e:
        logger.error(f"手动注册CategoryService服务失败: {e}")
        return False

def register_missing_services(service_factory: ServiceFactory) -> bool:
    """
    注册所有缺失的服务
    
    Args:
        service_factory: 服务工厂实例
        
    Returns:
        是否全部注册成功
    """
    success = True
    
    # 确保我们使用的是单例实例
    singleton = ServiceFactory.get_instance()
    if singleton is not service_factory:
        logger.warning("检测到不一致的ServiceFactory实例，将使用单例实例")
        service_factory = singleton
    
    # 首先确保config_service注册并初始化，因为其他服务依赖它
    if not service_factory.has_service('config_service') or 'config_service' not in service_factory._initialized_services:
        if not register_config_service(service_factory):
            success = False
    
    # 确保category_service注册并初始化
    if not service_factory.has_service('category_service') or 'category_service' not in service_factory._initialized_services:
        if not register_category_service(service_factory):
            success = False
    
    # 尝试注册TranslationManager服务
    if not service_factory.has_service('translation_manager_service'):
        if not register_translation_manager(service_factory):
            success = False
    
    # 尝试注册NamingService服务
    if not service_factory.has_service('naming_service'):
        if not register_naming_service(service_factory):
            success = False
    
    if success:
        logger.info("所有缺失服务已成功注册")
    else:
        logger.warning("部分缺失服务注册失败")
        
    return success 