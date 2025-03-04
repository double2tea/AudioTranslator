"""
UI工具函数和类
提供常用的UI组件和工具函数
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, Any, Dict


def create_tooltip(widget, text: str) -> None:
    """
    为控件创建悬浮提示
    
    Args:
        widget: 需要创建提示的控件
        text: 提示文本
    """
    tooltip = None
    
    def enter(event):
        nonlocal tooltip
        x, y, _, _ = widget.bbox("insert")
        x += widget.winfo_rootx() + 25
        y += widget.winfo_rooty() + 25
        
        # 创建提示窗口
        tooltip = tk.Toplevel(widget)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{x}+{y}")
        
        label = ttk.Label(tooltip, text=text, justify=tk.LEFT,
                         background="#ffffff", relief=tk.SOLID, borderwidth=1,
                         font=("宋体", "10", "normal"), padx=5, pady=2)
        label.pack(ipadx=1)
    
    def leave(event):
        nonlocal tooltip
        if tooltip:
            tooltip.destroy()
            tooltip = None
    
    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)


class ScrollableFrame(ttk.Frame):
    """
    可滚动的Frame
    
    用于创建带有垂直滚动条的Frame
    """
    
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        # 创建画布和滚动条
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # 配置滚动区域
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        # 创建窗口并配置滚动
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # 放置组件
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
    
    def _on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")


def center_window(window, width: Optional[int] = None, height: Optional[int] = None) -> None:
    """
    将窗口居中显示在屏幕上
    
    Args:
        window: 要居中的窗口
        width: 窗口宽度，如果为None则使用窗口当前宽度
        height: 窗口高度，如果为None则使用窗口当前高度
    """
    # 如果未指定尺寸，使用窗口当前尺寸
    if width is None:
        width = window.winfo_reqwidth()
    if height is None:
        height = window.winfo_reqheight()
    
    # 计算位置坐标
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    
    # 设置窗口位置
    window.geometry(f"{width}x{height}+{x}+{y}")


def create_form_field(parent, label_text: str, var, 
                     row: int, column: int = 0, 
                     widget_type: str = 'entry', 
                     options: Optional[Dict[str, Any]] = None,
                     tooltip: Optional[str] = None,
                     **kwargs) -> tk.Widget:
    """
    创建表单字段
    
    Args:
        parent: 父容器
        label_text: 标签文本
        var: 变量绑定
        row: 行位置
        column: 列位置
        widget_type: 控件类型，'entry'、'combobox'、'checkbox' 等
        options: 下拉选项（用于combobox）
        tooltip: 提示文本
        **kwargs: 其他参数
    
    Returns:
        创建的控件
    """
    # 创建标签
    label = ttk.Label(parent, text=label_text)
    label.grid(row=row, column=column, sticky=tk.W, padx=5, pady=2)
    
    # 根据控件类型创建不同控件
    widget = None
    if widget_type == 'entry':
        widget = ttk.Entry(parent, textvariable=var, **kwargs)
    elif widget_type == 'combobox':
        widget = ttk.Combobox(parent, textvariable=var, values=options, **kwargs)
    elif widget_type == 'checkbox':
        widget = ttk.Checkbutton(parent, variable=var, **kwargs)
    
    # 放置控件
    if widget:
        widget.grid(row=row, column=column+1, sticky=tk.EW, padx=5, pady=2)
        
        # 创建提示（如果指定）
        if tooltip:
            create_tooltip(widget, tooltip)
    
    return widget 