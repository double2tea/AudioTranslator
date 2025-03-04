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
        # 创建样式对象
        self.style = ttk.Style()
        
        # 设置主题
        if platform.system() == "Windows":
            self.style.theme_use("vista")
        elif platform.system() == "Darwin":
            self.style.theme_use("aqua")
        else:
            self.style.theme_use("clam")
        
        # 配置样式
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", background="#f0f0f0", font=("Arial", 10))
        self.style.configure("TButton", font=("Arial", 10))
        self.style.configure("Treeview", font=("Arial", 10), rowheight=25)
        self.style.configure("Treeview.Heading", font=("Arial", 10, "bold"))
        
        # 配置特殊样式
        self.style.configure("Title.TLabel", font=("", 12, "bold"))
        self.style.configure("Status.TLabel", padding=2)
        
        # 配置进度条样式
        self.style.configure("TProgressbar", thickness=8)
        
        # 分类列表样式
        self.style.configure("Category.TFrame", background="#e8e8e8")
        self.style.configure("Category.TLabel", background="#e8e8e8")
        
        # 工具栏样式
        self.style.configure("Toolbar.TFrame", background="#e0e0e0")
    
    def _create_ui(self):
        """创建用户界面"""
        # 创建主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 配置主框架网格
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=0)  # 工具栏
        self.main_frame.rowconfigure(1, weight=1)  # 标签页区域
        self.main_frame.rowconfigure(2, weight=0)  # 状态栏
        
        # 创建工具栏
        self._create_toolbar()
        
        # 创建标签页
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.grid(row=1, column=0, sticky="nsew")
        
        # 创建文件管理标签页
        self.file_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.file_tab, text="文件管理")
        
        # 配置文件标签页
        self.file_tab.columnconfigure(0, weight=1)
        self.file_tab.rowconfigure(0, weight=1)  # 文件区域
        self.file_tab.rowconfigure(1, weight=0)  # 分类区域
        
        # 创建文件相关组件
        self._create_file_area()
        self._create_category_area()
        
        # 创建服务管理标签页
        self.service_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.service_tab, text="服务管理")
        
        # 配置服务标签页
        self.service_tab.columnconfigure(0, weight=1)
        self.service_tab.rowconfigure(0, weight=1)
        
        # 获取服务管理器实例
        service_manager = self.service_factory.get_service("service_manager_service")
        if not service_manager:
            logger.error("无法获取服务管理器，服务管理面板可能无法正常工作")
            messagebox.showerror("初始化错误", "无法获取服务管理器，服务管理面板可能无法正常工作")
        
        # 创建服务管理面板
        self.service_panel = ServiceManagerPanel(self.service_tab, service_manager)
        self.service_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # 创建状态栏
        self._create_status_bar()
    
    def _create_toolbar(self):
        """创建工具栏"""
        # 创建工具栏框架
        toolbar = ttk.Frame(self.main_frame, style="Toolbar.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # 添加按钮
        ttk.Button(toolbar, text="打开文件夹", command=self._open_directory).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="刷新", command=self._refresh_files).pack(side=tk.LEFT, padx=5)
        
        # 添加当前目录显示
        ttk.Label(toolbar, text="当前目录:").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Label(toolbar, textvariable=self.current_directory, width=50, 
                 background="white", relief="sunken", anchor="w").pack(side=tk.LEFT, padx=5)
    
    def _create_file_area(self):
        """创建文件区域"""
        # 创建文件区域框架
        file_frame = ttk.LabelFrame(self.file_tab, text="文件列表")
        file_frame.grid(row=0, column=0, sticky="nsew", pady=(5, 10))
        
        # 配置文件区域网格
        file_frame.columnconfigure(0, weight=1)
        file_frame.rowconfigure(0, weight=1)
        
        # 创建文件树状视图
        self._create_file_tree(file_frame)
    
    def _create_file_tree(self, parent):
        """创建文件树状视图"""
        # 创建框架
        tree_frame = ttk.Frame(parent)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # 配置框架网格
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # 创建滚动条
        scrollbar_y = ttk.Scrollbar(tree_frame, orient="vertical")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        
        scrollbar_x = ttk.Scrollbar(tree_frame, orient="horizontal")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        # 创建树状视图
        self.file_tree = ttk.Treeview(
            tree_frame,
            columns=("name", "size", "type", "status"),
            show="headings",
            selectmode="extended",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )
        self.file_tree.grid(row=0, column=0, sticky="nsew")
        
        # 配置滚动条
        scrollbar_y.config(command=self.file_tree.yview)
        scrollbar_x.config(command=self.file_tree.xview)
        
        # 配置列
        self.file_tree.heading("name", text="文件名")
        self.file_tree.heading("size", text="大小")
        self.file_tree.heading("type", text="类型")
        self.file_tree.heading("status", text="状态")
        
        self.file_tree.column("name", width=400, anchor="w")
        self.file_tree.column("size", width=100, anchor="e")
        self.file_tree.column("type", width=100, anchor="w")
        self.file_tree.column("status", width=150, anchor="w")
        
        # 绑定事件
        self.file_tree.bind("<Double-1>", self._on_file_double_click)
        self.file_tree.bind("<Return>", self._on_file_double_click)
        
        # 添加按钮区域
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        
        # 添加按钮
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
        
        # 添加分类选项
        options_frame = ttk.Frame(button_frame)
        options_frame.pack(side=tk.RIGHT, padx=(10, 0))
        
        ttk.Label(options_frame, text="使用子分类:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Checkbutton(
            options_frame,
            text="",
            variable=self.category_manager.get_use_subcategory_var()
        ).pack(side=tk.RIGHT)
    
    def _create_category_area(self):
        """创建分类区域"""
        # 创建分类区域框架
        category_frame = ttk.LabelFrame(self.file_tab, text="分类操作")
        category_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        # 配置分类区域网格
        category_frame.columnconfigure(0, weight=1)
        category_frame.columnconfigure(1, weight=1)
        category_frame.rowconfigure(0, weight=0)
        
        # 创建分类按钮区域
        button_frame = ttk.Frame(category_frame)
        button_frame.grid(row=0, column=0, sticky="w", padx=10, pady=10)
        
        # 添加分类按钮
        ttk.Button(button_frame, text="手动分类", 
                  command=self._categorize_selected_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="自动分类", 
                  command=self._auto_categorize_files).pack(side=tk.LEFT, padx=5)
        
        # 创建子分类选项
        option_frame = ttk.Frame(category_frame)
        option_frame.grid(row=0, column=1, sticky="e", padx=10, pady=10)
        
        # 添加子分类复选框
        ttk.Checkbutton(option_frame, text="使用子分类", 
                       variable=self.category_manager.get_use_subcategory_var()).pack(side=tk.RIGHT)
    
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
        self.file_tree.bind("<<TreeviewSelect>>", self._on_file_select)
        # 文件双击事件
        self.file_tree.bind("<Double-1>", self._on_file_double_click)
    
    def _open_directory(self):
        """打开目录对话框"""
        directory = filedialog.askdirectory(
            title="选择文件夹",
            initialdir=self.current_directory.get()
        )
        
        if directory:
            self.current_directory.set(directory)
            self._load_files(directory)
    
    def _load_files(self, directory: str):
        """
        加载目录中的文件
        
        Args:
            directory: 目录路径
        """
        # 清空文件树
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        try:
            # 使用文件管理器加载文件
            files = self.file_manager.load_directory(directory)
            
            # 添加到树状视图
            for i, (name, size, file_type, status, file_path) in enumerate(files):
                item_id = self.file_tree.insert(
                    "", "end",
                    values=(name, size, file_type, status),
                    tags=(file_path, "unchecked")
                )
            
            # 更新状态
            self.status_message.set(f"已加载 {len(files)} 个文件")
            logger.info(f"已加载目录: {directory}, 共 {len(files)} 个文件")
            
        except Exception as e:
            messagebox.showerror("错误", f"加载文件失败: {str(e)}")
            logger.error(f"加载文件失败: {e}")
    
    def _refresh_files(self):
        """刷新文件列表"""
        directory = self.current_directory.get()
        if os.path.isdir(directory):
            self._load_files(directory)
    
    def _on_file_select(self, event):
        """
        处理文件选择事件
        
        Args:
            event: 事件对象
        """
        # 获取选中的项目
        selected_items = self.file_tree.selection()
        selected_files = [self.file_tree.item(item, "tags")[0] for item in selected_items]
        
        # 更新文件管理器中的选中文件
        self.file_manager.set_selected_files(selected_files)
        
        # 更新本地选中文件列表（为了兼容性）
        self.selected_files = selected_files
        
        # 更新状态
        self.status_message.set(f"已选择 {len(selected_files)} 个文件")
    
    def _on_file_double_click(self, event):
        """
        处理文件双击事件
        
        Args:
            event: 事件对象
        """
        # 获取选中的项目
        selected_item = self.file_tree.focus()
        if not selected_item:
            return
        
        # 获取文件路径
        file_path = self.file_tree.item(selected_item, "tags")[0]
        
        # 播放音频文件 (暂未实现)
        logger.info(f"双击文件: {file_path}")
        messagebox.showinfo("文件操作", f"已选择文件: {file_path}\n\n功能尚未实现")
    
    def _categorize_selected_files(self):
        """手动分类选中的文件"""
        # 确保有选中的文件
        selected_files = self.file_manager.get_selected_files()
        if not selected_files:
            messagebox.showinfo("提示", "请先选择要分类的文件")
            return
        
        # 获取所有分类
        categories = self.category_manager.get_all_categories()
        if not categories:
            messagebox.showinfo("提示", "没有可用的分类数据")
            return
        
        # 打开分类选择对话框
        dialog = CategorySelectionDialog(self.root, categories, selected_files)
        category = dialog.get_category()
        
        # 如果用户选择了分类
        if category:
            try:
                # 获取当前目录
                current_dir = self.current_directory.get()
                
                # 移动文件到选定的分类
                moved_files = self.category_manager.move_files_to_category(
                    selected_files, 
                    current_dir
                )
                
                # 更新文件状态
                for file_path in moved_files:
                    self.file_manager.update_file_status(file_path, "已分类")
                
                # 刷新文件列表
                self._refresh_files()
                
                # 显示结果消息
                messagebox.showinfo("分类完成", f"成功移动 {len(moved_files)} 个文件")
                
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
            category_manager=self.category_manager,
            target_dir=self.current_directory.get()
        )
        
        # 对话框关闭后刷新文件列表
        if dialog.is_completed:
            self._refresh_files()
    
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
        self.file_menu.add_command(label="刷新", command=self._refresh_files)
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