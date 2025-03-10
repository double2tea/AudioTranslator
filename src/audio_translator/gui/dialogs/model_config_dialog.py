"""
模型配置对话框，用于添加和编辑模型配置
"""
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Dict, Any, Optional, List, Callable


class ModelConfigDialog(tk.Toplevel):
    """模型配置对话框，用于添加和编辑模型配置"""
    
    def __init__(self, parent, service_manager, model_data=None, callback: Optional[Callable] = None):
        """
        初始化模型配置对话框
        
        Args:
            parent: 父窗口
            service_manager: 服务管理器实例
            model_data: 要编辑的模型数据，None表示新建
            callback: 保存完成后的回调函数
        """
        super().__init__(parent)
        self.title("模型配置")
        self.geometry("550x450")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.service_manager = service_manager
        self.model_data = model_data or {}
        self.callback = callback
        self.result = None
        self.logger = logging.getLogger(__name__)
        
        # 尝试应用主题
        try:
            # 尝试获取主题服务
            theme_service = service_manager.get_service('theme_service')
            if theme_service:
                # 应用主题到对话框
                theme_service.setup_dialog_theme(self)
        except Exception as e:
            self.logger.warning(f"应用主题到对话框失败: {e}")
        
        self._create_ui()
        self._center_window()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
    def _create_ui(self):
        """创建UI界面"""
        main_frame = ttk.Frame(self, padding="20 20 20 20")
        main_frame.pack(fill='both', expand=True)
        
        # 基本信息区域
        info_frame = ttk.LabelFrame(main_frame, text="基本信息")
        info_frame.pack(fill='x', pady=(0, 15))
        
        # 名称
        ttk.Label(info_frame, text="名称:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.name_var = tk.StringVar(value=self.model_data.get('name', ''))
        ttk.Entry(info_frame, textvariable=self.name_var, width=40).grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        
        # 类型
        ttk.Label(info_frame, text="类型:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.type_var = tk.StringVar(value=self.model_data.get('type', ''))
        type_combo = ttk.Combobox(info_frame, textvariable=self.type_var, width=40)
        type_combo['values'] = ['openai', 'anthropic', 'google', 'zhipuai', 'baidu', 'xunfei']
        type_combo.grid(row=1, column=1, sticky='ew', padx=5, pady=5)
        
        # API设置区域
        api_frame = ttk.LabelFrame(main_frame, text="API设置")
        api_frame.pack(fill='x', pady=(0, 15))
        
        # API密钥
        ttk.Label(api_frame, text="API密钥:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.api_key_var = tk.StringVar(value=self.model_data.get('api_key', ''))
        self.api_key_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, width=40, show="*")
        self.api_key_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        
        # 显示/隐藏密钥按钮
        self.show_key = tk.BooleanVar(value=False)
        ttk.Checkbutton(api_frame, text="显示", variable=self.show_key, 
                        command=self._toggle_key_visibility).grid(row=0, column=2)
        
        # API地址
        ttk.Label(api_frame, text="API地址:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.api_url_var = tk.StringVar(value=self.model_data.get('api_url', ''))
        ttk.Entry(api_frame, textvariable=self.api_url_var, width=40).grid(row=1, column=1, columnspan=2, sticky='ew', padx=5, pady=5)
        
        # 模型设置区域
        model_frame = ttk.LabelFrame(main_frame, text="模型设置")
        model_frame.pack(fill='x')
        
        # 默认模型
        ttk.Label(model_frame, text="默认模型:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.default_model_var = tk.StringVar(value=self.model_data.get('default_model', ''))
        ttk.Entry(model_frame, textvariable=self.default_model_var, width=40).grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        
        # 刷新模型列表按钮
        ttk.Button(model_frame, text="获取可用模型", command=self._fetch_models).grid(row=0, column=2, padx=5, pady=5)
        
        # 启用开关
        self.enabled_var = tk.BooleanVar(value=self.model_data.get('enabled', True))
        ttk.Checkbutton(model_frame, text="启用该服务", variable=self.enabled_var).grid(row=1, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill='x', pady=(15, 0))
        
        ttk.Button(btn_frame, text="测试连接", command=self._test_connection).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="取消", command=self._on_close).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="保存", command=self._save_model).pack(side='right', padx=5)
    
    def _toggle_key_visibility(self):
        """切换API密钥的可见性"""
        self.api_key_entry.config(show='' if self.show_key.get() else '*')
    
    def _center_window(self):
        """居中显示窗口"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry('{}x{}+{}+{}'.format(width, height, x, y))
    
    def _fetch_models(self):
        """获取可用模型列表"""
        try:
            # 创建临时服务实例来获取模型列表
            service_type = self.type_var.get()
            if not service_type:
                messagebox.showerror("错误", "请先选择服务类型")
                return
            
            # 准备临时配置
            temp_config = {
                'name': self.name_var.get() or 'temp',
                'type': service_type,
                'api_key': self.api_key_var.get(),
                'api_url': self.api_url_var.get() or None
            }
            
            # 创建临时服务实例
            service = self.service_manager.create_service(temp_config)
            if not service:
                messagebox.showerror("错误", "创建服务实例失败")
                return
                
            # 调用服务获取模型列表
            self.update_idletasks()
            messagebox.showinfo("提示", "正在获取模型列表，请稍候...")
            models = service.list_models()
            
            if not models:
                messagebox.showinfo("提示", "未找到可用模型")
                return
                
            # 显示模型列表对话框
            model_window = tk.Toplevel(self)
            model_window.title("可用模型")
            model_window.geometry("300x400")
            model_window.transient(self)
            model_window.grab_set()
            
            # 创建列表框和滚动条
            frame = ttk.Frame(model_window)
            frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            scrollbar = ttk.Scrollbar(frame)
            scrollbar.pack(side='right', fill='y')
            
            listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set)
            listbox.pack(fill='both', expand=True)
            
            scrollbar.config(command=listbox.yview)
            
            # 添加模型
            for model in models:
                listbox.insert(tk.END, model)
            
            # 添加选择按钮
            def select_model():
                selection = listbox.curselection()
                if selection:
                    self.default_model_var.set(listbox.get(selection[0]))
                    model_window.destroy()
            
            ttk.Button(model_window, text="选择", command=select_model).pack(pady=10)
            
        except Exception as e:
            self.logger.error(f"获取模型列表失败: {e}")
            messagebox.showerror("错误", f"获取模型列表失败: {str(e)}")
    
    def _test_connection(self):
        """测试连接到服务"""
        try:
            service_type = self.type_var.get()
            if not service_type:
                messagebox.showerror("错误", "请先选择服务类型")
                return
            
            # 准备临时配置
            temp_config = {
                'name': self.name_var.get() or 'temp',
                'type': service_type,
                'api_key': self.api_key_var.get(),
                'api_url': self.api_url_var.get() or None
            }
            
            # 创建临时服务实例
            service = self.service_manager.create_service(temp_config)
            if not service:
                messagebox.showerror("错误", "创建服务实例失败")
                return
                
            # 测试连接
            self.update_idletasks()
            messagebox.showinfo("提示", "正在测试连接，请稍候...")
            result = service.test_connection()
            
            if result.get('status') == 'success':
                messagebox.showinfo("成功", result.get('message', '连接成功'))
            else:
                messagebox.showerror("错误", result.get('message', '连接失败'))
            
        except Exception as e:
            self.logger.error(f"测试连接失败: {e}")
            messagebox.showerror("错误", f"测试连接失败: {str(e)}")
    
    def _save_model(self):
        """保存模型配置"""
        try:
            # 验证必填字段
            name = self.name_var.get().strip()
            service_type = self.type_var.get().strip()
            api_key = self.api_key_var.get().strip()
            
            if not name:
                messagebox.showerror("错误", "请输入名称")
                return
            
            if not service_type:
                messagebox.showerror("错误", "请选择服务类型")
                return
            
            if not api_key:
                messagebox.showerror("错误", "请输入API密钥")
                return
            
            # 创建配置
            config = {
                'id': self.model_data.get('id'),  # 保留原ID，如果有的话
                'name': name,
                'type': service_type,
                'api_key': api_key,
                'api_url': self.api_url_var.get().strip() or None,
                'default_model': self.default_model_var.get().strip() or None,
                'enabled': self.enabled_var.get()
            }
            
            self.result = config
            
            # 调用回调函数
            if self.callback:
                self.callback(config)
                
            self.destroy()
            
        except Exception as e:
            self.logger.error(f"保存模型配置失败: {e}")
            messagebox.showerror("错误", f"保存模型配置失败: {str(e)}")
    
    def _on_close(self):
        """关闭对话框"""
        self.result = None
        self.destroy() 