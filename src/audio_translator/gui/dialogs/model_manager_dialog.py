"""
模型管理对话框，用于整合模型列表面板
"""
import tkinter as tk
from tkinter import ttk, messagebox
import logging

from ...services.core.service_registry import ServiceRegistry
from ..panels.model_list_panel import ModelListPanel


class ModelManagerDialog(tk.Toplevel):
    """模型管理对话框，用于整合模型列表面板"""
    
    def __init__(self, parent, service_manager, config_service):
        """
        初始化模型管理对话框
        
        Args:
            parent: 父窗口
            service_manager: 服务管理器实例
            config_service: 配置服务实例
        """
        super().__init__(parent)
        self.title("模型管理")
        self.geometry("700x500")
        self.minsize(600, 400)
        self.transient(parent)
        self.grab_set()
        
        self.service_manager = service_manager
        self.config_service = config_service
        self.logger = logging.getLogger(__name__)
        
        # 创建服务注册表
        self.service_registry = ServiceRegistry(config_service)
        
        self._create_ui()
        self._center_window()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_ui(self):
        """创建UI界面"""
        # 主框架
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # 顶部帮助信息
        help_frame = ttk.Frame(main_frame)
        help_frame.pack(fill='x', pady=(0, 10))
        
        help_text = """在这里管理您的AI服务和模型。您可以添加、编辑、删除和测试服务连接。
启用或禁用服务将影响其在应用中的可用性。双击列表项可以编辑服务配置。"""
        help_label = ttk.Label(help_frame, text=help_text, wraplength=680, justify='left')
        help_label.pack(fill='x')
        
        # 分隔线
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=5)
        
        # 模型列表面板
        self.model_list_panel = ModelListPanel(main_frame, self.service_manager, self.service_registry)
        self.model_list_panel.pack(fill='both', expand=True)
        
        # 底部按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(btn_frame, text="刷新", command=self._on_refresh).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="关闭", command=self._on_close).pack(side='right', padx=5)
    
    def _center_window(self):
        """居中显示窗口"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry('{}x{}+{}+{}'.format(width, height, x, y))
    
    def _on_refresh(self):
        """刷新模型列表"""
        self.model_list_panel.refresh()
    
    def _on_close(self):
        """关闭对话框"""
        try:
            # 通知应用重新加载服务
            if hasattr(self.service_manager, 'reload_services'):
                self.service_manager.reload_services()
        except Exception as e:
            self.logger.error(f"重新加载服务时发生错误: {e}")
        
        self.destroy() 