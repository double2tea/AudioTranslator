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
from tkinter import ttk, filedialog, messagebox, simpledialog
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
from ..utils.ui_utils import create_tooltip
from ..gui.dialogs.translation.translation_strategy_ui import create_translation_strategy_dialog
from ..gui.dialogs.naming.naming_rule_ui import create_naming_rule_dialog
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
        
        # 获取翻译服务
        self.translator_service = service_factory.get_translator_service()
        if not self.translator_service:
            logger.warning("无法获取翻译服务，翻译功能可能无法正常工作")
        
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
        
        # 现在填充分类树
        self._populate_category_tree()
        
        # 更新翻译策略信息
        self._update_strategy_info()
    
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
        
        # 添加翻译策略按钮
        self.strategy_button = ttk.Button(button_frame, text="翻译策略", command=self._on_open_translation_strategy_dialog)
        self.strategy_button.pack(side=tk.LEFT, padx=5)
        create_tooltip(self.strategy_button, "配置和管理翻译策略 (Ctrl+T)")
        
        # 添加命名规则按钮
        self.naming_rule_button = ttk.Button(button_frame, text="命名规则", command=self._on_open_naming_rule_dialog)
        self.naming_rule_button.pack(side=tk.LEFT, padx=5)
        create_tooltip(self.naming_rule_button, "配置和管理命名规则 (Ctrl+N)")
        
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
    
    def _create_file_area(self, parent):
        """
        创建文件管理区域
        
        Args:
            parent: 父级容器
            
        Returns:
            文件管理区域Frame
        """
        # 创建文件区域框架
        file_area_frame = ttk.Frame(parent)
        
        # 创建文件管理面板，传递翻译服务
        self.file_manager_panel = FileManagerPanel(file_area_frame, self.file_manager, self.translator_service)
        self.file_manager_panel.pack(fill=tk.BOTH, expand=True)
        
        return file_area_frame
    
    def _create_category_area(self, parent):
        """
        创建分类管理区域
        
        Args:
            parent: 父级容器
            
        Returns:
            分类管理区域Frame
        """
        # 创建分类区域框架
        category_area_frame = ttk.Frame(parent)
        
        # 创建分类区域标题
        title_frame = ttk.Frame(category_area_frame)
        title_frame.pack(fill=tk.X, pady=(0, 5))
        
        title_label = ttk.Label(title_frame, text="分类管理", font=("Helvetica", 10, "bold"))
        title_label.pack(side=tk.LEFT, padx=5)
        
        # 创建操作按钮
        actions_frame = ttk.Frame(category_area_frame)
        actions_frame.pack(fill=tk.X, pady=5)
        
        # 添加分类按钮
        self.add_category_btn = ttk.Button(actions_frame, text="添加分类", width=12, 
                                           command=self._on_add_category)
        self.add_category_btn.pack(side=tk.LEFT, padx=5)
        create_tooltip(self.add_category_btn, "添加新的文件分类")
        
        # 删除分类按钮
        self.del_category_btn = ttk.Button(actions_frame, text="删除分类", width=12,
                                           command=self._on_delete_category)
        self.del_category_btn.pack(side=tk.LEFT, padx=5)
        create_tooltip(self.del_category_btn, "删除选定的分类")
        
        # 分类树区域
        tree_frame = ttk.Frame(category_area_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建滚动条
        tree_scroll = ttk.Scrollbar(tree_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建分类树
        self.category_tree = ttk.Treeview(tree_frame, yscrollcommand=tree_scroll.set, 
                                          selectmode="browse", height=15)
        self.category_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.config(command=self.category_tree.yview)
        
        # 配置分类树
        self.category_tree["columns"] = ("count",)
        self.category_tree.column("#0", width=180, minwidth=150)
        self.category_tree.column("count", width=50, minwidth=50, anchor=tk.CENTER)
        
        self.category_tree.heading("#0", text="分类名称", anchor=tk.W)
        self.category_tree.heading("count", text="数量", anchor=tk.CENTER)
        
        # 绑定事件
        self.category_tree.bind("<<TreeviewSelect>>", self._on_category_selected)
        self.category_tree.bind("<Double-1>", self._on_category_double_click)
        self.category_tree.bind("<Button-3>", self._show_category_context_menu)
        
        # 创建分类信息区域
        info_frame = ttk.LabelFrame(category_area_frame, text="分类信息")
        info_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # 分类信息表格
        info_grid = ttk.Frame(info_frame)
        info_grid.pack(fill=tk.X, padx=5, pady=5)
        
        # 分类路径
        ttk.Label(info_grid, text="路径:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.category_path_var = tk.StringVar()
        ttk.Label(info_grid, textvariable=self.category_path_var).grid(
            row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        # 分类数量
        ttk.Label(info_grid, text="文件数:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.category_count_var = tk.StringVar()
        ttk.Label(info_grid, textvariable=self.category_count_var).grid(
            row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        # 分类类型
        ttk.Label(info_grid, text="类型:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.category_type_var = tk.StringVar()
        ttk.Label(info_grid, textvariable=self.category_type_var).grid(
            row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # 操作按钮区域
        button_frame = ttk.Frame(category_area_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        # 分类按钮
        self.categorize_btn = ttk.Button(button_frame, text="分类文件", width=14, 
                                         command=self._categorize_selected_files)
        self.categorize_btn.pack(side=tk.LEFT, padx=5)
        create_tooltip(self.categorize_btn, "将选中的文件分配到所选分类")
        
        # 自动分类按钮
        self.auto_categorize_btn = ttk.Button(button_frame, text="自动分类", width=14,
                                             command=self._auto_categorize_files)
        self.auto_categorize_btn.pack(side=tk.LEFT, padx=5)
        create_tooltip(self.auto_categorize_btn, "使用AI自动分类选中的文件")
        
        # 不再在这里调用 _populate_category_tree
        
        return category_area_frame
    
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
        if hasattr(self, 'file_manager_panel'):
            self.file_manager_panel._on_search_change(*args)
        
    def _on_filter_change(self, *args):
        """当过滤条件变化时过滤文件列表"""
        # 将由FileManagerPanel处理
        if hasattr(self, 'file_manager_panel'):
            self.file_manager_panel._on_filter_change(*args)
        
    def _update_status_bar(self):
        """更新状态栏"""
        # 获取当前文件列表
        files = self.file_manager.get_files()
        
        # 更新状态栏
        self.status_message.set(f"已加载 {len(files)} 个文件")
    
    def _create_status_bar(self):
        """创建状态栏"""
        # 创建状态栏框架
        status_bar = ttk.Frame(self.root, relief=tk.SUNKEN, style="StatusBar.TFrame")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 创建状态消息标签
        self.status_message = tk.StringVar()
        self.status_message.set("就绪")
        status_label = ttk.Label(
            status_bar, 
            textvariable=self.status_message, 
            style="StatusBar.TLabel",
            padding=(5, 2)
        )
        status_label.pack(side=tk.LEFT, fill=tk.X)
        
        # 创建翻译策略信息标签
        self.strategy_info = tk.StringVar()
        self.strategy_info.set("当前翻译策略: 未设置")
        strategy_label = ttk.Label(
            status_bar,
            textvariable=self.strategy_info,
            style="StatusBar.TLabel",
            padding=(5, 2)
        )
        strategy_label.pack(side=tk.RIGHT, padx=10)
        
        # 初始化翻译策略信息
        self._update_strategy_info()
        
        # 创建版本信息标签
        # 尝试从配置服务获取版本号，如果不可用则使用默认值
        app_version = "1.0.0"
        config_service = self.service_factory.get_service('config_service')
        if config_service:
            app_version = config_service.get('app_version', app_version)
        
        version_label = ttk.Label(
            status_bar, 
            text=f"版本: {app_version}", 
            style="StatusBar.TLabel",
            padding=(5, 2)
        )
        version_label.pack(side=tk.RIGHT)
        
        # 初始更新状态栏
        self._update_status_bar()

    def _on_close(self):
        """处理窗口关闭事件"""
        # 在这里可以添加关闭前的清理工作
        logger.info("应用程序正在关闭")
        
        # 关闭服务
        if hasattr(self, 'service_factory') and self.service_factory:
            self.service_factory.shutdown_all_services()
        
        # 关闭窗口
        self.root.destroy()

    def _bind_events(self):
        """绑定事件处理函数"""
        # 绑定窗口大小变化事件
        self.root.bind("<Configure>", self._on_window_resize)
        
        # 绑定键盘快捷键
        self.root.bind("<Control-o>", lambda e: self._open_directory())
        self.root.bind("<Control-r>", lambda e: self._refresh_current_directory())
        self.root.bind("<Control-q>", lambda e: self._on_close())
        self.root.bind("<Control-p>", lambda e: self._on_preferences())
        self.root.bind("<Control-t>", lambda e: self._on_open_translation_strategy_dialog())
        self.root.bind("<Control-n>", lambda e: self._on_open_naming_rule_dialog())

    def _on_window_resize(self, event):
        """处理窗口大小变化事件"""
        # 只处理来自根窗口的事件
        if event.widget == self.root:
            # 可以在这里添加窗口大小变化的处理逻辑
            pass

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
        self.tools_menu.add_command(label="翻译策略", command=self._on_open_translation_strategy_dialog)
        self.tools_menu.add_command(label="命名规则", command=self._on_open_naming_rule_dialog)
        
        # 将菜单添加到菜单栏
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
        """
        处理分类选择事件
        
        Args:
            event: 事件对象
        """
        # 获取选中的分类项
        selection = self.category_tree.selection()
        if not selection:
            return
        
        # 获取分类ID
        category_id = selection[0]
        
        # 如果选择的是根节点，清空信息显示
        if category_id == "root":
            self.category_path_var.set("")
            self.category_count_var.set("")
            self.category_type_var.set("")
            return
        
        # 获取分类信息
        category_info = self.category_tree.item(category_id, "values")
        category_name = self.category_tree.item(category_id, "text")
        
        # 显示分类信息
        parent_id = self.category_tree.parent(category_id)
        if parent_id:
            parent_name = self.category_tree.item(parent_id, "text")
            path = f"{parent_name}/{category_name}"
        else:
            path = category_name
        
        self.category_path_var.set(path)
        
        # 显示该分类下的文件数量
        if category_info and len(category_info) > 0:
            self.category_count_var.set(category_info[0])
        else:
            self.category_count_var.set("0")
        
        # 显示分类类型
        if parent_id:
            self.category_type_var.set("子分类")
        else:
            self.category_type_var.set("主分类")

    def _on_category_double_click(self, event):
        """
        处理分类双击事件
        
        Args:
            event: 事件对象
        """
        # 获取选中的分类项
        selection = self.category_tree.selection()
        if not selection:
            return
        
        # 获取分类ID
        category_id = selection[0]
        
        # 获取分类信息
        category_name = self.category_tree.item(category_id, "text")
        
        # 如果是折叠状态，展开该分类；如果是展开状态，折叠该分类
        if self.category_tree.item(category_id, "open"):
            self.category_tree.item(category_id, open=False)
        else:
            self.category_tree.item(category_id, open=True)
        
        logger.info(f"分类 '{category_name}' 被双击")

    def _show_category_context_menu(self, event):
        """
        显示分类右键菜单
        
        Args:
            event: 事件对象
        """
        # 选中鼠标点击的项
        item_id = self.category_tree.identify_row(event.y)
        if item_id:
            self.category_tree.selection_set(item_id)
            
            # 创建右键菜单
            context_menu = tk.Menu(self.category_tree, tearoff=0)
            
            # 添加菜单项
            context_menu.add_command(label="添加子分类", 
                                     command=lambda: self._on_add_subcategory(item_id))
            context_menu.add_command(label="重命名分类", 
                                     command=lambda: self._on_rename_category(item_id))
            context_menu.add_separator()
            context_menu.add_command(label="删除分类", 
                                     command=lambda: self._on_delete_category(item_id))
            
            # 显示菜单
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()

    def _on_add_category(self):
        """添加新的主分类"""
        # 弹出对话框，获取分类名称
        category_name = simpledialog.askstring("添加分类", "请输入分类名称:", parent=self.root)
        
        # 如果用户取消或输入为空，直接返回
        if not category_name or category_name.strip() == "":
            return
        
        # 检查分类名称是否已存在
        existing_categories = []
        for item_id in self.category_tree.get_children():
            item_text = self.category_tree.item(item_id, "text")
            existing_categories.append(item_text)
        
        if category_name in existing_categories:
            messagebox.showerror("错误", f"分类 '{category_name}' 已存在！", parent=self.root)
            return

        # 获取UCS服务
        ucs_service = self.service_factory.get_service("ucs_service")
        if not ucs_service:
            messagebox.showerror("错误", "UCS服务不可用，无法添加分类！", parent=self.root)
            return

        # 添加分类
        try:
            # 创建分类字典
            category_data = {
                "name": category_name,
                "path": category_name,
                "parent": None,
                "level": 0,
                "count": 0
            }
            
            # 添加到UCS服务
            ucs_service.add_category(category_data)
            
            # 添加到分类树
            category_id = self.category_tree.insert("", "end", text=category_name, values=("0"))
            
            # 选择新添加的分类
            self.category_tree.selection_set(category_id)
            self.category_tree.see(category_id)
            
            logger.info(f"成功添加分类: {category_name}")
            messagebox.showinfo("成功", f"分类 '{category_name}' 添加成功！", parent=self.root)
        except Exception as e:
            logger.error(f"添加分类失败: {str(e)}")
            messagebox.showerror("错误", f"添加分类失败: {str(e)}", parent=self.root)

    def _on_add_subcategory(self, parent_id):
        """
        添加子分类
        
        Args:
            parent_id: 父分类ID
        """
        # 获取父分类名称
        parent_name = self.category_tree.item(parent_id, "text")
        
        # 弹出对话框，获取子分类名称
        subcategory_name = simpledialog.askstring("添加子分类", 
                                                 f"请输入 '{parent_name}' 的子分类名称:", 
                                                 parent=self.root)
        
        # 如果用户取消或输入为空，直接返回
        if not subcategory_name or subcategory_name.strip() == "":
            return
        
        # 检查子分类名称是否已存在
        existing_subcategories = []
        for item_id in self.category_tree.get_children(parent_id):
            item_text = self.category_tree.item(item_id, "text")
            existing_subcategories.append(item_text)
        
        if subcategory_name in existing_subcategories:
            messagebox.showerror("错误", f"子分类 '{subcategory_name}' 已存在于 '{parent_name}' 下！", 
                                parent=self.root)
            return
        
        # 获取UCS服务
        ucs_service = self.service_factory.get_service("ucs_service")
        if not ucs_service:
            messagebox.showerror("错误", "UCS服务不可用，无法添加子分类！", parent=self.root)
            return
        
        # 添加子分类
        try:
            # 创建子分类字典
            subcategory_data = {
                "name": subcategory_name,
                "path": f"{parent_name}/{subcategory_name}",
                "parent": parent_name,
                "level": 1,
                "count": 0
            }
            
            # 添加到UCS服务
            ucs_service.add_category(subcategory_data)
            
            # 添加到分类树
            subcategory_id = self.category_tree.insert(parent_id, "end", text=subcategory_name, values=(subcategory.count if hasattr(subcategory, 'count') else 0,))
            
            # 展开父分类
            self.category_tree.item(parent_id, open=True)
            
            # 选择新添加的子分类
            self.category_tree.selection_set(subcategory_id)
            self.category_tree.see(subcategory_id)
            
            logger.info(f"成功添加子分类: {parent_name}/{subcategory_name}")
            messagebox.showinfo("成功", f"子分类 '{subcategory_name}' 添加成功！", parent=self.root)
        except Exception as e:
            logger.error(f"添加子分类失败: {str(e)}")
            messagebox.showerror("错误", f"添加子分类失败: {str(e)}", parent=self.root)

    def _on_rename_category(self, category_id):
        """
        重命名分类
        
        Args:
            category_id: 分类ID
        """
        # 获取当前分类名称
        current_name = self.category_tree.item(category_id, "text")
        
        # 获取父分类ID和名称
        parent_id = self.category_tree.parent(category_id)
        parent_name = ""
        if parent_id:
            parent_name = self.category_tree.item(parent_id, "text")
        
        # 弹出对话框，获取新的分类名称
        new_name = simpledialog.askstring("重命名分类", 
                                         f"请输入新的分类名称 (当前: '{current_name}'):", 
                                         initialvalue=current_name, 
                                         parent=self.root)
        
        # 如果用户取消或输入为空，或者名称没有变化，直接返回
        if not new_name or new_name.strip() == "" or new_name == current_name:
            return
        
        # 检查新名称是否已存在
        existing_names = []
        for item_id in self.category_tree.get_children(parent_id):
            if item_id != category_id:  # 排除当前分类
                item_text = self.category_tree.item(item_id, "text")
                existing_names.append(item_text)
        
        if new_name in existing_names:
            messagebox.showerror("错误", f"分类 '{new_name}' 已存在！", parent=self.root)
            return
        
        # 获取UCS服务
        ucs_service = self.service_factory.get_service("ucs_service")
        if not ucs_service:
            messagebox.showerror("错误", "UCS服务不可用，无法重命名分类！", parent=self.root)
            return
        
        # 重命名分类
        try:
            # 构建分类路径
            old_path = current_name
            new_path = new_name
            if parent_name:
                old_path = f"{parent_name}/{current_name}"
                new_path = f"{parent_name}/{new_name}"
            
            # 更新UCS服务中的分类
            ucs_service.rename_category(old_path, new_path)
            
            # 更新分类树中的分类名称
            self.category_tree.item(category_id, text=new_name)
            
            logger.info(f"成功重命名分类: '{old_path}' -> '{new_path}'")
            messagebox.showinfo("成功", f"分类重命名成功: '{current_name}' -> '{new_name}'", parent=self.root)
        except Exception as e:
            logger.error(f"重命名分类失败: {str(e)}")
            messagebox.showerror("错误", f"重命名分类失败: {str(e)}", parent=self.root)

    def _on_delete_category(self, category_id=None):
        """
        删除分类
        
        Args:
            category_id: 分类ID，如果为None则使用当前选中的分类
        """
        # 如果没有指定分类ID，使用当前选中的分类
        if category_id is None:
            selection = self.category_tree.selection()
            if not selection:
                messagebox.showinfo("提示", "请先选择要删除的分类！", parent=self.root)
                return
            category_id = selection[0]
        
        # 获取分类名称
        category_name = self.category_tree.item(category_id, "text")
        
        # 检查是否有子分类
        if self.category_tree.get_children(category_id):
            messagebox.showerror("错误", f"分类 '{category_name}' 包含子分类，无法删除！请先删除所有子分类。", 
                                parent=self.root)
            return
        
        # 确认对话框
        if not messagebox.askyesno("确认删除", f"确定要删除分类 '{category_name}' 吗？此操作不可撤销！", 
                                  parent=self.root):
            return
        
        # 获取UCS服务
        ucs_service = self.service_factory.get_service("ucs_service")
        if not ucs_service:
            messagebox.showerror("错误", "UCS服务不可用，无法删除分类！", parent=self.root)
            return
        
        # 获取父分类名称
        parent_id = self.category_tree.parent(category_id)
        parent_name = ""
        if parent_id:
            parent_name = self.category_tree.item(parent_id, "text")
        
        # 构建分类路径
        category_path = category_name
        if parent_name:
            category_path = f"{parent_name}/{category_name}"
        
        # 删除分类
        try:
            # 从UCS服务中删除分类
            ucs_service.delete_category(category_path)
            
            # 从分类树中删除分类
            self.category_tree.delete(category_id)
            
            logger.info(f"成功删除分类: {category_path}")
            messagebox.showinfo("成功", f"分类 '{category_name}' 删除成功！", parent=self.root)
        except Exception as e:
            logger.error(f"删除分类失败: {str(e)}")
            messagebox.showerror("错误", f"删除分类失败: {str(e)}", parent=self.root)

    def _open_directory(self):
        """打开文件夹对话框并加载选择的目录"""
        from tkinter import filedialog
        directory = filedialog.askdirectory(title="选择文件夹")
        if directory:
            # 更新当前目录变量
            self.current_directory.set(directory)
            # 使用文件管理面板加载目录
            self.file_manager_panel.load_directory(directory)
            logger.info(f"已打开目录: {directory}")
            
    def _refresh_current_directory(self):
        """刷新当前目录"""
        # 获取当前目录
        directory = self.current_directory.get()
        
        if not directory or directory == "":
            # 如果没有选择目录，提示用户
            messagebox.showinfo("提示", "请先选择一个目录")
            return
        
        # 刷新文件管理面板
        self.file_manager_panel.load_directory(directory)
        
        # 记录日志
        logger.info(f"刷新目录: {directory}")
        
        # 更新状态栏
        self._update_status_bar()
            
    def _populate_category_tree(self):
        """加载分类树数据"""
        # 清空现有分类树
        for item in self.category_tree.get_children():
            self.category_tree.delete(item)
        
        # 获取分类管理器
        category_manager = CategoryManager(self.root)
        if not category_manager:
            logger.error("无法获取分类管理器，分类树加载失败")
            return
        
        # 获取所有分类
        categories = category_manager.get_all_categories()
        if not categories:
            logger.warning("未找到任何分类")
            return
        
        # 添加根分类
        for cat_id, category in categories.items():
            if not category.subcategory:  # 只添加根分类
                # 创建分类节点
                node_id = self.category_tree.insert("", "end", text=category.name_zh, 
                                                   values=(category.count if hasattr(category, 'count') else 0,))
                
                # 递归添加子分类
                self._add_subcategories(cat_id, node_id, category_manager)
        
        # 更新标题显示分类数量
        title_text = f"分类管理 (共{len(categories)}个分类)"
        # 直接更新分类区域的标题
        for widget in self.category_area.winfo_children():
            if isinstance(widget, ttk.LabelFrame) or isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Label) and "分类管理" in child.cget("text"):
                        child.config(text=title_text)
                        break
    
    def _add_subcategories(self, parent_id, tree_parent, category_manager):
        """递归添加子分类
        
        Args:
            parent_id: 父分类ID
            tree_parent: 树中的父节点ID
            category_manager: 分类管理器实例
        """
        # 获取子分类
        subcategories = category_manager.get_subcategories(parent_id)
        if not subcategories:
            return
        
        # 按名称排序
        subcategories.sort(key=lambda x: x.name_zh.lower())
        
        # 添加子分类
        for subcategory in subcategories:
            # 创建节点
            node_id = self.category_tree.insert(
                tree_parent, 
                "end", 
                text=subcategory.name_zh,
                values=(subcategory.count if hasattr(subcategory, 'count') else 0,)
            )
            
            # 递归添加子分类的子分类
            self._add_subcategories(subcategory.cat_id, node_id, category_manager)

    def _on_open_translation_strategy_dialog(self):
        """打开翻译策略配置对话框"""
        translation_manager = self.service_factory.get_service('translation_manager_service')
        if translation_manager:
            dialog = create_translation_strategy_dialog(self.root, translation_manager)
            self.root.wait_window(dialog)
            # 对话框关闭后更新策略信息
            self._update_strategy_info()
        else:
            messagebox.showerror("错误", "无法获取翻译管理器服务")
            
    def _update_strategy_info(self):
        """更新翻译策略信息"""
        try:
            translation_manager = self.service_factory.get_service('translation_manager_service')
            if translation_manager and hasattr(self, 'strategy_info'):
                default_strategy_name = translation_manager.config.get('default_strategy', '未设置')
                if default_strategy_name != '未设置':
                    strategy = translation_manager.get_translation_strategy(default_strategy_name)
                    if strategy:
                        strategy_info = f"当前翻译策略: {strategy.get_name()}"
                        self.strategy_info.set(strategy_info)
                        return
                self.strategy_info.set("当前翻译策略: 未设置")
        except Exception as e:
            logger.error(f"更新翻译策略信息失败: {e}")
            if hasattr(self, 'strategy_info'):
                self.strategy_info.set("当前翻译策略: 获取失败")
    
    def _on_open_naming_rule_dialog(self):
        """打开命名规则配置对话框"""
        naming_service = self.service_factory.get_service('naming_service')
        if naming_service:
            dialog = create_naming_rule_dialog(self.root, naming_service)
            self.root.wait_window(dialog)
            # 对话框关闭后可以添加任何需要的更新操作
        else:
            messagebox.showerror("错误", "无法获取命名服务")
            