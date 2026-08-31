# Case index and evaluation prompts

This reference is for Skill maintenance and testing only. A maintainer reads it only when validating or updating the Skill; normal task execution must not read it.

## Positive prompts

### P01 Mary LD

使用 $startask-io-contract-audit 审计 mary/V3版本脚本/车道线导出_中心线组.py 与 mary/V3版本脚本/校验脚本/validate_ld_export.py 的 LD 中心线导出合同。重点核对 children 语义来源和 subtype 缺失策略。只分析，不修改文件。

### P02 HALUO BEV4D

使用 $startask-io-contract-audit 审计 哈啰/T337_260611_LZY_哈啰BEV4D数据构建/main.py、哈啰/T337_260611_LZY_哈啰BEV4D数据构建/build_bev4d_from_sendlabel.py 和哈啰/T337_260611_LZY_哈啰BEV4D数据构建/test_import_1_00022_20260708-160827_0_all_cameras_extrinsic/summary.json。分别核对 reference image、坐标变换和原始血缘。只读分析，不访问或修改远端对象。

### P03 OCC semantic mapping

使用 $startask-io-contract-audit 审计 mary/V3版本脚本/OD_点云预标_V3_occ_test_0608.py 中客户 semantic ID、operator 支持类别和预标输出之间的合同。如果当前工作区缺少客户 config.json，明确说明能确认与不能确认的范围。不要改代码。

### P04 江淮 XML

使用 $startask-io-contract-audit 审计 江淮/T339_260714_WTH_江淮-通用导出脚本/main.py、test_main.py 和 docs/superpowers/specs/2026-07-14-jianghuai-operator-driven-xml-export-design.md。把 annotation、operator、exporter 和 validator 作为独立合同层，只分析交付风险。

## Negative prompts

### N01 unrelated conversion

把 samples/demo.csv 转成一个带冻结表头的 Excel 文件。

### N02 routine frozen implementation

Startask 的 box2d 合同已经确认且 operator 不变，请直接按现有导出 Playbook 给已定位函数补一个普通 box2d 解析分支。

### N03 unrelated review

检查这个 Python 排序函数的时间复杂度和变量命名，不修改代码。
