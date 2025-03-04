"""
服务注册表类，负责管理模型配置
"""
import logging
import uuid
from typing import Dict, Any, Optional, List

class ServiceRegistry:
    """服务注册表，负责管理模型配置"""
    
    def __init__(self, config_service):
        """
        初始化服务注册表
        
        Args:
            config_service: 配置服务实例，用于读写配置
        """
        self.config_service = config_service
        self.services = {}
        self.logger = logging.getLogger(__name__)
        self._load_services()
    
    def _load_services(self) -> None:
        """从配置服务加载服务列表"""
        try:
            self.services = self.config_service.get_services() or {}
            self.logger.info(f"成功加载 {len(self.services)} 个服务配置")
        except Exception as e:
            self.logger.error(f"加载服务配置失败: {e}")
            self.services = {}
    
    def register_service(self, service_config: Dict[str, Any]) -> Optional[str]:
        """
        注册一个新服务
        
        Args:
            service_config: 服务配置字典
            
        Returns:
            str: 成功返回服务ID，失败返回None
        """
        try:
            service_id = service_config.get('id') or str(uuid.uuid4())
            service_config['id'] = service_id
            
            # 保存到内存和配置文件
            self.services[service_id] = service_config
            self._save_services()
            
            self.logger.info(f"成功注册服务: {service_config.get('name', '未命名')}")
            return service_id
        except Exception as e:
            self.logger.error(f"注册服务失败: {e}")
            return None
    
    def unregister_service(self, service_id: str) -> bool:
        """
        注销一个服务
        
        Args:
            service_id: 服务ID
            
        Returns:
            bool: 成功返回True，失败返回False
        """
        try:
            if service_id in self.services:
                service_name = self.services[service_id].get('name', '未命名')
                del self.services[service_id]
                self._save_services()
                self.logger.info(f"成功注销服务: {service_name}")
                return True
            self.logger.warning(f"注销服务失败: 找不到ID为{service_id}的服务")
            return False
        except Exception as e:
            self.logger.error(f"注销服务失败: {e}")
            return False
    
    def update_service(self, service_id: str, service_config: Dict[str, Any]) -> bool:
        """
        更新服务配置
        
        Args:
            service_id: 服务ID
            service_config: 新的服务配置
            
        Returns:
            bool: 成功返回True，失败返回False
        """
        try:
            if service_id in self.services:
                service_config['id'] = service_id
                self.services[service_id] = service_config
                self._save_services()
                self.logger.info(f"成功更新服务: {service_config.get('name', '未命名')}")
                return True
            self.logger.warning(f"更新服务失败: 找不到ID为{service_id}的服务")
            return False
        except Exception as e:
            self.logger.error(f"更新服务失败: {e}")
            return False
    
    def get_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定服务的配置
        
        Args:
            service_id: 服务ID
            
        Returns:
            Dict: 服务配置，找不到返回None
        """
        return self.services.get(service_id)
    
    def get_all_services(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有服务配置
        
        Returns:
            Dict: 服务ID到服务配置的映射
        """
        return self.services.copy()
    
    def get_enabled_services(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有启用的服务配置
        
        Returns:
            Dict: 服务ID到服务配置的映射，仅包含启用的服务
        """
        return {k: v for k, v in self.services.items() if v.get('enabled', True)}
    
    def get_services_by_type(self, service_type: str) -> List[Dict[str, Any]]:
        """
        按类型获取服务列表
        
        Args:
            service_type: 服务类型
            
        Returns:
            List: 服务配置列表
        """
        return [v for v in self.services.values() if v.get('type') == service_type]
    
    def _save_services(self) -> bool:
        """
        保存服务配置到配置文件
        
        Returns:
            bool: 成功返回True，失败返回False
        """
        try:
            self.config_service.save_services(self.services)
            return True
        except Exception as e:
            self.logger.error(f"保存服务配置失败: {e}")
            return False 