import os
import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from pathlib import Path
import threading
import queue
import time
import datetime
from translator import Translator
from config import Config
from service_manager import ServiceManagerWindow
from dictionary_manager import DictionaryManagerWindow
import requests
import csv
from category_manager import CategoryManager
from theme_manager import ThemeManager
import sys

class AudioTranslatorGUI:
    # 深色主题配色
    COLORS = {
        'bg_dark': '#1E1E1E',      # 主背景色
        'bg_light': '#2D2D2D',     # 次要背景
        'fg': '#FFFFFF',           # 主文本色
        'fg_dim': '#AAAAAA',       # 次要文本
        'accent': '#007ACC',       # 强调色
        'border': '#3D3D3D',       # 边框色
        'hover': '#3D3D3D',        # 悬停色
        'selected': '#094771'      # 选中色
    }

    def __init__(self):
        """初始化 GUI 应用"""
        # 创建主窗口
        self.window = tk.Tk()
        self.window.withdraw()  # 先隐藏窗口
        
        # 设置 macOS 窗口样式
        if sys.platform == 'darwin':
            try:
                # 设置窗口按钮命令
                self.window.bind('<Command-w>', lambda e: self.on_closing())
                self.window.bind('<Command-q>', lambda e: self.on_closing())
                self.window.bind('<Command-m>', lambda e: self.window.iconify())
                
                # 设置窗口菜单命令
                self.window.createcommand('::tk::mac::Quit', self.on_closing)
                self.window.createcommand('::tk::mac::ReopenApplication', lambda: self.window.deiconify())
                
                # 移除窗口样式设置，使用系统默认样式
                
                # 绑定关闭事件
                self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
                self.window.bind('<Escape>', lambda e: self.on_closing())
            except Exception as e:
                logging.warning(f"设置 macOS 窗口样式失败: {e}")
        
        def toggle_zoom(self):
            """切换窗口最大化状态"""
            state = self.window.wm_state()
            if state == 'zoomed':
                self.window.wm_state('normal')
            else:
                self.window.wm_state('zoomed')
        
        # 初始化配置
        self.config = Config()
        
        # 设置窗口属性
        self.window.title("音效文件名翻译工具")
        self.window.geometry("1280x800")
        self.window.minsize(800, 600)
        
        # 更新窗口
        self.window.update_idletasks()
        
        # 设置主题
        ThemeManager.setup_window_theme(self.window, self.config.get("UI_THEME", "dark"))
        
        # 显示窗口
        self.window.deiconify()
        
        # 设置可用主题
        self.available_themes = ["light", "dark"]  # 只保留亮色和暗色主题
        saved_theme = self.config.get("UI_THEME", "dark")
        if saved_theme not in self.available_themes:
            saved_theme = "dark"
        
        # 初始化主题变量
        self.theme_var = tk.StringVar(value=saved_theme)
        
        # 初始化分类管理器
        self.category_manager = CategoryManager(self.window)
        
        # 添加自动分类选项变量
        self.auto_categorize = tk.BooleanVar(value=False)
        # 添加子分类选项变量
        self.use_subcategory = tk.BooleanVar(value=False)
        
        # 添加批量翻译选项变量
        self.batch_translate = tk.BooleanVar(value=True)
        self.batch_size = tk.StringVar(value="10")
        
        # 初始化配置和状态
        self.translator = Translator(self.config)
        self.translation_queue = queue.Queue()
        self.is_translating = False
        self.pause_event = threading.Event()
        self.pause_event.set()  # 初始状态为未暂停
        
        # 初始化计数器
        self.current_file = 0
        self.total_files = 0
        
        # 初始化缓存
        self.translation_cache = {}
        
        # 初始化进度变量
        self.total_progress_var = tk.DoubleVar(self.window)
        self.file_progress_var = tk.DoubleVar(self.window)
        
        # 初始化统计标签字典
        self.stats_labels = {}
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.window, padding=15)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        
        # 配置主窗口的网格权重
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(0, weight=1)
        
        # 设置界面
        self.setup_ui()
        self.load_services()
        
        # 绑定关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 创建右键菜单
        self.create_context_menu()

    def setup_window(self):
        """设置窗口大小和位置"""
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        width = int(screen_width * 0.8)
        height = int(screen_height * 0.8)
        
        # 设置最小窗口大小
        self.window.minsize(1200, 800)
        
        # 配置主窗口的网格权重
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(0, weight=1)
        
        # 设置窗口位置为屏幕中央
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        
        # 允许调整窗口大小
        self.window.resizable(True, True)

    def setup_theme(self):
        """配置深色主题"""
        style = ttk.Style()
        
        # 配置全局样式
        style.configure('.',
            background=self.COLORS['bg_dark'],
            foreground=self.COLORS['fg'],
            fieldbackground=self.COLORS['bg_dark'],
            borderwidth=1,
            relief='flat'
        )
        
        # 配置 Treeview 样式
        style.configure('Treeview',
            background=self.COLORS['bg_dark'],
            foreground=self.COLORS['fg'],
            fieldbackground=self.COLORS['bg_dark'],
            borderwidth=1,
            relief='solid'
        )
        
        # 配置 Treeview 表头
        style.configure('Treeview.Heading',
            background=self.COLORS['bg_light'],
            foreground=self.COLORS['fg'],
            relief='flat',
            borderwidth=1
        )
        
        # 配置选中和悬停状态
        style.map('Treeview',
            background=[('selected', self.COLORS['selected'])],
            foreground=[('selected', self.COLORS['fg'])]
        )
        style.map('Treeview.Heading',
            background=[('active', self.COLORS['hover'])],
            relief=[('pressed', 'sunken')]
        )
        
        # 配置按钮样式
        style.configure('TButton',
            background=self.COLORS['bg_light'],
            foreground=self.COLORS['fg'],
            borderwidth=1,
            relief='solid',
            padding=6
        )
        style.map('TButton',
            background=[('active', self.COLORS['hover']), 
                       ('pressed', self.COLORS['accent'])],
            foreground=[('pressed', self.COLORS['fg'])]
        )
        
        # 配置标签样式
        style.configure('TLabel',
            background=self.COLORS['bg_dark'],
            foreground=self.COLORS['fg'],
            padding=3
        )
        
        # 配置框架样式
        style.configure('TFrame',
            background=self.COLORS['bg_dark'],
            borderwidth=0
        )
        
        # 配置分组框样式
        style.configure('TLabelframe',
            background=self.COLORS['bg_dark'],
            foreground=self.COLORS['fg'],
            borderwidth=1,
            relief='solid'
        )
        style.configure('TLabelframe.Label',
            background=self.COLORS['bg_dark'],
            foreground=self.COLORS['fg'],
            padding=(6, 3)
        )
        
        # 配置进度条样式
        style.configure('Horizontal.TProgressbar',
            background=self.COLORS['accent'],
            troughcolor=self.COLORS['bg_light'],
            borderwidth=0,
            relief='flat'
        )
        
        # 配置下拉框样式
        style.configure('TCombobox',
            background=self.COLORS['bg_light'],
            foreground=self.COLORS['fg'],
            fieldbackground=self.COLORS['bg_light'],
            selectbackground=self.COLORS['selected'],
            selectforeground=self.COLORS['fg'],
            arrowcolor=self.COLORS['fg']
        )
        style.map('TCombobox',
            fieldbackground=[('readonly', self.COLORS['bg_light'])],
            selectbackground=[('readonly', self.COLORS['selected'])],
            selectforeground=[('readonly', self.COLORS['fg'])]
        )
        
        # 配置状态栏样式
        style.configure('StatusBar.TFrame',
            background=self.COLORS['bg_light'],
            relief='solid',
            borderwidth=1
        )
        style.configure('StatusBar.TLabel',
            background=self.COLORS['bg_light'],
            foreground=self.COLORS['fg_dim'],
            padding=6
        )
        
        # 设置全局选项
        self.window.option_add('*TCombobox*Listbox.background', self.COLORS['bg_light'])
        self.window.option_add('*TCombobox*Listbox.foreground', self.COLORS['fg'])
        self.window.option_add('*TCombobox*Listbox.selectBackground', self.COLORS['selected'])
        self.window.option_add('*TCombobox*Listbox.selectForeground', self.COLORS['fg'])
        
        # 设置 macOS 深色模式
        try:
            self.window.tk.call('tk::unsupported::MacWindowStyle', 'appearance', self.window, 'dark')
            self.window.tk.call('tk::unsupported::MacWindowStyle', 'style', self.window, 'plain')
        except Exception as e:
            logging.warning(f"设置 macOS 深色模式失败: {e}")
            
        # 强制设置窗口背景色
        self.window.configure(bg=self.COLORS['bg_dark'])
        
        # 设置全局颜色选项
        self.window.option_add('*Background', self.COLORS['bg_dark'])
        self.window.option_add('*Foreground', self.COLORS['fg'])
        self.window.option_add('*selectBackground', self.COLORS['selected'])
        self.window.option_add('*selectForeground', self.COLORS['fg'])
        self.window.option_add('*Entry.background', self.COLORS['bg_light'])
        self.window.option_add('*Entry.foreground', self.COLORS['fg'])
        self.window.option_add('*Text.background', self.COLORS['bg_light'])
        self.window.option_add('*Text.foreground', self.COLORS['fg'])
        self.window.option_add('*Listbox.background', self.COLORS['bg_light'])
        self.window.option_add('*Listbox.foreground', self.COLORS['fg'])
        self.window.option_add('*Menu.background', self.COLORS['bg_dark'])
        self.window.option_add('*Menu.foreground', self.COLORS['fg'])
        self.window.option_add('*Menu.selectColor', self.COLORS['selected'])
        self.window.option_add('*Menu.activeBackground', self.COLORS['hover'])
        self.window.option_add('*Menu.activeForeground', self.COLORS['fg'])

    def setup_ui(self):
        """创建界面组件"""
        # 配置主框架的网格权重
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)  # 文件列表区域可扩展
        
        # 创建菜单栏
        self.create_menu()
        
        # 创建工具栏
        toolbar = self.create_toolbar(self.main_frame)
        toolbar.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # 创建文件列表区域
        list_frame = ttk.LabelFrame(self.main_frame, text="文件列表", padding=10)
        list_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=(5,0))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        self.create_file_list(list_frame)
        
        # 创建进度信息区域
        info_frame = ttk.LabelFrame(self.main_frame, text="翻译进度", padding=10)
        info_frame.grid(row=3, column=0, sticky="nsew", padx=5, pady=(5,0))
        info_frame.grid_columnconfigure(0, weight=1)
        self.create_progress_info(info_frame)
        
        # 创建底部工具栏
        bottom_toolbar = self.create_bottom_toolbar(self.main_frame)
        bottom_toolbar.grid(row=4, column=0, sticky="nsew", padx=5, pady=5)
        
        # 创建状态栏
        self.create_status_bar(self.main_frame)

    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.window)
        self.window.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="打开文件", command=self.select_files)
        file_menu.add_command(label="打开文件夹", command=self.select_folder)
        file_menu.add_separator()
        file_menu.add_command(label="开始/暂停翻译", command=self.toggle_translation)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.on_closing)
        
        # 设置菜单
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="设置", menu=settings_menu)
        settings_menu.add_command(label="翻译服务配置", command=self.show_service_manager)
        settings_menu.add_command(label="词库管理", command=self.show_dictionary_manager)
        
        # 主题菜单
        theme_menu = tk.Menu(settings_menu, tearoff=0)
        settings_menu.add_cascade(label="界面主题", menu=theme_menu)
        
        # 添加主题选项
        for theme in self.available_themes:
            theme_menu.add_radiobutton(
                label=theme.capitalize(),
                variable=self.theme_var,
                value=theme,
                command=lambda t=theme: self.change_theme(t)
            )

    def create_toolbar(self, parent):
        """创建工具栏"""
        # 创建主工具栏框架
        toolbar = ttk.Frame(parent)
        
        # 配置列权重，使工具栏能够自适应宽度
        for i in range(3):  # 减少为3列，移除翻译控制区
            toolbar.grid_columnconfigure(i, weight=1)
        
        # 1. 文件操作区
        file_frame = ttk.Labelframe(toolbar, text="文件操作")
        file_frame.grid(row=0, column=0, padx=2, sticky="nsew")
        file_frame.grid_columnconfigure(0, weight=1)
        
        file_buttons = ttk.Frame(file_frame)
        file_buttons.grid(row=0, column=0, sticky="w")
        
        ttk.Button(
            file_buttons,
            text="添加文件",
            command=self.select_files,
            width=10
        ).grid(row=0, column=0, padx=2)
        
        ttk.Button(
            file_buttons,
            text="添加文件夹",
            command=self.select_folder,
            width=10
        ).grid(row=0, column=1, padx=2)
        
        ttk.Button(
            file_buttons,
            text="清空列表",
            command=self.clear_list,
            width=10
        ).grid(row=0, column=2, padx=2)

        # 2. 选择工具区
        select_frame = ttk.Labelframe(toolbar, text="选择工具")
        select_frame.grid(row=0, column=1, padx=2, sticky="nsew")
        select_frame.grid_columnconfigure(0, weight=1)
        
        select_buttons = ttk.Frame(select_frame)
        select_buttons.grid(row=0, column=0, sticky="w")
        
        ttk.Button(
            select_buttons,
            text="全选",
            command=self.select_all,
            width=8
        ).grid(row=0, column=0, padx=2)
        
        ttk.Button(
            select_buttons,
            text="取消全选",
            command=self.deselect_all,
            width=8
        ).grid(row=0, column=1, padx=2)
        
        ttk.Button(
            select_buttons,
            text="反选",
            command=self.invert_selection,
            width=8
        ).grid(row=0, column=2, padx=2)

        # 3. 编辑工具区
        edit_frame = ttk.Labelframe(toolbar, text="编辑工具")
        edit_frame.grid(row=0, column=2, padx=2, sticky="nsew")
        edit_frame.grid_columnconfigure(0, weight=1)
        
        # 批量编辑工具
        batch_frame = ttk.Frame(edit_frame)
        batch_frame.grid(row=0, column=0, sticky="w")
        
        ttk.Label(batch_frame, text="前缀:").grid(row=0, column=0)
        self.prefix_entry = ttk.Entry(batch_frame, width=6)
        self.prefix_entry.grid(row=0, column=1, padx=1)
        
        ttk.Label(batch_frame, text="后缀:").grid(row=0, column=2)
        self.suffix_entry = ttk.Entry(batch_frame, width=6)
        self.suffix_entry.grid(row=0, column=3, padx=1)
        
        ttk.Button(
            batch_frame,
            text="应用",
            command=lambda: self.batch_edit('add'),
            width=6
        ).grid(row=0, column=4, padx=1)
        
        # 替换工具
        replace_frame = ttk.Frame(edit_frame)
        replace_frame.grid(row=1, column=0, sticky="w", pady=2)
        
        ttk.Label(replace_frame, text="查找:").grid(row=0, column=0)
        self.find_entry = ttk.Entry(replace_frame, width=6)
        self.find_entry.grid(row=0, column=1, padx=1)
        
        ttk.Label(replace_frame, text="替换:").grid(row=0, column=2)
        self.replace_entry = ttk.Entry(replace_frame, width=6)
        self.replace_entry.grid(row=0, column=3, padx=1)
        
        ttk.Button(
            replace_frame,
            text="替换",
            command=lambda: self.batch_edit('replace'),
            width=6
        ).grid(row=0, column=4, padx=1)

        return toolbar

    def create_bottom_toolbar(self, parent):
        """创建底部工具栏"""
        bottom_toolbar = ttk.Frame(parent)
        
        # 配置列权重
        for i in range(3):
            bottom_toolbar.grid_columnconfigure(i, weight=1)
            
        # 1. 翻译操作区
        translate_frame = ttk.Labelframe(bottom_toolbar, text="翻译操作")
        translate_frame.grid(row=0, column=0, padx=2, sticky="nsew")
        translate_frame.grid_columnconfigure(0, weight=1)
        
        # 翻译服务和模型选择
        service_frame = ttk.Frame(translate_frame)
        service_frame.grid(row=0, column=0, sticky="w")
        
        # 第一行：服务和模型选择
        ttk.Label(service_frame, text="服务:").grid(row=0, column=0)
        self.service_combo = ttk.Combobox(
            service_frame,
            width=15,
            state="readonly"
        )
        self.service_combo.grid(row=0, column=1, padx=2)
        
        ttk.Label(service_frame, text="模型:").grid(row=0, column=2)
        self.model_combo = ttk.Combobox(
            service_frame,
            width=15,
            state="readonly"
        )
        self.model_combo.grid(row=0, column=3, padx=2)
        
        # 第二行：翻译选项
        options_frame = ttk.Frame(service_frame)
        options_frame.grid(row=1, column=0, columnspan=4, sticky="w", pady=(5,0))
        
        # 翻译选项
        ttk.Checkbutton(
            options_frame,
            text="翻译后自动分类",
            variable=self.auto_categorize
        ).grid(row=0, column=0, padx=5)
        
        # 添加批量翻译选项
        batch_frame = ttk.Frame(options_frame)
        batch_frame.grid(row=0, column=1, padx=5)
        
        ttk.Checkbutton(
            batch_frame,
            text="批量翻译",
            variable=self.batch_translate
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            batch_frame,
            text="批次大小:"
        ).pack(side=tk.LEFT, padx=(5, 0))
        
        # 批次大小选择框
        batch_size_combo = ttk.Combobox(
            batch_frame,
            textvariable=self.batch_size,
            values=["5", "10", "20", "50"],
            width=5,
            state="readonly"
        )
        batch_size_combo.pack(side=tk.LEFT, padx=2)
        
        # 第三行：操作按钮
        btn_frame = ttk.Frame(service_frame)
        btn_frame.grid(row=2, column=0, columnspan=4, sticky="w", pady=(5,0))
        
        ttk.Button(
            btn_frame,
            text="预览翻译",
            command=self.preview_translation,
            width=10
        ).grid(row=0, column=0, padx=5)
        
        self.control_btn = ttk.Button(
            btn_frame,
            text="开始翻译",
            command=self.toggle_translation,
            width=10,
            state='disabled'  # 初始状态为禁用
        )
        self.control_btn.grid(row=0, column=1, padx=5)
        
        # 添加确认重命名按钮
        self.rename_btn = ttk.Button(
            btn_frame,
            text="确认重命名",
            command=self.apply_rename,
            width=10,
            state='disabled'  # 初始状态为禁用
        )
        self.rename_btn.grid(row=0, column=2, padx=5)

        # 2. 分类管理区
        category_frame = ttk.Labelframe(bottom_toolbar, text="分类管理")
        category_frame.grid(row=0, column=1, padx=2, sticky="nsew")
        category_frame.grid_columnconfigure(0, weight=1)
        
        category_buttons = ttk.Frame(category_frame)
        category_buttons.grid(row=0, column=0, sticky="w")
        
        ttk.Button(
            category_buttons,
            text="手动分类",
            command=self.categorize_selected_files,
            width=8
        ).grid(row=0, column=0, padx=2)
        
        ttk.Button(
            category_buttons,
            text="自动分类",
            command=self.auto_categorize_files,
            width=8
        ).grid(row=0, column=1, padx=2)
        
        # 子分类选项
        ttk.Checkbutton(
            category_buttons,
            text="使用子分类",
            variable=self.use_subcategory
        ).grid(row=0, column=2, padx=2)

        # 3. 管理工具区
        manage_frame = ttk.Labelframe(bottom_toolbar, text="管理工具")
        manage_frame.grid(row=0, column=2, padx=2, sticky="nsew")
        manage_frame.grid_columnconfigure(0, weight=1)
        
        manage_buttons = ttk.Frame(manage_frame)
        manage_buttons.grid(row=0, column=0, sticky="w")
        
        ttk.Button(
            manage_buttons,
            text="服务管理",
            command=self.show_service_manager,
            width=8
        ).grid(row=0, column=0, padx=2)
        
        ttk.Button(
            manage_buttons,
            text="词库管理",
            command=self.show_dictionary_manager,
            width=8
        ).grid(row=0, column=1, padx=2)

        return bottom_toolbar

    def load_services(self):
        """加载翻译服务列表"""
        try:
            # 获取所有服务
            services = self.config.get("TRANSLATION_SERVICES", {})
            
            # 更新服务下拉框
            service_options = [
                f"{service['name']} ({service_id})"
                for service_id, service in services.items()
                if service.get('enabled', True)  # 只显示启用的服务
            ]
            
            if hasattr(self, 'service_combo'):
                self.service_combo['values'] = service_options
                
                # 选中当前使用的服务
                current_service = self.config.get("TRANSLATION_SERVICE")
                if current_service:
                    for option in service_options:
                        if current_service in option:
                            self.service_combo.set(option)
                            break
                
                # 加载对应的模型列表
                self.load_service_models()
            
            # 绑定服务选择事件
            self.service_combo.bind('<<ComboboxSelected>>', self.on_service_change)
            
        except Exception as e:
            logging.error(f"加载服务列表失败: {str(e)}")
            messagebox.showerror("错误", f"加载服务列表失败: {str(e)}")

    def load_service_models(self):
        """加载当前选中服务的模型列表"""
        try:
            service_text = self.service_combo.get()
            if not service_text:
                return
            
            # 从选项中提取服务ID
            service_id = service_text.split('(')[-1].rstrip(')')
            services = self.config.get("TRANSLATION_SERVICES", {})
            
            if service_id in services:
                service = services[service_id]
                models = service.get("models", [])
                
                # 更新模型下拉框
                model_options = [
                    f"{model['description']} ({model['name']})"
                    for model in models
                ]
                self.model_combo['values'] = model_options
                
                # 选中当前模型
                current_model = service.get("current_model")
                if current_model:
                    for model in models:
                        if model["name"] == current_model:
                            self.model_combo.set(f"{model['description']} ({model['name']})")
                            break
                        
        except Exception as e:
            logging.error(f"加载模型列表失败: {str(e)}")

    def on_service_change(self, event=None):
        """处理服务选择变更"""
        try:
            # 加载新服务的模型
            self.load_service_models()
            
            # 更新配置
            service_text = self.service_combo.get()
            if service_text:
                service_id = service_text.split('(')[-1].rstrip(')')
                self.config.set("TRANSLATION_SERVICE", service_id)
                self.config.save()
            
        except Exception as e:
            logging.error(f"切换服务失败: {str(e)}")
            messagebox.showerror("错误", f"切换服务失败: {str(e)}")

    def get_current_service_and_model(self):
        """获取当前选中的服务和模型"""
        service_text = self.service_combo.get()
        model_text = self.model_combo.get()
        
        if not service_text or not model_text:
            return None, None
        
        service_id = service_text.split('(')[-1].rstrip(')')
        model_name = model_text.split('(')[-1].rstrip(')')
        
        return service_id, model_name

    def create_file_list(self, parent):
        """创建文件列表"""
        try:
            # 创建列表容器
            list_container = ttk.Frame(parent)
            list_container.pack(fill=tk.BOTH, expand=True)
            
            # 配置列表容器的网格权重
            list_container.grid_columnconfigure(0, weight=1)
            list_container.grid_rowconfigure(0, weight=1)
            
            # 创建树形列表
            columns = ("选择", "原文件名", "翻译后文件名", "状态")
            self.tree = ttk.Treeview(
                list_container,
                columns=columns,
                show="headings",
                selectmode="extended"
            )
            
            # 配置列
            column_widths = {
                "选择": 60,
                "原文件名": 400,
                "翻译后文件名": 400,
                "状态": 100
            }
            
            for col in columns:
                self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c))
                self.tree.column(col, width=column_widths[col], minwidth=column_widths[col]//2, stretch=True)
            
            # 添加滚动条
            yscroll = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.tree.yview)
            xscroll = ttk.Scrollbar(list_container, orient=tk.HORIZONTAL, command=self.tree.xview)
            self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
            
            # 使用网格布局
            self.tree.grid(row=0, column=0, sticky="nsew")
            yscroll.grid(row=0, column=1, sticky="ns")
            xscroll.grid(row=1, column=0, sticky="ew")
            
            # 绑定事件
            self.tree.bind('<Double-1>', self.edit_filename)
            self.tree.bind('<Button-1>', self.on_click)
            self.tree.bind('<<TreeviewSelect>>', self.update_file_count)
            self.tree.bind('<space>', self.toggle_selection)
            self.tree.bind('<Control-a>', self.select_all)
            self.tree.bind('<Delete>', self.remove_selected)
            self.tree.bind('<Button-3>', self.show_context_menu)
            
            return list_container
            
        except Exception as e:
            logging.error(f"创建文件列表时出错: {str(e)}")
            raise

    def edit_filename(self, event):
        """编辑文件名"""
        try:
            # 获取选中的项目
            if event:
                item = self.tree.identify_row(event.y)
            else:
                selected = self.tree.selection()
                if not selected:
                    return
                item = selected[0]
            
            if not item:
                return
                
            # 获取当前文件名
            current_name = self.tree.set(item, "翻译后文件名")
            
            # 创建编辑对话框
            dialog = tk.Toplevel(self.window)
            dialog.title("编辑文件名")
            dialog.geometry("500x120")
            dialog.transient(self.window)
            dialog.grab_set()
            
            # 设置深色主题
            dialog.configure(bg=self.COLORS['bg_dark'])
            try:
                dialog.tk.call('tk::unsupported::MacWindowStyle', 'appearance', dialog, 'dark')
                dialog.tk.call('tk::unsupported::MacWindowStyle', 'style', dialog, 'plain')
            except Exception as e:
                logging.warning(f"设置 macOS 深色模式失败: {e}")
            
            # 创建编辑框
            frame = ttk.Frame(dialog, padding=10)
            frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(frame, text="新文件名:").pack(pady=(0,5))
            
            entry = ttk.Entry(frame, width=50)
            entry.insert(0, current_name)
            entry.pack(fill=tk.X, pady=(0,10))
            entry.select_range(0, tk.END)
            entry.focus_set()
            
            # 按钮区域
            btn_frame = ttk.Frame(frame)
            btn_frame.pack(fill=tk.X)
            
            
            def on_ok():
                new_name = entry.get()
                if new_name and new_name != current_name:
                    self.tree.set(item, "翻译后文件名", new_name)
                    self.tree.set(item, "状态", "已修改")
                dialog.destroy()
            
            ttk.Button(btn_frame, text="确定", command=on_ok).pack(side=tk.RIGHT, padx=5)
            ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT)
            
            # 绑定回车键
            entry.bind('<Return>', lambda e: on_ok())
            
            # 等待对话框关闭
            dialog.wait_window()
            
        except Exception as e:
            logging.error(f"编辑文件名时出错: {str(e)}")
            
    def batch_edit(self, mode):
        """批量编辑文件名
        
        Args:
            mode: 编辑模式，可选值：
                - prefix: 添加前缀
                - suffix: 添加后缀
                - replace: 替换文本
        """
        try:
            # 获取选中的项目
            selected = [item for item in self.tree.get_children() 
                       if self.tree.set(item, "选择") == "√"]
            
            if not selected:
                tk.messagebox.showwarning("警告", "请至少选择一个文件")
                return
            
            # 根据模式执行不同的编辑操作
            if mode in ("prefix", "suffix"):
                text = self.add_text.get().strip()
                if not text:
                    tk.messagebox.showwarning("警告", "请输入要添加的文本")
                    return
                    
                for item in selected:
                    current_name = self.tree.set(item, "翻译后文件名")
                    if mode == "prefix":
                        new_name = text + current_name
                    else:  # suffix
                        name, ext = os.path.splitext(current_name)
                        new_name = name + text + ext
                    
                    self.tree.set(item, "翻译后文件名", new_name)
                    self.tree.set(item, "状态", "已修改")
                    
            elif mode == "replace":
                find = self.find_text.get().strip()
                replace = self.replace_text.get()  # 允许替换为空字符串
                
                if not find:
                    tk.messagebox.showwarning("警告", "请输入要查找的文本")
                    return
                    
                for item in selected:
                    current_name = self.tree.set(item, "翻译后文件名")
                    if find in current_name:
                        new_name = current_name.replace(find, replace)
                        self.tree.set(item, "翻译后文件名", new_name)
                        self.tree.set(item, "状态", "已修改")
            
        except Exception as e:
            logging.error(f"批量编辑文件名时出错: {str(e)}")
            tk.messagebox.showerror("错误", f"批量编辑文件名时出错: {str(e)}")

    def toggle_translation(self, auto_categorize=False):
        """切换翻译状态"""
        try:
            if not self.is_translating:
                # 开始翻译
                selected = [item for item in self.tree.get_children() 
                           if self.tree.set(item, "选择") == "√"]
                
                if not selected:
                    messagebox.showwarning("警告", "请至少选择一个文件")
                    return
                
                # 设置自动分类选项
                if auto_categorize:
                    self.auto_categorize.set(True)
                
                self.is_translating = True
                self.pause_event.set()  # 确保未暂停
                self.control_btn.configure(text="暂停")
                
                # 启动翻译线程
                translation_thread = threading.Thread(
                    target=self.translation_worker,
                    args=(selected,),
                    daemon=True
                )
                translation_thread.start()
                
                # 启动进度检查
                self.window.after(100, self.check_progress)
            else:
                # 切换暂停/继续状态
                if self.pause_event.is_set():
                    # 暂停翻译
                    self.pause_event.clear()
                    self.control_btn.configure(text="继续")
                    self.status_label.config(text="翻译已暂停")
                else:
                    # 继续翻译
                    self.pause_event.set()
                    self.control_btn.configure(text="暂停")
                    self.status_label.config(text="翻译继续")
                
        except Exception as e:
            logging.error(f"切换翻译状态时出错: {str(e)}")
            messagebox.showerror("错误", f"切换翻译状态时出错: {str(e)}")

    def run(self):
        """启动主窗口主循环"""
        self.window.mainloop()

    def on_click(self, event):
        """处理点击事件"""
        try:
            region = self.tree.identify_region(event.x, event.y)
            if region == "cell":
                column = self.tree.identify_column(event.x)
                item = self.tree.identify_row(event.y)
                
                if item and column == '#1':  # 点击"选择"列
                    current_state = self.tree.set(item, "选择")
                    new_state = "" if current_state == "√" else "√"
                    self.tree.set(item, "选择", new_state)
                    self.update_file_count()
                    return "break"
                
        except Exception as e:
            logging.error(f"处理点击事件时出错: {e}")

    def select_all(self):
        """全选"""
        for item in self.tree.get_children():
            self.tree.set(item, "选择", "√")
        self.update_file_count()

    def deselect_all(self):
        """取消全选"""
        for item in self.tree.get_children():
            self.tree.set(item, "选择", "")
        self.update_file_count()

    def remove_selected(self):
        """删除选中项"""
        selected = [item for item in self.tree.get_children() 
                   if self.tree.set(item, "选择") == "√"]
        for item in selected:
            self.tree.delete(item)
        self.update_file_count()

    def clear_list(self):
        """清空列表"""
        if messagebox.askyesno("确认", "确定要清空列表吗？"):
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.update_file_count()

    def create_progress_info(self, parent):
        """创建进度信息区域"""
        try:
            # 进度条区域
            progress_frame = ttk.Frame(parent)
            progress_frame.grid(row=0, column=0, sticky="nsew", pady=(0,10))
            progress_frame.grid_columnconfigure(1, weight=1)  # 进度条可扩展
            
            # 总体进度
            ttk.Label(
                progress_frame,
                text="总体进度:"
            ).grid(row=0, column=0, sticky="w", padx=(0,10))
            
            ttk.Progressbar(
                progress_frame,
                variable=self.total_progress_var,
                mode='determinate',
                length=200
            ).grid(row=0, column=1, sticky="ew", pady=2)
            
            # 当前文件进度
            ttk.Label(
                progress_frame,
                text="当前文件:"
            ).grid(row=1, column=0, sticky="w", padx=(0,10))
            
            ttk.Progressbar(
                progress_frame,
                variable=self.file_progress_var,
                mode='determinate',
                length=200
            ).grid(row=1, column=1, sticky="ew", pady=2)
            
            # 统计信息
            stats_frame = ttk.Frame(parent)
            stats_frame.grid(row=1, column=0, sticky="ew", pady=(10,0))
            
            # 创建统计标签
            labels = [
                ("已处理", "已处理: 0"),
                ("成功", "成功: 0"),
                ("失败", "失败: 0"),
                ("耗时", "耗时: 0:00")
            ]
            
            for i, (key, text) in enumerate(labels):
                label = ttk.Label(stats_frame, text=text)
                label.grid(row=0, column=i, padx=(0,20), sticky="w")
                self.stats_labels[key] = label
            
        except Exception as e:
            logging.error(f"创建进度信息区域时出错: {str(e)}")
            raise

    def create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=5, column=0, sticky="nsew", pady=(5,0))
        status_frame.grid_columnconfigure(0, weight=1)  # 让文件计数标签可以扩展
        
        # 文件计数标签
        self.file_count_label = ttk.Label(
            status_frame,
            text="总文件数: 0 | 已选择: 0"
        )
        self.file_count_label.grid(row=0, column=0, sticky="w", padx=5)
        
        # 状态标签
        self.status_label = ttk.Label(
            status_frame,
            text="就绪"
        )
        self.status_label.grid(row=0, column=1, sticky="e", padx=5)

    def translation_worker(self, selected_items):
        """翻译工作线程"""
        start_time = datetime.datetime.now()
        success_count = 0
        fail_count = 0
        total = len(selected_items)
        last_update_time = time.time()  # 用于控制进度更新频率

        try:
            # 收集需要翻译的文件名
            filenames = []
            item_map = {}  # 用于保存item和文件名的映射
            for item in selected_items:
                filename = self.tree.set(item, "原文件名")
                filenames.append(filename)
                item_map[filename] = item
                self.tree.set(item, "状态", "等待中")

            if self.batch_translate.get():
                try:
                    batch_size = int(self.batch_size.get())
                except ValueError:
                    batch_size = 10

                # 分批处理文件
                for i in range(0, len(filenames), batch_size):
                    # 检查暂停状态
                    self.pause_event.wait()
                    if not self.is_translating:
                        break

                    batch = filenames[i:i + batch_size]
                    batch_results = {}  # 存储批次翻译结果
                    retry_files = []    # 存储需要重试的文件

                    # 更新状态为处理中
                    for filename in batch:
                        item = item_map[filename]
                        self.tree.set(item, "状态", "处理中")

                    # 第一次尝试翻译
                    try:
                        translated_names = self.translator.batch_translate_filenames(batch, batch_size=batch_size)
                        for filename, translated in zip(batch, translated_names):
                            if translated:
                                batch_results[filename] = translated
                            else:
                                retry_files.append(filename)
                    except Exception as e:
                        logging.error(f"批次翻译失败: {e}")
                        retry_files.extend(batch)

                    # 对失败的文件进行重试（单个翻译）
                    if retry_files:
                        for filename in retry_files:
                            try:
                                translated = self.translator.translate_filename(filename)
                                if translated:
                                    batch_results[filename] = translated
                            except Exception as e:
                                logging.error(f"重试翻译失败 {filename}: {e}")

                    # 更新界面和计数
                    for filename in batch:
                        item = item_map[filename]
                        if filename in batch_results:
                            self.tree.set(item, "翻译后文件名", batch_results[filename])
                            self.tree.set(item, "状态", "已完成")
                            success_count += 1
                            # 更新翻译缓存
                            self.translation_cache[filename] = batch_results[filename]
                        else:
                            self.tree.set(item, "状态", "失败")
                            fail_count += 1

                        # 控制进度更新频率（每100ms更新一次）
                        current_time = time.time()
                        if current_time - last_update_time >= 0.1:
                            elapsed = datetime.datetime.now() - start_time
                            self.translation_queue.put({
                                "success_count": success_count,
                                "fail_count": fail_count,
                                "total_progress": (success_count + fail_count) / total * 100,
                                "status": f"正在处理: {success_count + fail_count}/{total} | 耗时: {elapsed}"
                            })
                            last_update_time = current_time
                            self.window.update_idletasks()

                    # 清理过期缓存
                    self._cleanup_cache()

            else:
                # 单个文件翻译的逻辑保持不变
                for i, item in enumerate(selected_items, 1):
                    # 检查暂停状态
                    self.pause_event.wait()  # 如果暂停，在此等待
                    
                    # 检查是否需要停止
                    if not self.is_translating:
                        break
                    
                    # 获取原文件名
                    original = self.tree.set(item, "原文件名")
                    self.tree.set(item, "状态", "处理中")
                    
                    try:
                        # 执行翻译
                        translated = self.translator.translate_filename(original)
                        
                        # 更新界面
                        self.tree.set(item, "翻译后文件名", translated)
                        self.tree.set(item, "状态", "已完成")
                        success_count += 1
                    except Exception as e:
                        logging.error(f"翻译失败: {str(e)}")
                        self.tree.set(item, "状态", "失败")
                        fail_count += 1
                    
                    # 更新进度
                    elapsed = datetime.datetime.now() - start_time
                    self.translation_queue.put({
                        "success_count": success_count,
                        "fail_count": fail_count,
                        "total_progress": (i / total) * 100,
                        "status": f"正在处理: {i}/{total} | 耗时: {elapsed}"
                    })
                    
                    # 立即更新界面
                    self.window.update_idletasks()
            
            # 完成处理
            elapsed = datetime.datetime.now() - start_time
            self.translation_queue.put({
                "complete": True,
                "success_count": success_count,
                "fail_count": fail_count,
                "total_progress": 100,
                "status": "处理完成",
                "elapsed": elapsed
            })

        except Exception as e:
            logging.error(f"翻译线程异常: {str(e)}")
            self.translation_queue.put({
                "complete": True,
                "error": str(e)
            })
        finally:
            self.is_translating = False
            self.control_btn.configure(text="开始翻译", state='disabled')

    def _cleanup_cache(self):
        """清理翻译缓存"""
        try:
            if len(self.translation_cache) > 1000:
                # 保留最新的500条记录
                items = sorted(
                    self.translation_cache.items(),
                    key=lambda x: x[1].get('timestamp', 0),
                    reverse=True
                )[:500]
                self.translation_cache = dict(items)
        except Exception as e:
            logging.error(f"清理缓存失败: {e}")

    def _process_single_translation(self, item, translator):
        """处理单个文件的翻译"""
        try:
            original = self.tree.set(item, "原文件名")
            
            # 检查缓存
            if original in self.translation_cache:
                translated = self.translation_cache[original]
                self.translation_queue.put(("translation_complete", item, translated))
                return
                
            # 执行翻译，带重试机制
            self.translation_queue.put(("status_update", item, "翻译中..."))
            translated = self._translate_with_retry(translator, original)
            
            # 保存到缓存
            self.translation_cache[original] = translated
            
            self.translation_queue.put(("translation_complete", item, translated))
            
        except Exception as e:
            logging.error(f"翻译失败: {e}")
            self.translation_queue.put(("translation_error", item, str(e)))

    def _translate_with_retry(self, translator, text, max_retries=3):
        """带重试机制的翻译"""
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                return translator.translate_filename(text)
            except ConnectionError as e:
                last_error = e
                retry_count += 1
                time.sleep(1)  # 重试前等待
            except Exception as e:
                raise e
        
        if last_error:
            raise last_error
            
    def apply_rename(self):
        """改进的重命名操作"""
        selected = [item for item in self.tree.get_children() 
                   if self.tree.set(item, "选择") == "√" and 
                   self.tree.set(item, "翻译后文件名") and 
                   self.tree.set(item, "状态") == "已完成"]
        
        if not selected:
            messagebox.showwarning("警告", "请选择已完成翻译的文件进行重命名")
            return
    
        if not messagebox.askyesno("确认", "确定要重命名这些文件吗？"):
            return
    
        results = self._batch_rename(selected)
        self._show_rename_results(results)

    def _batch_rename(self, items):
        """批量重命名处理"""
        results = {'success': 0, 'fail': 0, 'errors': []}
        
        for item in items:
            try:
                original = self.tree.set(item, "原文件名")
                translated = self.tree.set(item, "翻译后文件名")
                
                file_path = self._get_full_path(original)
                if not file_path:
                    raise FileNotFoundError(f"找不到文件: {original}")
                
                # 获取分类信息
                cat_id = translated.split('_')[0]  # 获取CatID
                cat_zh = translated.split('_')[1]  # 获取中文分类名
                
                if self.auto_categorize.get():
                    # 创建分类文件夹
                    category_folder = Path(file_path).parent / f"{cat_id}_{cat_zh}"
                    category_folder.mkdir(exist_ok=True)
                    
                    # 如果启用子分类
                    if self.use_subcategory.get():
                        # 获取子分类信息
                        category_info = self.category_manager.get_category_by_id(cat_id)
                        if category_info and category_info.get('subcategory') and category_info.get('subcategory_zh'):
                            sub_folder = category_folder / f"{category_info['subcategory']}_{category_info['subcategory_zh']}"
                            sub_folder.mkdir(exist_ok=True)
                            # 使用子分类文件夹作为目标文件夹
                            category_folder = sub_folder
                    
                    # 生成新路径（在分类文件夹内）
                    new_path = self._generate_unique_path(category_folder / translated)
                else:
                    # 原来的重命名逻辑
                    new_path = self._generate_unique_path(file_path, translated)
                
                # 执行重命名/移动
                Path(file_path).rename(new_path)
                
                self.tree.set(item, "状态", "已重命名")
                results['success'] += 1
                
            except Exception as e:
                logging.error(f"重命名失败 {original}: {e}")
                self.tree.set(item, "状态", "重命名失败")
                results['fail'] += 1
                results['errors'].append(f"{original}: {str(e)}")
                
        return results

    def _generate_unique_path(self, folder_path, filename=None):
        """生成唯一的文件路径
        
        Args:
            folder_path: 目标文件夹路径（Path对象）
            filename: 目标文件名（如果为None，则使用folder_path的名称）
        """
        if isinstance(folder_path, str):
            folder_path = Path(folder_path)
            
        if filename is None:
            filename = folder_path.name
            folder_path = folder_path.parent
            
        # 确保目标文件夹存在
        folder_path.mkdir(parents=True, exist_ok=True)
        
        # 分离文件名和扩展名
        name = Path(filename).stem
        suffix = Path(filename).suffix
        
        new_path = folder_path / f"{name}{suffix}"
        counter = 1
        
        while new_path.exists():
            new_path = folder_path / f"{name}_{counter}{suffix}"
            counter += 1
            
        return new_path

    def _show_rename_results(self, results):
        """显示重命名结果"""
        message = f"重命名完成\n成功: {results['success']}\n失败: {results['fail']}"
        
        if results['errors']:
            message += "\n\n失败详情:"
            for error in results['errors'][:5]:  # 只显示前5个错误
                message += f"\n- {error}"
                
            if len(results['errors']) > 5:
                message += f"\n... 及其他 {len(results['errors']) - 5} 个错误"
                
        messagebox.showinfo("重命名结果", message)

    def setup_logging(self):
        """设置日志"""
        try:
            log_file = 'audio_translator.log'
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file, encoding='utf-8'),
                    logging.StreamHandler()
                ]
            )
            logging.info("程序启动")
        except Exception as e:
            print(f"设置日志时出错: {e}")
            
    def translate(self, text: str) -> str:
        """智能翻译方法（支持多服务切换）"""
        if not text:
            return ""

        # 动态选择翻译服务
        try:
            service = self.config.get("TRANSLATION_SERVICE", "UCS")  # 默认为UCS服务
            translated = self._dispatch_translation(service, text)
        except Exception as e:
            logging.error(f"翻译服务 {service} 失败: {str(e)}")
            translated = self._fallback_translation(text)  # 降级策略

        return translated

    def _dispatch_translation(self, service: str, text: str) -> str:
        service_mapping = {
            "UCS": self._translate_ucs,
            "ZhipuAI": self._translate_zhipu,
            "NVIDIA": self._translate_nvidia,
            "DeepSeek": self._translate_deepseek  # 确保键名与配置完全一致
        }        
        if service not in service_mapping:
            raise ValueError(f"不支持的翻译服务: {service}")
            
        logging.info(f"使用 {service} 服务翻译: {text}")
        return service_mapping[service](text)

    def _fallback_translation(self, text: str) -> str:
        """灾难恢复策略"""
        # 1. 尝试备用服务
        fallback_services = ["UCS", "ZhipuAI", "NVIDIA"]
        current_service = self.config.get("TRANSLATION_SERVICE")
        
        for service in fallback_services:
            if service != current_service:
                try:
                    return self._dispatch_translation(service, text)
                except Exception:
                    continue
                    
        # 2. 返回原始文本作为最后手段
        logging.warning("所有翻译服务不可用，返回原始文本")
        return text

    def _normalize_translation(self, translated: str) -> str:
        """统一格式化翻译结果"""
        # 移除可能存在的提示前缀
        markers = ["中文名:", "翻译结果:", "=>"]
        for marker in markers:
            if marker in translated:
                translated = translated.split(marker)[-1].strip()
                
        # 清理特殊字符
        return translated.strip("。：:")[:100]  # 限制最大长度

    def show_dictionary_manager(self):
        """显示词库管理器"""
        try:
            dictionary_manager = DictionaryManagerWindow(self.window)
            self.window.wait_window(dictionary_manager.window)
            
        except Exception as e:
            logging.error(f"打开词库管理器时出错: {e}")
            messagebox.showerror("错误", f"打开词库管理器时出错: {str(e)}")

    def show_service_manager(self):
        """显示服务管理窗口"""
        try:
            # 创建服务管理窗口
            manager = ServiceManagerWindow(self.window, self.config)
            # 等待窗口关闭
            self.window.wait_window(manager.window)
            # 重新加载服务列表
            self.load_services()
        except Exception as e:
            logging.error(f"打开服务管理窗口失败: {str(e)}")
            messagebox.showerror("错误", f"打开服务管理窗口失败: {str(e)}")

    def _translate_with_api(self, text: str) -> str:
        """使用API进行翻译的具体实现"""
        try:
            # 构建请求数据
            data = {
                "model": "glm-4",  # 或其他模型ID
                "messages": [
                    {
                        "role": "user",
                        "content": f"请将以下音效文件名翻译成中文：{text}"
                    }
                ],
                "temperature": 0.7,
                "stream": False
            }

            # 发送异步请求
            response = requests.post(
                "https://open.bigmodel.cn/api/paas/v4/async/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config.get('ZHIPU_API_KEY')}",
                    "Content-Type": "application/json"
                },
                json=data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                task_id = result.get("id")
                
                if not task_id:
                    raise ValueError("未获取到任务ID")
                
                # 循环查询任务状态，直到完成或超时
                start_time = time.time()
                while True:
                    task_result = self._check_task_status(task_id)
                    
                    if task_result:
                        # 提取翻译结果
                        translated = self._get_nested_value(
                            task_result,
                            ["choices", 0, "message", "content"],
                            default=None
                        )
                        if translated:
                            return translated
                        break
                    
                    if time.time() - start_time > 30:  # 设置查询超时时间
                        raise TimeoutError("任务查询超时")
                    
                    time.sleep(1)  # 每隔1秒查询一次
                    
            else:
                raise ValueError(f"API请求失败: {response.status_code}\n{response.text}")
            
        except Exception as e:
            logging.error(f"API 翻译失败: {str(e)}")
            raise

    def _check_task_status(self, task_id: str):
        """检查异步任务状态"""
        try:
            response = requests.get(
                f"https://open.bigmodel.cn/api/paas/v4/async/chat/completions/{task_id}",
                headers={
                    "Authorization": f"Bearer {self.config.get('ZHIPU_API_KEY')}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("task_status") == "SUCCESS":
                    return result
                elif result.get("task_status") == "FAIL":
                    raise ValueError(f"任务失败: {result.get('error', '未知错误')}")
                    
            return None
            
        except Exception as e:
            logging.error(f"检查任务状态失败: {str(e)}")
            return None

    def __del__(self):
        """清理资源"""
        try:
            self.config.save()
        except Exception as e:
            logging.error(f"保存配置失败: {e}")

    def create_main_window(self):
        self.window = tk.Tk()
        self.window.title("音频文件名翻译器")
        self.window.geometry("1200x800")

        # 创建主框架
        self.main_frame = ttk.Frame(self.window, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

    def setup_styles(self):
        style = ttk.Style()
        style.configure("Toolbar.TFrame", padding=5)
        style.configure("FileList.Treeview", rowheight=25)
        style.configure("StatusBar.TLabel", padding=5)

    def update_file_count(self, event=None):
        """更新文件计数和按钮状态"""
        try:
            total = len(self.tree.get_children())
            selected = len([item for item in self.tree.get_children() 
                           if self.tree.set(item, "选择") == "√"])
            
            if hasattr(self, 'file_count_label'):
                self.file_count_label.config(text=f"总文件数: {total} | 已选择: {selected}")
            
            # 更新控制按钮状态
            if hasattr(self, 'control_btn'):
                if selected > 0:
                    self.control_btn.configure(state='normal')
                    if self.is_translating:
                        self.control_btn.configure(
                            text="暂停" if self.pause_event.is_set() else "继续"
                        )
                    else:
                        self.control_btn.configure(text="开始翻译")
                else:
                    self.control_btn.configure(state='disabled', text="开始翻译")
            
            # 更新重命名按钮状态
            if hasattr(self, 'rename_btn'):
                # 检查是否有已完成翻译的文件
                has_completed = any(
                    self.tree.set(item, "状态") == "已完成"
                    for item in self.tree.get_children()
                    if self.tree.set(item, "选择") == "√"
                )
                self.rename_btn.configure(state='normal' if has_completed else 'disabled')
            
        except Exception as e:
            logging.error(f"更新文件计数时出错: {e}")

    def check_progress(self):
        """检查翻译进度"""
        try:
            while True:
                try:
                    data = self.translation_queue.get_nowait()
                    
                    if "complete" in data:
                        self.translation_complete()
                        self.is_translating = False
                        # 启用重命名按钮
                        self.rename_btn.configure(state='normal')
                        return
                    
                    # 更新统计信息
                    if "success_count" in data:
                        self.stats_labels["成功"].config(text=f"成功: {data['success_count']}")
                        self.stats_labels["失败"].config(text=f"失败: {data['fail_count']}")
                        self.stats_labels["已处理"].config(
                            text=f"已处理: {data['success_count'] + data['fail_count']}"
                        )
                    
                    if "total_progress" in data:
                        self.total_progress_var.set(data["total_progress"])
                    if "status" in data:
                        self.status_label.config(text=data["status"])
                    
                    # 立即更新界面
                    self.window.update_idletasks()
                    
                except queue.Empty:
                    break
            
            if self.is_translating:
                self.window.after(100, self.check_progress)
                
        except Exception as e:
            logging.error(f"更新进度失败: {e}")

    def translation_complete(self):
        """翻译完成处理"""
        messagebox.showinfo("完成", "所有文件处理完成！")
        if hasattr(self, 'status_label'):
            self.status_label.config(text="处理完成")
        if hasattr(self, 'control_btn'):
            self.control_btn.configure(state='disabled')
        if hasattr(self, 'rename_btn'):
            self.rename_btn.configure(state='normal')  # 启用重命名按钮
        self.pause_event.set()
    
    def on_closing(self):
        """处理窗口关闭事件"""
        if self.is_translating:
            if not messagebox.askyesno("确认", "翻译正在进行中，确定要退出吗？"):
                return
            
        # 停止所有进行中的任务
        self.is_translating = False
        self.pause_event.set()
        
        try:
            # 保存配置
            self.config.save()
            # 退出主循环
            self.window.quit()
            # 销毁窗口
            self.window.destroy()
        except Exception as e:
            logging.error(f"关闭窗口失败: {e}")
            # 强制销毁
            try:
                self.window.destroy()
            except:
                pass

    def select_files(self):
        """选择文件"""
        try:
            # 扩展支持的音频格式
            if sys.platform == 'darwin':  # macOS
                filetypes = (
                    ('音频文件', '*.wav *.mp3 *.ogg *.flac *.m4a *.aac *.aif *.aiff *.wma *.alac'),
                    ('所有文件', '*.*')
                )
            else:  # Windows/Linux
                filetypes = [
                    ('音频文件', '*.wav;*.mp3;*.ogg;*.flac;*.m4a;*.aac;*.aif;*.aiff;*.wma;*.alac'),
                    ('所有文件', '*.*')
                ]
            
            files = filedialog.askopenfilenames(
                title="选择音效文件",
                filetypes=filetypes,
                parent=self.window
            )
            
            if files:
                self.add_files(files)
            
        except Exception as e:
            logging.error(f"选择文件时出错: {str(e)}")
            messagebox.showerror("错误", f"选择文件时出错: {str(e)}")

    def select_folder(self):
        """选择文件夹"""
        try:
            folder = filedialog.askdirectory(title="选择文件夹")
            if folder:
                files = []
                # 扩展支持的音频格式
                audio_extensions = [
                    '.wav', '.mp3', '.ogg', '.flac', 
                    '.m4a', '.aac', '.aif', '.aiff',
                    '.wma', '.alac'
                ]
                for ext in audio_extensions:
                    files.extend(Path(folder).glob(f'**/*{ext}'))
                    files.extend(Path(folder).glob(f'**/*{ext.upper()}'))  # 添加大写扩展名支持
                
                if files:
                    self.add_files([str(f) for f in files])
                else:
                    messagebox.showinfo("提示", "所选文件夹中没有找到音频文件")
                
        except Exception as e:
            logging.error(f"选择文件夹时出错: {str(e)}")
            messagebox.showerror("错误", f"选择文件夹时出错: {str(e)}")

    def add_files(self, files):
        """添加文件到列表"""
        try:
            for file in files:
                # 获取文件名和完整路径
                filename = os.path.basename(file)
                
                # 检查是否已存在
                exists = False
                for item in self.tree.get_children():
                    if self.tree.set(item, "原文件名") == filename:
                        exists = True
                        break
                
                if not exists:
                    item = self.tree.insert(
                        "",
                        "end",
                        values=("", filename, "", "待处理"),
                        tags=(file,)  # 保存完整路径
                    )
                    
                    # 如果启用了自动分类，显示分类对话框
                    if self.auto_categorize.get():
                        category = self.category_manager.show_category_dialog([file])
                        if category:
                            base_path = Path(file).parent
                            moved_files = self.category_manager.move_files_to_category([file], category, base_path)
                            if moved_files:
                                # 更新文件路径
                                self.tree.item(item, tags=(moved_files[0],))
                                # 更新状态
                                self.tree.set(item, "状态", "已分类")
            
            self.update_file_count()
            
        except Exception as e:
            logging.error(f"添加文件时出错: {str(e)}")
            messagebox.showerror("错误", f"添加文件时出错: {str(e)}")

    def show_context_menu(self, event):
        """显示右键菜单"""
        try:
            # 获取点击的项目
            item = self.tree.identify_row(event.y)
            if item:
                # 如果点击的是未选中的项目，先选中它
                if item not in self.tree.selection():
                    self.tree.selection_set(item)
                
                # 根据当前状态更新菜单项
                is_translating = self.is_translating
                self.context_menu.entryconfig("开始翻译", 
                                            label="暂停" if is_translating and self.pause_event.is_set() 
                                                  else "继续" if is_translating 
                                                  else "开始翻译")
                
                # 更新菜单样式
                self.context_menu.configure(
                    bg=self.COLORS['bg_dark'],
                    fg=self.COLORS['fg'],
                    activebackground=self.COLORS['hover'],
                    activeforeground=self.COLORS['fg']
                )
                
                # 显示菜单
                self.context_menu.post(event.x_root, event.y_root)
                
        except Exception as e:
            logging.error(f"显示右键菜单时出错: {str(e)}")

    def toggle_selection(self, event=None):
        """切换选中状态"""
        try:
            for item in self.tree.selection():
                current_state = self.tree.set(item, "选择")
                new_state = "" if current_state == "√" else "√"
                self.tree.set(item, "选择", new_state)
            self.update_file_count()
            
        except Exception as e:
            logging.error(f"切换选择状态时出错: {str(e)}")

    def invert_selection(self):
        """反选"""
        try:
            for item in self.tree.get_children():
                current_state = self.tree.set(item, "选择")
                new_state = "" if current_state == "√" else "√"
                self.tree.set(item, "选择", new_state)
            self.update_file_count()
            
        except Exception as e:
            logging.error(f"反选时出错: {str(e)}")

    def preview_translation(self):
        """预览翻译结果"""
        try:
            selected = [item for item in self.tree.get_children() 
                       if self.tree.set(item, "选择") == "√"]
            
            if not selected:
                messagebox.showwarning("警告", "请至少选择一个文件")
                return
            
            # 创建预览窗口
            preview_window = tk.Toplevel(self.window)
            preview_window.title("翻译预览")
            preview_window.geometry("800x600")
            preview_window.minsize(600, 400)
            preview_window.transient(self.window)
            preview_window.grab_set()
            
            # 设置主题
            ThemeManager.setup_dialog_theme(preview_window)  # 不需要传递 theme_name
            
            # 创建预览文本框和滚动条
            preview_frame = ttk.Frame(preview_window, padding=10)
            preview_frame.pack(fill=tk.BOTH, expand=True)
            
            preview_text = tk.Text(
                preview_frame,
                wrap=tk.WORD,
                background=self.COLORS['bg_light'],
                foreground=self.COLORS['fg'],
                insertbackground=self.COLORS['fg'],
                selectbackground=self.COLORS['selected'],
                selectforeground=self.COLORS['fg'],
                relief='solid',
                borderwidth=1,
                highlightthickness=0
            )
            scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=preview_text.yview)
            preview_text.configure(yscrollcommand=scrollbar.set)
            
            preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 添加标题
            preview_text.insert(tk.END, "翻译预览结果：\n\n")
            
            # 收集需要预览的文件名
            filenames = []
            for item in selected:
                filename = self.tree.set(item, "原文件名")
                filenames.append(filename)
            
            # 使用批量翻译
            try:
                batch_size = int(self.batch_size.get()) if self.batch_translate.get() else 1
            except ValueError:
                batch_size = 5  # 预览时使用较小的批次大小
            
            translated_names = self.translator.batch_translate_filenames(filenames, batch_size=batch_size)
            
            # 显示结果
            for original, translated in zip(filenames, translated_names):
                preview_text.insert(tk.END, f"原文件名: {original}\n")
                preview_text.insert(tk.END, f"翻译结果: {translated}\n")
                preview_text.insert(tk.END, "-" * 50 + "\n\n")
            
            # 设置为只读
            preview_text.configure(state='disabled')
            
            # 添加关闭按钮
            button_frame = ttk.Frame(preview_window, padding=(0, 10, 0, 0))
            button_frame.pack(fill=tk.X)
            
            ttk.Button(
                button_frame,
                text="关闭",
                command=preview_window.destroy
            ).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            logging.error(f"预览翻译失败: {str(e)}")
            messagebox.showerror("错误", f"预览翻译失败: {str(e)}")

    def confirm_translation(self, filename, translated_result):
        """确认翻译结果"""
        self.translator.update_categories_database(
            filename, 
            translated_result, 
            confirmed=True
        )

    def sort_column(self, col):
        """对列表按指定列排序"""
        try:
            # 获取所有项目
            items = [(self.tree.set(item, col), item) for item in self.tree.get_children()]
            
            # 如果是"选择"列，使用简单排序
            if col == "选择":
                items.sort()
            else:
                # 对其他列使用不区分大小写的字符串排序
                items.sort(key=lambda x: x[0].lower())
            
            # 重新排列项目
            for index, (_, item) in enumerate(items):
                self.tree.move(item, '', index)
                
            # 更新文件计数
            self.update_file_count()
            
        except Exception as e:
            logging.error(f"排序时出错: {str(e)}")
            messagebox.showerror("错误", f"排序时出错: {str(e)}")

    def categorize_selected_files(self):
        """对选中的文件进行分类"""
        selected = [item for item in self.tree.get_children() 
                   if self.tree.set(item, "选择") == "√"]
        
        if not selected:
            messagebox.showwarning("警告", "请至少选择一个文件")
            return
            
        # 获取选中文件的完整路径
        files = []
        for item in selected:
            file_path = self.tree.item(item, "tags")[0]  # 从tags中获取完整路径
            files.append(file_path)
            
        # 显示分类选择对话框
        category = self.category_manager.show_category_dialog(files)
        if not category:
            return
            
        # 获取基础路径（第一个文件的父目录）
        base_path = Path(files[0]).parent
            
        # 移动文件到分类文件夹
        moved_files = self.category_manager.move_files_to_category(files, category, base_path)
        
        # 更新文件列表
        for item in selected:
            file_path = self.tree.item(item, "tags")[0]
            if file_path in moved_files:
                # 更新文件路径
                new_path = moved_files[moved_files.index(file_path)]
                self.tree.item(item, tags=(new_path,))
                # 更新状态
                self.tree.set(item, "状态", "已分类")
                
        messagebox.showinfo("完成", f"已将 {len(moved_files)} 个文件移动到分类文件夹")

    def auto_categorize_files(self):
        """自动分类选中的文件"""
        try:
            # 获取选中的文件
            selected = [item for item in self.tree.get_children() 
                       if self.tree.set(item, "选择") == "√"]
            
            if not selected:
                messagebox.showwarning("警告", "请至少选择一个文件")
                return
                
            # 获取选中文件的完整路径
            files = []
            for item in selected:
                file_path = self.tree.item(item, "tags")[0]  # 从tags中获取完整路径
                files.append(file_path)
                
            # 获取基础路径（第一个文件的父目录）
            base_path = Path(files[0]).parent
            
            # 开始自动分类
            moved_files = self.category_manager.start_auto_categorize(files, base_path)
            
            # 更新文件列表中的文件路径和状态
            for item in selected:
                file_path = self.tree.item(item, "tags")[0]
                if file_path in moved_files:
                    # 更新文件路径
                    new_path = moved_files[moved_files.index(file_path)]
                    self.tree.item(item, tags=(new_path,))
                    # 更新状态
                    self.tree.set(item, "状态", "已分类")
                    
        except Exception as e:
            logging.error(f"自动分类失败: {str(e)}")
            messagebox.showerror("错误", f"自动分类失败: {str(e)}")

    def change_theme(self, theme_name):
        """切换界面主题"""
        try:
            # 使用主题管理器切换主题
            ThemeManager.change_theme(self.window, theme_name)
            
            # 保存主题设置
            self.config.set("UI_THEME", theme_name)
            self.config.save()
            
        except Exception as e:
            logging.error(f"切换主题失败: {str(e)}")
            messagebox.showerror("错误", f"切换主题失败: {str(e)}")

    def on_config_change(self, event):
        """处理配置变更事件
        
        Args:
            event: ConfigChangeEvent 实例，包含 key, old_value, new_value
        """
        try:
            # 记录配置变更
            logging.info(f"配置变更: {event.key} = {event.new_value}")
            
            # 根据不同配置项进行处理
            if event.key == "UI_THEME":
                # 主题变更
                ThemeManager.change_theme(self.window, event.new_value)
                
            elif event.key == "TRANSLATION_SERVICE":
                # 翻译服务变更
                self.load_services()
                self.load_service_models()
                
            elif event.key == "COLORS":
                # 颜色主题变更
                self.setup_theme()
                
            elif event.key.startswith("TRANSLATION_SERVICES."):
                # 服务配置变更
                service_id = event.key.split('.')[1]
                self.update_service_display(service_id)
            
        except Exception as e:
            logging.error(f"处理配置变更失败: {str(e)}")
            messagebox.showerror("错误", f"处理配置变更失败: {str(e)}")

    def setup_config_listener(self):
        """设置配置监听器"""
        try:
            # 添加配置监听
            self.config.add_listener(self.on_config_change)
            logging.info("配置监听器设置成功")
            
            # 初始加载配置
            self.load_initial_config()
            
        except Exception as e:
            logging.error(f"设置配置监听器失败: {str(e)}")
            messagebox.showerror("错误", f"设置配置监听器失败: {str(e)}")

    def load_initial_config(self):
        """加载初始配置"""
        try:
            # 加载UI主题
            theme = self.config.get("UI_THEME", "dark")
            ThemeManager.change_theme(self.window, theme)
            
            # 加载颜色主题
            self.setup_theme()
            
            # 加载翻译服务
            self.load_services()
            
            # 加载其他配置...
            
        except Exception as e:
            logging.error(f"加载初始配置失败: {str(e)}")
            messagebox.showerror("错误", f"加载初始配置失败: {str(e)}")

    def create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.window, tearoff=0)
        self.context_menu.add_command(label="编辑文件名", command=lambda: self.edit_filename(None))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="预览翻译", command=self.preview_translation)
        self.context_menu.add_command(label="开始翻译", command=self.toggle_translation)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="删除选中", command=self.remove_selected)

    def _create_prompt_settings(self, parent):
        """创建 Prompt 设置框架"""
        frame = ttk.LabelFrame(parent, text="Prompt 模板设置")
        
        # Prompt 选择
        prompt_select_frame = ttk.Frame(frame)
        prompt_select_frame.pack(fill='x', padx=5, pady=2)
        
        ttk.Label(prompt_select_frame, text="当前使用的 Prompt:").pack(side='left')
        self.prompt_type = ttk.Combobox(prompt_select_frame, state='readonly')
        self.prompt_type.pack(side='left', padx=5)
        
        # Prompt 内容
        ttk.Label(frame, text="Prompt 内容:").pack(anchor='w', padx=5, pady=2)
        self.prompt_text = scrolledtext.ScrolledText(frame, height=10)
        self.prompt_text.pack(fill='both', expand=True, padx=5, pady=2)
        
        # 绑定选择事件
        self.prompt_type.bind('<<ComboboxSelected>>', self._on_prompt_type_changed)
        
        return frame

    def _load_prompt_settings(self):
        """加载 Prompt 设置"""
        service = self._get_current_service()
        if service:
            # 设置可选的 prompt 类型
            prompts = service.get('prompts', {})
            self.prompt_type['values'] = list(prompts.keys())
            
            # 设置当前选中的 prompt
            current_prompt = service.get('current_prompt', '通用翻译')
            self.prompt_type.set(current_prompt)
            
            # 显示当前 prompt 内容
            self.prompt_text.delete('1.0', tk.END)
            self.prompt_text.insert('1.0', prompts.get(current_prompt, ''))

    def _on_prompt_type_changed(self, event=None):
        """当选择的 prompt 类型改变时"""
        service = self._get_current_service()
        if service:
            prompt_type = self.prompt_type.get()
            prompts = service.get('prompts', {})
            self.prompt_text.delete('1.0', tk.END)
            self.prompt_text.insert('1.0', prompts.get(prompt_type, ''))

    def _save_prompt_settings(self):
        """保存 Prompt 设置"""
        service = self._get_current_service()
        if service:
            prompt_type = self.prompt_type.get()
            prompt_content = self.prompt_text.get('1.0', tk.END).strip()
            
            # 更新 prompt 内容
            if 'prompts' not in service:
                service['prompts'] = {}
            service['prompts'][prompt_type] = prompt_content
            service['current_prompt'] = prompt_type

if __name__ == "__main__":
    app = AudioTranslatorGUI()
    app.run()

