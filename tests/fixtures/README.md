# 回归基准

两份 `upstream_*.inp` 为 CP2K **v2026.1** 官方回归输入，保持原文：

- [He2_none.inp](https://github.com/cp2k/cp2k/blob/v2026.1/tests/QS/regtest-ot/He2_none.inp)：ENERGY。
- [H2O-geo-ot-evals.inp](https://github.com/cp2k/cp2k/blob/v2026.1/tests/QS/regtest-ot/H2O-geo-ot-evals.inp)：GEO_OPT。
- `upstream_TEST_FILES.toml` 是同目录的官方预期能量记录。

上游版权与 GPL 许可证见 `schemas/CP2K-LICENSE`。这些输入包含刻意缩短迭代、允许不收敛等回归测试设置，不是生产计算推荐参数。

测试先用 2026.1 XML 解析完整原文，再将应用支持的字段投影到明确构造的测试配置，比较生成输入中的 GLOBAL、SCF 阈值与迭代数、网格截断、泛函、逐元素基组/赝势、晶胞、坐标和 GEO_OPT。上游的打印配置、外推和测试专用开关不在本期模型范围内。没有实现任意 INP 导入。

He2 测试配置明确设置 charge=+1、multiplicity=2、UKS；水测试明确设置 charge=0、multiplicity=1。这些值只属于测试夹具，不会成为程序默认值。

`generated_ot.inp` 和 `generated_diagonalization.inp` 是 Studio 自身的精确文本快照，用于检查输出格式和两个 SCF/MOTION 分支的稳定性。

`upstream_vibrational_raman.inp` 原样取自 [v2026.1/tests/QS/regtest-gpw-2-1/N2_raman.inp](https://github.com/cp2k/cp2k/blob/v2026.1/tests/QS/regtest-gpw-2-1/N2_raman.inp)。用于检查顶层振动 Section、INTENSITIES、POLAR 激活、DO_RAMAN 和非周期偶极算符。其较松收敛阈值和测试迭代参数不被用作应用默认值；原文同时请求 IR 与 Raman，Studio 当前按三种独立模式生成其中所需的 Section。

本测试套件不调用 CP2K，也不将解析通过解释为重现了上游能量或证明了科学收敛。

`upstream_cell_opt_argon.inp` 原样来自 [v2026.1/tests/QS/regtest-spgr-id/argon.inp](https://github.com/cp2k/cp2k/blob/v2026.1/tests/QS/regtest-spgr-id/argon.inp)。用于核对 CELL_OPT 的 DIRECT_CELL_OPT 与 FORCE_EVAL/ANALYTICAL 应力结构，并用内置 XML 解析完整输入。源文件中的额外 GEO_OPT、色散、空间群检测及测试迭代选项不被用作应用默认值；Studio 的 DIRECT_CELL_OPT 不生成额外 GEO_OPT。Si 测试晶体由 ASE 合成，不是真实计算结果或收敛基准。

该历史文件保留了后来已移除的 CELL_OPT/TYPE。现在测试确认历史 XML 仍能解析它，但应用兼容性检查必须拒绝该关键字；不能据此夹具宣称新版可执行程序可运行。生成器的生产输入省略 TYPE，其他合法 TYPE（例如 DFTD3）不会被全局删除。
