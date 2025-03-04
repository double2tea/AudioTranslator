"""
配置服务模块

此模块提供了应用程序的配置管理功能，负责加载、保存和管理应用程序的配置项。
配置服务使用JSON格式存储配置项，并支持默认配置和用户配置的合并。
"""

import os
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, List, Union, Callable

from ..core.base_service import BaseService
from ...utils.env_loader import EnvLoader
from ...utils.events import EventManager, ConfigChangedEvent

# 设置日志记录器
logger = logging.getLogger(__name__)

class ConfigService(BaseService):
    """
    配置服务类
    
    负责加载、保存和管理应用程序的配置项。配置数据以JSON格式存储，
    支持默认配置和用户配置的合并，以及配置的热重载。
    
    Attributes:
        config_file: 配置文件路径
        default_config: 默认配置
        user_config: 用户配置
        config: 合并后的有效配置
        watch_interval: 配置文件监视间隔（秒）
        is_watching: 是否正在监视配置文件变化
    """
    
    def __init__(self, config_file: Optional[str] = None, default_config: Optional[Dict[str, Any]] = None):
        """
        初始化配置服务
        
        Args:
            config_file: 配置文件路径，如果为None则使用默认路径
            default_config: 默认配置，如果为None则使用内置默认配置
        """
        super().__init__("config_service")
        
        # 设置配置文件路径
        if config_file is None:
            # 使用项目根目录下的config目录
            self.config_dir = Path(__file__).parent.parent.parent.parent / "config"
            self.config_file = self.config_dir / "app_config.json"
        else:
            self.config_file = Path(config_file)
            self.config_dir = self.config_file.parent
        
        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 初始化配置
        self.default_config = default_config or self._get_default_config()
        self.user_config = {}
        self.config = self.default_config.copy()
        
        # 配置文件监视相关
        self.watch_interval = 5.0  # 默认5秒检查一次
        self.is_watching = False
        self.watch_thread = None
        self.last_modified_time = 0
        
        # 事件管理器
        self.event_manager = EventManager.get_instance()
        
        # 配置变更回调函数
        self.config_change_callbacks: Dict[str, List[Callable[[str, Any, Any], None]]] = {}
    
    def initialize(self) -> bool:
        """
        初始化配置服务
        
        加载配置文件，如果文件不存在则创建默认配置文件。
        
        Returns:
            初始化是否成功
        """
        try:
            # 加载环境变量
            EnvLoader.load_dotenv()
            
            # 尝试加载用户配置
            if self.config_file.exists():
                self._load_config()
            else:
                # 如果配置文件不存在，创建默认配置文件
                self._save_config(self.default_config)
                self.user_config = self.default_config.copy()
            
            # 合并配置
            self._merge_config()
            
            # 记录最后修改时间
            if self.config_file.exists():
                self.last_modified_time = self.config_file.stat().st_mtime
            
            logger.info(f"配置服务初始化成功，配置文件: {self.config_file}")
            self.is_initialized = True
            
            # 注册事件类型
            self.event_manager.register_event_type("config_changed")
            
            return True
            
        except Exception as e:
            logger.error(f"配置服务初始化失败: {e}")
            return False
    
    def shutdown(self) -> bool:
        """
        关闭配置服务
        
        停止配置文件监视线程，执行必要的清理工作。
        
        Returns:
            关闭是否成功
        """
        self.stop_watching()
        logger.info("配置服务已关闭")
        return super().shutdown()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认配置
        
        Returns:
            默认配置项
        """
        return {
            "app": {
                "name": "音频文件翻译器",
                "version": "1.0.0",
                "language": "zh_CN",
                "theme": "system",
                "debug": False,
                "first_run": True
            },
            "directories": {
                "last_open": "",
                "favorites": [],
                "recent": []
            },
            "ui": {
                "window_width": 1200,
                "window_height": 800,
                "sidebar_width": 300,
                "show_toolbar": True,
                "show_statusbar": True
            },
            "audio": {
                "player": "system",
                "volume": 75,
                "autoplay": False
            },
            "file_types": {
                "audio": [".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"],
                "text": [".txt", ".md", ".csv", ".json"]
            }
        }
    
    def _load_config(self) -> None:
        """
        从配置文件加载用户配置
        """
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.user_config = json.load(f)
            
            # 处理用户配置中的环境变量引用
            self.user_config = EnvLoader.parse_env_vars(self.user_config)
            logger.debug(f"成功加载配置文件: {self.config_file}")
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误: {e}，尝试恢复备份")
            self._restore_config_backup()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，将使用默认配置")
            self.user_config = {}
    
    def _save_config(self, config_data: Dict[str, Any]) -> bool:
        """
        保存配置到配置文件
        
        Args:
            config_data: 要保存的配置数据
            
        Returns:
            保存是否成功
        """
        try:
            # 创建备份
            self._create_config_backup()
            
            # 保存新配置
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            # 更新最后修改时间
            if self.config_file.exists():
                self.last_modified_time = self.config_file.stat().st_mtime
                
            logger.debug(f"成功保存配置文件: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False
    
    def _create_config_backup(self) -> bool:
        """
        创建配置文件备份
        
        Returns:
            备份是否成功
        """
        if not self.config_file.exists():
            return False
            
        try:
            backup_file = self.config_dir / f"{self.config_file.stem}_backup.json"
            with open(self.config_file, 'r', encoding='utf-8') as src:
                with open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            logger.debug(f"创建配置备份: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"创建配置备份失败: {e}")
            return False
    
    def _restore_config_backup(self) -> bool:
        """
        从备份恢复配置文件
        
        Returns:
            恢复是否成功
        """
        backup_file = self.config_dir / f"{self.config_file.stem}_backup.json"
        if not backup_file.exists():
            logger.warning("配置备份文件不存在，无法恢复")
            return False
            
        try:
            with open(backup_file, 'r', encoding='utf-8') as src:
                self.user_config = json.load(src)
            logger.info(f"从备份恢复配置: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"恢复配置备份失败: {e}")
            return False
    
    def _merge_config(self) -> None:
        """
        合并默认配置和用户配置
        
        用户配置会覆盖默认配置中的相应项
        """
        self.config = self.default_config.copy()
        
        def deep_update(source, updates):
            for key, value in updates.items():
                if key in source and isinstance(source[key], dict) and isinstance(value, dict):
                    deep_update(source[key], value)
                else:
                    source[key] = value
        
        deep_update(self.config, self.user_config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项的值
        
        支持使用点号分隔的路径访问嵌套配置，如 "app.name"
        
        Args:
            key: 配置项键名，支持使用点号分隔的路径
            default: 如果配置项不存在，返回的默认值
            
        Returns:
            配置项的值，如果配置项不存在则返回默认值
        """
        if not key:
            return default
        
        if "." not in key:
            return self.config.get(key, default)
        
        # 处理嵌套路径
        parts = key.split(".")
        current = self.config
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        
        return current
    
    def set(self, key: str, value: Any, save: bool = True) -> bool:
        """
        设置配置项的值
        
        支持使用点号分隔的路径设置嵌套配置，如 "app.name"
        
        Args:
            key: 配置项键名，支持使用点号分隔的路径
            value: 要设置的值
            save: 是否立即保存到配置文件
            
        Returns:
            操作是否成功
        """
        if not key:
            return False
        
        # 获取旧值用于事件通知
        old_value = self.get(key)
        
        # 更新用户配置和合并后的配置
        if "." not in key:
            self.user_config[key] = value
            self.config[key] = value
        else:
            # 处理嵌套路径
            parts = key.split(".")
            user_current = self.user_config
            config_current = self.config
            
            # 创建或更新嵌套字典
            for i, part in enumerate(parts[:-1]):
                if part not in user_current:
                    user_current[part] = {}
                if part not in config_current:
                    config_current[part] = {}
                
                user_current = user_current[part]
                config_current = config_current[part]
            
            # 设置最终值
            user_current[parts[-1]] = value
            config_current[parts[-1]] = value
        
        # 触发配置变更事件
        self._trigger_config_change(key, old_value, value)
        
        # 保存配置
        if save:
            return self._save_config(self.user_config)
        return True
    
    def _trigger_config_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """
        触发配置变更事件
        
        Args:
            key: 变更的配置项键名
            old_value: 变更前的值
            new_value: 变更后的值
        """
        # 触发回调函数
        if key in self.config_change_callbacks:
            for callback in self.config_change_callbacks[key]:
                try:
                    callback(key, old_value, new_value)
                except Exception as e:
                    logger.error(f"配置变更回调执行失败: {e}")
        
        # 发布配置变更事件
        event = ConfigChangedEvent(self, key, old_value, new_value)
        self.event_manager.post_event(event)
    
    def register_change_callback(self, key: str, callback: Callable[[str, Any, Any], None]) -> None:
        """
        注册配置变更回调函数
        
        当指定的配置项发生变更时，将调用回调函数。
        
        Args:
            key: 配置项键名
            callback: 回调函数，接收参数(key, old_value, new_value)
        """
        if key not in self.config_change_callbacks:
            self.config_change_callbacks[key] = []
        if callback not in self.config_change_callbacks[key]:
            self.config_change_callbacks[key].append(callback)
    
    def unregister_change_callback(self, key: str, callback: Callable[[str, Any, Any], None]) -> None:
        """
        注销配置变更回调函数
        
        Args:
            key: 配置项键名
            callback: 要注销的回调函数
        """
        if key in self.config_change_callbacks and callback in self.config_change_callbacks[key]:
            self.config_change_callbacks[key].remove(callback)
    
    def save(self) -> bool:
        """
        保存当前用户配置到配置文件
        
        Returns:
            保存是否成功
        """
        return self._save_config(self.user_config)
    
    def reset(self) -> bool:
        """
        重置配置为默认值
        
        Returns:
            重置是否成功
        """
        old_config = self.user_config.copy()
        self.user_config = self.default_config.copy()
        self.config = self.default_config.copy()
        
        # 触发配置变更事件
        for key in set(old_config.keys()) | set(self.default_config.keys()):
            old_value = old_config.get(key)
            new_value = self.default_config.get(key)
            if old_value != new_value:
                self._trigger_config_change(key, old_value, new_value)
        
        return self._save_config(self.user_config)
    
    def reload(self) -> bool:
        """
        重新加载配置文件
        
        Returns:
            重载是否成功
        """
        try:
            old_config = self.config.copy()
            self._load_config()
            self._merge_config()
            
            # 触发配置变更事件
            for key in set(old_config.keys()) | set(self.config.keys()):
                if "." not in key:  # 只处理顶层配置项
                    old_value = old_config.get(key)
                    new_value = self.config.get(key)
                    if old_value != new_value:
                        self._trigger_config_change(key, old_value, new_value)
            
            return True
        except Exception as e:
            logger.error(f"重载配置失败: {e}")
            return False
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置项
        
        Returns:
            所有配置项字典
        """
        return self.config.copy()
    
    def start_watching(self, interval: float = None) -> None:
        """
        开始监视配置文件变化
        
        当配置文件发生变化时，自动重新加载配置。
        
        Args:
            interval: 检查间隔（秒），如果为None则使用默认间隔
        """
        if self.is_watching:
            return
            
        if interval is not None:
            self.watch_interval = interval
            
        self.is_watching = True
        self.watch_thread = threading.Thread(target=self._watch_config_file)
        self.watch_thread.daemon = True
        self.watch_thread.start()
        logger.info(f"开始监视配置文件变化，间隔: {self.watch_interval}秒")
    
    def stop_watching(self) -> None:
        """停止监视配置文件变化"""
        if not self.is_watching:
            return
            
        self.is_watching = False
        if self.watch_thread:
            self.watch_thread.join(timeout=1.0)
            self.watch_thread = None
        logger.info("停止监视配置文件变化")
    
    def _watch_config_file(self) -> None:
        """配置文件监视线程"""
        while self.is_watching:
            try:
                if self.config_file.exists():
                    mtime = self.config_file.stat().st_mtime
                    if mtime > self.last_modified_time:
                        logger.info("检测到配置文件变化，重新加载")
                        self.reload()
                        self.last_modified_time = mtime
            except Exception as e:
                logger.error(f"监视配置文件时出错: {e}")
                
            time.sleep(self.watch_interval)
        
    def load_services_config(self) -> Dict[str, Any]:
        """
        加载服务配置
        
        Returns:
            服务配置字典，如果文件不存在或加载失败则返回空字典
        """
        services_config_file = self.get_config_path("services.json")
        try:
            if services_config_file.exists():
                with open(services_config_file, 'r', encoding='utf-8') as f:
                    services_config = json.load(f)
                
                # 处理环境变量引用
                services_config = EnvLoader.parse_env_vars(services_config)
                logger.debug(f"成功加载服务配置文件: {services_config_file}")
                return services_config
            else:
                logger.debug(f"服务配置文件不存在: {services_config_file}")
                return {}
        except json.JSONDecodeError as e:
            logger.error(f"服务配置文件格式错误: {e}，尝试恢复备份")
            return self._restore_services_config_backup() or {}
        except Exception as e:
            logger.error(f"加载服务配置文件失败: {e}")
            return {}
    
    def _create_services_config_backup(self) -> bool:
        """
        创建服务配置文件备份
        
        Returns:
            备份是否成功
        """
        services_config_file = self.get_config_path("services.json")
        if not services_config_file.exists():
            return False
            
        try:
            backup_file = self.config_dir / "services_backup.json"
            with open(services_config_file, 'r', encoding='utf-8') as src:
                with open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            logger.debug(f"创建服务配置备份: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"创建服务配置备份失败: {e}")
            return False
    
    def _restore_services_config_backup(self) -> Optional[Dict[str, Any]]:
        """
        从备份恢复服务配置文件
        
        Returns:
            恢复的服务配置，如果恢复失败则返回None
        """
        backup_file = self.config_dir / "services_backup.json"
        if not backup_file.exists():
            logger.warning("服务配置备份文件不存在，无法恢复")
            return None
            
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                services_config = json.load(f)
            
            # 恢复到原文件
            services_config_file = self.get_config_path("services.json")
            with open(services_config_file, 'w', encoding='utf-8') as f:
                json.dump(services_config, f, ensure_ascii=False, indent=2)
                
            logger.info(f"从备份恢复服务配置: {backup_file}")
            return services_config
        except Exception as e:
            logger.error(f"恢复服务配置备份失败: {e}")
            return None
    
    def save_services_config(self, services_config: Dict[str, Any]) -> bool:
        """
        保存服务配置
        
        Args:
            services_config: 服务配置字典
            
        Returns:
            保存是否成功
        """
        services_config_file = self.get_config_path("services.json")
        try:
            # 创建备份
            self._create_services_config_backup()
            
            # 保存新配置
            with open(services_config_file, 'w', encoding='utf-8') as f:
                json.dump(services_config, f, ensure_ascii=False, indent=2)
                
            # 触发服务配置变更事件
            event = ConfigChangedEvent(self, "services", None, services_config, True)
            self.event_manager.post_event(event)
            
            logger.debug(f"成功保存服务配置文件: {services_config_file}")
            return True
        except Exception as e:
            logger.error(f"保存服务配置文件失败: {e}")
            return False
    
    def get_enabled_services(self) -> List[Dict[str, Any]]:
        """
        获取所有启用的服务配置
        
        Returns:
            已启用的服务配置列表
        """
        services_config = self.load_services_config()
        if not services_config or "services" not in services_config:
            return []
        
        return [service for service in services_config.get("services", [])
                if service.get("enabled", True)]
        
    def get_config_path(self, filename: str) -> Path:
        """
        获取配置文件的路径
        
        Args:
            filename: 配置文件名
            
        Returns:
            配置文件的完整路径
        """
        return self.config_dir / filename 