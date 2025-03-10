import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import logging
from typing import Dict, Any, List, Optional, Callable

from ....services.business.translation.translation_manager import TranslationManager

logger = logging.getLogger(__name__)

class TranslationStrategyUI:
    """翻译策略选择和配置界面"""
    
    def __init__(self, root: tk.Tk, translation_manager: TranslationManager):
        """
        初始化翻译策略UI
        
        Args:
            root: Tkinter根窗口
            translation_manager: 翻译管理器实例
        """
        self.root = root
        self.translation_manager = translation_manager
        self.current_strategy = None
        self.callbacks = {}  # 回调函数字典
        
        # 获取主题服务
        self.theme_service = None
        self.colors = {}
        
        try:
            service_factory = translation_manager.service_factory
            if service_factory:
                self.theme_service = service_factory.get_service('theme_service')
                if self.theme_service:
                    # 获取当前主题颜色
                    self.colors = self.theme_service.get_theme_colors()
                    # 为根窗口设置背景色
                    if isinstance(root, tk.Toplevel):
                        root.configure(bg=self.colors.get('bg_dark', '#212121'))
        except Exception as e:
            logger.warning(f"获取主题服务失败: {e}")
            # 使用默认暗色主题
            self.colors = {
                'bg_dark': '#212121',
                'bg_light': '#333333',
                'fg': '#FFFFFF',
                'accent': '#2196F3',
                'border': '#555555',
                'hover': '#484848',
                'selected': '#1976D2',
            }
        
        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建UI组件
        self._create_strategy_selection_section()
        self._create_strategy_details_section()
        self._create_test_section()
        self._create_metrics_section()
        
        # 加载策略列表
        self._load_strategies()
    
    def _create_strategy_selection_section(self):
        """创建策略选择部分"""
        # 创建框架
        frame = ttk.LabelFrame(self.main_frame, text="策略选择", padding="5")
        frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建策略选择下拉框
        ttk.Label(frame, text="翻译策略:").grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)
        self.strategy_var = tk.StringVar()
        self.strategy_combo = ttk.Combobox(frame, textvariable=self.strategy_var, state="readonly", width=30)
        self.strategy_combo.grid(column=1, row=0, sticky=tk.W, padx=5, pady=5)
        self.strategy_combo.bind("<<ComboboxSelected>>", self._on_strategy_selected)
        
        # 创建设为默认按钮
        ttk.Button(frame, text="设为默认", command=self._set_default_strategy).grid(column=2, row=0, padx=5, pady=5)
        
        # 创建重新加载按钮
        ttk.Button(frame, text="重新加载策略", command=self._reload_strategies).grid(column=3, row=0, padx=5, pady=5)
    
    def _create_strategy_details_section(self):
        """创建策略详情部分"""
        # 创建框架
        self.details_frame = ttk.LabelFrame(self.main_frame, text="策略详情", padding="5")
        self.details_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建详情文本框
        self.details_text = scrolledtext.ScrolledText(self.details_frame, wrap=tk.WORD, width=50, height=10)
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.details_text.config(state=tk.DISABLED)
        
        # 创建配置框架
        self.config_frame = ttk.LabelFrame(self.main_frame, text="策略配置", padding="5")
        self.config_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 配置框架的内容将在选择策略时动态生成
    
    def _create_test_section(self):
        """创建测试部分"""
        # 创建框架
        test_frame = ttk.LabelFrame(self.main_frame, text="翻译测试", padding="5")
        test_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建输入文本框
        ttk.Label(test_frame, text="输入文本:").grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)
        self.input_text = scrolledtext.ScrolledText(test_frame, wrap=tk.WORD, width=50, height=5)
        self.input_text.grid(column=0, row=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # 创建翻译按钮
        ttk.Button(test_frame, text="翻译", command=self._translate_text).grid(column=0, row=2, padx=5, pady=5)
        
        # 创建输出文本框
        ttk.Label(test_frame, text="翻译结果:").grid(column=0, row=3, sticky=tk.W, padx=5, pady=5)
        self.output_text = scrolledtext.ScrolledText(test_frame, wrap=tk.WORD, width=50, height=5)
        self.output_text.grid(column=0, row=4, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.output_text.config(state=tk.DISABLED)
    
    def _create_metrics_section(self):
        """创建指标部分"""
        # 创建框架
        metrics_frame = ttk.LabelFrame(self.main_frame, text="性能指标", padding="5")
        metrics_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建指标文本框
        self.metrics_text = scrolledtext.ScrolledText(metrics_frame, wrap=tk.WORD, width=50, height=5)
        self.metrics_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.metrics_text.config(state=tk.DISABLED)
        
        # 创建更新按钮
        ttk.Button(metrics_frame, text="更新指标", command=self._update_metrics).pack(padx=5, pady=5)
    
    def _load_strategies(self):
        """加载策略列表"""
        strategies = self.translation_manager.get_available_strategies()
        strategy_names = [s["name"] for s in strategies]
        
        # 更新下拉框
        self.strategy_combo["values"] = strategy_names
        
        # 选择默认策略
        default_strategy = self.translation_manager.default_strategy
        if default_strategy in strategy_names:
            self.strategy_var.set(default_strategy)
            self._on_strategy_selected(None)
    
    def _on_strategy_selected(self, event):
        """
        当策略被选择时调用
        
        Args:
            event: Tkinter事件
        """
        strategy_name = self.strategy_var.get()
        if not strategy_name:
            return
            
        # 获取策略
        self.current_strategy = self.translation_manager.get_strategy(strategy_name)
        if not self.current_strategy:
            messagebox.showerror("错误", f"无法获取策略: {strategy_name}")
            return
            
        # 更新详情
        self._update_strategy_details()
        
        # 动态创建配置UI
        self._create_config_ui()
        
        # 触发回调
        if "strategy_selected" in self.callbacks:
            self.callbacks["strategy_selected"](strategy_name, self.current_strategy)
    
    def _update_strategy_details(self):
        """更新策略详情"""
        if not self.current_strategy:
            return
            
        # 获取策略信息
        name = self.current_strategy.get_name()
        description = self.current_strategy.get_description()
        capabilities = self.current_strategy.get_capabilities()
        
        # 格式化详情
        details = f"名称: {name}\n"
        details += f"描述: {description}\n\n"
        details += "能力:\n"
        for key, value in capabilities.items():
            details += f"  - {key}: {value}\n"
        
        # 更新文本框
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, details)
        self.details_text.config(state=tk.DISABLED)
    
    def _create_config_ui(self):
        """动态创建配置UI"""
        # 清空现有配置UI
        for widget in self.config_frame.winfo_children():
            widget.destroy()
            
        if not self.current_strategy:
            return
            
        # 获取配置模式
        config_schema = self.current_strategy.get_config_schema()
        if not config_schema:
            ttk.Label(self.config_frame, text="此策略没有可配置选项").pack(padx=5, pady=5)
            return
            
        # 创建配置字段
        self.config_vars = {}
        row = 0
        
        for field_name, field_info in config_schema.get("properties", {}).items():
            field_type = field_info.get("type", "string")
            field_title = field_info.get("title", field_name)
            field_description = field_info.get("description", "")
            field_default = field_info.get("default", "")
            
            # 创建标签
            ttk.Label(self.config_frame, text=f"{field_title}:").grid(column=0, row=row, sticky=tk.W, padx=5, pady=5)
            
            # 根据字段类型创建不同的输入控件
            if field_type == "string":
                var = tk.StringVar(value=field_default)
                ttk.Entry(self.config_frame, textvariable=var, width=30).grid(column=1, row=row, sticky=tk.W, padx=5, pady=5)
                self.config_vars[field_name] = var
            elif field_type == "boolean":
                var = tk.BooleanVar(value=field_default)
                ttk.Checkbutton(self.config_frame, variable=var).grid(column=1, row=row, sticky=tk.W, padx=5, pady=5)
                self.config_vars[field_name] = var
            elif field_type == "integer" or field_type == "number":
                var = tk.StringVar(value=str(field_default))
                ttk.Entry(self.config_frame, textvariable=var, width=10).grid(column=1, row=row, sticky=tk.W, padx=5, pady=5)
                self.config_vars[field_name] = var
            elif field_type == "array" and "enum" in field_info.get("items", {}):
                var = tk.StringVar(value=field_default[0] if field_default and isinstance(field_default, list) else "")
                ttk.Combobox(self.config_frame, textvariable=var, values=field_info["items"]["enum"], width=30).grid(column=1, row=row, sticky=tk.W, padx=5, pady=5)
                self.config_vars[field_name] = var
                
            # 添加提示信息
            if field_description:
                ttk.Label(self.config_frame, text=field_description, foreground="gray").grid(column=2, row=row, sticky=tk.W, padx=5, pady=5)
                
            row += 1
            
        # 添加应用配置按钮
        ttk.Button(self.config_frame, text="应用配置", command=self._apply_config).grid(column=0, row=row, columnspan=2, padx=5, pady=10)
    
    def _apply_config(self):
        """应用配置"""
        if not self.current_strategy:
            return
            
        # 收集配置值
        config = {}
        for field_name, var in self.config_vars.items():
            value = var.get()
            # 转换数值类型
            try:
                if isinstance(value, str) and value.isdigit():
                    value = int(value)
                elif isinstance(value, str) and "." in value and all(part.isdigit() for part in value.split(".", 1)):
                    value = float(value)
            except:
                pass
                
            config[field_name] = value
            
        # 更新策略配置
        try:
            if self.current_strategy.update_config(config):
                messagebox.showinfo("成功", "配置已应用")
            else:
                messagebox.showerror("错误", "应用配置失败")
        except Exception as e:
            messagebox.showerror("错误", f"应用配置时发生错误: {e}")
    
    def _set_default_strategy(self):
        """设置默认策略"""
        strategy_name = self.strategy_var.get()
        if not strategy_name:
            messagebox.showwarning("警告", "请先选择一个策略")
            return
            
        if self.translation_manager.set_default_strategy(strategy_name):
            messagebox.showinfo("成功", f"已将 {strategy_name} 设为默认策略")
        else:
            messagebox.showerror("错误", f"设置默认策略失败")
    
    def _reload_strategies(self):
        """重新加载策略"""
        try:
            count = self.translation_manager.reload_strategies()
            messagebox.showinfo("成功", f"已重新加载 {count} 个策略")
            self._load_strategies()
        except Exception as e:
            messagebox.showerror("错误", f"重新加载策略失败: {e}")
    
    def _translate_text(self):
        """测试翻译"""
        input_text = self.input_text.get(1.0, tk.END).strip()
        if not input_text:
            messagebox.showwarning("警告", "请输入要翻译的文本")
            return
            
        strategy_name = self.strategy_var.get()
        if not strategy_name:
            messagebox.showwarning("警告", "请先选择一个策略")
            return
            
        try:
            # 执行翻译
            translation = self.translation_manager.translate(input_text, strategy_name)
            
            # 更新输出文本框
            self.output_text.config(state=tk.NORMAL)
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(tk.END, translation)
            self.output_text.config(state=tk.DISABLED)
            
            # 更新指标
            self._update_metrics()
        except Exception as e:
            messagebox.showerror("错误", f"翻译失败: {e}")
    
    def _update_metrics(self):
        """更新性能指标"""
        try:
            metrics = self.translation_manager.get_metrics()
            
            # 格式化指标
            metrics_text = "全局指标:\n"
            metrics_text += f"  - 总请求数: {metrics.get('total_requests', 0)}\n"
            metrics_text += f"  - 成功请求数: {metrics.get('successful_requests', 0)}\n"
            metrics_text += f"  - 失败请求数: {metrics.get('failed_requests', 0)}\n"
            # 使用get方法防止KeyError
            avg_response_time = metrics.get('average_response_time', 0.0)
            metrics_text += f"  - 平均响应时间: {avg_response_time:.4f}秒\n\n"
            
            if "cache" in metrics:
                cache_metrics = metrics["cache"]
                metrics_text += "缓存指标:\n"
                # 使用get方法防止KeyError
                metrics_text += f"  - 请求总数: {cache_metrics.get('requests', cache_metrics.get('total_requests', 0))}\n"
                metrics_text += f"  - 命中数: {cache_metrics.get('hits', 0)}\n"
                metrics_text += f"  - 未命中数: {cache_metrics.get('misses', 0)}\n"
                # 计算命中率，防止除零错误
                hit_rate = 0.0
                if 'hit_rate' in cache_metrics:
                    hit_rate = cache_metrics['hit_rate']
                elif 'hits' in cache_metrics and ('requests' in cache_metrics or 'total_requests' in cache_metrics):
                    total = cache_metrics.get('requests', cache_metrics.get('total_requests', 0))
                    if total > 0:
                        hit_rate = cache_metrics['hits'] / total
                
                metrics_text += f"  - 命中率: {hit_rate:.2%}\n"
                metrics_text += f"  - 当前缓存大小: {cache_metrics.get('size', 0)}\n\n"
            
            if self.current_strategy:
                strategy_name = self.current_strategy.get_name()
                if "strategies" in metrics and strategy_name in metrics["strategies"]:
                    strategy_metrics = metrics["strategies"][strategy_name]
                    metrics_text += f"策略 {strategy_name} 指标:\n"
                    # 遍历字典项时使用items()方法
                    for key, value in strategy_metrics.items():
                        metrics_text += f"  - {key}: {value}\n"
            
            # 更新文本框
            self.metrics_text.config(state=tk.NORMAL)
            self.metrics_text.delete(1.0, tk.END)
            self.metrics_text.insert(tk.END, metrics_text)
            self.metrics_text.config(state=tk.DISABLED)
        except Exception as e:
            import traceback
            logger.error(f"更新指标失败: {e}\n{traceback.format_exc()}")
            # 使用更友好的错误消息
            error_message = f"更新指标失败: {type(e).__name__}"
            if "requests" in str(e):
                error_message = "更新指标失败: 需要安装requests模块"
            elif "ModuleNotFoundError" in str(e):
                error_message = f"更新指标失败: 缺少必要模块 - {str(e)}"
            messagebox.showinfo("提示", error_message)
    
    def register_callback(self, event_name: str, callback: Callable) -> None:
        """
        注册事件回调
        
        Args:
            event_name: 事件名称
            callback: 回调函数
        """
        self.callbacks[event_name] = callback
    
    def show(self):
        """显示界面"""
        self._load_strategies()
        self._update_metrics()


def create_translation_strategy_dialog(parent, translation_manager: TranslationManager) -> tk.Toplevel:
    """
    创建翻译策略配置对话框
    
    Args:
        parent: 父窗口
        translation_manager: 翻译管理器实例
        
    Returns:
        Toplevel对话框实例
    """
    dialog = tk.Toplevel(parent)
    dialog.title("翻译策略配置")
    dialog.geometry("800x600")
    dialog.minsize(600, 500)
    
    # 设置为模态对话框
    dialog.transient(parent)
    dialog.grab_set()
    
    # 应用主题
    try:
        # 尝试获取主题服务
        service_factory = translation_manager.service_factory
        if service_factory:
            theme_service = service_factory.get_service('theme_service')
            if theme_service:
                # 应用主题到对话框
                theme_service.setup_dialog_theme(dialog)
    except Exception as e:
        logger.warning(f"应用主题到对话框失败: {e}")
    
    ui = TranslationStrategyUI(dialog, translation_manager)
    
    # 修复CacheManager中的requests错误
    try:
        ui.show()
    except Exception as e:
        if 'requests' in str(e):
            import tkinter.messagebox as messagebox
            messagebox.showinfo("提示", "缓存指标获取失败，请安装requests模块或忽略此错误继续使用")
        else:
            # 其他错误则重新抛出
            raise
    
    return dialog 