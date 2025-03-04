# 音频翻译器 - 下一步开发计划

## 1. 翻译结果列实现

当前已经在UI中预留了翻译结果列，但还缺少实际的翻译功能实现。需要完成以下任务：

### 文件元数据扩展

1. 修改`FileManager`类的`_process_file`方法，在返回的元组中添加`translated_name`字段：
   ```python
   # 当前: (file_name, size_str, file_type, status, file_path)
   # 修改为: (file_name, size_str, file_type, status, file_path, translated_name)
   ```

2. 更新`FileManager`类中的相关方法，确保它们正确处理新增的字段：
   - `update_file_status`
   - `batch_update_status`
   - `_sort_files`

3. 添加更新翻译结果的专用方法：
   ```python
   def update_file_translation(self, file_path: str, translated_name: str):
       """更新文件的翻译结果"""
       # 实现代码
   
   def batch_update_translations(self, file_paths: List[str], translations: List[str]) -> int:
       """批量更新文件的翻译结果"""
       # 实现代码
   ```

### 翻译服务集成

1. 在`FileManagerPanel`类中添加对`TranslatorService`的引用：
   ```python
   def __init__(self, parent: tk.Widget, file_manager: Optional[FileManager] = None, 
                translator_service: Optional[TranslatorService] = None):
       # 保存translator_service引用
       self.translator_service = translator_service
   ```

2. 实现翻译按钮和菜单的功能，完成`_translate_selected_files`方法：
   ```python
   def _translate_selected_files(self) -> None:
       """翻译选中的文件名"""
       if not self.translator_service:
           messagebox.showwarning("翻译服务不可用", "翻译服务未配置或不可用。")
           return
       
       # 实现翻译逻辑
   ```

3. 添加翻译进度显示功能：
   - 创建进度条对话框
   - 使用异步翻译队列
   - 更新状态栏中的翻译计数

## 2. 文件名编辑功能

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

## 3. 翻译工作流优化

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

## 4. 优先级实施计划

根据功能依赖和重要性，建议按以下顺序实施：

1. ✅ 优化文件选择功能，提升大量文件处理性能
2. ✅ 实现异步批处理机制，为后续功能做准备
3. 扩展`FileManager`类，添加翻译相关字段
4. 在`FileManagerPanel`中集成`TranslatorService`
5. 实现基本的单文件翻译功能，整合异步处理机制
6. 添加翻译进度显示，复用现有的进度条组件
7. 实现单个文件编辑功能
8. 添加批量翻译功能
9. 开发批量编辑界面
10. 优化翻译队列管理
11. 改进状态显示和用户反馈

## 技术参考

- `TranslatorService`: `src/audio_translator/services/business/translator_service.py`
- `FileManager`: `src/audio_translator/managers/file_manager.py`
- `FileManagerPanel`: `src/audio_translator/gui/panels/file_manager_panel.py`

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