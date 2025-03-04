"""
事件系统模块

此模块提供了应用程序内部的事件管理系统，允许组件之间通过事件机制进行松耦合通信。
事件系统支持自定义事件类型、事件分发和事件订阅。
"""

import logging
import queue
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar

# 设置日志记录器
logger = logging.getLogger(__name__)

# 定义EventType类型变量，用于类型提示
T = TypeVar('T', bound='Event')

class Event:
    """
    事件基类
    
    所有自定义事件类型应继承此类。
    
    Attributes:
        event_type: 事件类型
        source: 事件源对象
        timestamp: 事件发生的时间戳
        data: 事件数据
    """
    
    def __init__(self, event_type: str, source: Any = None, data: Any = None):
        """
        初始化事件
        
        Args:
            event_type: 事件类型
            source: 事件源对象
            data: 事件数据
        """
        self.event_type = event_type
        self.source = source
        self.timestamp = time.time()
        self.data = data
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(type={self.event_type}, source={self.source}, timestamp={self.timestamp})"


class ConfigChangedEvent(Event):
    """
    配置变更事件
    
    当配置服务中的配置项发生变更时触发。
    
    Attributes:
        key: 变更的配置项键名
        old_value: 变更前的值
        new_value: 变更后的值
        is_service_config: 是否是服务配置
    """
    
    def __init__(self, source: Any, key: str, old_value: Any, new_value: Any, is_service_config: bool = False):
        """
        初始化配置变更事件
        
        Args:
            source: 事件源对象
            key: 变更的配置项键名
            old_value: 变更前的值
            new_value: 变更后的值
            is_service_config: 是否是服务配置
        """
        super().__init__("config_changed", source, {
            "key": key,
            "old_value": old_value,
            "new_value": new_value,
            "is_service_config": is_service_config
        })
        self.key = key
        self.old_value = old_value
        self.new_value = new_value
        self.is_service_config = is_service_config


class ServiceEvent(Event):
    """
    服务事件基类
    
    与服务相关的事件的基类。
    
    Attributes:
        service_id: 服务ID
        service_type: 服务类型
    """
    
    def __init__(self, event_type: str, source: Any, service_id: str, service_type: str, data: Any = None):
        """
        初始化服务事件
        
        Args:
            event_type: 事件类型
            source: 事件源对象
            service_id: 服务ID
            service_type: 服务类型
            data: 事件数据
        """
        super().__init__(event_type, source, data)
        self.service_id = service_id
        self.service_type = service_type


class ServiceRegisteredEvent(ServiceEvent):
    """服务注册事件，当新服务被注册时触发"""
    
    def __init__(self, source: Any, service_id: str, service_type: str, service_name: str):
        super().__init__("service_registered", source, service_id, service_type, {
            "service_name": service_name
        })
        self.service_name = service_name


class ServiceUnregisteredEvent(ServiceEvent):
    """服务注销事件，当服务被移除时触发"""
    
    def __init__(self, source: Any, service_id: str, service_type: str):
        super().__init__("service_unregistered", source, service_id, service_type)


class ServiceUpdatedEvent(ServiceEvent):
    """服务更新事件，当服务配置被更新时触发"""
    
    def __init__(self, source: Any, service_id: str, service_type: str, changes: Dict[str, Any]):
        super().__init__("service_updated", source, service_id, service_type, {
            "changes": changes
        })
        self.changes = changes


class EventManager:
    """
    事件管理器
    
    负责事件的注册、分发和处理。
    支持同步和异步事件处理。
    
    使用单例模式确保全局只有一个事件管理器实例。
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'EventManager':
        """
        获取EventManager的单例实例
        
        Returns:
            EventManager实例
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """初始化事件管理器"""
        if EventManager._instance is not None:
            raise RuntimeError("EventManager is a singleton class, use get_instance() instead")
        
        self._listeners: Dict[str, List[Callable[[Event], None]]] = {}
        self._event_queue: queue.Queue = queue.Queue()
        self._is_dispatching = False
        self._dispatching_thread = None
        self._event_types: Set[str] = set()
    
    def register_event_type(self, event_type: str) -> None:
        """
        注册事件类型
        
        Args:
            event_type: 事件类型
        """
        self._event_types.add(event_type)
    
    def add_listener(self, event_type: str, listener: Callable[[Event], None]) -> None:
        """
        添加事件监听器
        
        Args:
            event_type: 要监听的事件类型
            listener: 事件处理函数
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        if listener not in self._listeners[event_type]:
            self._listeners[event_type].append(listener)
    
    def remove_listener(self, event_type: str, listener: Callable[[Event], None]) -> None:
        """
        移除事件监听器
        
        Args:
            event_type: 事件类型
            listener: 要移除的事件处理函数
        """
        if event_type in self._listeners and listener in self._listeners[event_type]:
            self._listeners[event_type].remove(listener)
    
    def dispatch_event(self, event: Event) -> None:
        """
        同步分发事件
        
        直接调用所有监听器处理事件。
        
        Args:
            event: 要分发的事件
        """
        event_type = event.event_type
        if event_type in self._listeners:
            for listener in self._listeners[event_type]:
                try:
                    listener(event)
                except Exception as e:
                    logger.error(f"事件处理错误: {e}", exc_info=True)
    
    def post_event(self, event: Event) -> None:
        """
        异步分发事件
        
        将事件加入队列，由事件分发线程处理。
        
        Args:
            event: 要分发的事件
        """
        self._event_queue.put(event)
        if not self._is_dispatching:
            self._start_dispatching()
    
    def _start_dispatching(self) -> None:
        """启动事件分发线程"""
        if self._dispatching_thread is None or not self._dispatching_thread.is_alive():
            self._is_dispatching = True
            self._dispatching_thread = threading.Thread(target=self._dispatching_loop)
            self._dispatching_thread.daemon = True
            self._dispatching_thread.start()
    
    def _dispatching_loop(self) -> None:
        """事件分发循环"""
        while self._is_dispatching:
            try:
                event = self._event_queue.get(timeout=0.1)
                self.dispatch_event(event)
                self._event_queue.task_done()
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"事件分发错误: {e}", exc_info=True)
    
    def stop_dispatching(self) -> None:
        """停止事件分发"""
        self._is_dispatching = False
        if self._dispatching_thread is not None:
            self._dispatching_thread.join(timeout=1.0)
            self._dispatching_thread = None 