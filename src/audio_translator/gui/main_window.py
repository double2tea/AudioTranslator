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
        
        # 在服务选项卡中添加占位标签
        ttk.Label(
            self.service_tab, 
            text="服务管理功能正在开发中...", 
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
        
        # 创建目录显示框架
        dir_frame = ttk.Frame(file_area_frame, style="Dark.TFrame", padding=(5, 5))
        dir_frame.pack(fill=tk.X, side=tk.TOP, pady=(0, 5))
        
        # 添加目录标签
        ttk.Label(dir_frame, text="当前目录:", style="Dark.TLabel").pack(side=tk.LEFT, padx=(0, 5))
        
        # 添加目录路径显示
        self.current_dir_var = tk.StringVar(value="未选择目录")
        ttk.Label(dir_frame, textvariable=self.current_dir_var, style="Dark.TLabel").pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 创建文件框架
        file_frame = ttk.Frame(file_area_frame, style="Dark.TFrame")
        file_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建文件树形视图
        columns = ("size", "type", "status")
        self.file_tree = ttk.Treeview(file_frame, columns=columns, show="tree headings", selectmode="extended")
        
        # 设置列宽和标题
        self.file_tree.column("#0", width=250, minwidth=200)
        self.file_tree.column("size", width=80, anchor=tk.E)
        self.file_tree.column("type", width=80, anchor=tk.CENTER)
        self.file_tree.column("status", width=80, anchor=tk.CENTER)
        
        # 设置表头
        self.file_tree.heading("#0", text="文件名", command=lambda: self._sort_file_tree("#0"))
        self.file_tree.heading("size", text="大小", command=lambda: self._sort_file_tree("size"))
        self.file_tree.heading("type", text="类型", command=lambda: self._sort_file_tree("type"))
        self.file_tree.heading("status", text="状态", command=lambda: self._sort_file_tree("status"))
        
        # 添加垂直滚动条
        vsb = ttk.Scrollbar(file_frame, orient="vertical", command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=vsb.set)
        
        # 添加水平滚动条
        hsb = ttk.Scrollbar(file_frame, orient="horizontal", command=self.file_tree.xview)
        self.file_tree.configure(xscrollcommand=hsb.set)
        
        # 放置文件树和滚动条
        self.file_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        # 配置网格布局权重
        file_frame.grid_rowconfigure(0, weight=1)
        file_frame.grid_columnconfigure(0, weight=1)
        
        # 绑定双击事件
        self.file_tree.bind("<Double-1>", self._on_file_double_click)
        
        # 绑定选择事件
        self.file_tree.bind("<<TreeviewSelect>>", self._on_file_selected)
        
        # 绑定右键菜单
        self.file_tree.bind("<Button-3>", self._show_file_context_menu)
        
        # 创建右键菜单
        self.file_context_menu = tk.Menu(self.root, tearoff=0, bg=self.COLORS['bg_dark'], fg=self.COLORS['fg'])
        self.file_context_menu.add_command(label="打开文件", command=self._open_selected_file)
        self.file_context_menu.add_command(label="复制文件路径", command=self._copy_file_path)
        self.file_context_menu.add_command(label="删除文件", command=self._delete_selected_files)
        self.file_context_menu.add_separator()
        self.file_context_menu.add_command(label="手动分类", command=self._categorize_selected_files)
        self.file_context_menu.add_command(label="自动分类", command=self._auto_categorize_files)
        
        return file_area_frame
    
    def _on_file_selected(self, event):
        """处理文件选择事件
        
        Args:
            event: 事件对象
        """
        selected_items = self.file_tree.selection()
        selected_files = []
        
        # 获取选中文件的路径
        for item in selected_items:
            if item:
                file_path = self.file_tree.item(item, "tags")[0]
                selected_files.append(file_path)
        
        # 更新文件管理器中的选中文件
        self.file_manager.set_selected_files(selected_files)
        
        # 更新本地选中文件列表
        self.selected_files = selected_files
        
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
                
    def _open_selected_file(self):
        """打开选中的文件（使用系统默认程序）"""
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
                
    def _copy_file_path(self):
        """复制选中文件的路径到剪贴板"""
        selected_items = self.file_tree.selection()
        if not selected_items:
            return
            
        # 获取文件信息
        file_name = self.file_tree.item(selected_items[0], "text")
        file_info = self.file_manager.get_file_info(file_name)
        
        if file_info and 'path' in file_info:
            # 复制路径到剪贴板
            self.root.clipboard_clear()
            self.root.clipboard_append(file_info['path'])
            # 在状态栏显示提示
            self.status_message.set(f"已复制路径: {file_info['path']}")
            
    def _delete_selected_files(self):
        """删除选中的文件"""
        selected_items = self.file_tree.selection()
        if not selected_items:
            return
            
        # 获取选中的所有文件名
        file_names = [self.file_tree.item(item, "text") for item in selected_items]
        
        # 确认是否删除
        if len(file_names) == 1:
            confirm = messagebox.askyesno("确认删除", f"确定要删除文件 '{file_names[0]}' 吗？")
        else:
            confirm = messagebox.askyesno("确认删除", f"确定要删除选中的 {len(file_names)} 个文件吗？")
            
        if confirm:
            try:
                # 删除文件
                for file_name in file_names:
                    file_info = self.file_manager.get_file_info(file_name)
                    if file_info and os.path.exists(file_info.get('path')):
                        os.remove(file_info.get('path'))
                
                # 刷新文件列表
                self._refresh_file_tree()
                self.status_message.set(f"已删除 {len(file_names)} 个文件")
            except Exception as e:
                messagebox.showerror("删除错误", f"删除文件时发生错误: {e}")
        
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
    
    def _create_status_bar(self):
        """创建状态栏"""
        # 创建状态栏框架
        self.status_bar = ttk.Frame(self.root, style="Dark.TFrame")
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        
        # 左侧状态信息
        self.status_left = ttk.Label(
            self.status_bar, 
            text="就绪", 
            style="Dark.TLabel", 
            padding=(5, 2)
        )
        self.status_left.pack(side=tk.LEFT)
        
        # 右侧文件计数
        self.file_count_label = ttk.Label(
            self.status_bar, 
            text="文件数: 0", 
            style="Dark.TLabel", 
            padding=(5, 2)
        )
        self.file_count_label.pack(side=tk.RIGHT)
        
        # 中间进度条（默认隐藏）
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.status_bar, 
            orient=tk.HORIZONTAL, 
            length=200, 
            mode='determinate', 
            variable=self.progress_var
        )
        # 进度条默认隐藏，需要时再显示
    
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
        def done_callback(files):
            try:
                # 文件已经被加载到FileManager中，直接刷新文件树UI
                self._refresh_file_tree()
                
                # 更新状态
                total_files = len(files) if isinstance(files, list) else len(self.file_manager.get_files())
                self.status_message.set(f"已加载 {total_files} 个文件")
                
                # 记录日志
                logger.info(f"已加载目录: {directory}, 共 {total_files} 个文件")
            except Exception as e:
                # 显示错误信息
                logger.error(f"加载文件回调错误: {e}")
                self.status_message.set(f"加载文件失败: {str(e)}")
                messagebox.showerror("加载错误", f"加载文件失败: {str(e)}")
        
        # 异步加载文件
        self.file_manager.load_directory(
            directory, 
            callback=done_callback
        )
    
    def _refresh_file_tree(self):
        """刷新文件树显示"""
        # 保存当前选中的文件
        selected_items = self.file_tree.selection()
        selected_iids = {}
        
        # 保存选中的文件路径作为标识符
        for item in selected_items:
            file_path = self.file_tree.item(item, "tags")[0] if self.file_tree.item(item, "tags") else None
            if file_path:
                selected_iids[file_path] = True
        
        # 清空文件树
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # 获取文件列表 - 格式为: [(name, size_str, file_type, status, file_path), ...]
        files = self.file_manager.get_files()
        
        # 应用排序
        if hasattr(self.file_manager, 'sorting_key') and hasattr(self.file_manager, 'sorting_reverse'):
            reverse = self.file_manager.sorting_reverse
            
            if self.file_manager.sorting_key == 'name':
                sorted_files = sorted(files, key=lambda x: x[0].lower(), reverse=reverse)
            elif self.file_manager.sorting_key == 'size':
                # 尝试将大小字符串转换为字节数进行排序
                def size_to_bytes(size_str):
                    try:
                        if 'KB' in size_str:
                            return float(size_str.replace('KB', '').strip()) * 1024
                        elif 'MB' in size_str:
                            return float(size_str.replace('MB', '').strip()) * 1024 * 1024
                        elif 'GB' in size_str:
                            return float(size_str.replace('GB', '').strip()) * 1024 * 1024 * 1024
                        else:
                            return float(size_str.replace('B', '').strip())
                    except:
                        return 0
                
                sorted_files = sorted(files, key=lambda x: size_to_bytes(x[1]), reverse=reverse)
            elif self.file_manager.sorting_key == 'type':
                sorted_files = sorted(files, key=lambda x: x[2].lower(), reverse=reverse)
            elif self.file_manager.sorting_key == 'status':
                sorted_files = sorted(files, key=lambda x: x[3].lower(), reverse=reverse)
            else:
                sorted_files = files
        else:
            sorted_files = files
        
        # 填充文件树
        for name, size_str, file_type, status, file_path in sorted_files:
            # 应用搜索过滤器
            search_text = self.search_var.get().lower()
            if search_text and search_text not in name.lower():
                continue
            
            # 应用状态过滤器
            status_filter = self.status_filter_var.get()
            if status_filter != "全部" and status != status_filter:
                continue
            
            # 添加文件到树
            item_id = self.file_tree.insert(
                "", 
                "end", 
                text=name, 
                values=(size_str, file_type, status),
                tags=(file_path,)
            )
            
            # 恢复选中状态
            if file_path in selected_iids:
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

    def _create_category_area(self, parent_frame):
        """创建分类区域"""
        # 创建分类区域框架
        category_frame = ttk.LabelFrame(parent_frame, text="分类管理", style="Dark.TLabelframe")
        category_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建内容框架
        content_frame = ttk.Frame(category_frame, style="Dark.TFrame")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建选项框架
        options_frame = ttk.Frame(content_frame, style="Dark.TFrame")
        options_frame.pack(fill=tk.X, side=tk.TOP, pady=(0, 5))
        
        # 添加子分类选项
        self.use_subcategory_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, 
            text="使用子分类", 
            variable=self.use_subcategory_var,
            style="Dark.TCheckbutton"
        ).pack(side=tk.LEFT, padx=5)
        
        # 创建树形视图框架
        tree_frame = ttk.Frame(content_frame, style="Dark.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        
        # 创建分类树形视图
        columns = ("count",)
        self.category_tree = ttk.Treeview(tree_frame, columns=columns, selectmode="browse")
        self.category_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 配置列宽和标题
        self.category_tree.column("#0", width=200, minwidth=150)
        self.category_tree.column("count", width=60, anchor=tk.CENTER)
        
        # 设置表头
        self.category_tree.heading("#0", text="分类名称")
        self.category_tree.heading("count", text="文件数")
        
        # 添加垂直滚动条
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.category_tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.category_tree.configure(yscrollcommand=vsb.set)
        
        # 创建按钮框架
        button_frame = ttk.Frame(content_frame, style="Dark.TFrame")
        button_frame.pack(fill=tk.X, side=tk.TOP, pady=5)
        
        # 添加分类按钮
        ttk.Button(
            button_frame, 
            text="手动分类", 
            command=self._categorize_selected_files,
            style="Dark.TButton"
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="自动分类", 
            command=self._auto_categorize_files,
            style="Dark.TButton"
        ).pack(side=tk.LEFT, padx=5)
        
        # 创建统计框架
        stats_frame = ttk.Frame(content_frame, style="Dark.TFrame")
        stats_frame.pack(fill=tk.X, side=tk.TOP, pady=5)
        
        # 添加分类统计信息
        self.category_stats_label = ttk.Label(
            stats_frame, 
            text="共0个分类", 
            style="Dark.TLabel"
        )
        self.category_stats_label.pack(side=tk.LEFT, padx=5)
        
        # 绑定分类树选择事件
        self.category_tree.bind("<<TreeviewSelect>>", self._on_category_selected)
        
        return category_frame

    def _on_tab_changed(self, event):
        """当选项卡切换时处理"""
        # 在这里可以添加选项卡切换后的处理逻辑
        logger.info("选项卡切换")

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