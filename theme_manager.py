import logging
import tkinter as tk
from tkinter import ttk, messagebox
import sys

class ThemeManager:
    """统一主题管理器"""
    
    # macOS 风格配色
    COLORS = {
        'bg_dark': '#2C2C2C',      # 深色背景
        'bg_light': '#FFFFFF',      # 浅色背景
        'fg_dark': '#FFFFFF',       # 深色文本
        'fg_light': '#000000',      # 浅色文本
        'accent': '#0A84FF',        # macOS 蓝
        'border': '#404040',        # 深色边框
        'border_light': '#E5E5E5',  # 浅色边框
        'hover': '#4C4C4C',         # 深色悬停
        'hover_light': '#F0F0F0',   # 浅色悬停
        'selected': '#1F69D3',      # 选中色
        'disabled': '#808080'       # 禁用色
    }
    
    @staticmethod
    def setup_window_theme(window, theme_name="dark"):
        """设置窗口主题"""
        try:
            # 设置 ttk 样式
            style = ttk.Style(window)
            ThemeManager.setup_ttk_styles(style, theme_name == "dark")
            
            # 更新窗口颜色
            bg_color = ThemeManager.COLORS['bg_dark'] if theme_name == "dark" else ThemeManager.COLORS['bg_light']
            fg_color = ThemeManager.COLORS['fg_dark'] if theme_name == "dark" else ThemeManager.COLORS['fg_light']
            window.configure(bg=bg_color)
            
            # 更新全局选项
            window.option_add('*Background', bg_color)
            window.option_add('*Foreground', fg_color)
            
        except Exception as e:
            logging.warning(f"设置窗口主题失败: {str(e)}")

    @staticmethod
    def setup_dialog_theme(dialog, theme_name=None):
        """设置对话框主题"""
        try:
            # 确保窗口已创建
            dialog.update_idletasks()
            
            # 设置对话框背景色
            dialog.configure(bg='#1E1E1E')  # 深色背景
            
            # 设置样式
            style = ttk.Style(dialog)
            
            # 配置基本样式
            style.configure('.',
                background='#1E1E1E',
                foreground='#FFFFFF',
                fieldbackground='#2D2D2D'
            )
            
            # 配置按钮样式
            style.configure('TButton',
                background='#2D2D2D',
                foreground='#FFFFFF',
                padding=5
            )
            
            # 配置标签样式
            style.configure('TLabel',
                background='#1E1E1E',
                foreground='#FFFFFF'
            )
            
            # 配置输入框样式
            style.configure('TEntry',
                fieldbackground='#2D2D2D',
                foreground='#FFFFFF'
            )
            
            # macOS 特殊处理
            if sys.platform == 'darwin':
                try:
                    # 确保窗口已完全创建
                    dialog.update_idletasks()
                    dialog.tk.call('tk::unsupported::MacWindowStyle', 'appearance', dialog, 'dark')
                except Exception as e:
                    logging.warning(f"设置 macOS 深色模式失败: {e}")
                    
        except Exception as e:
            logging.error(f"设置对话框主题失败: {e}")
    
    @classmethod
    def change_theme(cls, window, theme_name):
        """切换主题"""
        try:
            is_dark = theme_name == "dark"
            
            # 更新样式
            style = ttk.Style(window)
            cls.setup_ttk_styles(style, is_dark)
            
            # 更新窗口颜色
            bg_color = cls.COLORS['bg_dark'] if is_dark else cls.COLORS['bg_light']
            fg_color = cls.COLORS['fg_dark'] if is_dark else cls.COLORS['fg_light']
            window.configure(bg=bg_color)
            
            # 更新全局选项
            window.option_add('*Background', bg_color)
            window.option_add('*Foreground', fg_color)
            
            # 刷新界面
            window.update_idletasks()
            
        except Exception as e:
            logging.error(f"切换主题失败: {e}")
            messagebox.showerror("错误", f"切换主题失败: {str(e)}")
    
    @classmethod
    def setup_ttk_styles(cls, style, is_dark=False):
        """配置 ttk 样式"""
        bg_color = cls.COLORS['bg_dark'] if is_dark else cls.COLORS['bg_light']
        fg_color = cls.COLORS['fg_dark'] if is_dark else cls.COLORS['fg_light']
        border_color = cls.COLORS['border'] if is_dark else cls.COLORS['border_light']
        hover_color = cls.COLORS['hover'] if is_dark else cls.COLORS['hover_light']
        
        # 配置全局样式
        style.configure('.',
            background=bg_color,
            foreground=fg_color,
            fieldbackground=bg_color,
            borderwidth=1,
            relief='flat'
        )
        
        # 配置 Treeview 样式
        style.configure('Treeview',
            background=bg_color,
            foreground=fg_color,
            fieldbackground=bg_color,
            borderwidth=1,
            relief='solid'
        )
        style.configure('Treeview.Heading',
            background=bg_color,
            foreground=fg_color,
            relief='flat'
        )
        style.map('Treeview',
            background=[('selected', cls.COLORS['selected'])],
            foreground=[('selected', cls.COLORS['fg_dark'])]
        )
        
        # 配置按钮样式
        style.configure('TButton',
            background=bg_color,
            foreground=fg_color,
            borderwidth=1,
            relief='solid',
            padding=6
        )
        style.map('TButton',
            background=[('active', hover_color)],
            foreground=[('active', fg_color)]
        )
        
        # 配置标签样式
        style.configure('TLabel',
            background=bg_color,
            foreground=fg_color
        )
        
        # 配置框架样式
        style.configure('TFrame',
            background=bg_color,
            borderwidth=0
        )
        
        # 配置分组框样式
        style.configure('TLabelframe',
            background=bg_color,
            foreground=fg_color,
            borderwidth=1,
            relief='solid'
        )
        style.configure('TLabelframe.Label',
            background=bg_color,
            foreground=fg_color
        )
        
        # 配置进度条样式
        style.configure('Horizontal.TProgressbar',
            background=cls.COLORS['accent'],
            troughcolor=hover_color,
            borderwidth=0,
            relief='flat'
        )
        
        # 配置下拉框样式
        style.configure('TCombobox',
            background=bg_color,
            foreground=fg_color,
            fieldbackground=bg_color,
            selectbackground=cls.COLORS['selected'],
            selectforeground=cls.COLORS['fg_dark'],
            borderwidth=1,
            relief='solid',
            arrowsize=12
        ) 