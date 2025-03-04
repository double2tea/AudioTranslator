"""
服务面板模块

此模块提供了一个支持服务工厂的高级面板类，用于构建需要服务访问的UI组件。
服务面板提供了通用的UI结构、事件处理和服务访问机制。
"""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Dict, Any, Optional, Callable, List, Union, Type

from ...services.core.service_factory import ServiceFactory

# 设置日志记录器
logger = logging.getLogger(__name__)

class ServicePanel(ttk.Frame):
    """
    服务面板基类
    
    为需要访问应用服务的面板提供基础功能。主要特性包括：
    - 通用UI结构和布局管理
    - 面板生命周期管理（初始化、激活、挂起、销毁）
    - 事件处理和回调机制
    - 服务访问和配置访问
    - 公共工具方法
    
    Attributes:
        parent: 父级容器
        service_factory: 服务工厂实例
        panel_name: 面板名称
        config: 面板配置
    """
    
    def __init__(self, parent: Union[tk.Widget, ttk.Widget], service_factory: ServiceFactory, 
                 panel_name: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化服务面板
        
        Args:
            parent: 父级容器
            service_factory: 服务工厂实例
            panel_name: 面板名称
            config: 面板配置
        """
        super().__init__(parent)
        
        self.parent = parent
        self.service_factory = service_factory
        self.panel_name = panel_name
        self.config = config or {}
        
        # 事件回调字典
        self._callbacks: Dict[str, List[Callable]] = {}
        
        # 子面板和组件
        self._components: Dict[str, Any] = {}
        
        # 面板状态
        self._is_active = False
        self._is_initialized = False
        
        logger.debug(f"创建面板: {panel_name}")
    
    def initialize(self) -> bool:
        """
        初始化面板
        
        执行面板的初始化工作，包括创建UI组件和绑定事件。
        此方法应该在子类中重写以添加特定的初始化逻辑。
        
        Returns:
            初始化是否成功
        """
        if self._is_initialized:
            return True
        
        try:
            # 创建UI组件
            self._create_ui()
            
            # 绑定事件
            self._bind_events()
            
            # 加载配置
            self._load_config()
            
            self._is_initialized = True
            logger.debug(f"面板初始化成功: {self.panel_name}")
            return True
            
        except Exception as e:
            logger.error(f"面板初始化失败: {self.panel_name}, 错误: {e}")
            return False
    
    def _create_ui(self) -> None:
        """
        创建UI组件
        
        此方法应该在子类中重写以创建特定的UI组件。
        """
        pass
    
    def _bind_events(self) -> None:
        """
        绑定事件
        
        此方法应该在子类中重写以绑定特定的事件。
        """
        pass
    
    def _load_config(self) -> None:
        """
        加载配置
        
        此方法从配置服务中加载面板的配置。
        """
        try:
            config_service = self.service_factory.get_config_service()
            if config_service:
                panel_config = config_service.get(f"panels.{self.panel_name}", {})
                if panel_config:
                    self.config.update(panel_config)
                    logger.debug(f"已加载面板配置: {self.panel_name}")
        except Exception as e:
            logger.error(f"加载面板配置失败: {self.panel_name}, 错误: {e}")
    
    def _save_config(self) -> None:
        """
        保存配置
        
        此方法将面板的配置保存到配置服务。
        """
        try:
            config_service = self.service_factory.get_config_service()
            if config_service and self.config:
                config_service.set(f"panels.{self.panel_name}", self.config)
                logger.debug(f"已保存面板配置: {self.panel_name}")
        except Exception as e:
            logger.error(f"保存面板配置失败: {self.panel_name}, 错误: {e}")
    
    def activate(self) -> None:
        """
        激活面板
        
        当面板被显示时调用，用于准备面板的可见状态。
        子类可以重写此方法以添加特定的激活逻辑。
        """
        if not self._is_initialized:
            self.initialize()
        
        self._is_active = True
        logger.debug(f"面板已激活: {self.panel_name}")
        
        # 触发激活事件
        self._trigger_event("activate")
    
    def deactivate(self) -> None:
        """
        挂起面板
        
        当面板被隐藏时调用，用于暂停面板的活动状态。
        子类可以重写此方法以添加特定的挂起逻辑。
        """
        self._is_active = False
        logger.debug(f"面板已挂起: {self.panel_name}")
        
        # 触发挂起事件
        self._trigger_event("deactivate")
    
    def is_active(self) -> bool:
        """
        检查面板是否处于活动状态
        
        Returns:
            面板是否处于活动状态
        """
        return self._is_active
    
    def destroy(self) -> None:
        """
        销毁面板
        
        完全销毁面板及其所有子组件，清理资源。
        """
        try:
            # 保存配置
            self._save_config()
            
            # 触发销毁事件
            self._trigger_event("destroy")
            
            # 销毁所有子组件
            for component in self._components.values():
                if hasattr(component, 'destroy') and callable(component.destroy):
                    component.destroy()
            
            self._components.clear()
            self._callbacks.clear()
            
            logger.debug(f"面板已销毁: {self.panel_name}")
            
        except Exception as e:
            logger.error(f"销毁面板时发生错误: {self.panel_name}, 错误: {e}")
        
        # 调用父类的destroy方法
        super().destroy()
    
    def refresh(self) -> None:
        """
        刷新面板
        
        重新加载面板内容，更新显示。
        子类应该重写此方法以实现特定的刷新逻辑。
        """
        # 触发刷新事件
        self._trigger_event("refresh")
    
    def register_callback(self, event_name: str, callback: Callable) -> None:
        """
        注册事件回调
        
        Args:
            event_name: 事件名称
            callback: 回调函数
        """
        if event_name not in self._callbacks:
            self._callbacks[event_name] = []
        
        if callback not in self._callbacks[event_name]:
            self._callbacks[event_name].append(callback)
            logger.debug(f"已注册回调: {event_name} - {self.panel_name}")
    
    def unregister_callback(self, event_name: str, callback: Callable) -> None:
        """
        取消注册事件回调
        
        Args:
            event_name: 事件名称
            callback: 回调函数
        """
        if event_name in self._callbacks and callback in self._callbacks[event_name]:
            self._callbacks[event_name].remove(callback)
            logger.debug(f"已取消注册回调: {event_name} - {self.panel_name}")
    
    def _trigger_event(self, event_name: str, **kwargs) -> None:
        """
        触发事件
        
        Args:
            event_name: 事件名称
            **kwargs: 事件参数
        """
        if event_name in self._callbacks:
            for callback in self._callbacks[event_name]:
                try:
                    callback(**kwargs)
                except Exception as e:
                    logger.error(f"事件回调执行错误: {event_name} - {self.panel_name}, 错误: {e}")
    
    def add_component(self, name: str, component: Any) -> None:
        """
        添加组件
        
        Args:
            name: 组件名称
            component: 组件实例
        """
        self._components[name] = component
    
    def get_component(self, name: str) -> Optional[Any]:
        """
        获取组件
        
        Args:
            name: 组件名称
            
        Returns:
            组件实例，如果不存在则返回None
        """
        return self._components.get(name)
    
    def show_message(self, message: str, message_type: str = "info") -> None:
        """
        显示消息
        
        Args:
            message: 消息内容
            message_type: 消息类型，可选值：info, warning, error
        """
        from tkinter import messagebox
        
        if message_type == "info":
            messagebox.showinfo("信息", message, parent=self)
        elif message_type == "warning":
            messagebox.showwarning("警告", message, parent=self)
        elif message_type == "error":
            messagebox.showerror("错误", message, parent=self)
        else:
            messagebox.showinfo("消息", message, parent=self) 