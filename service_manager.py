import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import requests
import threading
import time
import logging
import copy
from theme_manager import ThemeManager
import sys

class ServiceManagerWindow:
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

    def __init__(self, parent, config):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.config = config
        self.has_changes = False
        
        # 设置 macOS 窗口样式
        if sys.platform == 'darwin':
            try:
                # 设置为模态对话框
                self.window.transient(parent)
                self.window.grab_set()
                
                # 绑定关闭事件
                self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
                self.window.bind('<Escape>', lambda e: self.on_closing())
                
                # 禁用调整大小
                self.window.resizable(False, False)
            except Exception as e:
                logging.warning(f"设置 macOS 窗口样式失败: {e}")
        
        # 设置窗口属性
        self.window.title("翻译服务管理")
        self.window.minsize(800, 600)
        
        # 获取父窗口大小的80%作为初始大小
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        width = int(parent_width * 0.8)
        height = int(parent_height * 0.8)
        
        # 设置窗口位置为屏幕中央
        x = parent.winfo_x() + (parent_width - width) // 2
        y = parent.winfo_y() + (parent_height - height) // 2
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        
        # 初始化组件变量
        self.service_list = None
        self.model_list = None
        self.prompt_combo = None
        self.enable_var = tk.BooleanVar(value=True)
        self.api_key_var = tk.StringVar()
        self.api_url_var = tk.StringVar()
        self.prompt_var = tk.StringVar(value="双语音效描述")
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.window, padding=15)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建分隔窗口
        self.paned = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)
        
        # 创建组件
        self.create_service_list()
        self.create_config_panel()
        self.create_toolbar()
        
        # 确保组件已创建
        self.window.update_idletasks()
        
        # 加载数据
        self.load_services()
        
        # 绑定事件
        if self.service_list:
            self.service_list.bind('<<TreeviewSelect>>', self.on_service_select)
        if self.prompt_combo:
            self.prompt_combo.bind('<<ComboboxSelected>>', self.on_prompt_select)

    def create_service_list(self):
        """创建服务列表"""
        try:
            # 左侧面板
            left_frame = ttk.Frame(self.paned, width=300)
            left_frame.pack_propagate(False)
            
            # 标题和按钮区域
            header = ttk.Frame(left_frame)
            header.pack(fill=tk.X, pady=(0, 10))
            
            ttk.Label(header, text="翻译服务", style='Title.TLabel').pack(side=tk.LEFT)
            
            # 按钮区域
            btn_frame = ttk.Frame(header)
            btn_frame.pack(side=tk.RIGHT)
            
            ttk.Button(
                btn_frame, 
                text="添加服务", 
                command=self.add_service, 
                width=8
            ).pack(side=tk.LEFT, padx=(0, 5))
            
            ttk.Button(
                btn_frame, 
                text="删除服务", 
                command=self.delete_service, 
                width=8
            ).pack(side=tk.LEFT)
            
            # 创建服务列表
            tree_frame = ttk.Frame(left_frame)
            tree_frame.pack(fill=tk.BOTH, expand=True)
            
            self.service_list = ttk.Treeview(
                tree_frame,
                columns=("名称", "状态"),
                show="headings",
                height=20
            )
            
            # 配置列
            self.service_list.heading("名称", text="服务名称")
            self.service_list.heading("状态", text="状态")
            self.service_list.column("名称", width=180)
            self.service_list.column("状态", width=80)
            
            # 添加滚动条
            scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.service_list.yview)
            self.service_list.configure(yscrollcommand=scrollbar.set)
            
            # 布局
            self.service_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 添加到分隔窗口
            self.paned.add(left_frame)
            
        except Exception as e:
            logging.error(f"创建服务列表失败: {e}")
            if self.window and self.window.winfo_exists():
                messagebox.showerror("错误", f"创建服务列表失败: {str(e)}")

    def create_config_panel(self):
        """创建右侧配置面板"""
        # 创建右侧面板
        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame)
        
        # 创建滚动区域
        canvas = tk.Canvas(right_frame)
        scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 创建配置区域
        self.create_basic_settings(scrollable_frame)
        self.create_api_settings(scrollable_frame)
        self.create_prompt_settings(scrollable_frame)
        self.create_model_settings(scrollable_frame)
        
        # 布局滚动区域
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def create_toolbar(self):
        """创建底部工具栏"""
        toolbar = ttk.Frame(self.main_frame)
        toolbar.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            toolbar,
            text="保存配置",
            command=self.save_all_changes,
            width=15
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            toolbar,
            text="测试连接",
            command=self.test_connection,
            width=15
        ).pack(side=tk.RIGHT)

    def create_basic_settings(self, parent):
        """创建基本设置区域"""
        basic_frame = ttk.LabelFrame(parent, text="基本设置", padding=10)
        basic_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 服务启用开关
        self.enable_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            basic_frame,
            text="启用此服务",
            variable=self.enable_var
        ).pack(anchor=tk.W)

    def create_api_settings(self, parent):
        """创建API配置区域"""
        api_frame = ttk.LabelFrame(parent, text="API 配置", padding=10)
        api_frame.pack(fill=tk.X, pady=(0, 10))
        
        # API Key 输入
        key_frame = ttk.Frame(api_frame)
        key_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(key_frame, text="API Key:").pack(side=tk.LEFT)
        
        self.api_key_var = tk.StringVar()
        self.key_entry = ttk.Entry(
            key_frame,
            textvariable=self.api_key_var,
            width=50
        )
        self.key_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # API URL 输入
        url_frame = ttk.Frame(api_frame)
        url_frame.pack(fill=tk.X)
        
        ttk.Label(url_frame, text="API URL:").pack(side=tk.LEFT)
        
        self.api_url_var = tk.StringVar()
        self.url_entry = ttk.Entry(
            url_frame,
            textvariable=self.api_url_var,
            width=50
        )
        self.url_entry.pack(side=tk.LEFT, padx=(10, 0))

    def create_prompt_settings(self, parent):
        """创建提示词配置区域"""
        prompt_frame = ttk.LabelFrame(parent, text="提示词配置", padding=10)
        prompt_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 提示词模板选择
        template_frame = ttk.Frame(prompt_frame)
        template_frame.pack(fill=tk.X)
        
        ttk.Label(template_frame, text="提示词模板:").pack(side=tk.LEFT)
        
        # 获取所有可用的 prompt 模板
        prompts = self.config.get_prompt_templates()
        self.prompt_combo = ttk.Combobox(
            template_frame,
            textvariable=self.prompt_var,
            values=list(prompts.keys()),
            state="readonly",
            width=30
        )
        self.prompt_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        # 提示词管理按钮
        ttk.Button(
            template_frame,
            text="保存为新模板",
            command=self.save_as_prompt
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Button(
            template_frame,
            text="删除模板",
            command=self.delete_prompt
        ).pack(side=tk.LEFT, padx=5)
        
        # 提示词编辑区域
        self.prompt_text = tk.Text(
            prompt_frame,
            height=10,
            width=50,
            wrap=tk.WORD
        )
        self.prompt_text.pack(fill=tk.X, pady=(10, 0))
        
        # 加载默认提示词
        default_prompt = self.config.get_ucs_prompt()
        self.prompt_text.insert("1.0", default_prompt)

    def create_model_settings(self, parent):
        """创建模型配置区域"""
        model_frame = ttk.LabelFrame(parent, text="模型配置", padding=10)
        model_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 创建模型列表
        list_container = ttk.Frame(model_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        columns = ("名称", "描述")
        self.model_list = ttk.Treeview(
            list_container,
            columns=columns,
            show="headings",
            height=5
        )
        
        # 配置列
        self.model_list.heading("名称", text="模型名称")
        self.model_list.heading("描述", text="描述")
        self.model_list.column("名称", width=150)
        self.model_list.column("描述", width=250)
        
        # 添加滚动条
        model_scrollbar = ttk.Scrollbar(
            list_container,
            orient=tk.VERTICAL,
            command=self.model_list.yview
        )
        
        self.model_list.configure(yscrollcommand=model_scrollbar.set)
        
        self.model_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        model_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 模型管理按钮
        model_btn_frame = ttk.Frame(model_frame)
        model_btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            model_btn_frame,
            text="添加模型",
            command=self.add_model
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            model_btn_frame,
            text="删除模型",
            command=self.delete_model
        ).pack(side=tk.LEFT)

    def save_config(self):
        """保存当前服务的配置"""
        selected = self.service_list.selection()
        if not selected:
            return
        
        service_id = self.service_list.item(selected[0])["text"]
        services = self.config.get("TRANSLATION_SERVICES", {})
        
        if service_id in services:
            service = services[service_id]
            
            # 更新基本设置
            service["enabled"] = self.enable_var.get()
            
            # 更新API设置
            service["api_key"] = self.api_key_var.get().strip()
            service["api_url"] = self.api_url_var.get().strip()
            service["headers"] = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {service['api_key']}"
            }
            
            # 更新提示词设置
            current_template = self.prompt_var.get()
            current_prompt = self.prompt_text.get("1.0", tk.END).strip()
            
            if current_template == "默认UCS提示词":
                service["custom_prompt"] = False
                service["prompt_template"] = self.config.get_ucs_prompt()
            else:
                service["custom_prompt"] = True
                service["prompt_template"] = current_prompt
            
            # 保存配置
            self.config.set("TRANSLATION_SERVICES", services)
            self.config.save()
            
            messagebox.showinfo("成功", "配置已保存")

    def test_connection(self):
        """测试API连接"""
        selected = self.service_list.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个服务")
            return
        
        service_id = self.service_list.item(selected[0])["text"]
        api_key = self.api_key_var.get().strip()
        api_url = self.api_url_var.get().strip()
        
        if not api_key or not api_url:
            messagebox.showwarning("警告", "请填写 API Key 和 API URL")
            return
        
        try:
            # 获取服务配置
            services = self.config.get("TRANSLATION_SERVICES", {})
            if service_id not in services:
                messagebox.showerror("错误", "服务配置不存在")
                return
            
            service = services[service_id]
            
            # 显示测试对话框
            self.show_test_dialog(api_url, api_key, service_id)
            
        except Exception as e:
            logging.error(f"测试连接失败: {str(e)}")
            messagebox.showerror("错误", f"测试连接失败: {str(e)}")

    def show_test_dialog(self, api_url, api_key, service_id):
        """显示测试对话框"""
        dialog = tk.Toplevel(self.window)
        dialog.title("API连接测试")
        dialog.geometry("600x400")
        dialog.transient(self.window)
        dialog.grab_set()
        
        # 设置 macOS 窗口样式
        if sys.platform == 'darwin':
            try:
                dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
                dialog.bind('<Escape>', lambda e: dialog.destroy())
            except Exception as e:
                logging.warning(f"设置 macOS 窗口样式失败: {e}")
        
        # 使用 ThemeManager 设置主题
        ThemeManager.setup_dialog_theme(dialog)
        
        # 创建测试界面
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 模型选择
        model_frame = ttk.Frame(main_frame)
        model_frame.pack(fill=tk.X, pady=(0,10))
        
        ttk.Label(model_frame, text="测试模型:").pack(side=tk.LEFT)
        model_combo = ttk.Combobox(
            model_frame,
            values=[m["name"] for m in self.get_current_models()],
            state="readonly",
            width=30
        )
        model_combo.pack(side=tk.LEFT, padx=5)
        if model_combo["values"]:
            model_combo.set(model_combo["values"][0])
        
        # 测试文本输入
        ttk.Label(main_frame, text="测试文本:").pack(anchor=tk.W)
        test_text = ttk.Entry(main_frame, width=50)
        test_text.insert(0, "Hello, this is a test message.")
        test_text.pack(fill=tk.X, pady=(0,10))
        
        # 响应显示
        ttk.Label(main_frame, text="响应结果:").pack(anchor=tk.W)
        response_text = tk.Text(main_frame, height=10, width=50)
        response_text.pack(fill=tk.BOTH, expand=True)
        
        def run_test():
            model = model_combo.get()
            text = test_text.get()
            
            if not model or not text:
                messagebox.showwarning("警告", "请选择模型并输入测试文本")
                return
            
            try:
                response_text.delete("1.0", tk.END)
                response_text.insert("1.0", "正在测试...\n")
                dialog.update()
                
                # 根据不同服务配置请求头
                headers = {
                    "Content-Type": "application/json"
                }
                
                # 硅基流动 API 特殊处理
                if "moonshot" in service_id:
                    headers["Authorization"] = f"Bearer {api_key}"
                else:
                    headers["Authorization"] = f"Bearer {api_key}"
                
                # 构建请求数据
                data = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": text}
                    ]
                }
                
                # 发送请求
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=data,
                    timeout=30
                )
                
                # 显示完整响应
                response_text.delete("1.0", tk.END)
                if response.status_code == 200:
                    result = response.json()
                    
                    # 尝试提取响应内容
                    content = None
                    if "choices" in result and result["choices"]:
                        content = result["choices"][0].get("message", {}).get("content")
                    
                    if content:
                        response_text.insert("1.0", f"测试成功!\n\n响应内容:\n{content}\n\n完整响应:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
                    else:
                        response_text.insert("1.0", f"无法解析响应内容\n\n完整响应:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
                else:
                    response_text.insert("1.0", f"测试失败!\n\n状态码: {response.status_code}\n响应内容:\n{response.text}")
                
            except Exception as e:
                response_text.delete("1.0", tk.END)
                response_text.insert("1.0", f"测试出错: {str(e)}")
                logging.error(f"API测试失败: {str(e)}")
        
        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10,0))
        
        ttk.Button(btn_frame, text="运行测试", command=run_test).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=dialog.destroy).pack(side=tk.RIGHT)

    def load_services(self):
        """加载翻译服务列表"""
        try:
            # 确保组件已创建
            if not hasattr(self, 'service_list') or not self.service_list:
                logging.warning("服务列表组件未创建")
                return
            
            # 获取所有服务
            services = self.config.get("TRANSLATION_SERVICES", {})
            
            # 更新服务列表
            for item in self.service_list.get_children():
                self.service_list.delete(item)
            
            for service_id, service in services.items():
                status = "启用" if service.get("enabled", True) else "禁用"
                self.service_list.insert(
                    "",
                    "end",
                    text=service_id,
                    values=(service.get("name", ""), status)
                )
            
            # 选中当前服务
            current = self.config.get("TRANSLATION_SERVICE")
            if current:
                for item in self.service_list.get_children():
                    if self.service_list.item(item)["text"] == current:
                        self.service_list.selection_set(item)
                        self.service_list.see(item)
                        self.on_service_select(None)
                        break
                    
        except Exception as e:
            logging.error(f"加载服务列表失败: {str(e)}")
            if self.window and self.window.winfo_exists():
                messagebox.showerror("错误", f"加载服务列表失败: {str(e)}")

    def toggle_service(self):
        """切换服务启用状态"""
        selected = self.service_list.selection()
        if not selected:
            return
        
        service_id = self.service_list.item(selected[0])["text"]
        services = self.config.get("TRANSLATION_SERVICES", {})
        
        if service_id in services:
            services[service_id]["enabled"] = self.enable_var.get()
            self.config.set("TRANSLATION_SERVICES", services)
            
            # 更新列表显示
            status = "启用" if self.enable_var.get() else "禁用"
            self.service_list.set(selected[0], "状态", status)

    def on_service_select(self, event=None):
        """处理服务选择事件"""
        selected = self.service_list.selection()
        if not selected:
            return
        
        service_id = self.service_list.item(selected[0])["text"]
        services = self.config.get("TRANSLATION_SERVICES", {})
        
        if service_id in services:
            service = services[service_id]
            
            # 更新基本设置
            self.enable_var.set(service.get("enabled", True))
            
            # 更新API设置
            self.api_key_var.set(service.get("api_key", ""))
            self.api_url_var.set(service.get("api_url", ""))
            
            # 更新提示词设置
            current_template = self.prompt_var.get()
            current_prompt = self.prompt_text.get("1.0", tk.END).strip()
            
            if current_template == "默认UCS提示词":
                self.prompt_var.set("默认UCS提示词")
                self.prompt_text.delete("1.0", tk.END)
                self.prompt_text.insert("1.0", self.config.get_ucs_prompt())
            else:
                self.prompt_var.set(current_template)
                self.prompt_text.delete("1.0", tk.END)
                self.prompt_text.insert("1.0", current_prompt)
            
            # 加载模型列表
            self.load_models(service)

    def reset_services(self):
        """重置所有服务配置"""
        if messagebox.askyesno("确认", "确定要重置所有服务配置吗？这将恢复所有默认服务。"):
            # 获取默认配置
            default_config = self.config._get_default_config()
            
            # 更新服务配置
            self.config.set("TRANSLATION_SERVICES", default_config["TRANSLATION_SERVICES"])
            
            # 刷新列表
            self.load_services()
            messagebox.showinfo("成功", "服务配置已重置")

    def save_as_prompt(self):
        """将当前提示词保存为新模板"""
        name = simpledialog.askstring("保存模板", "请输入模板名称:")
        if name:
            if name == "默认UCS提示词":
                messagebox.showerror("错误", "不能使用保留的模板名称")
                return
            
            prompts = self.config.get("PROMPT_TEMPLATES", {})
            prompts[name] = self.prompt_text.get("1.0", tk.END).strip()
            self.config.set("PROMPT_TEMPLATES", prompts)
            
            # 更新下拉列表
            template_options = ["默认UCS提示词"] + list(prompts.keys())
            self.prompt_combo["values"] = template_options
            self.prompt_var.set(name)
            
            # 保存配置
            self.config.save()
            messagebox.showinfo("成功", "提示词模板已保存")

    def delete_prompt(self):
        """删除当前提示词模板"""
        current = self.prompt_var.get()
        if current not in ["默认UCS提示词", "自定义模板"]:
            if messagebox.askyesno("确认", f"确定要删除模板 {current} 吗？"):
                prompts = self.config.get("PROMPT_TEMPLATES", {})
                if current in prompts:
                    del prompts[current]
                    self.config.set("PROMPT_TEMPLATES", prompts)
                    
                    # 更新下拉列表
                    self.prompt_combo["values"] = ["默认UCS提示词", "自定义模板"] + list(prompts.keys())
                    self.prompt_var.set("默认UCS提示词")
                    self.load_prompt_template("默认UCS提示词")

    def on_prompt_select(self, event=None):
        """处理提示词模板选择"""
        selected = self.prompt_var.get()
        
        if selected == "默认UCS提示词":
            # 加载默认UCS提示词
            default_prompt = self.config.get_ucs_prompt()
            self.prompt_text.delete("1.0", tk.END)
            self.prompt_text.insert("1.0", default_prompt)
        else:
            # 加载选中的模板
            templates = self.config.get("PROMPT_TEMPLATES", {})
            template = templates.get(selected, "")
            self.prompt_text.delete("1.0", tk.END)
            self.prompt_text.insert("1.0", template)

    def load_prompt_template(self, template_name):
        """加载指定的提示词模板"""
        self.prompt_text.delete("1.0", tk.END)
        
        if template_name == "默认UCS提示词":
            prompt = self.config.get_ucs_prompt()
        elif template_name == "自定义模板":
            return  # 保持当前内容
        else:
            prompts = self.config.get("PROMPT_TEMPLATES", {})
            prompt = prompts.get(template_name, "")
        
        self.prompt_text.insert("1.0", prompt) 

    def test_prompt(self):
        """测试当前提示词"""
        try:
            selected = self.service_list.selection()
            if not selected:
                messagebox.showwarning("警告", "请先选择一个服务")
                return
            
            test_text = self.test_input.get().strip()
            if not test_text:
                messagebox.showwarning("警告", "请输入测试文本")
                return
            
            service_id = self.service_list.item(selected[0])["text"]
            services = self.config.get("TRANSLATION_SERVICES", {})
            
            if service_id in services:
                service = services[service_id]
                
                # 获取当前配置
                api_url = self.api_url_var.get().strip()
                api_key = self.api_key_var.get().strip()
                prompt = self.prompt_text.get("1.0", tk.END).strip()
                
                # 获取当前选中的模型
                selected_model = self.model_list.selection()
                if not selected_model:
                    messagebox.showwarning("警告", "请选择一个模型")
                    return
                
                model_name = self.model_list.item(selected_model[0])["values"][0]
                
                # 准备请求数据
                # 使用 json.dumps 处理提示词中的特殊字符
                formatted_prompt = json.dumps(prompt.format(text=test_text))[1:-1]
                
                # 使用服务特定的请求格式
                if service.get("request_format"):
                    # 如果服务有特定的请求格式，使用它
                    request_format = service.get("request_format")
                    data = json.loads(
                        json.dumps(request_format)
                        .replace("{model}", model_name)
                        .replace("{prompt}", formatted_prompt)
                        .replace("{text}", test_text)
                    )
                else:
                    # 使用默认的消息格式
                    data = {
                        "model": model_name,
                        "messages": [
                            {
                                "role": "system",
                                "content": "你是一个专业的音效文件命名专家，严格遵循 UCS v8.2.1 标准。"
                            },
                            {
                                "role": "user",
                                "content": formatted_prompt
                            }
                        ]
                    }
                
                # 显示等待提示
                self.test_result.delete("1.0", tk.END)
                self.test_result.insert("1.0", "正在请求翻译...")
                self.test_result.update()
                
                # 发送请求
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # 使用配置的响应路径
                    response_path = service.get("response_path", "choices[0].message.content")
                    translated = self._get_nested_value(result, response_path.split("."))
                    
                    if translated:
                        self.test_result.delete("1.0", tk.END)
                        self.test_result.insert("1.0", f"原文: {test_text}\n翻译: {translated}")
                    else:
                        raise ValueError("API 返回数据格式不正确")
                else:
                    self.test_result.delete("1.0", tk.END)
                    self.test_result.insert("1.0", f"API返回错误: {response.status_code}\n{response.text}")
        
        except Exception as e:
            self.test_result.delete("1.0", tk.END)
            self.test_result.insert("1.0", f"错误: {str(e)}")
            logging.error(f"翻译测试失败: {str(e)}")

    def _get_nested_value(self, obj, path):
        """获取嵌套字典中的值"""
        try:
            for key in path:
                if key.endswith(']'):
                    key, index = key[:-1].split('[')
                    obj = obj[key][int(index)]
                else:
                    obj = obj[key]
            return obj
        except (KeyError, IndexError, TypeError):
            return None

    def add_service(self):
        """添加新的翻译服务"""
        dialog = tk.Toplevel(self.window)
        dialog.title("添加翻译服务")
        dialog.geometry("500x400")
        dialog.transient(self.window)
        dialog.grab_set()
        
        # 设置 macOS 窗口样式
        if sys.platform == 'darwin':
            try:
                dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
                dialog.bind('<Escape>', lambda e: dialog.destroy())
            except Exception as e:
                logging.warning(f"设置 macOS 窗口样式失败: {e}")
        
        # 使用 ThemeManager 设置主题
        ThemeManager.setup_dialog_theme(dialog)
        
        # 创建表单
        form_frame = ttk.Frame(dialog, padding=10)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(form_frame, text="服务ID:").pack(anchor=tk.W, pady=(10,0))
        id_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=id_var, width=40).pack(fill=tk.X)
        
        ttk.Label(form_frame, text="服务名称:").pack(anchor=tk.W, pady=(10,0))
        name_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=name_var, width=40).pack(fill=tk.X)
        
        ttk.Label(form_frame, text="API URL:").pack(anchor=tk.W, pady=(10,0))
        url_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=url_var, width=40).pack(fill=tk.X)
        
        ttk.Label(form_frame, text="API Key:").pack(anchor=tk.W, pady=(10,0))
        key_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=key_var, width=40).pack(fill=tk.X)
        
        # 保存服务
        def save_service():
            service_id = id_var.get().strip()
            name = name_var.get().strip()
            url = url_var.get().strip()
            key = key_var.get().strip()
            
            if not all([service_id, name, url, key]):
                messagebox.showwarning("警告", "请填写所有字段")
                return
            
            services = self.config.get("TRANSLATION_SERVICES", {})
            if service_id in services:
                messagebox.showerror("错误", "服务ID已存在")
                return
            
            # 创建新服务配置
            services[service_id] = {
                "name": name,
                "enabled": True,
                "api_url": url,
                "api_key": key,
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {key}"
                },
                "models": [],
                "prompt_template": self.config.get("DEFAULT_PROMPT_TEMPLATE"),
                "custom_prompt": False,
                "messages_format": True,
                "response_path": "choices[0].message.content"
            }
            
            self.config.set("TRANSLATION_SERVICES", services)
            self.load_services()
            self.has_changes = True
            dialog.destroy()
            messagebox.showinfo("成功", "服务已添加")
        
        # 底部按钮
        btn_frame = ttk.Frame(dialog, padding=(10,10,10,10))
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        ttk.Button(
            btn_frame,
            text="取消",
            command=dialog.destroy
        ).pack(side=tk.RIGHT, padx=(5,0))
        
        ttk.Button(
            btn_frame,
            text="保存",
            command=save_service
        ).pack(side=tk.RIGHT)

    def delete_service(self):
        """删除选中的服务"""
        selected = self.service_list.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要删除的服务")
            return
        
        service_id = self.service_list.item(selected[0])["text"]
        service_name = self.service_list.item(selected[0])["values"][0]
        
        if messagebox.askyesno("确认", f"确定要删除服务 {service_name} 吗？"):
            try:
                # 获取当前配置的副本
                services = self.config.get("TRANSLATION_SERVICES", {}).copy()
                
                # 检查是否是当前使用的服务
                current_service = self.config.get("TRANSLATION_SERVICE")
                if service_id == current_service:
                    messagebox.showerror("错误", "无法删除当前正在使用的服务")
                    return
                
                # 删除服务
                if service_id in services:
                    del services[service_id]
                    
                # 更新配置
                self.config.set("TRANSLATION_SERVICES", services)
                # 立即保存配置到文件
                self.config.save()
                
                # 清空当前选择
                self.service_list.selection_remove(selected)
                
                # 重新加载服务列表
                self.load_services()
                
                # 清空右侧面板
                self.clear_config_panel()
                
                messagebox.showinfo("成功", "服务已删除")
                
            except Exception as e:
                logging.error(f"删除服务失败: {str(e)}")
                messagebox.showerror("错误", f"删除服务失败: {str(e)}")

    def clear_config_panel(self):
        """清空配置面板"""
        self.enable_var.set(False)
        self.api_key_var.set("")
        self.api_url_var.set("")
        self.prompt_var.set("双语音效描述")
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert("1.0", self.config.get_ucs_prompt())
        
        # 清空模型列表
        for item in self.model_list.get_children():
            self.model_list.delete(item)

    def save_all_changes(self):
        """保存所有更改"""
        try:
            # 获取当前配置的副本
            services = self.config.get("TRANSLATION_SERVICES", {}).copy()
            
            # 保存当前编辑的服务配置
            selected = self.service_list.selection()
            if selected:
                service_id = self.service_list.item(selected[0])["text"]
                if service_id in services:
                    service = services[service_id]
                    self.update_service_config(service)
                    
                    # 更新配置
                    self.config.set("TRANSLATION_SERVICES", services)
                    # 立即保存到文件
                    self.config.save()
                    
                    # 重新加载服务列表以更新显示
                    self.load_services()
                    
                    self.has_changes = False
                    messagebox.showinfo("成功", "配置已保存")
                    
        except Exception as e:
            logging.error(f"保存配置失败: {str(e)}")
            messagebox.showerror("错误", f"保存配置失败: {str(e)}")

    def update_service_config(self, service):
        """更新服务配置"""
        # 更新基本设置
        service["enabled"] = self.enable_var.get()
        
        # 更新API设置
        service["api_key"] = self.api_key_var.get().strip()
        service["api_url"] = self.api_url_var.get().strip()
        service["headers"] = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {service['api_key']}"
        }
        
        # 更新提示词设置
        current_prompt = self.prompt_var.get()
        service['current_prompt'] = current_prompt
        
        # 确保 prompts 字典存在
        if 'prompts' not in service:
            service['prompts'] = self.config.get_prompt_templates()

    def get_current_models(self):
        """获取当前服务的模型列表"""
        selected = self.service_list.selection()
        if not selected:
            return []
        
        service_id = self.service_list.item(selected[0])["text"]
        services = self.config.get("TRANSLATION_SERVICES", {})
        
        if service_id in services:
            return services[service_id].get("models", []) 

    def on_closing(self):
        """处理窗口关闭事件"""
        try:
            if self.has_changes:
                if messagebox.askyesno("确认", "有未保存的更改，是否保存？"):
                    self.save_all_changes()
            
            # 解除其他绑定
            try:
                self.window.unbind_all('<Escape>')
                self.window.protocol("WM_DELETE_WINDOW", None)
            except:
                pass
            
            # 释放资源
            self.window.grab_release()
            
            # 销毁窗口
            if self.window.winfo_exists():
                self.window.destroy()
            
        except Exception as e:
            logging.error(f"关闭窗口失败: {e}")
            # 强制销毁窗口
            try:
                if self.window.winfo_exists():
                    self.window.destroy()
            except:
                pass

    def add_model(self):
        """添加新模型"""
        selected = self.service_list.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个服务")
            return
        
        dialog = tk.Toplevel(self.window)
        dialog.title("添加模型")
        dialog.geometry("400x300")
        dialog.transient(self.window)
        dialog.grab_set()
        
        # 创建表单
        form_frame = ttk.Frame(dialog, padding=10)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(form_frame, text="模型名称:").pack(anchor=tk.W, pady=(10,0))
        name_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=name_var, width=40).pack(fill=tk.X)
        
        ttk.Label(form_frame, text="描述:").pack(anchor=tk.W, pady=(10,0))
        desc_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=desc_var, width=40).pack(fill=tk.X)
        
        def save_model():
            name = name_var.get().strip()
            desc = desc_var.get().strip()
            
            if not name:
                messagebox.showwarning("警告", "请填写模型名称")
                return
            
            try:
                service_id = self.service_list.item(selected[0])["text"]
                services = self.config.get("TRANSLATION_SERVICES", {}).copy()
                
                if service_id in services:
                    service = services[service_id]
                    models = service.get("models", [])
                    
                    # 检查模型是否已存在
                    if any(m["name"] == name for m in models):
                        messagebox.showerror("错误", "模型已存在")
                        return
                    
                    # 添加新模型
                    models.append({
                        "name": name,
                        "description": desc
                    })
                    service["models"] = models
                    
                    # 如果是第一个模型，设为当前模型
                    if len(models) == 1:
                        service["current_model"] = name
                    
                    # 保存配置
                    self.config.set("TRANSLATION_SERVICES", services)
                    self.config.save()
                    
                    # 刷新显示
                    self.load_models(service)
                    dialog.destroy()
                    messagebox.showinfo("成功", "模型已添加")
                    
            except Exception as e:
                logging.error(f"添加模型失败: {str(e)}")
                messagebox.showerror("错误", f"添加模型失败: {str(e)}")
        
        # 底部按钮
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)
        
        ttk.Button(
            btn_frame,
            text="取消",
            command=dialog.destroy
        ).pack(side=tk.RIGHT, padx=(5,0))
        
        ttk.Button(
            btn_frame,
            text="保存",
            command=save_model
        ).pack(side=tk.RIGHT)

    def delete_model(self):
        """删除选中的模型"""
        selected_model = self.model_list.selection()
        if not selected_model:
            messagebox.showwarning("警告", "请先选择要删除的模型")
            return
        
        selected_service = self.service_list.selection()
        if not selected_service:
            return
        
        service_id = self.service_list.item(selected_service[0])["text"]
        model_name = self.model_list.item(selected_model[0])["values"][0]
        
        if messagebox.askyesno("确认", f"确定要删除模型 {model_name} 吗？"):
            try:
                services = self.config.get("TRANSLATION_SERVICES", {}).copy()
                
                if service_id in services:
                    service = services[service_id]
                    models = service.get("models", [])
                    
                    # 检查是否是当前使用的模型
                    if model_name == service.get("current_model"):
                        messagebox.showerror("错误", "无法删除当前正在使用的模型")
                        return
                    
                    # 删除模型
                    models = [m for m in models if m["name"] != model_name]
                    service["models"] = models
                    
                    # 保存配置
                    self.config.set("TRANSLATION_SERVICES", services)
                    self.config.save()
                    
                    # 刷新显示
                    self.load_models(service)
                    messagebox.showinfo("成功", "模型已删除")
                    
            except Exception as e:
                logging.error(f"删除模型失败: {str(e)}")
                messagebox.showerror("错误", f"删除模型失败: {str(e)}")

    def load_models(self, service=None):
        """加载当前服务的模型列表"""
        try:
            # 清空列表
            for item in self.model_list.get_children():
                self.model_list.delete(item)
            
            if service:
                models = service.get("models", [])
                current_model = service.get("current_model")
                
                for model in models:
                    item = self.model_list.insert(
                        "",
                        "end",
                        values=(
                            model["name"],
                            model.get("description", "")
                        )
                    )
                    
                    # 选中当前使用的模型
                    if model["name"] == current_model:
                        self.model_list.selection_set(item)
                        self.model_list.see(item)
                    
        except Exception as e:
            logging.error(f"加载模型列表失败: {str(e)}")

    def load_service_models(self):
        """加载当前服务的模型列表"""
        try:
            # 获取当前选中的服务
            selected = self.service_list.selection()
            if not selected:
                return
            
            # 获取服务ID
            service_id = self.service_list.item(selected[0])["text"]
            services = self.config.get("TRANSLATION_SERVICES", {})
            
            if service_id in services:
                service = services[service_id]
                models = service.get("models", [])
                
                # 更新模型列表
                for item in self.model_list.get_children():
                    self.model_list.delete(item)
                    
                for model in models:
                    self.model_list.insert(
                        "",
                        "end",
                        values=(model["name"], model.get("description", ""))
                    )
                    
                # 选中当前模型
                current_model = service.get("current_model")
                if current_model:
                    for item in self.model_list.get_children():
                        if self.model_list.item(item)["values"][0] == current_model:
                            self.model_list.selection_set(item)
                            self.model_list.see(item)
                            break
                            
        except Exception as e:
            logging.error(f"加载模型列表失败: {e}") 