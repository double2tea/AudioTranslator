import os
import json
import logging
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Dict, Any, Optional, List, Tuple, Union, Callable

from ...services.api.model_service import ModelService
from ...services.core.service_manager_service import ServiceManagerService
from ...utils.ui_utils import create_tooltip, ScrollableFrame
from ...utils.events import EventManager, ServiceRegisteredEvent, ServiceUnregisteredEvent, ServiceUpdatedEvent, Event
from ..base import ServicePanel

# 设置日志记录器
logger = logging.getLogger(__name__)

class ServiceManagerPanel(ServicePanel):
    """
    服务管理面板
    
    用于管理AI模型服务，包括添加、删除、配置和测试服务。
    支持事件驱动的UI更新，响应服务变更事件。
    
    Attributes:
        service_manager: 服务管理器
        current_service: 当前选中的服务ID
        has_changes: 是否有未保存的更改
    """
    
    def __init__(self, parent: tk.Widget, service_manager: Optional[ServiceManagerService] = None):
        """
        初始化服务管理面板
        
        Args:
            parent: 父级窗口部件
            service_manager: 服务管理器实例
        """
        # 创建事件管理器
        self.event_manager = EventManager.get_instance()
        
        # 检查service_manager是否为None
        if service_manager is None:
            # 使用ttk.Frame的构造函数，因为service_factory不可用
            ttk.Frame.__init__(self, parent)
            # 设置变量
            self.service_manager = None
            self.service_factory = None
            self.current_service = None
            self.has_changes = False
            
            # 创建变量
            self.name_var = tk.StringVar()
            self.type_var = tk.StringVar()
            self.api_key_var = tk.StringVar()
            self.api_url_var = tk.StringVar()
            self.enable_var = tk.BooleanVar()
            self.model_var = tk.StringVar()
            self.status_var = tk.StringVar(value="服务管理器不可用")
            
            # 简单显示错误消息
            label = ttk.Label(self, text="服务管理器不可用，请检查应用程序配置")
            label.pack(padx=20, pady=20)
            return
        
        # 获取service_factory，通常从service_manager中获取
        service_factory = service_manager.service_factory
        
        # 调用父类构造函数
        super().__init__(parent, service_factory, "service_manager_panel")
        
        # 面板特有属性
        self.service_manager = service_manager
        self.current_service = None
        self.has_changes = False
        
        # 创建变量
        self.name_var = tk.StringVar()
        self.type_var = tk.StringVar()
        self.api_key_var = tk.StringVar()
        self.api_url_var = tk.StringVar()
        self.enable_var = tk.BooleanVar()
        self.model_var = tk.StringVar()
        self.status_var = tk.StringVar(value="就绪")
        
        # 初始化UI
        self._init_ui()
        
        # 注册事件监听器
        self._register_event_listeners()
        
        # 加载服务列表
        self._load_services()
        
    def _init_ui(self) -> None:
        """初始化UI组件"""
        # 创建主布局
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        
        # 创建服务列表框架
        service_frame = ttk.LabelFrame(self, text="服务列表", padding=5)
        service_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        service_frame.rowconfigure(0, weight=1)
        service_frame.columnconfigure(0, weight=1)
        
        # 创建服务列表
        self.service_tree = ttk.Treeview(
            service_frame,
            columns=("name", "type", "status"),
            show="headings",
            selectmode="browse"
        )
        
        self.service_tree.heading("name", text="名称")
        self.service_tree.heading("type", text="类型")
        self.service_tree.heading("status", text="状态")
        
        self.service_tree.column("name", width=150)
        self.service_tree.column("type", width=100)
        self.service_tree.column("status", width=80)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(service_frame, orient="vertical", command=self.service_tree.yview)
        self.service_tree.configure(yscrollcommand=scrollbar.set)
        
        # 放置服务列表组件
        self.service_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # 创建服务控制按钮
        btn_frame = ttk.Frame(service_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        
        ttk.Button(btn_frame, text="添加", command=self._add_service).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="删除", command=self._delete_service).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="刷新", command=self._refresh_services).pack(side="left", padx=2)
        
        # 创建配置框架
        config_frame = ttk.LabelFrame(self, text="服务配置", padding=5)
        config_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        config_frame.rowconfigure(0, weight=1)
        config_frame.columnconfigure(0, weight=1)
        
        # 创建配置表单
        form_frame = ttk.Frame(config_frame)
        form_frame.pack(fill="both", expand=True)
        
        # 服务名称
        ttk.Label(form_frame, text="服务名称:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(form_frame, textvariable=self.name_var)
        self.name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        # 服务类型
        ttk.Label(form_frame, text="服务类型:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.type_var = tk.StringVar()
        self.type_combo = ttk.Combobox(
            form_frame,
            textvariable=self.type_var,
            values=self.service_manager.get_available_services(),
            state="readonly"
        )
        self.type_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        # API Key
        ttk.Label(form_frame, text="API Key:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(form_frame, textvariable=self.api_key_var, show="*")
        self.api_key_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        
        # 显示/隐藏API Key按钮
        self.show_key = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            form_frame,
            text="显示API Key",
            variable=self.show_key,
            command=self._toggle_api_key_visibility
        ).grid(row=2, column=2, padx=5, pady=5)
        
        # API URL
        ttk.Label(form_frame, text="API URL:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.api_url_var = tk.StringVar()
        self.api_url_entry = ttk.Entry(form_frame, textvariable=self.api_url_var)
        self.api_url_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=5)
        
        # 启用开关
        self.enable_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            form_frame,
            text="启用服务",
            variable=self.enable_var
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=5, pady=5)
        
        # 模型选择
        ttk.Label(form_frame, text="默认模型:").grid(row=5, column=0, sticky="e", padx=5, pady=5)
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(
            form_frame,
            textvariable=self.model_var,
            state="readonly"
        )
        self.model_combo.grid(row=5, column=1, sticky="ew", padx=5, pady=5)
        
        # 服务状态
        ttk.Label(form_frame, text="服务状态:").grid(row=6, column=0, sticky="e", padx=5, pady=5)
        self.status_frame = ttk.Frame(form_frame)
        self.status_frame.grid(row=6, column=1, sticky="ew", padx=5, pady=5)
        
        self.status_indicator = ttk.Label(self.status_frame, text="●", foreground="gray")
        self.status_indicator.pack(side="left", padx=2)
        
        self.status_label = ttk.Label(self.status_frame, text="未知")
        self.status_label.pack(side="left", padx=2)
        
        # 操作按钮
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=7, column=0, columnspan=3, sticky="ew", pady=10)
        
        ttk.Button(
            btn_frame,
            text="保存",
            command=self._save_service
        ).pack(side="left", padx=5)
        
        ttk.Button(
            btn_frame,
            text="测试连接",
            command=self._test_connection
        ).pack(side="left", padx=5)
        
        ttk.Button(
            btn_frame,
            text="获取模型列表",
            command=self._fetch_models
        ).pack(side="left", padx=5)
        
        # 绑定事件
        self.service_tree.bind("<<TreeviewSelect>>", self._on_service_select)
        self.type_combo.bind("<<ComboboxSelected>>", self._on_type_change)
        
        # 配置表单网格
        form_frame.columnconfigure(1, weight=1)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        
    def _register_event_listeners(self) -> None:
        """注册事件监听器"""
        self.event_manager.add_listener("service_registered", self._on_service_registered)
        self.event_manager.add_listener("service_unregistered", self._on_service_unregistered)
        self.event_manager.add_listener("service_updated", self._on_service_updated)
        
    def _on_service_registered(self, event: Event) -> None:
        """
        处理服务注册事件
        
        Args:
            event: 服务注册事件
        """
        self._refresh_services()
        self.status_var.set(f"服务 {event.service_name} 已注册")
        
    def _on_service_unregistered(self, event: Event) -> None:
        """
        处理服务注销事件
        
        Args:
            event: 服务注销事件
        """
        self._refresh_services()
        self.status_var.set(f"服务 {event.service_id} 已注销")
        
    def _on_service_updated(self, event: Event) -> None:
        """
        处理服务更新事件
        
        Args:
            event: 服务更新事件
        """
        self._refresh_services()
        self.status_var.set(f"服务 {event.service_id} 已更新")
        
    def _toggle_api_key_visibility(self) -> None:
        """切换API Key的可见性"""
        if self.show_key.get():
            self.api_key_entry.config(show="")
        else:
            self.api_key_entry.config(show="*")
            
    def _on_type_change(self, event=None) -> None:
        """处理服务类型变更"""
        service_type = self.type_var.get()
        if not service_type:
            return
            
        # 根据服务类型更新UI
        if service_type == "openai":
            self.api_url_var.set("https://api.openai.com/v1")
        elif service_type == "anthropic":
            self.api_url_var.set("https://api.anthropic.com")
        elif service_type == "gemini":
            self.api_url_var.set("")  # Gemini使用SDK，不需要URL
            
    def _load_services(self) -> None:
        """加载服务到树形视图"""
        # 清除现有项目
        for item in self.service_tree.get_children():
            self.service_tree.delete(item)
            
        # 加载服务
        for service in self.service_manager.list_services():
            status = "启用" if service["enabled"] else "禁用"
            status_tags = ("enabled",) if service["enabled"] else ("disabled",)
            
            self.service_tree.insert(
                "",
                "end",
                values=(
                    service["name"],
                    service["type"],
                    status
                ),
                tags=(service["id"], *status_tags)
            )
            
        # 设置标签样式
        self.service_tree.tag_configure("enabled", foreground="green")
        self.service_tree.tag_configure("disabled", foreground="gray")
            
    def _on_service_select(self, event=None) -> None:
        """处理服务选择"""
        selection = self.service_tree.selection()
        if not selection:
            return
            
        service_id = self.service_tree.item(selection[0])["tags"][0]
        service = self.service_manager.get_service(service_id)
        
        if service:
            # 如果选择了不同的服务，更新当前服务ID
            if self.current_service != service_id:
                self.current_service = service_id
                self._load_service_config(service)
                
                # 更新状态栏
                self.status_var.set(f"已加载服务: {service.name}")
                
                # 如果模型列表为空或只有提示文本，尝试自动加载模型列表
                model_values = self.model_combo["values"]
                if not model_values or (len(model_values) == 1 and model_values[0] == "<点击获取模型列表>"):
                    # 使用异步方式加载模型列表，避免阻塞UI
                    self.after(100, lambda: self._auto_load_models(service))
            
    def _load_service_config(self, service: ModelService) -> None:
        """
        加载服务配置到表单
        
        Args:
            service: 服务实例
        """
        self.name_var.set(service.name)
        self.type_var.set(service.type)
        self.api_key_var.set(service.api_key)
        self.api_url_var.set(service.api_url)
        self.enable_var.set(service.enabled)
        
        # 更新状态指示器
        if service.enabled:
            self.status_indicator.config(foreground="green")
            self.status_label.config(text="已启用")
        else:
            self.status_indicator.config(foreground="gray")
            self.status_label.config(text="已禁用")
            
        # 加载模型列表并自动设置当前模型
        self._update_model_list(service.models)
        
        # 设置当前模型（如果有）
        if hasattr(service, "current_model") and service.current_model:
            self.model_var.set(service.current_model)
        elif hasattr(service, "default_model") and service.default_model:
            self.model_var.set(service.default_model)
        else:
            self.model_var.set("")
        
    def _update_model_list(self, models: List[str]) -> None:
        """更新模型列表"""
        if not models:
            self.model_combo["values"] = ["<点击获取模型列表>"]
            self.model_combo.current(0)
            return
            
        self.model_combo["values"] = models
        
        # 获取当前选中的服务
        service_id = self.current_service
        if not service_id:
            self.model_combo.current(0)
            return
            
        service = self.service_manager.get_service(service_id)
        if not service:
            self.model_combo.current(0)
            return
            
        # 如果服务有当前模型，选择它
        if service.current_model and service.current_model in models:
            current_index = models.index(service.current_model)
            self.model_combo.current(current_index)
        else:
            # 否则选择第一个模型并更新服务配置
            self.model_combo.current(0)
            if models:
                service.current_model = models[0]
                # 保存更新后的服务配置
                self.service_manager.update_service(service_id, service.to_dict())
                self.service_manager.save_config()
        
    def _save_service(self) -> None:
        """保存当前服务配置"""
        if not self.current_service:
            return
            
        config = {
            "name": self.name_var.get(),
            "type": self.type_var.get(),
            "api_key": self.api_key_var.get(),
            "api_url": self.api_url_var.get(),
            "enabled": self.enable_var.get()
        }
        
        # 如果有选择模型，也保存模型
        if self.model_var.get() and self.model_var.get() != "<点击获取模型列表>":
            config["default_model"] = self.model_var.get()
        
        try:
            self.service_manager.update_service(self.current_service, config)
            self.status_var.set("服务配置已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存服务配置失败: {str(e)}")
            self.status_var.set(f"保存失败: {str(e)}")
            
    def _test_connection(self) -> None:
        """测试当前服务连接"""
        if not self.current_service:
            return
            
        self.status_var.set("正在测试连接...")
        self.update()  # 强制更新UI
            
        try:
            result = self.service_manager.test_service(self.current_service)
            if result.get("status") == "success":
                messagebox.showinfo("测试结果", "连接测试成功")
                self.status_indicator.config(foreground="green")
                self.status_label.config(text="连接正常")
            else:
                messagebox.showerror("测试结果", f"连接测试失败: {result.get('message', '未知错误')}")
                self.status_indicator.config(foreground="red")
                self.status_label.config(text="连接失败")
        except Exception as e:
            messagebox.showerror("测试结果", f"连接测试失败: {str(e)}")
            self.status_indicator.config(foreground="red")
            self.status_label.config(text="连接失败")
            
        self.status_var.set("就绪")
            
    def _fetch_models(self) -> None:
        """获取当前服务的模型列表"""
        if not self.current_service:
            return
            
        service = self.service_manager.get_service(self.current_service)
        if not service:
            return
            
        self.status_var.set("正在获取模型列表...")
        self.update()  # 强制更新UI
            
        try:
            if hasattr(service, "list_models"):
                models = service.list_models()
                if models:
                    self.model_combo["values"] = models
                    
                    # 如果当前没有选择模型或选择的是提示文本，则自动选择第一个模型
                    current_model = self.model_var.get()
                    if not current_model or current_model == "<点击获取模型列表>":
                        self.model_var.set(models[0])
                        
                        # 更新服务的当前模型
                        if hasattr(service, "current_model"):
                            service.current_model = models[0]
                            
                            # 保存更新到配置
                            config = service.to_dict()
                            config["current_model"] = models[0]
                            self.service_manager.update_service(self.current_service, config)
                    
                    messagebox.showinfo("成功", f"成功获取到 {len(models)} 个模型")
                else:
                    messagebox.showinfo("提示", "未获取到模型列表")
            else:
                messagebox.showinfo("提示", "此服务不支持获取模型列表")
        except Exception as e:
            messagebox.showerror("错误", f"获取模型列表失败: {str(e)}")
            
        self.status_var.set("就绪")
            
    def _add_service(self) -> None:
        """添加新服务"""
        # 创建添加服务的对话框
        dialog = tk.Toplevel(self)
        dialog.title("添加服务")
        dialog.geometry("400x350")
        dialog.resizable(False, False)
        dialog.transient(self)  # 设置为应用模态
        dialog.grab_set()
        
        # 配置对话框网格
        dialog.columnconfigure(1, weight=1)
        
        # 服务名称
        ttk.Label(dialog, text="服务名称:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var)
        name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        # 服务类型
        ttk.Label(dialog, text="服务类型:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        type_var = tk.StringVar()
        type_combo = ttk.Combobox(
            dialog,
            textvariable=type_var,
            values=self.service_manager.get_available_services(),
            state="readonly"
        )
        type_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        type_combo.current(0)  # 默认选择第一个选项
        
        # API Key
        ttk.Label(dialog, text="API Key:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        api_key_var = tk.StringVar()
        api_key_entry = ttk.Entry(dialog, textvariable=api_key_var, show="*")
        api_key_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        
        # 显示/隐藏API Key
        show_key = tk.BooleanVar(value=False)
        
        def toggle_key_visibility():
            if show_key.get():
                api_key_entry.config(show="")
            else:
                api_key_entry.config(show="*")
                
        ttk.Checkbutton(
            dialog,
            text="显示API Key",
            variable=show_key,
            command=toggle_key_visibility
        ).grid(row=2, column=2, padx=5, pady=5)
        
        # API URL
        ttk.Label(dialog, text="API URL:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        api_url_var = tk.StringVar()
        api_url_entry = ttk.Entry(dialog, textvariable=api_url_var)
        api_url_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=5)
        
        # 根据类型自动填充URL
        def on_type_select(event=None):
            selected_type = type_var.get()
            if selected_type == "openai":
                api_url_var.set("https://api.openai.com/v1")
            elif selected_type == "anthropic":
                api_url_var.set("https://api.anthropic.com")
            elif selected_type == "gemini":
                api_url_var.set("")  # Gemini使用SDK，不需要URL
                
        type_combo.bind("<<ComboboxSelected>>", on_type_select)
        
        # 启用开关
        enable_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            dialog,
            text="启用服务",
            variable=enable_var
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=5, pady=5)
        
        # 服务描述
        ttk.Label(dialog, text="服务描述:").grid(row=5, column=0, sticky="ne", padx=5, pady=5)
        description_var = tk.StringVar()
        description_text = tk.Text(dialog, height=3, width=30, wrap=tk.WORD)
        description_text.grid(row=5, column=1, sticky="ew", padx=5, pady=5)
        
        # 按钮框架
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=6, column=0, columnspan=3, sticky="ew", padx=5, pady=10)
        
        # 保存和取消按钮
        def save_service():
            """保存新服务配置"""
            if not name_var.get().strip():
                messagebox.showerror("错误", "服务名称不能为空")
                return
                
            if not type_var.get():
                messagebox.showerror("错误", "必须选择服务类型")
                return
                
            if not api_key_var.get().strip():
                messagebox.showerror("错误", "API Key不能为空")
                return
                
            try:
                config = {
                    "name": name_var.get().strip(),
                    "type": type_var.get(),
                    "api_key": api_key_var.get().strip(),
                    "api_url": api_url_var.get().strip(),
                    "enabled": enable_var.get(),
                    "description": description_text.get("1.0", tk.END).strip()
                }
                
                self.service_manager.register_service(config)
                dialog.destroy()
                self.status_var.set(f"服务 {config['name']} 添加成功")
            except Exception as e:
                messagebox.showerror("错误", f"添加服务失败: {str(e)}")
                
        ttk.Button(btn_frame, text="保存", command=save_service).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side="right", padx=5)
        
        # 初始聚焦到名称输入框
        name_entry.focus_set()
        
        # 等待对话框关闭
        self.wait_window(dialog)
        
    def _delete_service(self) -> None:
        """删除选中的服务"""
        if not self.current_service:
            return
            
        if messagebox.askyesno("确认", "确定要删除选中的服务吗？"):
            try:
                self.service_manager.unregister_service(self.current_service)
                self.current_service = None
                self.status_var.set("服务已删除")
            except Exception as e:
                messagebox.showerror("错误", f"删除服务失败: {str(e)}")
                
    def _refresh_services(self) -> None:
        """刷新服务列表"""
        self._load_services()
        
        # 如果有当前选中的服务，保持选中状态
        if self.current_service:
            for item in self.service_tree.get_children():
                if self.current_service in self.service_tree.item(item)["tags"]:
                    self.service_tree.selection_set(item)
                    break 

    def _auto_load_models(self, service: ModelService) -> None:
        """自动加载模型列表，避免用户手动点击获取模型按钮"""
        try:
            # 首先尝试从服务配置中获取模型列表
            if service.models and len(service.models) > 0:
                self._update_model_list(service.models)
                self.status_var.set(f"已从配置加载模型列表: {service.name}")
                return
                
            # 如果配置中没有模型列表，尝试从API获取
            models = service.list_models()
            if models and len(models) > 0:
                # 更新服务的模型列表
                service.models = models
                
                # 如果没有当前模型，设置第一个为当前模型
                if not service.current_model and models:
                    service.current_model = models[0]
                    
                # 更新UI中的模型列表
                self._update_model_list(models)
                
                # 保存更新后的服务配置
                self.service_manager.update_service(service.service_id, service.to_dict())
                self.service_manager.save_config()
                
                self.status_var.set(f"已成功获取模型列表: {service.name}")
            else:
                self.status_var.set(f"未能获取模型列表: {service.name}")
        except Exception as e:
            logger.error(f"自动加载模型列表失败: {str(e)}")
            self.status_var.set(f"加载模型列表失败: {str(e)}")
            
            # 确保至少有一个默认选项
            self.model_combo["values"] = ["<点击获取模型列表>"]
            self.model_combo.current(0) 