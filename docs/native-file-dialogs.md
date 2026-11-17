# 恢复系统原生文件选择窗口

## 原因与修复

双语言改造后的 `i18n/qt.py::_file_call()` 曾在全部文件/目录选择调用上添加 `QFileDialog.Option.DontUseNativeDialog`，并通过语言管理器检查打开的 QFileDialog、修改标题和文件类型。强制标志使 macOS 原生文件选择窗口无法使用。

本次删除强制标志，直接调用 `PySide6.QtWidgets.QFileDialog` 的四个官方静态方法：`getOpenFileName`、`getOpenFileNames`、`getSaveFileName`、`getExistingDirectory`。保留薄适配层，只在打开前翻译应用提供的标题、过滤器等 `Message` 参数，原样转发父窗口、路径、选项、选中文件与取消返回值。没有实例化自定义文件窗口，没有给系统窗口设置 QSS，也不再扫描或重译已打开的文件窗口。语言管理器中不再使用的文件过滤器更新逻辑已删除；消息和输入对话框的实时翻译保留。

已检查应用源代码：没有设置全局 `AA_DontUseNativeDialogs`，其他文件选择入口也没有单独强制关闭原生模式。

## 统一生效的入口

- 打开/保存项目、导入已有 INP。
- 第 01 页导入 XSD / CIF / XYZ / EXTXYZ。
- 选择 CP2K XML。
- 数据库目录、基组及赝势文件选择。
- 单独导出 INP、计算包目标目录选择。

Qt 根据平台提供系统文件选择窗口：macOS 为 NSOpenPanel/NSSavePanel，Windows 为系统文件窗口，Linux 优先使用可用的平台实现；原生服务不可用时允许 Qt 自动回退。应用不额外覆盖调用方显式选项。

应用按钮与错误提示继续使用当前界面语言。系统面板内部的控件语言和外观遵循操作系统；不为强制翻译系统控件而退回 Qt 内置窗口。对话框结束后应用语言保持不变。

**已在运行的程序需要重新启动，才能载入本次 Python 源码修改。**

## 修改文件

- `i18n/qt.py`：恢复原生默认行为。
- `i18n/language_manager.py`：清理仅用于 Qt 文件窗口的过滤器重译分支。
- `tests/test_i18n.py`：移除强制要求 Qt 文件窗口实时重译的旧测试部分，保留输入弹窗实时重译测试。
- `tests/test_native_file_dialogs.py`：新增 20 项回归测试，覆盖四类静态调用、双语标题/过滤器、选项转发、特殊文件名、取消、失败、结构和固定状态同步。
- `docs/internationalization.md`：更新原生窗口与系统语言约定。
- `docs/native-file-dialogs.md`：本说明。

## 验证结果与范围

相关测试 **97 passed, 45 warnings，22.94 秒**。警告为 ASE 和 cp2k-input-tools 的弃用提示。覆盖文件对话框封装、语言切换、项目菜单、原子固定、持续 3D 预览、导出工作流及运行环境。使用合成 TiO2 测试结构、文件名 `TiO2_rutile (1 1 0).cif`，另测 XYZ 和 EXTXYZ；这不是材料适用性或计算精度测试。

测试在 offscreen Qt 平台拦截官方文件选择方法，验证原生模式未被关闭、参数及文件返回值正确传递；其结果不能证明系统面板外观。本机尝试启动 Cocoa 窗口并连接界面自动化工具，但工具未能连接 Python GUI 进程，因此 **macOS 原生面板外观、目录导航及搜索尚未实际验证**。**Windows/Linux 原生桌面同样未实机验证**。

没有修改结构解析、数据模型、固定约束、CP2K INP、run.sh 或计算包生成逻辑。
