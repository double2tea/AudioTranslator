"""
基础UI组件包

此包提供两种类型的面板基类：
1. SimplePanel: 轻量级面板，不依赖服务工厂，适用于简单UI组件
2. ServicePanel: 高级面板，支持服务工厂和事件回调，适用于需要访问应用服务的组件
"""

from .simple_panel import SimplePanel
from .service_panel import ServicePanel

__all__ = [
    'SimplePanel',
    'ServicePanel'
] 