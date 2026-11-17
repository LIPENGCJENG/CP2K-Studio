# OT ENERGY_GAP 与精度帮助

第 04 页 OT Settings 的 PRECONDITIONER 下方可设置 ENERGY_GAP，单位 Ha。空白输入框显示 `Auto (-1.0)`；留空或输入 `Auto` 会将模型中的 `dft.scf.energy_gap` 保存为 `null`，不输出关键字，沿用 CP2K 原生行为。明确输入 `-1.0` 则原样输出负值，由 CP2K 按预条件器处理。

支持有限实数和科学计数法；无效或非有限输入保留为编辑草稿并显示错误。只在 OT 激活时生成 `FORCE_EVAL/DFT/SCF/OT/ENERGY_GAP`。切换 DIAGONALIZATION 后不生成 OT，已保存的 ENERGY_GAP 仍保留，重新切回可继续使用。数值采用浮点数的可往返精度输出，其他参数的序列化不变。

项目 JSON、预设及受支持的 INP 导入均保留该字段；旧项目缺少字段时默认 Auto。统一生成器用于实时预览、独立 INP 和计算包。官方 2026.1 XML 中 ENERGY_GAP 为实数，默认 -1.0；负值将选择交给 CP2K，FULL_ALL 通常应低估 HOMO–LUMO 能隙。

三个参数旁的原生 Qt 帮助图标提供 English / 简体中文说明：

- ENERGY_GAP：预条件器能隙的意义及试算建议。
- MINIMIZER：DIIS 与 CG 的速度和稳健性比较；现有默认 CG 保持不变。
- QS / EPS_DEFAULT：精度经验关系及示例。该公式是参考，不是强制校验，不自动改变默认 `1e-10` 或用户设置。

这些建议不代表已验证特定材料的最优参数；仍需比较 SCF 耗时、迭代次数和数值收敛性。XML 语法检查不等于 CP2K 实际运行验证。
