"""
主题服务模块

此模块提供了应用程序的主题管理功能，负责设置和切换应用程序的视觉主题。
ThemeService 作为服务层组件，提供了主题配置、应用和切换功能。
"""

import logging
import tkinter as tk
from tkinter import ttk
import sys
from typing import Dict, Any, Optional, Callable, List

from ..core.base_service import BaseService
from ..infrastructure.config_service import ConfigService

# 设置日志记录器
logger = logging.getLogger(__name__)

class ThemeService(BaseService):
    """
    主题服务类
    
    负责管理应用程序的视觉主题，提供主题配置、应用和切换功能。
    
    Attributes:
        config_service: 配置服务实例
        current_theme: 当前主题名称
        themes: 可用主题字典
        theme_listeners: 主题变更监听器列表
    """
    
    # 默认主题配色
    DEFAULT_COLORS = {
        # 深色主题
        'dark': {
            'bg_dark': '#1E1E1E',      # 主背景色
            'bg_light': '#2D2D2D',     # 次要背景
            'fg': '#FFFFFF',           # 主文本色
            'fg_dim': '#AAAAAA',       # 次要文本
            'accent': '#007ACC',       # 强调色
            'border': '#3D3D3D',       # 边框色
            'hover': '#3D3D3D',        # 悬停色
            'selected': '#094771',     # 选中色
            'disabled': '#6D6D6D'      # 禁用色
        },
        # 浅色主题
        'light': {
            'bg_dark': '#F5F5F5',      # 主背景色
            'bg_light': '#FFFFFF',     # 次要背景
            'fg': '#000000',           # 主文本色
            'fg_dim': '#555555',       # 次要文本
            'accent': '#0078D7',       # 强调色
            'border': '#CCCCCC',       # 边框色
            'hover': '#E5E5E5',        # 悬停色
            'selected': '#CCE4F7',     # 选中色
            'disabled': '#AAAAAA'      # 禁用色
        }
    }
    
    def __init__(self, config_service: ConfigService = None):
        """
        初始化主题服务
        
        Args:
            config_service: 配置服务实例，如果为None则通过服务工厂获取
        """
        super().__init__("theme_service")
        
        self.config_service = config_service
        
        # 初始化属性
        self.current_theme = "dark"  # 默认使用深色主题
        self.themes = self.DEFAULT_COLORS.copy()
        self.theme_listeners: List[Callable[[str, Dict[str, str]], None]] = []
    
    def initialize(self) -> bool:
        """
        初始化主题服务
        
        获取必要的依赖服务并加载配置。
        
        Returns:
            初始化是否成功
        """
        try:
            # 获取配置服务
            if not self.config_service:
                if self.service_factory:
                    self.config_service = self.service_factory.get_config_service()
                
                if not self.config_service:
                    logger.warning("无法获取配置服务，将使用默认主题配置")
            
            # 加载主题配置
            self._load_theme_config()
            
            self.is_initialized = True
            logger.info("主题服务初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"主题服务初始化失败: {e}")
            return False
    
    def shutdown(self) -> bool:
        """
        关闭主题服务
        
        保存配置并清理资源。
        
        Returns:
            关闭是否成功
        """
        try:
            # 保存主题配置
            self._save_theme_config()
            
            # 清理监听器
            self.theme_listeners.clear()
            
            logger.info("主题服务已关闭")
            return True
            
        except Exception as e:
            logger.error(f"主题服务关闭失败: {e}")
            return False
    
    def _load_theme_config(self) -> None:
        """加载主题配置"""
        if not self.config_service:
            return
            
        try:
            # 加载当前主题
            theme_name = self.config_service.get("UI_THEME", "dark")
            self.current_theme = theme_name if theme_name in self.themes else "dark"
            
            # 加载自定义主题颜色
            custom_colors = self.config_service.get("COLORS", {})
            if custom_colors:
                for theme_name, colors in custom_colors.items():
                    if theme_name in self.themes:
                        self.themes[theme_name].update(colors)
            
            logger.debug(f"已加载主题配置，当前主题: {self.current_theme}")
            
        except Exception as e:
            logger.error(f"加载主题配置失败: {e}")
    
    def _save_theme_config(self) -> None:
        """保存主题配置"""
        if not self.config_service:
            return
            
        try:
            # 保存当前主题
            self.config_service.set("UI_THEME", self.current_theme)
            
            # 保存自定义主题颜色
            self.config_service.set("COLORS", self.themes)
            
            logger.debug("已保存主题配置")
            
        except Exception as e:
            logger.error(f"保存主题配置失败: {e}")
    
    def get_current_theme(self) -> str:
        """
        获取当前主题名称
        
        Returns:
            当前主题名称
        """
        return self.current_theme
    
    def get_theme_colors(self, theme_name: Optional[str] = None) -> Dict[str, str]:
        """
        获取主题颜色
        
        Args:
            theme_name: 主题名称，如果为None则使用当前主题
            
        Returns:
            主题颜色字典
        """
        theme = theme_name or self.current_theme
        return self.themes.get(theme, self.themes['dark']).copy()
    
    def set_theme(self, theme_name: str) -> bool:
        """
        设置当前主题
        
        Args:
            theme_name: 主题名称
            
        Returns:
            设置是否成功
        """
        if theme_name not in self.themes:
            logger.error(f"未知主题: {theme_name}")
            return False
            
        # 更新当前主题
        old_theme = self.current_theme
        self.current_theme = theme_name
        
        # 保存配置
        self._save_theme_config()
        
        # 通知监听器
        self._notify_theme_changed(old_theme, theme_name)
        
        logger.info(f"已切换主题: {theme_name}")
        return True
    
    def add_theme_listener(self, listener: Callable[[str, Dict[str, str]], None]) -> None:
        """
        添加主题变更监听器
        
        Args:
            listener: 监听器函数，接收主题名称和颜色字典作为参数
        """
        if listener not in self.theme_listeners:
            self.theme_listeners.append(listener)
    
    def remove_theme_listener(self, listener: Callable[[str, Dict[str, str]], None]) -> None:
        """
        移除主题变更监听器
        
        Args:
            listener: 要移除的监听器函数
        """
        if listener in self.theme_listeners:
            self.theme_listeners.remove(listener)
    
    def _notify_theme_changed(self, old_theme: str, new_theme: str) -> None:
        """
        通知主题变更
        
        Args:
            old_theme: 旧主题名称
            new_theme: 新主题名称
        """
        colors = self.get_theme_colors(new_theme)
        for listener in self.theme_listeners:
            try:
                listener(new_theme, colors)
            except Exception as e:
                logger.error(f"执行主题监听器时出错: {e}")
    
    def setup_window_theme(self, window: tk.Tk, theme_name: Optional[str] = None) -> None:
        """
        设置窗口主题
        
        Args:
            window: 窗口对象
            theme_name: 主题名称，如果为None则使用当前主题
        """
        try:
            theme = theme_name or self.current_theme
            colors = self.get_theme_colors(theme)
            
            # 设置 ttk 样式
            style = ttk.Style(window)
            self._setup_ttk_styles(style, colors)
            
            # 更新窗口颜色
            window.configure(bg=colors['bg_dark'])
            
            # 更新全局选项
            window.option_add('*Background', colors['bg_dark'])
            window.option_add('*Foreground', colors['fg'])
            
            # macOS 特殊处理
            if sys.platform == 'darwin':
                try:
                    # 设置 macOS 深色模式
                    if theme == 'dark':
                        window.tk.call('tk::unsupported::MacWindowStyle', 'appearance', window, 'dark')
                    else:
                        window.tk.call('tk::unsupported::MacWindowStyle', 'appearance', window, 'light')
                except Exception as e:
                    logger.warning(f"设置 macOS 主题模式失败: {e}")
            
            logger.debug(f"已设置窗口主题: {theme}")
            
        except Exception as e:
            logger.error(f"设置窗口主题失败: {e}")
    
    def setup_dialog_theme(self, dialog: tk.Toplevel, theme_name: Optional[str] = None) -> None:
        """
        设置对话框主题
        
        Args:
            dialog: 对话框对象
            theme_name: 主题名称，如果为None则使用当前主题
        """
        try:
            # 确保窗口已创建
            dialog.update_idletasks()
            
            theme = theme_name or self.current_theme
            colors = self.get_theme_colors(theme)
            
            # 设置对话框背景色
            dialog.configure(bg=colors['bg_dark'])
            
            # 设置样式
            style = ttk.Style(dialog)
            
            # 配置基本样式
            style.configure('.',
                background=colors['bg_dark'],
                foreground=colors['fg'],
                fieldbackground=colors['bg_light']
            )
            
            # 配置按钮样式
            style.configure('TButton',
                background=colors['bg_light'],
                foreground=colors['fg'],
                padding=5
            )
            
            # 配置标签样式
            style.configure('TLabel',
                background=colors['bg_dark'],
                foreground=colors['fg']
            )
            
            # 配置输入框样式
            style.configure('TEntry',
                fieldbackground=colors['bg_light'],
                foreground=colors['fg']
            )
            
            # macOS 特殊处理
            if sys.platform == 'darwin':
                try:
                    # 设置 macOS 深色模式
                    if theme == 'dark':
                        dialog.tk.call('tk::unsupported::MacWindowStyle', 'appearance', dialog, 'dark')
                    else:
                        dialog.tk.call('tk::unsupported::MacWindowStyle', 'appearance', dialog, 'light')
                except Exception as e:
                    logger.warning(f"设置 macOS 主题模式失败: {e}")
            
            logger.debug(f"已设置对话框主题: {theme}")
            
        except Exception as e:
            logger.error(f"设置对话框主题失败: {e}")
    
    def _setup_ttk_styles(self, style: ttk.Style, colors: Dict[str, str]) -> None:
        """
        配置 ttk 样式
        
        Args:
            style: ttk.Style 对象
            colors: 颜色字典
        """
        # 配置全局样式
        style.configure('.',
            background=colors['bg_dark'],
            foreground=colors['fg'],
            fieldbackground=colors['bg_dark'],
            borderwidth=1,
            relief='flat'
        )
        
        # 配置 Treeview 样式
        style.configure('Treeview',
            background=colors['bg_dark'],
            foreground=colors['fg'],
            fieldbackground=colors['bg_dark'],
            borderwidth=1,
            relief='solid'
        )
        style.configure('Treeview.Heading',
            background=colors['bg_light'],
            foreground=colors['fg'],
            relief='flat'
        )
        style.map('Treeview',
            background=[('selected', colors['selected'])],
            foreground=[('selected', colors['fg'])]
        )
        
        # 配置按钮样式
        style.configure('TButton',
            background=colors['bg_light'],
            foreground=colors['fg'],
            borderwidth=1,
            relief='solid',
            padding=6
        )
        style.map('TButton',
            background=[('active', colors['hover'])],
            foreground=[('active', colors['fg'])]
        )
        
        # 配置强调按钮样式
        style.configure('Accent.TButton',
            background=colors['accent'],
            foreground=colors['fg'],
            borderwidth=1,
            relief='solid',
            padding=6
        )
        style.map('Accent.TButton',
            background=[('active', colors['selected'])],
            foreground=[('active', colors['fg'])]
        )
        
        # 配置标签样式
        style.configure('TLabel',
            background=colors['bg_dark'],
            foreground=colors['fg']
        )
        
        # 配置标题标签样式
        style.configure('Title.TLabel',
            background=colors['bg_dark'],
            foreground=colors['fg'],
            font=('Arial', 12, 'bold')
        )
        
        # 配置框架样式
        style.configure('TFrame',
            background=colors['bg_dark'],
            borderwidth=0
        )
        
        # 配置分组框样式
        style.configure('TLabelframe',
            background=colors['bg_dark'],
            foreground=colors['fg'],
            borderwidth=1,
            relief='solid'
        )
        style.configure('TLabelframe.Label',
            background=colors['bg_dark'],
            foreground=colors['fg']
        )
        
        # 配置进度条样式
        style.configure('Horizontal.TProgressbar',
            background=colors['accent'],
            troughcolor=colors['bg_light'],
            borderwidth=0,
            relief='flat'
        )
        
        # 配置下拉框样式
        style.configure('TCombobox',
            background=colors['bg_light'],
            foreground=colors['fg'],
            fieldbackground=colors['bg_light'],
            selectbackground=colors['selected'],
            selectforeground=colors['fg'],
            borderwidth=1,
            relief='solid',
            arrowsize=12
        )
        
        # 配置状态栏样式
        style.configure('StatusBar.TFrame',
            background=colors['bg_light'],
            relief='solid',
            borderwidth=1
        )
        style.configure('StatusBar.TLabel',
            background=colors['bg_light'],
            foreground=colors['fg_dim'],
            padding=6
        )
    
    def add_custom_theme(self, theme_name: str, colors: Dict[str, str]) -> bool:
        """
        添加自定义主题
        
        Args:
            theme_name: 主题名称
            colors: 颜色字典
            
        Returns:
            添加是否成功
        """
        try:
            # 验证颜色字典
            required_colors = ['bg_dark', 'bg_light', 'fg', 'fg_dim', 'accent', 'border', 'hover', 'selected']
            for color in required_colors:
                if color not in colors:
                    logger.error(f"添加自定义主题失败: 缺少必要的颜色 '{color}'")
                    return False
            
            # 添加主题
            self.themes[theme_name] = colors
            
            # 保存配置
            self._save_theme_config()
            
            logger.info(f"已添加自定义主题: {theme_name}")
            return True
            
        except Exception as e:
            logger.error(f"添加自定义主题失败: {e}")
            return False
    
    def remove_custom_theme(self, theme_name: str) -> bool:
        """
        移除自定义主题
        
        Args:
            theme_name: 主题名称
            
        Returns:
            移除是否成功
        """
        try:
            # 不允许移除默认主题
            if theme_name in ['dark', 'light']:
                logger.error(f"无法移除默认主题: {theme_name}")
                return False
            
            # 如果当前主题是要移除的主题，切换到默认主题
            if self.current_theme == theme_name:
                self.set_theme('dark')
            
            # 移除主题
            if theme_name in self.themes:
                del self.themes[theme_name]
                
                # 保存配置
                self._save_theme_config()
                
                logger.info(f"已移除自定义主题: {theme_name}")
                return True
            else:
                logger.warning(f"主题不存在: {theme_name}")
                return False
            
        except Exception as e:
            logger.error(f"移除自定义主题失败: {e}")
            return False 