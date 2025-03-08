# 音频翻译器 - 下一步开发计划

## 0. 已完成的重构与优化

### 核心服务重构 ✅

1. 基础架构重构：
   - 实现了清晰的服务接口与抽象基类
   - 建立了统一的服务工厂与注册机制
   - 支持依赖注入和服务发现
   - 提高了代码复用性和可维护性

2. 服务框架优化：
   - 实现了 BaseService 抽象基类
   - 规范了服务生命周期管理
   - 简化了服务配置管理
   - 提供了统一的日志和错误处理

### 分类服务优化 ✅

1. 重构 CategoryService：
   - 优化了分类数据结构
   - 添加了高效的分类匹配算法
   - 实现了分类数据的加载与保存
   - 提供了分类目录创建功能

2. UI交互优化：
   - 将 CategoryManager 重构为UI组件
   - 实现了分类选择对话框
   - 添加了自动分类功能
   - 优化了分类管理界面

### 命名服务实现 ✅

1. 命名规则引擎：
   - 实现了 INamingRule 接口
   - 支持多种命名规则（直接、双语、UCS、模板）
   - 创建了规则注册和验证机制
   - 实现了模板处理功能

2. 命名服务核心：
   - 实现 NamingService 服务类
   - 支持规则注册和管理
   - 提供文件名格式化功能
   - 实现命名预览功能

### 文件选择功能改进 ✅

1. 文件ID系统优化：
   - 修改了`FileManager`类，为每个文件分配唯一ID
   - 在树视图中使用ID作为树项标识符，而不是直接使用文件路径
   - 添加了专用方法获取和更新文件属性

2. 直接多选功能实现：
   - 实现无需按住Ctrl/Command键即可多选文件
   - 点击文件直接添加到选择，无需修饰键
   - 改进选择视觉反馈，使用标记和颜色

3. 文件打开功能优化：
   - 修复了文件打开功能，确保使用正确的文件路径
   - 增加了文件存在性检查和错误处理
   - 支持多文件路径复制

## 1. 当前开发重点：翻译策略服务实现 🚀

基于已完成的核心服务重构和命名服务实现，下一步开发重点是完善翻译策略服务，主要包括：

### 翻译策略接口设计

1. 完善 ITranslationStrategy 接口：
   ```python
   class ITranslationStrategy(ABC):
       """翻译策略接口"""
       
       @abstractmethod
       def translate(self, text: str, context: Dict[str, Any] = None) -> str:
           """翻译文本"""
           pass
       
       @abstractmethod
       def batch_translate(self, texts: List[str], context: Dict[str, Any] = None) -> List[str]:
           """批量翻译文本"""
           pass
           
       # 更多方法...
   ```

2. 实现策略注册表：
   ```python
   class StrategyRegistry:
       """翻译策略注册表"""
       
       def __init__(self):
           self.strategies: Dict[str, ITranslationStrategy] = {}
           self.default_strategy = None
           
       def register_strategy(self, name: str, strategy: ITranslationStrategy) -> bool:
           """注册翻译策略"""
           pass
           
       # 更多方法...
   ```

### 模型服务适配器实现

1. 完成各种模型服务的适配器：
   - 已实现 OpenAI 适配器
   - 继续实现 Anthropic 适配器
   - 实现 Gemini 适配器
   - 实现 Alibaba 适配器
   - 实现 Zhipu 适配器
   - 实现 Volc 适配器
   - 实现 DeepSeek 适配器

2. 统一适配器接口：
   ```python
   class ModelServiceAdapter(ITranslationStrategy):
       """模型服务适配器基类"""
       
       def __init__(self, model_service, config: Dict[str, Any]):
           self.model_service = model_service
           self.config = config
           
       # 实现接口方法...
   ```

### 翻译管理器

1. 实现 TranslationManager 类：
   ```python
   class TranslationManager(BaseService):
       """翻译管理器"""
       
       def __init__(self, config: Optional[Dict[str, Any]] = None):
           super().__init__(config)
           self.registry = StrategyRegistry()
           self.cache_manager = CacheManager()
           self.context_processor = ContextProcessor()
           
       # 实现方法...
   ```

