"""
音效文件翻译器主窗口模块

此模块提供了AudioTranslatorGUI类，用于创建和管理应用程序的主窗口。
主要功能包括：
1. 创建主界面布局
2. 初始化各个管理器
3. 处理用户交互
4. 管理文件操作
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple, Union
import platform
import subprocess

# 导入管理器
from ..managers.file_manager import FileManager
from ..managers.category_manager import CategoryManager
from ..gui.dialogs.category_selection_dialog import CategorySelectionDialog
from ..gui.dialogs.auto_categorize_dialog import AutoCategorizeDialog
from ..services.core.service_manager_service import ServiceManagerService
from ..services.api.model_service import ModelService
from ..gui.panels.service_manager_panel import ServiceManagerPanel
from ..gui.panels.file_manager_panel import FileManagerPanel
from ..services.core.service_factory import ServiceFactory
# 设置日志记录器
logger = logging.getLogger(__name__)

class AudioTranslatorGUI:
    """音效文件翻译器GUI类"""
    
    def __init__(self, root: tk.Tk, service_factory: ServiceFactory):
        """
        初始化主窗口
        
        Args:
            root: Tkinter根窗口
            service_factory: 服务工厂，提供应用所需的核心服务
            
        初始化过程:
            1. 设置窗口属性（标题、大小、图标）
            2. 获取基础服务（FileService、AudioService）
            3. 初始化管理器（FileManager、CategoryManager）
            4. 初始化变量和状态
            5. 设置UI样式
            6. 创建UI组件
            7. 绑定事件处理
        """
        self.root = root
        self.root.title("音频文件翻译器")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # 设置应用程序图标
        self._set_app_icon()
        
        # 获取基础服务
        self.service_factory = service_factory
        self.file_service = service_factory.get_file_service()
        self.audio_service = service_factory.get_audio_service()
        
        if not self.file_service or not self.audio_service:
            logger.error("无法获取基础服务，应用程序可能无法正常工作")
            messagebox.showerror("初始化错误", "无法获取基础服务，应用程序可能无法正常工作")
        
        # 初始化管理器
        self.file_manager = FileManager()
        
        # 获取UCS服务实例用于分类管理
        self.ucs_service = service_factory.get_service("ucs_service")
        if not self.ucs_service:
            logger.error("无法获取UCS服务，分类功能可能无法正常工作")
            messagebox.showerror("初始化错误", "无法获取UCS服务，分类功能可能无法正常工作")
        
        # 初始化分类管理器并传入UCS服务和根窗口
        self.category_manager = CategoryManager(self.root)
        
        # 手动将UCS服务传递给分类管理器
        if hasattr(self.category_manager, 'set_ucs_service') and self.ucs_service:
            self.category_manager.set_ucs_service(self.ucs_service)
        
        # 初始化变量
        self.current_directory = tk.StringVar(value=str(self.file_manager.current_directory))
        self.status_message = tk.StringVar(value="就绪")
        self.selected_files = []
        
        # 设置样式
        self._setup_styles()
        
        # 创建UI
        self._create_ui()
        
        # 绑定事件
        self._bind_events()
        
        # 设置窗口关闭处理
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # 创建菜单
        self._create_menus()
        
        logger.info("主窗口初始化完成")
    
    def _set_app_icon(self):
        """设置应用程序图标"""
        try:
            # 尝试设置 .ico 格式图标 (Windows)
            icon_path = Path(__file__).parent.parent.parent.parent / "assets" / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
                return
            
            # 尝试设置 .png 格式图标 (macOS/Linux)
            icon_path = Path(__file__).parent.parent.parent.parent / "assets" / "icon.png"
            if icon_path.exists():
                img = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, img)
                return
        except Exception as e:
            logger.warning(f"设置应用程序图标失败: {e}")
    
    def _setup_styles(self):
        """设置UI样式"""
        # 定义颜色方案
        self.COLORS = {
            'bg_dark': '#1E1E1E',  # 深色背景
            'bg_light': '#2D2D2D',  # 稍亮的背景
            'bg_accent': '#3C3C3C',  # 强调背景
            'fg': '#FFFFFF',        # 前景文本颜色
            'accent': '#0078D7',    # 强调色
            'highlight': '#505050', # 高亮色
            'active': '#007ACC',    # 激活状态颜色
            'hover': '#404040',     # 悬浮状态颜色
            'selected': '#264F78',  # 选中状态颜色
            'border': '#555555',    # 边框颜色
        }
        
        # 获取当前系统
        system = platform.system()
        
        # 配置样式
        style = ttk.Style()
        
        # 设置主题
        if system == "Windows":
            style.theme_use("vista")
        elif system == "Darwin":  # macOS
            style.theme_use("aqua")
        else:  # Linux
            style.theme_use("clam")
            
        # 配置Treeview样式（暗色）
        style.configure("Treeview",
            background=self.COLORS['bg_light'],
            foreground=self.COLORS['fg'],
            fieldbackground=self.COLORS['bg_light'],
            borderwidth=0)
        
        # 配置Treeview标题样式
        style.configure("Treeview.Heading",
            background=self.COLORS['bg_accent'],
            foreground=self.COLORS['fg'],
            relief="flat")
        style.map("Treeview.Heading",
            background=[('active', self.COLORS['hover'])])
            
        # 配置Treeview选中项样式
        style.map("Treeview",
            background=[('selected', self.COLORS['selected'])],
            foreground=[('selected', self.COLORS['fg'])])
            
        # 配置标签样式
        style.configure("TLabel", 
            background=self.COLORS['bg_dark'],
            foreground=self.COLORS['fg'])
            
        # 配置按钮样式
        style.configure("TButton", 
            background=self.COLORS['bg_accent'],
            foreground=self.COLORS['fg'])
        style.map("TButton",
            background=[('active', self.COLORS['active'])],
            relief=[('pressed', 'sunken')])
            
        # 配置输入框样式
        style.configure("TEntry", 
            fieldbackground=self.COLORS['bg_light'],
            foreground=self.COLORS['fg'],
            insertcolor=self.COLORS['fg'])
            
        # 配置框架样式
        style.configure("TFrame", 
            background=self.COLORS['bg_dark'])
            
        # 配置标签框架样式
        style.configure("TLabelframe", 
            background=self.COLORS['bg_dark'],
            foreground=self.COLORS['fg'])
        style.configure("TLabelframe.Label", 
            background=self.COLORS['bg_dark'],
            foreground=self.COLORS['fg'])
            
        # 配置Notebook样式
        style.configure("TNotebook", 
            background=self.COLORS['bg_dark'],
            tabmargins=[2, 5, 2, 0])
        style.configure("TNotebook.Tab", 
            background=self.COLORS['bg_accent'],
            foreground=self.COLORS['fg'],
            padding=[10, 2])
        style.map("TNotebook.Tab",
            background=[('selected', self.COLORS['active'])],
            expand=[('selected', [1, 1, 1, 0])])
            
        # 配置进度条样式
        style.configure("Horizontal.TProgressbar", 
            background=self.COLORS['accent'])
            
        # 配置组合框样式
        style.configure("TCombobox", 
            fieldbackground=self.COLORS['bg_light'],
            foreground=self.COLORS['fg'],
            background=self.COLORS['bg_accent'])
        style.map("TCombobox",
            fieldbackground=[('readonly', self.COLORS['bg_light'])],
            selectbackground=[('readonly', self.COLORS['selected'])],
            selectforeground=[('readonly', self.COLORS['fg'])])
            
        # 创建暗色样式变体
        style.configure("Dark.TFrame", background=self.COLORS['bg_dark'])
        style.configure("Dark.TLabel", background=self.COLORS['bg_dark'], foreground=self.COLORS['fg'])
        style.configure("Dark.TButton", background=self.COLORS['bg_accent'], foreground=self.COLORS['fg'])
        style.configure("Dark.TEntry", fieldbackground=self.COLORS['bg_light'], foreground=self.COLORS['fg'])
        style.configure("Dark.TLabelframe", background=self.COLORS['bg_dark'])
        style.configure("Dark.TLabelframe.Label", background=self.COLORS['bg_dark'], foreground=self.COLORS['fg'])
        style.configure("Dark.TNotebook", background=self.COLORS['bg_dark'])
        style.configure("Dark.TNotebook.Tab", background=self.COLORS['bg_accent'], foreground=self.COLORS['fg'])
        
        # 服务管理面板特定样式
        style.configure("Dark.Treeview", 
            background=self.COLORS['bg_light'],
            foreground=self.COLORS['fg'],
            fieldbackground=self.COLORS['bg_light'])
        style.configure("Dark.Treeview.Heading", 
            background=self.COLORS['bg_accent'],
            foreground=self.COLORS['fg'])
        style.map("Dark.Treeview",
            background=[('selected', self.COLORS['selected'])],
            foreground=[('selected', self.COLORS['fg'])])
        
        # 复选框和单选按钮样式
        style.configure("Dark.TCheckbutton", 
            background=self.COLORS['bg_dark'],
            foreground=self.COLORS['fg'])
        style.map("Dark.TCheckbutton",
            background=[('active', self.COLORS['bg_dark'])],
            foreground=[('active', self.COLORS['fg'])])
        
        style.configure("Dark.TRadiobutton", 
            background=self.COLORS['bg_dark'],
            foreground=self.COLORS['fg'])
        style.map("Dark.TRadiobutton",
            background=[('active', self.COLORS['bg_dark'])],
            foreground=[('active', self.COLORS['fg'])])
        
        # 下拉列表样式
        style.configure("Dark.TCombobox", 
            fieldbackground=self.COLORS['bg_light'],
            foreground=self.COLORS['fg'],
            background=self.COLORS['bg_accent'])
        style.map("Dark.TCombobox",
            fieldbackground=[('readonly', self.COLORS['bg_light'])],
            selectbackground=[('readonly', self.COLORS['selected'])],
            selectforeground=[('readonly', self.COLORS['fg'])])
        
        # 设置根窗口背景色
        self.root.configure(background=self.COLORS['bg_dark'])
    
    def _create_ui(self):
        """创建主用户界面"""
        # 创建主框架
        self.main_frame = ttk.Frame(self.root, style="Dark.TFrame")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 设置根窗口背景
        self.root.configure(background=self.COLORS['bg_dark'])
        
        # 创建工具栏
        self._create_toolbar()
        
        # 创建选项卡
        self.notebook = ttk.Notebook(self.main_frame, style="Dark.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # 创建文件管理标签页
        self.file_tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.file_tab, text="文件管理")
        
        # 配置文件标签页
        self.file_tab.columnconfigure(0, weight=2)  # 文件区域占更多空间
        self.file_tab.columnconfigure(1, weight=1)  # 分类区域占更少空间
        self.file_tab.rowconfigure(0, weight=1)
        
        # 创建文件相关组件
        self.file_area = self._create_file_area(self.file_tab)
        self.file_area.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        # 创建分类相关组件
        self.category_area = self._create_category_area(self.file_tab)
        self.category_area.grid(row=0, column=1, sticky='nsew')
        
        # 创建服务管理标签页
        self.service_tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.service_tab, text="服务管理")
        
        # 获取service_manager_service实例
        service_manager = self.service_factory.get_service("service_manager_service")
        
        # 创建ServiceManagerPanel并添加到服务管理标签页
        if service_manager:
            self.service_manager_panel = ServiceManagerPanel(self.service_tab, service_manager)
            self.service_manager_panel.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        else:
            # 如果服务管理器不可用，显示错误消息
            ttk.Label(
                self.service_tab, 
                text="服务管理功能不可用，请检查配置", 
                style="Dark.TLabel"
            ).pack(expand=True, pady=50)
        
        # 创建状态栏
        self._create_status_bar()
        
        # 关联选项卡切换事件
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
    
    def _create_toolbar(self):
        """创建工具栏"""
        # 创建工具栏框架
        toolbar_frame = ttk.Frame(self.main_frame, style="Dark.TFrame", padding=5)
        toolbar_frame.pack(fill=tk.X, side=tk.TOP, pady=(0, 5))
        
        # 创建按钮框架
        button_frame = ttk.Frame(toolbar_frame, style="Dark.TFrame")
        button_frame.pack(side=tk.LEFT)
        
        # 添加按钮
        ttk.Button(button_frame, text="打开文件夹", command=self._open_directory).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="刷新", command=self._refresh_current_directory).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="分类", command=self._categorize_selected_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="自动分类", command=self._auto_categorize_files).pack(side=tk.LEFT, padx=5)
        
        # 添加搜索标签
        ttk.Label(toolbar_frame, text="搜索:", style="Dark.TLabel").pack(side=tk.LEFT, padx=(15, 5))
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search_change)
        self.search_entry = ttk.Entry(toolbar_frame, textvariable=self.search_var, width=15, style="Dark.TEntry")
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # 添加状态过滤器
        ttk.Label(toolbar_frame, text="状态:", style="Dark.TLabel").pack(side=tk.LEFT, padx=(0, 5))
        
        self.status_filter_var = tk.StringVar(value="全部")
        status_filter = ttk.Combobox(
            toolbar_frame, 
            textvariable=self.status_filter_var,
            values=["全部", "未处理", "处理中", "已完成", "已分类", "已删除"],
            width=10,
            state="readonly"
        )
        status_filter.pack(side=tk.LEFT)
        status_filter.bind("<<ComboboxSelected>>", self._on_filter_change)
    
    def _create_file_area(self, parent_frame):
        """创建文件区域"""
        # 创建文件区域容器框架
        file_area_frame = ttk.LabelFrame(parent_frame, text="文件列表", style="Dark.TLabelframe")
        file_area_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建FileManagerPanel实例
        self.file_manager_panel = FileManagerPanel(file_area_frame, self.file_manager)
        self.file_manager_panel.pack(fill=tk.BOTH, expand=True)
        
        # 保留目录显示功能
        # 创建目录显示框架
        dir_frame = ttk.Frame(file_area_frame, style="Dark.TFrame", padding=(5, 5))
        dir_frame.pack(fill=tk.X, side=tk.TOP, pady=(0, 5))
        
        # 添加目录标签
        ttk.Label(dir_frame, text="当前目录:", style="Dark.TLabel").pack(side=tk.LEFT, padx=(0, 5))
        
        # 添加目录路径显示
        self.current_dir_var = tk.StringVar(value="未选择目录")
        ttk.Label(dir_frame, textvariable=self.current_dir_var, style="Dark.TLabel").pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        return file_area_frame
    
    def _on_file_selected(self, event):
        """
        处理文件选择事件
        
        此方法现在由FileManagerPanel内部处理，保留此方法是为了兼容现有代码
        """
        pass
    
    def _on_file_double_click(self, event):
        """
        处理文件双击事件
        
        此方法现在由FileManagerPanel内部处理，保留此方法是为了兼容现有代码
        """
        pass
    
    def _show_file_context_menu(self, event):
        """
        显示文件右键菜单
        
        此方法现在由FileManagerPanel内部处理，保留此方法是为了兼容现有代码
        """
        pass
    
    def _open_selected_file(self):
        """
        打开选中的文件
        
        此方法现在由FileManagerPanel内部处理，保留此方法是为了兼容现有代码
        """
        pass
    
    def _copy_file_path(self):
        """
        复制文件路径
        
        此方法现在由FileManagerPanel内部处理，保留此方法是为了兼容现有代码
        """
        pass
    
    def _delete_selected_files(self):
        """
        删除选定的文件
        
        此方法现在由FileManagerPanel内部处理，保留此方法是为了兼容现有代码
        """
        pass
        
    def _categorize_selected_files(self):
        """
        分类选定的文件
        
        使用FileManagerPanel获取选中的文件
        """
        if not hasattr(self, 'file_manager_panel'):
            messagebox.showinfo("提示", "请先加载文件")
            return
            
        selected_files = self.file_manager_panel.get_selected_files()
        if not selected_files:
            messagebox.showinfo("提示", "请选择要分类的文件")
            return
            
        # 创建分类选择对话框
        dialog = CategorySelectionDialog(
            self.root, 
            self.category_manager, 
            selected_files
        )
        
        # 如果用户确认分类，更新文件状态
        if dialog.result:
            category_id = dialog.result
            category_name = self.category_manager.get_category_name(category_id)
            
            # 更新文件状态
            count = self.file_manager.batch_update_status(selected_files, f"已分类: {category_name}")
            
            # 更新UI
            if hasattr(self, 'file_manager_panel'):
                self.file_manager_panel._refresh_files()
                
            # 更新状态栏
            self.status_message.set(f"已将 {count} 个文件分类为 {category_name}")
            
            # 记录日志
            logger.info(f"已将 {count} 个文件分类为 {category_name} (ID: {category_id})")
    
    def _auto_categorize_files(self):
        """
        自动分类文件
        
        使用FileManagerPanel获取选中的文件
        """
        if not hasattr(self, 'file_manager_panel'):
            messagebox.showinfo("提示", "请先加载文件")
            return
            
        selected_files = self.file_manager_panel.get_selected_files()
        if not selected_files:
            messagebox.showinfo("提示", "请选择要自动分类的文件")
            return
            
        # 创建自动分类对话框
        dialog = AutoCategorizeDialog(
            self.root, 
            self.category_manager,
            self.file_manager,
            selected_files
        )
        
        # 如果用户确认分类，更新文件状态并刷新UI
        if dialog.categorized_files:
            # 更新UI
            if hasattr(self, 'file_manager_panel'):
                self.file_manager_panel._refresh_files()
                
            # 更新状态栏
            count = len(dialog.categorized_files)
            self.status_message.set(f"已自动分类 {count} 个文件")
            
            # 记录日志
            logger.info(f"已自动分类 {count} 个文件")
    
    def _on_search_change(self, *args):
        """当搜索文本变化时过滤文件列表"""
        # 将由FileManagerPanel处理
        pass
        
    def _on_filter_change(self, event):
        """当过滤条件变化时过滤文件列表"""
        # 将由FileManagerPanel处理
        pass
        
    def _update_status_bar(self):
        """更新状态栏"""
        # 获取当前文件列表
        files = self.file_manager.get_files()
        
        # 更新状态栏
        self.status_message.set(f"已加载 {len(files)} 个文件")
    
    def _on_close(self):
        """处理窗口关闭事件"""
        # 在这里可以添加关闭前的清理工作
        logger.info("应用程序正在关闭")
        self.root.destroy()

    def _create_menus(self):
        """创建菜单栏"""
        self.menu_bar = tk.Menu(self.root)
        
        # 文件菜单
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="打开文件夹", command=self._open_directory)
        self.file_menu.add_command(label="刷新", command=self._refresh_current_directory)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="退出", command=self._on_close)
        
        # 编辑菜单
        self.edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.edit_menu.add_command(label="首选项", command=self._on_preferences)
        
        # 工具菜单
        self.tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.tools_menu.add_command(label="模型管理", command=self._on_model_manager)
        
        # 添加菜单到菜单栏
        self.menu_bar.add_cascade(label="文件", menu=self.file_menu)
        self.menu_bar.add_cascade(label="编辑", menu=self.edit_menu)
        self.menu_bar.add_cascade(label="工具", menu=self.tools_menu)
        
        # 设置菜单栏
        self.root.config(menu=self.menu_bar)

    def _on_model_manager(self):
        """打开模型管理对话框"""
        try:
            from .dialogs.model_manager_dialog import ModelManagerDialog
            
            # 获取服务管理器和配置服务
            service_manager = self.service_factory.get_service("service_manager_service")
            config_service = self.service_factory.get_service("config_service")
            
            if not service_manager or not config_service:
                messagebox.showerror("错误", "无法获取服务管理器或配置服务")
                return
            
            # 创建并显示模型管理对话框
            dialog = ModelManagerDialog(self.root, service_manager, config_service)
            self.root.wait_window(dialog)
            
            # 对话框关闭后，可能需要刷新UI或其他操作
            self._refresh_ui()
        except Exception as e:
            logger.error(f"打开模型管理对话框时发生错误: {e}")
            messagebox.showerror("错误", f"无法打开模型管理对话框: {e}")
            
    def _refresh_ui(self):
        """刷新UI界面"""
        try:
            # 刷新可能需要更新的UI组件
            if hasattr(self, 'status_bar'):
                self.status_bar.update_status("UI已刷新")
            
            # 刷新分类树
            if hasattr(self, 'category_tree'):
                self._populate_category_tree()
                logger.info("分类树已刷新")
            
            # 如果有其他需要刷新的UI组件，在这里添加
            
            logger.info("UI已刷新")
        except Exception as e:
            logger.error(f"刷新UI时发生错误: {e}")
        
    def _on_preferences(self):
        """打开首选项对话框"""
        # 临时实现，后续可以添加实际的首选项对话框
        messagebox.showinfo("首选项", "首选项功能正在开发中...")

    def _on_tab_changed(self, event=None):
        """处理标签页切换事件"""
        # 记录标签页切换
        current_tab = self.notebook.select()
        tab_id = self.notebook.index(current_tab)
        tab_name = self.notebook.tab(tab_id, "text")
        logger.info(f"选项卡切换: {tab_name}")
        
        # 如果切换到服务管理标签页，更新服务列表
        if tab_name == "服务管理" and hasattr(self, 'service_manager_panel'):
            # 仅当面板存在时刷新
            if hasattr(self.service_manager_panel, '_refresh_services'):
                self.service_manager_panel._refresh_services()

    def _on_category_selected(self, event):
        """当分类树中选择某个分类时处理
        
        Args:
            event: 事件对象
        """
        # 获取选中的分类
        selected_items = self.category_tree.selection()
        if not selected_items:
            return
        
        # 获取分类ID和名称
        category_id = selected_items[0]  # 使用item_id作为分类ID
        category_name = self.category_tree.item(category_id, "text")
        
        # 在这里可以添加选中分类后的处理逻辑，例如过滤文件列表等
        logger.info(f"选中分类: {category_name} (ID: {category_id})")
        
        # 更新状态栏
        self.status_message.set(f"选中分类: {category_name}")
        
    def _on_preferences(self):
        """打开首选项对话框"""
        # 临时实现，后续可以添加实际的首选项对话框
        messagebox.showinfo("首选项", "首选项功能正在开发中...")

    def _populate_category_tree(self):
        """填充分类树"""
        # 清空分类树
        for item in self.category_tree.get_children():
            self.category_tree.delete(item)
        
        # 获取分类列表
        categories = list(self.category_manager.categories.values())
        
        # 按字母顺序排序
        categories.sort(key=lambda x: x.name_zh.lower())
        
        # 插入根分类
        for category in categories:
            # 只显示根分类
            if not category.subcategory:
                # 创建根节点
                node_id = self.category_tree.insert(
                    "", 
                    "end", 
                    text=category.name_zh, 
                    values=(category.count if hasattr(category, 'count') else 0,)
                )
                
                # 递归添加子分类
                self._add_subcategories(category.cat_id, node_id)
        
        # 更新统计信息
        self.category_stats_label.config(text=f"共{len(categories)}个分类")
    
    def _add_subcategories(self, parent_id, tree_parent):
        """递归添加子分类
        
        Args:
            parent_id: 父分类ID
            tree_parent: 树中的父节点ID
        """
        # 获取子分类
        subcategories = self.category_manager.get_subcategories(parent_id)
        
        # 按字母顺序排序
        subcategories.sort(key=lambda x: x.name_zh.lower())
        
        # 添加子分类
        for subcategory in subcategories:
            # 创建节点
            node_id = self.category_tree.insert(
                tree_parent, 
                "end", 
                text=subcategory.name_zh,  # 使用中文名称
                values=(subcategory.count if hasattr(subcategory, 'count') else 0,)
            )
            
            # 递归添加子分类的子分类
            self._add_subcategories(subcategory.cat_id, node_id) 