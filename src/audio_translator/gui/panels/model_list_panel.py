"""
模型列表管理面板，用于显示和管理模型
"""
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Dict, Any, Optional, List, Callable
import os

from ...services.core.service_registry import ServiceRegistry
from ..dialogs.model_config_dialog import ModelConfigDialog


class ModelListPanel(ttk.Frame):
    """模型列表管理面板，用于显示和管理模型"""
    
    def __init__(self, parent, service_manager, service_registry: ServiceRegistry):
        """
        初始化模型列表管理面板
        
        Args:
            parent: 父窗口
            service_manager: 服务管理器实例
            service_registry: 服务注册表实例
        """
        super().__init__(parent)
        self.service_manager = service_manager
        self.service_registry = service_registry
        self.logger = logging.getLogger(__name__)
        
        self._create_ui()
        self._load_icons()
        self._create_context_menu()
        self._refresh_model_list()
    
    def _load_icons(self):
        """加载图标"""
        self.icons = {}
        try:
            # 图标路径可能需要根据实际项目结构调整
            icon_path = os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'icons')
            
            # 加载各种图标
            icon_files = {
                'add': 'add.png',
                'edit': 'edit.png',
                'delete': 'delete.png',
                'refresh': 'refresh.png',
                'enabled': 'enabled.png',
                'disabled': 'disabled.png'
            }
            
            for name, file in icon_files.items():
                icon_path_full = os.path.join(icon_path, file)
                if os.path.exists(icon_path_full):
                    self.icons[name] = tk.PhotoImage(file=icon_path_full)
                    # 缩放图标
                    self.icons[name] = self.icons[name].subsample(2, 2)
        except Exception as e:
            self.logger.warning(f"加载图标失败: {e}")
    
    def _create_ui(self):
        """创建UI界面"""
        # 头部工具栏
        toolbar_frame = ttk.Frame(self)
        toolbar_frame.pack(fill='x', padx=5, pady=5)
        
        # 标题
        ttk.Label(toolbar_frame, text="模型管理", font=('', 12, 'bold')).pack(side='left')
        
        # 工具按钮
        self.btn_frame = ttk.Frame(toolbar_frame)
        self.btn_frame.pack(side='right')
        
        # 添加、编辑、删除、刷新按钮将在_load_icons后添加
        
        # 模型列表（使用Treeview）
        list_frame = ttk.Frame(self)
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 创建带滚动条的树形控件
        self.columns = ('名称', '类型', '状态', 'ID')
        self.model_tree = ttk.Treeview(list_frame, columns=self.columns, show='headings', height=15)
        
        # 设置列
        for col in self.columns:
            self.model_tree.heading(col, text=col)
            if col == 'ID':  # 隐藏ID列
                self.model_tree.column(col, width=0, stretch=tk.NO)
            elif col == '名称':
                self.model_tree.column(col, width=150)
            elif col == '类型':
                self.model_tree.column(col, width=100)
            else:
                self.model_tree.column(col, width=80)
        
        # 添加滚动条
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.model_tree.yview)
        hsb = ttk.Scrollbar(list_frame, orient="horizontal", command=self.model_tree.xview)
        self.model_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # 布局
        self.model_tree.grid(column=0, row=0, sticky='nsew')
        vsb.grid(column=1, row=0, sticky='ns')
        hsb.grid(column=0, row=1, sticky='ew')
        
        # 配置list_frame的网格权重
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # 绑定事件
        self.model_tree.bind('<Double-1>', self._on_model_double_click)
        self.model_tree.bind('<Button-3>', self._on_right_click)
    
    def _add_toolbar_buttons(self):
        """添加工具栏按钮"""
        # 清除现有按钮
        for widget in self.btn_frame.winfo_children():
            widget.destroy()
        
        # 添加按钮
        buttons = [
            ('添加', self.icons.get('add'), self._on_add_model),
            ('编辑', self.icons.get('edit'), self._on_edit_model),
            ('删除', self.icons.get('delete'), self._on_delete_model),
            ('刷新', self.icons.get('refresh'), self._refresh_model_list)
        ]
        
        for text, icon, command in buttons:
            btn = ttk.Button(self.btn_frame, text=text, image=icon, compound='left' if icon else 'none',
                            command=command)
            btn.pack(side='left', padx=2)
            if icon:
                btn.image = icon  # 保持引用
    
    def _create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="编辑", command=self._on_edit_model)
        self.context_menu.add_command(label="删除", command=self._on_delete_model)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="启用/禁用", command=self._on_toggle_enabled)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="测试连接", command=self._on_test_connection)
    
    def _on_right_click(self, event):
        """处理右键点击事件"""
        item = self.model_tree.identify_row(event.y)
        if item:
            # 选中被点击的项
            self.model_tree.selection_set(item)
            # 显示上下文菜单
            self.context_menu.post(event.x_root, event.y_root)
    
    def _refresh_model_list(self):
        """刷新模型列表"""
        try:
            # 清空现有项
            for item in self.model_tree.get_children():
                self.model_tree.delete(item)
            
            # 获取所有服务并添加到列表
            services = self.service_registry.get_all_services()
            for service_id, config in services.items():
                status = "启用" if config.get('enabled', True) else "禁用"
                
                # 添加到树形控件
                self.model_tree.insert("", "end", values=(
                    config.get('name', '未命名'),
                    config.get('type', '未知'),
                    status,
                    service_id  # ID列
                ))
            
            # 隐藏ID列
            self.model_tree["displaycolumns"] = self.columns[:-1]
            
            # 添加工具栏按钮（延迟到图标加载后）
            self._add_toolbar_buttons()
            
        except Exception as e:
            self.logger.error(f"刷新模型列表失败: {e}")
            messagebox.showerror("错误", f"刷新模型列表失败: {str(e)}")
    
    def _get_selected_service_id(self):
        """获取选中的服务ID"""
        selection = self.model_tree.selection()
        if not selection:
            messagebox.showinfo("提示", "请先选择一个模型")
            return None
        
        item = selection[0]
        values = self.model_tree.item(item, "values")
        if len(values) >= 4:
            return values[3]  # ID在第4列
        return None
    
    def _on_model_double_click(self, event):
        """处理模型项双击事件"""
        self._on_edit_model()
    
    def _on_add_model(self):
        """添加新模型"""
        try:
            # 打开模型配置对话框
            dialog = ModelConfigDialog(
                self.winfo_toplevel(),
                self.service_manager,
                callback=self._on_model_saved
            )
            # 等待对话框关闭
            self.wait_window(dialog)
        except Exception as e:
            self.logger.error(f"添加模型时发生错误: {e}")
            messagebox.showerror("错误", f"添加模型时发生错误: {str(e)}")
    
    def _on_edit_model(self):
        """编辑模型"""
        try:
            service_id = self._get_selected_service_id()
            if not service_id:
                return
            
            # 获取服务配置
            service_config = self.service_registry.get_service(service_id)
            if not service_config:
                messagebox.showerror("错误", "找不到模型配置")
                return
            
            # 打开编辑对话框
            dialog = ModelConfigDialog(
                self.winfo_toplevel(),
                self.service_manager,
                service_config,
                callback=self._on_model_saved
            )
            # 等待对话框关闭
            self.wait_window(dialog)
        except Exception as e:
            self.logger.error(f"编辑模型时发生错误: {e}")
            messagebox.showerror("错误", f"编辑模型时发生错误: {str(e)}")
    
    def _on_delete_model(self):
        """删除模型"""
        try:
            service_id = self._get_selected_service_id()
            if not service_id:
                return
            
            # 获取服务名称
            service_config = self.service_registry.get_service(service_id)
            if not service_config:
                messagebox.showerror("错误", "找不到模型配置")
                return
            
            service_name = service_config.get('name', '未命名')
            
            # 询问用户确认
            if not messagebox.askyesno("确认删除", f"确定要删除模型 '{service_name}' 吗？"):
                return
            
            # 删除服务
            if self.service_registry.unregister_service(service_id):
                self._refresh_model_list()
                messagebox.showinfo("成功", f"已删除模型 '{service_name}'")
            else:
                messagebox.showerror("错误", f"删除模型 '{service_name}' 失败")
        except Exception as e:
            self.logger.error(f"删除模型时发生错误: {e}")
            messagebox.showerror("错误", f"删除模型时发生错误: {str(e)}")
    
    def _on_toggle_enabled(self):
        """切换模型启用/禁用状态"""
        try:
            service_id = self._get_selected_service_id()
            if not service_id:
                return
            
            # 获取服务配置
            service_config = self.service_registry.get_service(service_id)
            if not service_config:
                messagebox.showerror("错误", "找不到模型配置")
                return
            
            # 切换启用状态
            service_config['enabled'] = not service_config.get('enabled', True)
            
            # 更新服务
            if self.service_registry.update_service(service_id, service_config):
                self._refresh_model_list()
                status = "启用" if service_config['enabled'] else "禁用"
                messagebox.showinfo("成功", f"已{status}模型 '{service_config.get('name', '未命名')}'")
            else:
                messagebox.showerror("错误", f"更新模型 '{service_config.get('name', '未命名')}' 状态失败")
        except Exception as e:
            self.logger.error(f"切换模型状态时发生错误: {e}")
            messagebox.showerror("错误", f"切换模型状态时发生错误: {str(e)}")
    
    def _on_test_connection(self):
        """测试连接"""
        try:
            service_id = self._get_selected_service_id()
            if not service_id:
                return
            
            # 获取服务配置
            service_config = self.service_registry.get_service(service_id)
            if not service_config:
                messagebox.showerror("错误", "找不到模型配置")
                return
            
            # 创建服务实例
            service = self.service_manager.create_service(service_config)
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
            self.logger.error(f"测试连接时发生错误: {e}")
            messagebox.showerror("错误", f"测试连接时发生错误: {str(e)}")
    
    def _on_model_saved(self, config):
        """模型保存回调函数"""
        try:
            if config.get('id'):
                # 更新现有模型
                if self.service_registry.update_service(config['id'], config):
                    self._refresh_model_list()
                    messagebox.showinfo("成功", f"已更新模型 '{config.get('name', '未命名')}'")
                else:
                    messagebox.showerror("错误", f"更新模型 '{config.get('name', '未命名')}' 失败")
            else:
                # 注册新模型
                service_id = self.service_registry.register_service(config)
                if service_id:
                    self._refresh_model_list()
                    messagebox.showinfo("成功", f"已添加模型 '{config.get('name', '未命名')}'")
                else:
                    messagebox.showerror("错误", f"添加模型 '{config.get('name', '未命名')}' 失败")
        except Exception as e:
            self.logger.error(f"保存模型时发生错误: {e}")
            messagebox.showerror("错误", f"保存模型时发生错误: {str(e)}")
    
    def refresh(self):
        """刷新面板"""
        self._refresh_model_list() 