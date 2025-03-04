"""
简单面板模块

提供一个轻量级的基础面板实现，不依赖服务工厂。
适用于简单UI组件和独立面板。
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, Dict, Any, List


class SimplePanel(ttk.Frame):
    """
    简单面板基类
    
    为不需要服务工厂支持的UI面板提供基础功能。
    适用于简单UI组件和轻量级功能模块。
    
    Attributes:
        parent: 父级容器
    """
    
    def __init__(self, parent: tk.Widget):
        """
        初始化简单面板
        
        Args:
            parent: 父级容器
        """
        super().__init__(parent)
        self.parent = parent
        
        # 面板状态
        self._is_visible = False
        
        # 初始化UI
        self._init_ui()
        
    def _init_ui(self) -> None:
        """
        初始化UI组件
        
        子类应重写此方法实现自己的UI
        """
        pass
    
    def update_ui(self) -> None:
        """
        更新UI组件
        
        当需要刷新UI时调用
        """
        pass
    
    def get_panel_name(self) -> str:
        """
        获取面板名称
        
        Returns:
            面板名称
        """
        return self.__class__.__name__
    
    def show(self) -> None:
        """
        显示面板
        """
        self._is_visible = True
        self.on_panel_show()
    
    def hide(self) -> None:
        """
        隐藏面板
        """
        self._is_visible = False
        self.on_panel_hide()
    
    def is_visible(self) -> bool:
        """
        检查面板是否可见
        
        Returns:
            面板是否可见
        """
        return self._is_visible
    
    def on_panel_show(self) -> None:
        """
        当面板显示时调用
        
        子类可以重写此方法添加特定的显示逻辑
        """
        pass
    
    def on_panel_hide(self) -> None:
        """
        当面板隐藏时调用
        
        子类可以重写此方法添加特定的隐藏逻辑
        """
        pass
    
    def save_settings(self) -> Dict[str, Any]:
        """
        保存面板设置
        
        Returns:
            设置字典
        """
        return {}
    
    def load_settings(self, settings: Dict[str, Any]) -> None:
        """
        加载面板设置
        
        Args:
            settings: 设置字典
        """
        pass 