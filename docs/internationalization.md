# English / 简体中文界面

每次启动默认 **English**，不读取或保存语言偏好。顶部最右侧的 **Language:** 下拉框可立即切换到 **简体中文**；中文界面标签为「语言：」。选项名称固定使用各自语言。启动命令仍为 `python main.py`。

## 工作方式

- `i18n/language_manager.py` 集中管理 `QTranslator`、Qt 自带的标准对话框翻译、`QLocale` 和文本绑定。切换仅重新渲染绑定属性，更新时阻断控件信号，不调用参数收集、项目加载、数据库推荐或综合检查。
- `i18n/qt.py` 为手工构建的 Qt 界面提供轻量文本绑定。只有显式的 `Message` 会翻译；普通字符串视为用户数据或 CP2K 标识。控件实例、下拉框 `userData`、选择和编辑草稿均保留。自绘 3D 视图只请求重绘，不重建场景或重置相机。
- `i18n/messages.py` 的 `Message` 保留英文模板、稳定 `code` 和具名参数，可组合为结构化报告。异常只保留错误内容，不保留 traceback。已有报告可用同一结果渲染两种语言，无需重新校验；阶段状态和导航状态保持不变。
- 为兼容既有字符串消费者、模块定位和项目中的数据库来源元数据，`Message` 的字符串兼容值保留历史中文拼写；不要把这个兼容值作为新增 UI 的最终显示文本。显示使用 `i18n_render()` 或绑定控件，代码与参数通过 `Message.to_dict()` 获取。该兼容层不改变项目格式、校验规则或科学参数。
- Qt 创建的标准按钮和消息/输入对话框会注册文本绑定。文件或目录选择通过 PySide6 官方静态 QFileDialog 方法打开，不强制关闭原生模式：macOS 使用系统面板，Windows/Linux 由 Qt 选择平台支持的原生窗口，不可用时自动回退。应用传入打开时当前语言的标题和过滤器，系统窗口内部控件遵循系统语言；不在打开期间检查、定制或强制重新翻译原生文件窗口。文件路径保持原样，关闭后应用语言不变。macOS 可能按照平台惯例隐藏消息框窗口标题。
- 窗口由 Qt 在 GUI 线程销毁；顶层窗口和原生控件包装对象在 C++ 生命周期内保持引用，避免后台校验触发 Python GC 时释放 GUI 对象。

## 覆盖范围

当前两个语言目录各有 **608 个模板**，包括八个参数页面、导航、顶部菜单、项目及预设管理、XML 设置、数据库管理、推荐与连续 Apply、坐标范围对话框、导出提示、状态栏、HelpIcon、3D 空状态及统计、配置校验和综合检查阶段的动态消息。

`RUN_TYPE`、`GEO_OPT`、`BASIS_SET` 等 CP2K Section/Keyword、枚举值、基组/赝势名称、元素、用户项目名、用户预设名/描述、路径和数据库原始内容不翻译。CP2K 原生 INP、`run.sh` 和 `EXPORT_NOTES.txt` 的生成流程不依赖界面语言。

第三方 CP2K 解析器、ASE、Pydantic 及操作系统返回的原始诊断细节保持其原始语言，应用自身的标题、上下文和已建模诊断均可翻译。不通过字符串替换猜测第三方错误含义。

## 添加文本与构建翻译

新增界面文字应采用英文模板和具名参数：

```python
from i18n.messages import i18n_msg
from i18n.qt import QLabel

label = QLabel(i18n_msg('Configured {count}/{total} elements',
                       code='recommendation.progress', count=2, total=3))
```

`code` 应稳定且唯一。不要把用户文件名、基组名称或已经拼好的整段报告作为翻译查找键。不要将翻译后的下拉框 `currentText()` 当作业务枚举，应使用 `currentData()`。普通 Qt 内部创建的标准按钮可使用 `i18n.qt.set_button_text()` 绑定自定义标题。

在项目根目录使用同一虚拟环境：

```bash
python scripts/build_translations.py --update
```

脚本从 UI、core 诊断和 i18n 模块中的 `i18n_msg()` 提取英文模板，生成 `i18n/catalog_sources.py`，调用 **pyside6-lupdate** 更新 TS，然后调用 **pyside6-lrelease** 编译 QM。提取标记文件有源文件位置注释，仅由脚本生成。维护者在 Qt Linguist 或文本编辑器中编辑 `i18n/cp2kstudio_zh_CN.ts`，必须保留 `{parameter}`、格式化后缀和真实 CP2K Keyword。英文 TS 始终使用英文源文本。

修改 TS 后只需重新编译：

```bash
python scripts/build_translations.py
python -m pytest tests/test_i18n.py -q
```

新中文条目保持 unfinished，Qt 会明确回退到英文模板；缺少整个 QM 时同样回退到英文。应用启动只加载随源码发布的预编译 QM，不需要网络或运行 lupdate/lrelease。翻译完整性测试会检查目录与源模板一致、无未完成条目、参数占位符一致，以及 QM 可加载。

## 发布资源

源码分发必须完整包含 `i18n/` 下的 Python、两份 TS 和两份 QM，保持相对目录结构。已有资源随本次源码一起交付。

若使用 PyInstaller，额外指定：

```bash
pyinstaller --additional-hooks-dir scripts/hooks <项目既有的打包参数>
```

`hook-i18n.py` 将 TS/QM 收集到包对应目录。其他既有资源（官方数据库、XML、主题和图标）仍需按项目原有打包方式收集。此项目没有新增安装器或强制 PyInstaller 依赖；本次未构建独立安装包。

## 验证范围

自动化覆盖进程重启默认英语、双向切换、所有页面与菜单、HelpIcon、3D 重绘、已打开的应用弹窗、文件选择调用参数、推荐过滤/Apply、已有报告无重校验切换、编辑草稿和相机/选择保留，以及中英文生成的 INP、项目 JSON、结构、run.sh、EXPORT_NOTES.txt 字节一致。

macOS 原生 Cocoa 界面已检查 1480 和 1050 宽度、中英文页面与推荐窗口；Linux 原生桌面和打包后的独立程序尚未实机验证。没有启动 CP2K 数值计算，本次验证覆盖 XML 和生成工件，不代表科学收敛性测试。

本次新增和修改文件完整清单见 [i18n-changes.md](i18n-changes.md)。

## 本次测试记录（2026-10-29，macOS / Python 3.12）

- 全量回归：**433 passed, 572 warnings, 217.00s**。
- 最后一次窄窗口布局调整后，重新运行语言、KIND 布局、推荐、工作流、项目菜单和 UI 回归：**99 passed, 27 warnings, 30.00s**，其中包含 **16 项语言测试**；两种语言下第 05 页在 1050px 窗口均无页面级横向溢出。
- 警告来自 cp2k-input-tools / ASE 的弃用提示，以及故意构造无效运行参数的 Pydantic 序列化用例。
- 全量测试使用独立临时 `XDG_CACHE_HOME`，不删除或改写用户已下载的数据库缓存。
- `pyside6-lupdate` / `pyside6-lrelease`：两种语言各 **608 个完成条目，0 unfinished**。`compileall` 检查通过。
- INP、run.sh、EXPORT_NOTES.txt 三个生成模块及坐标显示精度委托与本次修改前的源码字节完全相同。
