from typing import Dict, List, Optional
import json
import logging
import uuid
from pathlib import Path
from ..api.model_service import ModelService
from ..api.providers.openai.openai_service import OpenAIService
from ..api.providers.anthropic.anthropic_service import AnthropicService
from ..api.providers.gemini.gemini_service import GeminiService
from ..api.providers.volc.volc_service import VolcEngineService
from ..api.providers.zhipu.zhipu_service import ZhipuAIService
from ..api.providers.alibaba.alibaba_service import AlibabaService
from ..api.providers.deepseek.deepseek_service import DeepSeekService
from ..business.ucs.ucs_service import UCSService
from .base_service import BaseService
from ...utils.events import EventManager, ServiceRegisteredEvent, ServiceUnregisteredEvent, ServiceUpdatedEvent
import os

# 设置日志记录器
logger = logging.getLogger(__name__)

class ServiceManagerService(BaseService):
    """
    服务管理器
    
    负责管理所有的AI模型服务。主要功能包括：
    - 注册和注销服务
    - 获取服务列表和特定服务
    - 测试服务连接
    - 加载和保存服务配置
    
    Attributes:
        config_path: 配置文件路径
        services: 服务字典，以service_id为键
        service_factory: 服务工厂实例，用于访问其他服务
    """
    
    def __init__(self, config_path: Optional[str] = None, service_factory=None):
        """
        初始化服务管理器
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
            service_factory: 服务工厂实例，用于访问其他服务
        """
        # 确保调用BaseService的构造函数时提供name参数
        super().__init__("service_manager_service")
        
        # 如果未提供配置路径，计算项目级配置目录
        if not config_path:
            # 从当前文件所在目录开始向上找，直到找到src/config目录
            current_file = Path(__file__).resolve()
            project_root = current_file.parent
            
            # 向上寻找直到找到src目录
            while project_root.name != "src" and project_root != project_root.parent:
                project_root = project_root.parent
                
            # 项目级配置目录路径
            config_dir = project_root / "config"
            
            if config_dir.exists():
                self.config_path = config_dir / "services.json"
                logger.info(f"使用项目级配置目录: {config_dir}")
            else:
                # 回退到旧路径（虽然这个分支应该不会再执行）
                self.config_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "config" / "services.json"
                logger.warning(f"项目级配置目录不存在，回退到包内配置: {self.config_path}")
        else:
            # 使用用户提供的配置路径
            self.config_path = Path(config_path)
        
        self.services: Dict[str, ModelService] = {}
        self.service_factory = service_factory
        
        # 创建事件管理器
        self.event_manager = EventManager.get_instance()
        
        # 加载配置
        self.load_config()
        
    def initialize(self) -> bool:
        """初始化服务"""
        # 注册事件类型
        self.event_manager.register_event_type("service_registered")
        self.event_manager.register_event_type("service_unregistered")
        self.event_manager.register_event_type("service_updated")
        
        # 确保配置同步
        if self.services:
            self.save_config()
            
        logger.info(f"服务管理器初始化完成，配置文件: {self.config_path}")
        return True
        
    def shutdown(self) -> bool:
        """关闭服务"""
        logger.info("服务管理器已关闭")
        return True
        
    def load_config(self) -> None:
        """从文件加载服务配置"""
        try:
            if self.config_path.exists():
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                except json.JSONDecodeError as je:
                    logger.error(f"服务配置文件格式错误: {je}，尝试恢复备份")
                    if self._restore_config_backup():
                        return
                    else:
                        # 如果无法恢复备份，创建空的服务配置
                        config = {'services': {}}
                
                services_config = config.get('services', {})
                
                # 清空当前服务字典，避免重复加载
                self.services.clear()
                
                # 加载所有服务配置，但不逐个保存
                for service_id, service_config in services_config.items():
                    try:
                        # 尝试从配置中获取服务类型，如果没有则尝试从服务ID推断
                        service_type = service_config.get('type', '').lower()
                        
                        # 如果没有提供type字段，尝试从服务名称或ID中推断
                        if not service_type:
                            # 检查提供商名称中的关键词
                            service_name = service_config.get('name', '').lower()
                            for known_type in self.get_available_services():
                                if known_type in service_name:
                                    service_type = known_type
                                    logger.warning(f"服务 {service_id} 配置中缺少type字段，从名称中推断为: {service_type}")
                                    service_config['type'] = service_type
                                    break
                            
                            # 如果仍然无法推断，记录警告并跳过
                            if not service_type:
                                logger.warning(f"服务 {service_id} 配置中缺少type字段，无法加载")
                                continue
                        
                        if service_type not in self.get_available_services():
                            logging.warning(f"不支持的服务类型: {service_type}，跳过加载")
                            continue
                            
                        # 确保current_model字段存在
                        if 'models' in service_config and service_config.get('models') and not service_config.get('current_model'):
                            first_model = service_config['models'][0]['name']
                            service_config['current_model'] = first_model
                            logger.warning(f"服务 {service_id} 配置中缺少current_model字段，使用第一个可用模型: {first_model}")
                            
                        service_class = self.get_service_class(service_type)
                        service = service_class(service_config)
                        
                        if not service.validate_config():
                            logging.warning(f"服务配置无效: {service_id}，跳过加载")
                            continue
                            
                        self.services[service_id] = service
                    except Exception as service_error:
                        logging.error(f"加载服务 {service_id} 失败: {str(service_error)}")
                
                # 所有服务加载完成后，记录日志
                logging.info(f"服务配置加载完成，共加载 {len(self.services)} 个服务")
                
                # 如果进行了字段修复，立即保存配置
                if len(self.services) > 0:
                    self.save_config()
            else:
                logger.info(f"服务配置文件不存在: {self.config_path}，将创建默认配置")
                # 配置文件不存在时，初始化为空字典
                self.services = {}
                
        except Exception as e:
            logging.error(f"加载服务配置失败: {str(e)}")
            
    def _create_config_backup(self) -> bool:
        """
        创建配置文件备份
        
        Returns:
            备份是否成功
        """
        if not self.config_path.exists():
            return False
            
        try:
            backup_file = self.config_path.with_name(f"{self.config_path.stem}_backup.json")
            with open(self.config_path, 'r', encoding='utf-8') as src:
                with open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            logger.debug(f"创建服务配置备份: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"创建服务配置备份失败: {e}")
            return False
    
    def _restore_config_backup(self) -> bool:
        """
        从备份恢复配置文件
        
        Returns:
            恢复是否成功
        """
        backup_file = self.config_path.with_name(f"{self.config_path.stem}_backup.json")
        if not backup_file.exists():
            logger.warning("服务配置备份文件不存在，无法恢复")
            return False
            
        try:
            with open(backup_file, 'r', encoding='utf-8') as src:
                with open(self.config_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            logger.info(f"从备份恢复服务配置: {backup_file}")
            
            # 重新加载配置
            self.load_config()
            
            return True
        except Exception as e:
            logger.error(f"恢复服务配置备份失败: {e}")
            return False
            
    def save_config(self) -> None:
        """保存服务配置到文件"""
        try:
            # 创建备份
            self._create_config_backup()
            
            # 构建服务配置字典
            services_dict = {
                service_id: service.to_dict()
                for service_id, service in self.services.items()
            }
            
            config = {
                'services': services_dict
            }
            
            # 记录即将保存的服务数量
            logger.info(f"正在保存服务配置，共 {len(services_dict)} 个服务")
            
            # 保存到文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
                
            logger.info(f"服务配置已保存到: {self.config_path}")
        except Exception as e:
            logging.error(f"保存服务配置失败: {str(e)}")
            # 尝试恢复备份
            self._restore_config_backup()
            
    def register_service(self, config: Dict) -> str:
        """
        注册新服务
        
        Args:
            config: 服务配置
            
        Returns:
            服务ID
            
        Raises:
            ValueError: 如果服务类型不支持或配置无效
        """
        try:
            service_id = config.get('service_id', str(uuid.uuid4()))
            service_type = config.get('type', '').lower()
            service_name = config.get('name', f'未命名{service_type}服务')
            
            if service_type not in self.get_available_services():
                raise ValueError(f"不支持的服务类型: {service_type}")
                
            service_class = self.get_service_class(service_type)
            service = service_class(config)
            
            if not service.validate_config():
                raise ValueError("服务配置无效")
                
            # 更新或添加服务ID
            config['service_id'] = service_id
            service = service_class(config)
            
            self.services[service_id] = service
            
            # 保存配置
            self.save_config()
            
            # 触发服务注册事件
            event = ServiceRegisteredEvent(self, service_id, service_type, service_name)
            self.event_manager.post_event(event)
            
            return service_id
        except Exception as e:
            logging.error(f"注册服务失败: {str(e)}")
            raise
            
    def unregister_service(self, service_id: str) -> None:
        """
        注销服务
        
        Args:
            service_id: 服务ID
        """
        if service_id in self.services:
            service = self.services[service_id]
            service_type = service.type
            
            del self.services[service_id]
            
            # 保存配置
            self.save_config()
            
            # 触发服务注销事件
            event = ServiceUnregisteredEvent(self, service_id, service_type)
            self.event_manager.post_event(event)
            
    def get_service(self, service_id: str) -> Optional[ModelService]:
        """
        获取服务实例
        
        Args:
            service_id: 服务ID
            
        Returns:
            服务实例，如果不存在则返回None
        """
        return self.services.get(service_id)
        
    def list_services(self) -> List[Dict]:
        """
        列出所有已注册服务
        
        Returns:
            服务信息列表
        """
        return [
            {
                'id': service_id,
                'name': service.name,
                'type': service.type,
                'enabled': service.enabled
            }
            for service_id, service in self.services.items()
        ]
        
    def update_service(self, service_id: str, config: Dict) -> None:
        """
        更新服务配置
        
        Args:
            service_id: 服务ID
            config: 新的配置信息
        """
        if service_id not in self.services:
            raise KeyError(f"服务ID '{service_id}' 不存在")
            
        # 获取当前服务实例
        service = self.services[service_id]
        
        # 特殊处理models字段，确保自定义模型不会被覆盖
        if 'models' in config and hasattr(service, 'models'):
            # 如果service.models是列表且包含自定义模型
            if isinstance(service.models, list):
                custom_models = []
                # 收集现有的自定义模型
                for model in service.models:
                    if isinstance(model, dict) and model.get('is_custom', False):
                        custom_models.append(model)
                        
                # 如果配置中的models是列表
                if isinstance(config['models'], list):
                    # 处理新配置的模型列表，保留原来的自定义模型
                    for custom_model in custom_models:
                        # 检查新列表中是否已包含此自定义模型
                        model_exists = False
                        for new_model in config['models']:
                            if isinstance(new_model, dict) and new_model.get('name') == custom_model.get('name'):
                                model_exists = True
                                break
                            elif isinstance(new_model, str) and new_model == custom_model.get('name'):
                                model_exists = True
                                break
                                
                        # 如果不存在，则添加到新列表
                        if not model_exists:
                            config['models'].append(custom_model)
        
        # 更新服务配置
        service.update_config(config)
        
        # 触发服务更新事件
        event = ServiceUpdatedEvent(self, service_id, service.type, config)
        self.event_manager.post_event(event)
        
        # 保存配置到文件
        self.save_config()
        
        logger.info(f"服务 '{service.name}' (ID: {service_id}) 已更新")
            
    def test_service(self, service_id: str) -> Dict:
        """
        测试服务连接
        
        Args:
            service_id: 服务ID
            
        Returns:
            测试结果
            
        Raises:
            ValueError: 如果服务不存在
        """
        if service := self.get_service(service_id):
            return service.test_connection()
        raise ValueError(f"服务不存在: {service_id}")
        
    @staticmethod
    def get_available_services() -> List[str]:
        """
        获取可用服务类型列表
        
        Returns:
            服务类型列表
        """
        return ['openai', 'anthropic', 'gemini', 'azure', 'volcengine', 'zhipuai', 'alibaba', 'deepseek']
        
    @staticmethod
    def get_service_class(service_type: str) -> type:
        """
        获取服务类
        
        Args:
            service_type: 服务类型
            
        Returns:
            服务类
            
        Raises:
            ValueError: 如果服务类型不支持
        """
        service_classes = {
            'openai': OpenAIService,
            'anthropic': AnthropicService,
            'gemini': GeminiService,
            'volcengine': VolcEngineService,
            'zhipuai': ZhipuAIService,
            'alibaba': AlibabaService,
            'deepseek': DeepSeekService
        }
        
        if service_type not in service_classes:
            raise ValueError(f"不支持的服务类型: {service_type}")
            
        return service_classes[service_type] 