2. 添加上下文处理和缓存管理功能

### 动态加载机制

1. 实现动态策略加载器：
   ```python
   class DynamicStrategyLoader:
       """动态策略加载器"""
       
       def load_strategies_from_directory(self, directory: str) -> List[ITranslationStrategy]:
           """从目录加载策略"""
           pass
           
       # 更多方法...
   ```

## 2. 翻译结果列实现

当前已经在UI中预留了翻译结果列，但还缺少实际的翻译功能实现。需要完成以下任务：

### 文件元数据扩展 ✅

1. 修改`FileManager`类的`_process_file`方法，在返回的元组中添加`translated_name`字段：
   ```python
   # 当前: (file_name, size_str, file_type, status, file_path)
   # 修改为: (file_id, name, size_str, file_type, translated_name, status, file_path)
   ```

2. 更新`FileManager`类中的相关方法，确保它们正确处理新增的字段 ✅
   - 添加了`get_file_property`方法获取文件属性
   - 添加了`update_file_property`方法更新文件属性
   - 修改了文件信息存储结构，使用ID作为主键

3. 添加更新翻译结果的专用方法 ✅
   ```python
   def update_file_property(self, file_id: str, property_name: str, value: str) -> bool:
       """更新文件的指定属性"""
       # 已实现代码
   ```

### 翻译服务集成 ✅

1. 在`FileManagerPanel`类中添加对`TranslatorService`的引用 ✅
   ```python
   def __init__(self, parent: tk.Widget, file_manager: Optional[FileManager] = None, 
                translator_service: Optional[TranslatorService] = None):
       # 保存translator_service引用
       self.translator_service = translator_service
   ```

2. 实现翻译按钮和菜单的功能，完成`_translate_selected_files`方法 ✅
   ```python
   def _translate_selected_files(self) -> None:
       """翻译选中的文件"""
       # 实现翻译逻辑
       # 显示进度条
       # 异步处理翻译请求
   ```

3. 添加翻译进度显示功能：
   - 创建进度条对话框
   - 使用异步翻译队列
   - 更新状态栏中的翻译计数

## 3. 文件名编辑功能

当前仅有UI界面上的编辑按钮和菜单项，需要实现实际的编辑功能：

### 单个文件编辑

1. 实现`_edit_translation`方法：
   ```python
   def _edit_translation(self) -> None:
       """编辑已翻译的文件名"""
       if not self.selected_files:
           return
           
       file_path = self.selected_files[0]
       file_info = self.file_manager.get_file_info(file_path)
       
       # 创建编辑对话框
       # 实现保存逻辑
   ```

2. 为翻译结果列添加双击编辑事件：
   ```python
   def _create_file_tree(self) -> None:
       # 现有代码...
       
       # 添加双击编辑事件
       self.file_tree.tag_bind("translated_cell", "<Double-1>", self._on_translated_name_double_click)
   ```

3. 实现编辑后的保存和更新逻辑

### 批量编辑功能

1. 添加批量编辑按钮和对话框：
   ```python
   def _create_toolbar(self) -> None:
       # 现有代码...
       
       # 添加批量编辑按钮
       self.batch_edit_btn = ttk.Button(toolbar, text="批量编辑", state="disabled")
       self.batch_edit_btn.pack(side=tk.LEFT, padx=2)
       create_tooltip(self.batch_edit_btn, "批量编辑选中文件的翻译结果")
   ```

2. 实现批量编辑对话框和功能：
   - 创建可视化的批量编辑界面
   - 支持不同的编辑模式（替换、添加前缀/后缀、正则替换）
   - 添加预览功能

## 4. 翻译工作流优化

优化翻译过程的效率和用户体验：

### 翻译队列管理

1. 创建`TranslationQueueManager`类：
   - 管理翻译任务队列
   - 支持暂停/继续功能
   - 实现失败重试机制

2. 添加队列控制UI：
   - 添加暂停/继续按钮
   - 显示队列状态和进度

