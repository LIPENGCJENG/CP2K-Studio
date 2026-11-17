# CP2K Studio v1.0.0 — macOS 打包测试记录

测试日期：2026-11-08。发布阶段：Stage 1 — Personal Testing。

## 产物和环境

- 产物：项目根目录下 `dist/CP2K Studio.app`，约 204 MiB 磁盘占用，Finder 显示约 212.8 MB。
- Apple M4，macOS 15.5，ARM64。此构建不面向 Intel Mac。
- Python 3.12.12、PyInstaller 6.22.3、pyinstaller-hooks-contrib 2026.9、PySide6 6.12.0。
- ASE 3.29.0、NumPy 2.5.4、Pydantic 2.14.1。完整版本清单位于 App 的 `Contents/Resources/build-info.json`。
- 名称 CP2K Studio，版本 1.0.0，构建号 1，Bundle ID `org.cp2kstudio.desktop`。
- 主程序与独立终端助手均为 ARM64。自动 ad-hoc 签名通过 `codesign --verify --deep --strict`；未使用 Developer ID，未公证。
- 没有升级项目运行依赖，只在原有虚拟环境添加构建工具。

## 自动化结果

全部原有回归测试分八批执行，**1318 passed，0 failed**。打包、项目路径和预设兼容专项测试另执行 **27 passed**，包括新增的移动 App 后数据库指纹匹配恢复测试。两者有覆盖重叠，不应相加作为独立用例总数。第三方 ASE / CP2K 输入解析器的弃用提示仍存在，不是配置校验中的 Warning。

冻结程序的 17 组冒烟检查全部通过，覆盖：

- Qt 启动、应用图标、目标 2026.1 XML、外部个人预设目录。
- CIF、XYZ、EXTXYZ；三个真实 Materials Studio XSD 样例（H₂O 3 原子、金红石 6 原子、Slab 22 原子）。
- ENERGY、GEO_OPT、CELL_OPT、MD、VIBRATIONAL_ANALYSIS 的表单、实时预览及 XML 解析；振动任务同时生成 IR 和 Raman 配置。
- 3D 离屏绘制、原子选择和固定标记、Aa、中英文切换时项目/Dirty/修订号/INP/视角状态保持。
- 综合检查、项目与预设往返、独立 INP、完整计算包及依赖、run.sh、EXPORT_NOTES.txt。
- 最小 GUI PATH 下的环境检测，独立终端助手的无害脚本、目录处理、标准输出/错误、退出码及监控独立性。
- 原生文件对话框禁用标志未被设置。

独立性测试：将整个 App 复制到 `/tmp/CP2K Studio relocation 中文 (test)/`，以 `/private/tmp` 为工作目录；再暂时隐藏项目 `.venv`，仅保留 `/usr/bin:/bin` PATH，执行冻结程序的全部冒烟检查，**17/17 通过**。测试结束后 `.venv` 已恢复。App 的 Python、XML、数据库和翻译均来自自身 Bundle。

可重复测试命令见 [打包说明](macos-packaging.md)。测试运行输出保存在本机 `/tmp/cp2k-macos-regression-20261108/`、`/tmp/cp2k-relocated-smoke-20261108-c/` 和 `/tmp/cp2k-no-dev-venv-smoke-20261108-d/`；临时目录可能被系统清理。

## macOS 桌面实测

- Finder 双击原 App 及移动后的 App 均成功；主窗口正常，无额外 Python 控制台，默认英文，八个步骤及右侧 3D/INP 正常显示。关闭后重新启动成功。
- Finder「显示简介」实际显示自定义 CP2K 图标、Application (Apple silicon) 和版本 1.0.0。Qt 应用图标加载通过；Dock 和应用切换器图标未单独做视觉验收。
- 结构导入为系统原生 `NSOpenPanel`（可访问性角色 `open-panel`），成功选择带中文、空格及括号的 CIF 路径。导入后原子表、晶胞、3D 同步显示，中英文切换及 Aa 状态保留。
- Local Run 文件夹选择为系统原生面板。结构导入和目录选择已做视觉实测；项目打开/保存和导出文件面板复用原生接口，其取消及业务流程由现有自动测试覆盖，未逐个做视觉检查。
- 原生 Environment Check 正确识别 CP2K **2026.2**、Open MPI **5.0.11**、Apple M4、物理/逻辑 10 核、约 16 GiB 内存。目标仍是 2026.1，因此版本差异提示正确；报告正确区分 Homebrew 已安装但不在 Finder GUI PATH。打包的科学依赖没有误报缺失。
- 原生 Local Run 实际打开两个独立 Terminal 会话，分别使用 `ttys000` / `ttys001`，运行目录包含中文、空格及引号。只运行无害 Bash 脚本，未调用 CP2K / MPI 计算。
- 停止该测试的监控助手后，运行记录仍为 running；关闭测试 GUI 后确认脚本完成标记和退出码 **7**。独立助手由 Terminal 管理，GUI 不发送停止计算信号。退出码 7 是有意设置的测试结果，不代表失败的打包测试。

## 修复与限制

构建过程中发现并修复了 CP2K 输入解析器单位资源漏收集，以及两个 EXE 组合时 BUNDLE 错误继承控制台助手的后台模式。最终 App 包含单位定义，且不再作为后台应用启动。

App 不内置 CP2K 引擎或 MPI。未进行耗时的真实 DFT、频率、光谱或晶胞优化计算；XML 通过不代表这些计算已经运行验证。用户脚本仍须在目标终端环境找到兼容的 `mpirun` 和 `cp2k.psmp`。

首次控制 Terminal 可能需要 macOS Automation 授权；本机允许的环境下已完成实测，其他账户的首次授权交互及拒绝情况未做系统级视觉复验，后端保留明确的拒绝/超时错误处理。程序不修改系统权限、PATH、TCC 或图标缓存。

没有测试其他 Mac、Intel、其他 macOS 版本及 Gatekeeper 分发行为。此版没有 Developer ID 或公证，不承诺可直接分发给所有用户。

## 文件清单

新增：`build_macos.sh`、`CP2K_Studio.spec`、`requirements-build.txt`、`core/app_info.py`、`core/resources.py`、`resources/icons/cp2k_studio.icns`、`scripts/macos_build_assets.py`、`scripts/verify_macos_bundle.py`、`scripts/macos_smoke.py`、`scripts/local_run_entry.py`、`tests/test_macos_packaging.py`、`docs/macos-packaging.md`、本测试记录。

修改：`main.py`；资源访问相关的 `core/schema.py`、`core/database_manager.py`、`core/presets.py`、`core/project_io.py`、`ui/app_icon.py`、`ui/main_window.py`、`ui/theme.py`；冻结适配的 `core/environment_check.py`、`core/local_run.py`；翻译相关的 `i18n/language_manager.py`、`i18n/messages.py`、`i18n/catalog_sources.py`、两种语言的 TS/QM；`README.md`、`resources/icons/README.md`、`docs/local-run.md`、`.gitignore`。

复用现有 ASE/i18n PyInstaller hooks。没有修改科学参数默认值、五种任务生成算法、数据库匹配规则或页面布局。

重新构建：

```bash
bash build_macos.sh
```
