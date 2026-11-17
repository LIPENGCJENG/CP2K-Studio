# XSD 回归文件来源

下面三份文件均为本次用户提供的真实 Materials Studio 文件，按原始字节复制，用于本地兼容性回归。源文件未修改，测试不依赖用户 Downloads 路径。

| 夹具 | 原始文件名 | SHA-256 |
|---|---|---|
| rutile_ms23.xsd | TiO2_rutile.xsd | acfe6abecd1b695616e1395880f00e86e5fdbbea14b5729abf2b63263e9ded65 |
| slab_ms23.xsd | TiO2 slab.xsd | 1d13b210b5ffd4b2192c32115f19333879b7cab1a6be138b18f49f730b9cdab3 |
| h2o_ms23.xsd | h2o.xsd | 0ea88ec5eb886e3cfcdc5ec9a9c48bb1e4c7416a56b61a648c9ea62bddfc37ac |

rutile 文件是空间群 136 的不对称表示：2 个独立位点，完整晶胞应为 Ti₂O₄，共 6 个原子；不能把显示用的 ImageMapping 数量当成原子数量。Slab 含 22 个显式原子（Ti₈O₁₄），晶胞经过旋转，其三个基矢相互正交；测试另行生成真正的非正交样例，不能把这个 Slab 误称为非正交晶胞。H₂O 为 3 个笛卡尔坐标、NONE 周期性且无晶胞。

`tests/test_xsd_import.py` 中由 ASE write() 生成的三斜样例，以及通过修改 XML 构造的损坏、空位、缺失/重复算符等样例，均明确属于合成测试，不代表额外真实 Materials Studio 版本验证。