### 翻译状态显示

1. 扩展文件状态枚举：
   - 未翻译
   - 翻译中
   - 已翻译
   - 翻译失败
   - 手动编辑

2. 使用图标或颜色区分不同状态：
   ```python
   def _update_file_status_display(self, item_id, status):
       """更新文件的状态显示"""
       # 根据状态设置不同的图标或标签
   ```

### 异步处理优化

1. 使用已实现的异步批处理机制处理翻译任务：
   ```python
   def _translate_selected_files(self) -> None:
       """翻译选中的文件名"""
       if not self.translator_service:
           messagebox.showwarning("翻译服务不可用", "翻译服务未配置或不可用。")
           return
       
       selected_files = self.selected_files.copy()
       if not selected_files:
           return
       
       # 使用异步批处理机制处理翻译任务
       self._process_items_async(
           items=selected_files,
           process_func=self._translate_single_file,
           title="正在翻译文件",
           description="正在翻译文件名，请稍候...",
           finish_callback=self._on_translation_complete
       )
   ```

2. 实现单个文件翻译处理函数：
   ```python
   def _translate_single_file(self, file_path: str) -> bool:
       """翻译单个文件名，由异步批处理调用"""
       try:
           file_info = self.file_manager.get_file_info(file_path)
           original_name = file_info[0]
           
           # 调用翻译服务
           translated_name = self.translator_service.translate_text(
               original_name, 
               source_lang="auto", 
               target_lang="zh-CN"
           )
           
           # 更新文件的翻译结果
           self.file_manager.update_file_translation(file_path, translated_name)
           
           # 更新UI显示（需要在主线程中执行）
           self.after_idle(lambda: self._update_file_translation_display(file_path, translated_name))
           return True
       except Exception as e:
           logger.error(f"翻译文件名失败：{file_path}，错误：{str(e)}")
           return False
   ```

3. 实现翻译完成回调：
   ```python
   def _on_translation_complete(self, results: Dict[str, bool]) -> None:
       """翻译完成后的回调函数"""
       success_count = sum(1 for success in results.values() if success)
       fail_count = len(results) - success_count
       
       self.update_status(f"翻译完成: {success_count}个成功, {fail_count}个失败")
       
       # 刷新文件树视图
       self._refresh_file_tree()
   ```

## 5. 优先级实施计划

根据功能依赖和重要性，建议按以下顺序实施：

1. ✅ 核心服务重构 - 提供坚实的架构基础
2. ✅ 分类服务优化 - 完善分类功能
3. ✅ 命名服务实现 - 支持灵活的文件命名
4. 🚀 翻译策略服务实现 - 当前开发重点
   - 完成各模型服务适配器
   - 实现翻译管理器
   - 添加上下文处理功能
   - 实现缓存管理
5. 文件名编辑功能 - 增强用户交互
6. 翻译工作流优化 - 提升整体体验

## 技术参考

- `TranslatorService`: `src/audio_translator/services/business/translator_service.py`
- `FileManager`: `src/audio_translator/managers/file_manager.py`
- `FileManagerPanel`: `src/audio_translator/gui/panels/file_manager_panel.py`
- `NamingService`: `src/audio_translator/services/business/naming/naming_service.py`
- `CategoryService`: `src/audio_translator/services/business/category/category_service.py`
- `ITranslationStrategy`: `src/audio_translator/services/business/translation/strategies/base_strategy.py`

## 最近完成的核心优化

1. **异步批处理机制**
   - 实现了通用的异步批处理方法`_process_items_async`，支持处理大量文件时不阻塞UI
   - 添加了进度显示和取消功能，提升用户体验
   - 支持完成回调，方便处理批处理结果

2. **性能优化**
   - 优化了全选、反选和取消选择等批量操作的性能
   - 添加了智能检测，避免重复执行已完成的操作
   - 减少了不必要的UI更新，提升响应速度

3. **选择功能增强**
   - 支持直接点击选择列选择文件，无需修饰键
   - 兼容标准的Ctrl/Shift多选操作
   - 实现了稳定的状态更新机制 