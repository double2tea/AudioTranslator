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
        self.category_manager = CategoryManager(self.root)
        
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
        # 创建样式
        style = ttk.Style()
        
        # 检测当前系统
        system = platform.system()
        
        # 设置主题
        if system == "Windows":
            style.theme_use('vista')
        elif system == "Darwin":  # macOS
            style.theme_use('aqua')
        else:  # Linux
            try:
                style.theme_use('clam')
            except:
                pass
        
        # 设置Treeview样式
        style.configure("Treeview", 
                        rowheight=25,
                        borderwidth=0,
                        background="#f5f5f5",
                        fieldbackground="#f5f5f5")
        style.map("Treeview",
                 background=[('selected', '#0078D7')],
                 foreground=[('selected', 'white')])
        
        # 设置TButton样式
        style.configure("TButton", 
                        padding=5,
                        font=('宋体', 10))
        
        # 设置状态标签样式
        style.configure("Status.TLabel", 
                       background="#f0f0f0",
                       padding=2)
        
        # 设置标题标签样式
        style.configure("Title.TLabel", 
                       font=('宋体', 12, 'bold'),
                       padding=5)
        
        # 设置进度样式
        style.configure("TProgressbar", 
                       thickness=10,
                       background='#0078D7')
        
        # 设置TNotebook样式
        style.configure("TNotebook", 
                       padding=5,
                       tabmargins=[2, 5, 2, 0])
        style.configure("TNotebook.Tab", 
                       padding=[10, 2],
                       font=('宋体', 10))
        style.map("TNotebook.Tab",
                 background=[('selected', '#0078D7'), ('active', '#CCE4F7')],
                 foreground=[('selected', 'white'), ('active', 'black')])
    
    def _create_ui(self):
        """创建主窗口UI组件"""
        # 创建主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建分隔窗格 - 水平分割
        self.main_paned = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        # 创建左侧面板（文件区域）
        self.left_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.left_frame, weight=3)
        
        # 创建右侧面板（服务配置区域）
        self.right_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.right_frame, weight=2)
        
        # 创建左侧垂直分隔窗格
        self.left_paned = ttk.PanedWindow(self.left_frame, orient=tk.VERTICAL)
        self.left_paned.pack(fill=tk.BOTH, expand=True)
        
        # 创建工具栏
        self._create_toolbar()
        
        # 创建文件区域
        self._create_file_area()
        
        # 创建右侧分隔窗格 - 垂直分割
        self.right_paned = ttk.PanedWindow(self.right_frame, orient=tk.VERTICAL)
        self.right_paned.pack(fill=tk.BOTH, expand=True)
        
        # 获取服务管理服务
        self.service_manager = self.service_factory.get_service_manager_service()
        
        if not self.service_manager:
            logger.error("无法获取服务管理器，服务功能将不可用")
            messagebox.showerror("初始化错误", "无法获取服务管理器，服务功能将不可用")
        
        # 创建服务面板（上面）
        service_frame = ttk.LabelFrame(self.right_paned, text="服务配置")
        self.right_paned.add(service_frame, weight=2)
        
        # 创建服务管理面板
        self.service_manager_panel = ServiceManagerPanel(service_frame, self.service_manager)
        self.service_manager_panel.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建分类区域（下面）
        self._create_category_area()
        
        # 创建状态栏
        self._create_status_bar()
    
    def _create_toolbar(self):
        """创建工具栏"""
        # 创建工具栏框架
        toolbar_frame = ttk.Frame(self.left_paned)
        self.left_paned.add(toolbar_frame, weight=1)
        
        # 左侧按钮区域
        button_frame = ttk.Frame(toolbar_frame)
        button_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        # 添加打开目录按钮
        self.open_button = ttk.Button(
            button_frame, 
            text="打开目录", 
            command=self._open_directory,
            style="TButton"
        )
        self.open_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # 添加刷新按钮
        self.refresh_button = ttk.Button(
            button_frame, 
            text="刷新", 
            command=self._refresh_current_directory,
            style="TButton"
        )
        self.refresh_button.pack(side=tk.LEFT, padx=5)
        
        # 添加分类按钮
        self.categorize_button = ttk.Button(
            button_frame, 
            text="手动分类", 
            command=self._categorize_selected_files,
            style="TButton"
        )
        self.categorize_button.pack(side=tk.LEFT, padx=5)
        
        # 添加自动分类按钮
        self.auto_categorize_button = ttk.Button(
            button_frame, 
            text="自动分类", 
            command=self._auto_categorize_files,
            style="TButton"
        )
        self.auto_categorize_button.pack(side=tk.LEFT, padx=5)
        
        # 右侧搜索和过滤区域
        filter_frame = ttk.Frame(toolbar_frame)
        filter_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 添加搜索框
        ttk.Label(filter_frame, text="搜索:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search_change)
        self.search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=15)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # 添加状态过滤器
        ttk.Label(filter_frame, text="状态:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.status_filter_var = tk.StringVar(value="全部")
        status_filter = ttk.Combobox(
            filter_frame, 
            textvariable=self.status_filter_var,
            values=["全部", "未处理", "处理中", "已完成", "已分类", "已删除"],
            width=10,
            state="readonly"
        )
        status_filter.pack(side=tk.LEFT)
        status_filter.bind("<<ComboboxSelected>>", self._on_filter_change)
    
    def _create_file_area(self):
        """创建文件区域"""
        # 创建目录区域框架
        dir_frame = ttk.Frame(self.left_paned)
        self.left_paned.add(dir_frame, weight=1)
        
        # 当前目录标签
        ttk.Label(dir_frame, text="当前目录:").pack(side=tk.LEFT, padx=(0, 5))
        
        # 当前目录显示框
        dir_entry = ttk.Entry(dir_frame, textvariable=self.current_directory, width=50)
        dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 浏览按钮
        ttk.Button(
            dir_frame, 
            text="浏览...", 
            command=self._open_directory,
            style="TButton",
            width=8
        ).pack(side=tk.LEFT, padx=(5, 0))
        
        # 创建文件树
        self._create_file_tree()
    
    def _create_file_tree(self):
        """创建文件树控件"""
        # 创建文件树区域
        file_frame = ttk.Frame(self.left_paned)
        self.left_paned.add(file_frame, weight=3)
        
        # 创建水平和垂直滚动条
        scroll_frame = ttk.Frame(file_frame)
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 垂直滚动条
        y_scrollbar = ttk.Scrollbar(scroll_frame, orient=tk.VERTICAL)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 水平滚动条
        x_scrollbar = ttk.Scrollbar(scroll_frame, orient=tk.HORIZONTAL)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 创建树形视图
        self.file_tree = ttk.Treeview(
            scroll_frame,
            columns=("size", "type", "status"),
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set,
            selectmode="extended"
        )
        
        # 配置滚动条
        y_scrollbar.config(command=self.file_tree.yview)
        x_scrollbar.config(command=self.file_tree.xview)
        
        # 设置列
        self.file_tree.column("#0", width=300, stretch=tk.YES)
        self.file_tree.column("size", width=100, anchor=tk.E)
        self.file_tree.column("type", width=100, anchor=tk.CENTER)
        self.file_tree.column("status", width=150, anchor=tk.CENTER)
        
        # 设置列标题
        self.file_tree.heading("#0", text="文件名", command=lambda: self._sort_files('name'))
        self.file_tree.heading("size", text="大小", command=lambda: self._sort_files('size'))
        self.file_tree.heading("type", text="类型", command=lambda: self._sort_files('type'))
        self.file_tree.heading("status", text="状态", command=lambda: self._sort_files('status'))
        
        # 包装文件树
        self.file_tree.pack(fill=tk.BOTH, expand=True)
        
        # 绑定事件
        self.file_tree.bind("<ButtonRelease-1>", self._on_file_selected)
        self.file_tree.bind("<Double-1>", self._on_file_double_click)
        self.file_tree.bind("<ButtonRelease-3>", self._show_file_context_menu)
        
        # 创建右键菜单
        self.file_context_menu = tk.Menu(self.root, tearoff=0)
        self.file_context_menu.add_command(label="设为未处理", command=lambda: self._set_file_status("未处理"))
        self.file_context_menu.add_command(label="设为处理中", command=lambda: self._set_file_status("处理中"))
        self.file_context_menu.add_command(label="设为已完成", command=lambda: self._set_file_status("已完成"))
        self.file_context_menu.add_command(label="设为已删除", command=lambda: self._set_file_status("已删除"))
        
        # 创建分隔符
        self.file_context_menu.add_separator()
        
        # 添加分类菜单
        self.file_context_menu.add_command(label="手动分类", command=self._categorize_selected_files)
        self.file_context_menu.add_command(label="自动分类", command=self._auto_categorize_files)
    
    def _on_file_selected(self, event):
        """文件选择事件处理
        
        Args:
            event: 事件对象
        """
        # 获取选中的文件
        selected_items = self.file_tree.selection()
        
        # 设置选中文件
        selected_files = [self.file_tree.item(item, "text") for item in selected_items]
        self.file_manager.set_selected_files(selected_files)
        
        # 更新状态栏
        self._update_status_bar()
        
    def _on_file_double_click(self, event):
        """文件双击事件处理
        
        Args:
            event: 事件对象
        """
        # 获取选中的文件
        selected_items = self.file_tree.selection()
        if not selected_items:
            return
            
        # 获取文件信息
        file_name = self.file_tree.item(selected_items[0], "text")
        file_info = self.file_manager.get_file_info(file_name)
        
        # 检查文件是否存在
        if file_info and os.path.exists(file_info.get('path')):
            # 打开文件 (使用系统默认程序)
            try:
                if platform.system() == 'Darwin':  # macOS
                    subprocess.call(('open', file_info.get('path')))
                elif platform.system() == 'Windows':  # Windows
                    os.startfile(file_info.get('path'))
                else:  # Linux
                    subprocess.call(('xdg-open', file_info.get('path')))
            except Exception as e:
                messagebox.showerror("打开文件错误", f"无法打开文件: {e}")
        
    def _show_file_context_menu(self, event):
        """显示文件右键菜单
        
        Args:
            event: 事件对象
        """
        # 获取选中的文件
        selected_items = self.file_tree.selection()
        if not selected_items:
            return
            
        # 显示右键菜单
        try:
            self.file_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.file_context_menu.grab_release()
            
    def _set_file_status(self, status):
        """设置文件状态
        
        Args:
            status: 文件状态
        """
        # 获取选中的文件
        selected_items = self.file_tree.selection()
        if not selected_items:
            return
            
        # 获取文件名
        file_names = [self.file_tree.item(item, "text") for item in selected_items]
        
        # 批量更新文件状态
        self.file_manager.batch_update_status(file_names, status)
        
        # 刷新文件树
        self._refresh_file_tree()
        
    def _sort_files(self, column):
        """排序文件
        
        Args:
            column: 排序列
        """
        # 设置排序键和排序方向
        if self.file_manager.sorting_key == column:
            # 如果已经是当前排序列，则反转排序方向
            self.file_manager.sorting_reverse = not self.file_manager.sorting_reverse
        else:
            # 否则，设置新的排序列，并设置升序排序
            self.file_manager.sorting_key = column
            self.file_manager.sorting_reverse = False
            
        # 刷新文件树
        self._refresh_file_tree()
        
    def _apply_filters(self):
        """应用过滤器"""
        # 获取搜索文本
        search_text = self.search_var.get().lower()
        
        # 获取状态过滤器
        status_filter = self.status_filter_var.get()
        
        # 清空文件树
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
            
        # 获取文件列表
        files = self.file_manager.get_files()
        
        # 应用过滤器
        for file_name, file_info in files.items():
            # 应用搜索过滤器
            if search_text and search_text not in file_name.lower():
                continue
                
            # 应用状态过滤器
            if status_filter != "全部" and file_info.get('status') != status_filter:
                continue
                
            # 添加文件到树
            self.file_tree.insert(
                "", 
                "end", 
                text=file_name, 
                values=(
                    file_info.get('formatted_size', '未知'),
                    file_info.get('extension', '未知'),
                    file_info.get('status', '未处理')
                )
            )
            
        # 更新状态栏
        self._update_status_bar()
    
    def _create_category_area(self):
        """创建分类区域"""
        # 创建分类区域框架
        category_frame = ttk.LabelFrame(self.right_paned, text="分类管理")
        self.right_paned.add(category_frame, weight=1)
        
        # 创建分类框架的内容
        content_frame = ttk.Frame(category_frame, padding=5)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建分类选项区域
        options_frame = ttk.Frame(content_frame)
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 使用子分类选项
        ttk.Label(options_frame, text="使用子分类:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Checkbutton(
            options_frame,
            variable=self.category_manager.get_use_subcategory_var()
        ).pack(side=tk.LEFT)
        
        # 创建分类树
        tree_frame = ttk.Frame(content_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # 分类列表标签
        ttk.Label(tree_frame, text="可用分类:", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 5))
        
        # 创建分类树滚动区域
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建分类树
        self.category_tree = ttk.Treeview(
            tree_frame,
            columns=("count"),
            yscrollcommand=scrollbar.set,
            selectmode="browse",
            height=10
        )
        self.category_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 配置滚动条
        scrollbar.config(command=self.category_tree.yview)
        
        # 设置列
        self.category_tree.column("#0", width=300, stretch=tk.YES)
        self.category_tree.column("count", width=50, anchor=tk.CENTER)
        
        self.category_tree.heading("#0", text="分类名称")
        self.category_tree.heading("count", text="文件数")
        
        # 填充分类树
        self._populate_category_tree()
        
        # 创建分类操作按钮
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            button_frame,
            text="手动分类选中文件",
            command=self._categorize_selected_files
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            button_frame,
            text="自动分类选中文件",
            command=self._auto_categorize_files
        ).pack(side=tk.LEFT, padx=5)
        
        # 显示分类统计信息
        stats_frame = ttk.Frame(content_frame)
        stats_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(stats_frame, text="分类统计:").pack(side=tk.LEFT)
        self.category_stats_label = ttk.Label(stats_frame, text="共0个分类")
        self.category_stats_label.pack(side=tk.LEFT, padx=(5, 0))
    
    def _populate_category_tree(self):
        """填充分类树"""
        # 清空分类树
        for item in self.category_tree.get_children():
            self.category_tree.delete(item)
        
        # 获取分类列表
        categories = self.category_manager.categories
        
        # 按字母顺序排序
        categories.sort(key=lambda x: x.name.lower())
        
        # 插入根分类
        for category in categories:
            # 只显示根分类
            if not category.parent:
                # 创建根节点
                node_id = self.category_tree.insert(
                    "", 
                    "end", 
                    text=category.name, 
                    values=(category.count if hasattr(category, 'count') else 0,)
                )
                
                # 递归添加子分类
                self._add_subcategories(category.id, node_id)
        
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
        subcategories.sort(key=lambda x: x.name.lower())
        
        # 添加子分类
        for subcategory in subcategories:
            # 创建节点
            node_id = self.category_tree.insert(
                tree_parent, 
                "end", 
                text=subcategory.name, 
                values=(subcategory.count if hasattr(subcategory, 'count') else 0,)
            )
            
            # 递归添加子分类的子分类
            self._add_subcategories(subcategory.id, node_id)
    
    def _create_status_bar(self):
        """创建状态栏"""
        # 创建状态栏框架
        status_bar = ttk.Frame(self.main_frame, relief="sunken", border=1)
        status_bar.grid(row=2, column=0, sticky="ew")
        
        # 配置状态栏网格
        status_bar.columnconfigure(0, weight=1)
        status_bar.columnconfigure(1, weight=0)
        
        # 添加状态消息
        ttk.Label(status_bar, textvariable=self.status_message, 
                 style="Status.TLabel").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        
        # 添加版本信息
        ttk.Label(status_bar, text="v1.0.0", 
                 style="Status.TLabel").grid(row=0, column=1, sticky="e", padx=5, pady=2)
    
    def _bind_events(self):
        """绑定事件处理函数"""
        # 文件选择事件
        self.file_tree.bind("<<TreeviewSelect>>", self._on_file_selected)
        # 文件双击事件
        self.file_tree.bind("<Double-1>", self._on_file_double_click)
        # 鼠标右键菜单事件
        self.file_tree.bind("<Button-3>", self._show_file_context_menu)
        
        # 窗口大小调整事件
        self.root.bind("<Configure>", self._on_window_resize)
        
        # 键盘快捷键
        self.root.bind("<Control-o>", lambda e: self._open_directory())
        self.root.bind("<Control-r>", lambda e: self._refresh_current_directory())
        self.root.bind("<Control-f>", lambda e: self.search_entry.focus_set())
        self.root.bind("<Escape>", lambda e: self.root.focus_set())
    
    def _on_window_resize(self, event):
        """窗口大小调整事件处理
        
        Args:
            event: 事件对象
        """
        # 仅在主窗口大小调整时处理
        if event.widget == self.root:
            # 调整文件树列宽
            tree_width = self.file_tree.winfo_width()
            if tree_width > 100:  # 防止过小时调整
                self.file_tree.column("#0", width=int(tree_width * 0.5))
                self.file_tree.column("size", width=int(tree_width * 0.15))
                self.file_tree.column("type", width=int(tree_width * 0.15))
                self.file_tree.column("status", width=int(tree_width * 0.2))
    
    def _open_directory(self):
        """打开目录对话框"""
        directory = filedialog.askdirectory(
            title="选择音频文件目录",
            initialdir=self.current_directory.get() or os.path.expanduser("~")
        )
        
        if directory:
            self.current_directory.set(directory)
            self._load_files(directory)
            
    def _refresh_current_directory(self):
        """刷新当前目录"""
        directory = self.current_directory.get()
        if directory and os.path.isdir(directory):
            self._load_files(directory)
        else:
            messagebox.showerror("错误", "请先选择一个有效的目录")
    
    def _load_files(self, directory=None):
        """加载文件夹中的文件
        
        Args:
            directory: 要加载的目录，如果为None则使用当前目录
        """
        if directory is None:
            directory = self.current_directory.get()
            
        if not directory or not os.path.isdir(directory):
            messagebox.showerror("错误", "无效的目录路径")
            return
            
        # 更新当前目录
        self.current_directory.set(directory)
        
        # 清空文件树
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
            
        # 设置状态信息
        self.status_message.set("正在加载文件，请稍候...")
        self.root.update_idletasks()
        
        # 定义进度回调函数
        def progress_callback(current, total, file=None):
            message = f"正在加载... {current}/{total}"
            if file:
                message += f" - {os.path.basename(file)}"
            self.status_message.set(message)
            self.root.update_idletasks()
            
        # 定义完成回调函数
        def done_callback(result):
            if result.get('success', False):
                # 刷新文件树
                self._refresh_file_tree()
                # 更新状态
                self.status_message.set(f"已加载 {len(self.file_manager.get_files())} 个文件")
            else:
                # 显示错误信息
                error = result.get('error', '未知错误')
                self.status_message.set(f"加载文件失败: {error}")
                messagebox.showerror("加载错误", f"加载文件失败: {error}")
        
        # 异步加载文件
        self.file_manager.load_directory(
            directory, 
            progress_callback=progress_callback, 
            done_callback=done_callback
        )
    
    def _refresh_file_tree(self):
        """刷新文件树显示"""
        # 保存当前选中的文件
        selected_items = self.file_tree.selection()
        selected_files = [self.file_tree.item(item, "text") for item in selected_items]
        
        # 清空文件树
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
            
        # 获取文件列表
        files = self.file_manager.get_files()
        
        # 根据排序键进行排序
        sorted_files = []
        for file_name, file_info in files.items():
            sorted_files.append((file_name, file_info))
            
        # 根据排序键和排序方向进行排序
        if self.file_manager.sorting_key == 'name':
            sorted_files.sort(key=lambda x: x[0].lower(), reverse=self.file_manager.sorting_reverse)
        elif self.file_manager.sorting_key == 'size':
            sorted_files.sort(key=lambda x: x[1].get('size', 0), reverse=self.file_manager.sorting_reverse)
        elif self.file_manager.sorting_key == 'type':
            sorted_files.sort(key=lambda x: x[1].get('extension', '').lower(), reverse=self.file_manager.sorting_reverse)
        elif self.file_manager.sorting_key == 'status':
            sorted_files.sort(key=lambda x: x[1].get('status', '').lower(), reverse=self.file_manager.sorting_reverse)
            
        # 填充文件树
        for file_name, file_info in sorted_files:
            # 应用搜索过滤器
            search_text = self.search_var.get().lower()
            if search_text and search_text not in file_name.lower():
                continue
                
            # 应用状态过滤器
            status_filter = self.status_filter_var.get()
            if status_filter != "全部" and file_info.get('status') != status_filter:
                continue
                
            # 添加文件到树
            item_id = self.file_tree.insert(
                "", 
                "end", 
                text=file_name, 
                values=(
                    file_info.get('formatted_size', '未知'),
                    file_info.get('extension', '未知'),
                    file_info.get('status', '未处理')
                )
            )
            
            # 恢复选中状态
            if file_name in selected_files:
                self.file_tree.selection_add(item_id)
                
        # 更新状态栏
        self._update_status_bar()
    
    def _on_search_change(self, *args):
        """当搜索文本变化时过滤文件列表"""
        self._apply_filters()
        
    def _on_filter_change(self, event):
        """当过滤条件变化时过滤文件列表"""
        self._apply_filters()
        
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
        self.tools_menu.add_command(label="API密钥管理", command=self._on_api_key_manager)
        self.tools_menu.add_command(label="模型管理", command=self._on_model_manager)
        
        # 添加菜单到菜单栏
        self.menu_bar.add_cascade(label="文件", menu=self.file_menu)
        self.menu_bar.add_cascade(label="编辑", menu=self.edit_menu)
        self.menu_bar.add_cascade(label="工具", menu=self.tools_menu)
        
        # 设置菜单栏
        self.root.config(menu=self.menu_bar)

    def _on_api_key_manager(self):
        """打开API密钥管理对话框"""
        from .dialogs.api_key_manager import APIKeyManagerDialog
        
        # 获取服务管理器
        service_manager = self.service_factory.get_service("service_manager_service")
        if not service_manager:
            messagebox.showerror("错误", "无法获取服务管理器")
            return
            
        dialog = APIKeyManagerDialog(self.root, service_manager)
        self.root.wait_window(dialog)
        
    def _on_model_manager(self):
        """打开模型管理对话框"""
        try:
            from .dialogs.model_manager_dialog import ModelManagerDialog
            
            # 获取服务管理器和配置服务
            service_manager = None
            config_service = None
            
            if hasattr(self, 'service_manager'):
                service_manager = self.service_manager
            
            if hasattr(self, 'config_service'):
                config_service = self.config_service
            
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
            
            # 如果有其他需要刷新的UI组件，在这里添加
            
            logger.info("UI已刷新")
        except Exception as e:
            logger.error(f"刷新UI时发生错误: {e}")
        
    def _on_preferences(self):
        """打开首选项对话框"""
        # 临时实现，后续可以添加实际的首选项对话框
        messagebox.showinfo("首选项", "首选项功能正在开发中...")

    def _categorize_selected_files(self):
        """手动分类选中的文件"""
        # 确保有选中的文件
        selected_files = self.file_manager.get_selected_files()
        if not selected_files:
            messagebox.showinfo("提示", "请先选择要分类的文件")
            return
            
        # 获取所有分类
        categories = self.category_manager.get_categories()
        if not categories:
            messagebox.showinfo("提示", "没有可用的分类数据")
            return
            
        # 打开分类选择对话框
        dialog = CategorySelectionDialog(
            self.root, 
            categories, 
            selected_files,
            self.category_manager.get_use_subcategory_var().get()
        )
        result = dialog.result
        
        # 如果用户选择了分类
        if result and 'category_id' in result:
            try:
                # 获取选择的分类ID
                category_id = result['category_id']
                
                # 移动文件到选定的分类
                moved_files = self.category_manager.move_files_to_category(
                    selected_files, 
                    category_id
                )
                
                # 批量更新文件状态
                file_names = [os.path.basename(file) for file in moved_files]
                self.file_manager.batch_update_status(file_names, "已分类")
                
                # 刷新文件树
                self._refresh_file_tree()
                
                # 显示结果消息
                messagebox.showinfo("分类完成", f"成功分类 {len(moved_files)} 个文件")
                
            except Exception as e:
                messagebox.showerror("错误", f"分类文件失败: {str(e)}")
                logger.error(f"分类文件失败: {e}")
                
    def _auto_categorize_files(self):
        """自动分类选中的文件"""
        # 确保有选中的文件
        selected_files = self.file_manager.get_selected_files()
        if not selected_files:
            messagebox.showinfo("提示", "请先选择要分类的文件")
            return
            
        # 打开自动分类对话框
        dialog = AutoCategorizeDialog(
            self.root,
            selected_files,
            self.file_manager,
            self.category_manager
        )
        
        if dialog.result.get('success', False):
            # 刷新文件树
            self._refresh_file_tree()
            
            # 更新分类树
            self._populate_category_tree()
            
            # 显示成功消息
            messagebox.showinfo("自动分类", f"成功完成 {len(selected_files)} 个文件的自动分类") 