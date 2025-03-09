import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import logging
from typing import Dict, Any, List, Optional, Callable

from audio_translator.services.business.naming.naming_service import NamingService

# 设置日志记录器
logger = logging.getLogger(__name__)


class NamingRuleUI:
    """命名规则选择和配置界面"""
    
    def __init__(self, root: tk.Toplevel, naming_service: NamingService):
        """
        初始化命名规则UI
        
        Args:
            root: Tkinter窗口
            naming_service: 命名服务实例
        """
        self.root = root
        self.naming_service = naming_service
        self.current_rule = None
        self.callbacks = {}  # 回调函数字典
        
        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建UI组件
        self._create_rule_selection_section()
        self._create_rule_details_section()
        self._create_test_section()
        self._create_template_editor_section()
        
        # 加载规则列表
        self._load_rules()
    
    def _create_rule_selection_section(self):
        """创建规则选择部分"""
        # 创建框架
        frame = ttk.LabelFrame(self.main_frame, text="规则选择", padding="5")
        frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建规则选择下拉框
        ttk.Label(frame, text="命名规则:").grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)
        self.rule_var = tk.StringVar()
        self.rule_combo = ttk.Combobox(frame, textvariable=self.rule_var, state="readonly", width=30)
        self.rule_combo.grid(column=1, row=0, sticky=tk.W, padx=5, pady=5)
        self.rule_combo.bind("<<ComboboxSelected>>", self._on_rule_selected)
        
        # 创建设置为默认按钮
        self.set_default_button = ttk.Button(
            frame, 
            text="设为默认", 
            command=self._on_set_default
        )
        self.set_default_button.grid(column=2, row=0, padx=5, pady=5)
        
        # 创建新建规则按钮
        ttk.Button(
            frame, 
            text="新建规则", 
            command=self._on_create_rule
        ).grid(column=3, row=0, padx=5, pady=5)
    
    def _create_rule_details_section(self):
        """创建规则详情部分"""
        # 创建框架
        frame = ttk.LabelFrame(self.main_frame, text="规则详情", padding="5")
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建规则信息显示
        self.info_frame = ttk.Frame(frame)
        self.info_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 规则名称
        ttk.Label(self.info_frame, text="名称:").grid(column=0, row=0, sticky=tk.W, padx=5, pady=2)
        self.name_var = tk.StringVar()
        ttk.Label(self.info_frame, textvariable=self.name_var).grid(column=1, row=0, sticky=tk.W, padx=5, pady=2)
        
        # 规则描述
        ttk.Label(self.info_frame, text="描述:").grid(column=0, row=1, sticky=tk.W, padx=5, pady=2)
        self.description_var = tk.StringVar()
        ttk.Label(self.info_frame, textvariable=self.description_var).grid(column=1, row=1, sticky=tk.W, padx=5, pady=2)
        
        # 所需字段
        ttk.Label(self.info_frame, text="所需字段:").grid(column=0, row=2, sticky=tk.NW, padx=5, pady=2)
        self.required_fields_text = tk.Text(self.info_frame, height=3, width=40, wrap=tk.WORD)
        self.required_fields_text.grid(column=1, row=2, sticky=tk.W, padx=5, pady=2)
        self.required_fields_text.config(state=tk.DISABLED)
    
    def _create_test_section(self):
        """创建测试部分"""
        # 创建框架
        frame = ttk.LabelFrame(self.main_frame, text="测试命名", padding="5")
        frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 原始文件名
        ttk.Label(frame, text="原始文件名:").grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)
        self.original_name_var = tk.StringVar()
        original_entry = ttk.Entry(frame, textvariable=self.original_name_var, width=40)
        original_entry.grid(column=1, row=0, sticky=tk.W, padx=5, pady=5)
        
        # 翻译后文本
        ttk.Label(frame, text="翻译文本:").grid(column=0, row=1, sticky=tk.W, padx=5, pady=5)
        self.translated_name_var = tk.StringVar()
        translated_entry = ttk.Entry(frame, textvariable=self.translated_name_var, width=40)
        translated_entry.grid(column=1, row=1, sticky=tk.W, padx=5, pady=5)
        
        # 测试按钮
        ttk.Button(
            frame, 
            text="测试", 
            command=self._on_test_naming
        ).grid(column=2, row=1, padx=5, pady=5)
        
        # 结果显示
        ttk.Label(frame, text="命名结果:").grid(column=0, row=2, sticky=tk.W, padx=5, pady=5)
        self.result_var = tk.StringVar()
        result_entry = ttk.Entry(frame, textvariable=self.result_var, width=40, state="readonly")
        result_entry.grid(column=1, row=2, sticky=tk.W, padx=5, pady=5)
    
    def _create_template_editor_section(self):
        """创建模板编辑器部分"""
        # 创建框架
        self.template_editor_frame = ttk.LabelFrame(self.main_frame, text="模板编辑器", padding="5")
        self.template_editor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 模板名称
        ttk.Label(self.template_editor_frame, text="模板名称:").grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)
        self.template_name_var = tk.StringVar()
        template_name_entry = ttk.Entry(self.template_editor_frame, textvariable=self.template_name_var, width=30)
        template_name_entry.grid(column=1, row=0, sticky=tk.W, padx=5, pady=5)
        
        # 模板描述
        ttk.Label(self.template_editor_frame, text="模板描述:").grid(column=0, row=1, sticky=tk.W, padx=5, pady=5)
        self.template_desc_var = tk.StringVar()
        template_desc_entry = ttk.Entry(self.template_editor_frame, textvariable=self.template_desc_var, width=30)
        template_desc_entry.grid(column=1, row=1, sticky=tk.W, padx=5, pady=5)
        
        # 模板内容
        ttk.Label(self.template_editor_frame, text="模板内容:").grid(column=0, row=2, sticky=tk.NW, padx=5, pady=5)
        self.template_text = scrolledtext.ScrolledText(self.template_editor_frame, height=5, width=40, wrap=tk.WORD)
        self.template_text.grid(column=1, row=2, sticky=tk.NSEW, padx=5, pady=5)
        
        # 变量帮助
        variables_frame = ttk.Frame(self.template_editor_frame)
        variables_frame.grid(column=0, row=3, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(variables_frame, text="可用变量:").pack(side=tk.LEFT, padx=2)
        
        for var in ["original_name", "translated_name", "category", "extension"]:
            var_button = ttk.Button(
                variables_frame, 
                text=var, 
                command=lambda v=var: self._insert_variable(v)
            )
            var_button.pack(side=tk.LEFT, padx=2)
        
        # 按钮区域
        button_frame = ttk.Frame(self.template_editor_frame)
        button_frame.grid(column=0, row=4, columnspan=2, sticky=tk.E, padx=5, pady=5)
        
        ttk.Button(
            button_frame, 
            text="验证模板", 
            command=self._validate_template
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="保存模板", 
            command=self._save_template
        ).pack(side=tk.LEFT, padx=5)
    
    def _load_rules(self):
        """加载命名规则列表"""
        rule_names = self.naming_service.get_available_rules()
        if not rule_names:
            self.rule_combo.config(values=["无可用规则"])
            self.rule_combo.current(0)
            return
            
        self.rule_combo.config(values=rule_names)
        
        # 设置默认选中项
        default_rule = None
        try:
            # 获取当前默认规则
            default_rule = self.naming_service.get_rule()
            if default_rule:
                # 获取默认规则名称
                for name in rule_names:
                    metadata = self.naming_service.get_rule_metadata(name)
                    if metadata and 'is_default' in metadata and metadata['is_default']:
                        self.rule_var.set(name)
                        break
        except Exception as e:
            logger.error(f"加载默认规则失败: {e}")
        
        # 如果没有找到默认规则，选择第一个
        if not self.rule_var.get() and rule_names:
            self.rule_var.set(rule_names[0])
        
        # 触发选择事件
        self._on_rule_selected()
    
    def _on_rule_selected(self, event=None):
        """处理规则选择事件"""
        rule_name = self.rule_var.get()
        if not rule_name or rule_name == "无可用规则":
            return
            
        # 获取规则元数据
        metadata = self.naming_service.get_rule_metadata(rule_name)
        if not metadata:
            messagebox.showerror("错误", f"获取规则'{rule_name}'的元数据失败")
            return
            
        # 更新UI
        self.name_var.set(metadata.get('name', '未知'))
        self.description_var.set(metadata.get('description', '无描述'))
        
        # 获取规则实例
        rule = self.naming_service.get_rule(rule_name)
        if rule:
            self.current_rule = rule
            
            # 更新所需字段
            self.required_fields_text.config(state=tk.NORMAL)
            self.required_fields_text.delete("1.0", tk.END)
            required_fields = rule.get_required_fields()
            if required_fields:
                self.required_fields_text.insert(tk.END, ", ".join(required_fields))
            else:
                self.required_fields_text.insert(tk.END, "无特定要求")
            self.required_fields_text.config(state=tk.DISABLED)
            
            # 如果是模板规则，启用模板编辑器
            if metadata.get('type') == 'template':
                for child in self.template_editor_frame.winfo_children():
                    child.config(state=tk.NORMAL)
                    
                # 加载模板内容
                if 'template' in metadata:
                    self.template_text.delete("1.0", tk.END)
                    self.template_text.insert(tk.END, metadata['template'])
                    self.template_name_var.set(metadata.get('name', ''))
                    self.template_desc_var.set(metadata.get('description', ''))
            else:
                # 禁用模板编辑器
                for child in self.template_editor_frame.winfo_children():
                    if isinstance(child, ttk.Entry) or isinstance(child, scrolledtext.ScrolledText):
                        child.config(state=tk.DISABLED)
    
    def _on_set_default(self):
        """设置为默认规则"""
        rule_name = self.rule_var.get()
        if not rule_name or rule_name == "无可用规则":
            messagebox.showinfo("提示", "请先选择一个规则")
            return
            
        success = self.naming_service.set_default_rule(rule_name)
        if success:
            messagebox.showinfo("成功", f"已将'{rule_name}'设置为默认命名规则")
        else:
            messagebox.showerror("错误", f"设置默认规则失败")
    
    def _on_test_naming(self):
        """测试命名规则"""
        if not self.current_rule:
            messagebox.showinfo("提示", "请先选择一个规则")
            return
            
        original_name = self.original_name_var.get()
        translated_name = self.translated_name_var.get()
        
        if not original_name:
            messagebox.showinfo("提示", "请输入原始文件名")
            return
            
        if not translated_name:
            messagebox.showinfo("提示", "请输入翻译后文本")
            return
            
        # 构建上下文
        context = {
            'original_name': original_name,
            'translated_name': translated_name,
            'extension': '.wav'  # 默认扩展名
        }
        
        try:
            # 执行命名预览
            rule_name = self.rule_var.get()
            result = self.naming_service.preview_filename(rule_name, context)
            self.result_var.set(result)
        except Exception as e:
            messagebox.showerror("错误", f"命名失败: {str(e)}")
    
    def _on_create_rule(self):
        """创建新规则"""
        # 清空模板编辑器
        self.template_name_var.set("")
        self.template_desc_var.set("")
        self.template_text.delete("1.0", tk.END)
        
        # 启用模板编辑器
        for child in self.template_editor_frame.winfo_children():
            if isinstance(child, ttk.Entry) or isinstance(child, scrolledtext.ScrolledText):
                child.config(state=tk.NORMAL)
    
    def _insert_variable(self, variable):
        """插入变量到模板中"""
        self.template_text.insert(tk.INSERT, f"{{{variable}}}")
    
    def _validate_template(self):
        """验证模板"""
        template = self.template_text.get("1.0", tk.END).strip()
        if not template:
            messagebox.showinfo("提示", "请输入模板内容")
            return
            
        try:
            # 验证模板格式
            validated = self.naming_service.template_processor.validate_template(template)
            if validated:
                messagebox.showinfo("成功", "模板格式有效")
            else:
                messagebox.showerror("错误", "模板格式无效")
        except Exception as e:
            messagebox.showerror("错误", f"验证失败: {str(e)}")
    
    def _save_template(self):
        """保存模板规则"""
        name = self.template_name_var.get()
        template = self.template_text.get("1.0", tk.END).strip()
        description = self.template_desc_var.get()
        
        if not name:
            messagebox.showinfo("提示", "请输入模板名称")
            return
            
        if not template:
            messagebox.showinfo("提示", "请输入模板内容")
            return
            
        try:
            # 创建模板规则
            success = self.naming_service.create_template_rule(name, template, description)
            if success:
                messagebox.showinfo("成功", f"模板规则'{name}'已保存")
                # 重新加载规则列表
                self._load_rules()
                # 选择新创建的规则
                self.rule_var.set(name)
                self._on_rule_selected()
            else:
                messagebox.showerror("错误", "保存模板规则失败")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
    
    def show(self):
        """显示UI"""
        # 使用引用循环来防止界面被垃圾回收
        self.root._ui_ref = self


def create_naming_rule_dialog(parent, naming_service: NamingService) -> tk.Toplevel:
    """
    创建命名规则配置对话框
    
    Args:
        parent: 父窗口
        naming_service: 命名服务实例
        
    Returns:
        Toplevel对话框实例
    """
    dialog = tk.Toplevel(parent)
    dialog.title("命名规则配置")
    dialog.geometry("800x600")
    dialog.minsize(600, 500)
    
    # 设置为模态对话框
    dialog.transient(parent)
    dialog.grab_set()
    
    ui = NamingRuleUI(dialog, naming_service)
    ui.show()
    
    return dialog 