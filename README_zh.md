# RAPID: FPGA-Based Adaptive Multi-Feature Filtering for DNS Flood Mitigation

[English](README.md)

本仓库公开 RAPID 研究中的合成流量生成程序、DDiDD 基线评估工具，以及已发表结果的统计数据和核查脚本。

**RAPID 的 FPGA 实现属于保密内容，不在本仓库发布。** 不包含 RTL、硬件工程、位流、仿真接口、测试平台、硬件诊断记录或相关实现补丁；也不包含论文 LaTeX 源码、模板、作者文件及论文构建工具。

## 可以使用的内容

| 文件 | 用途 |
| --- | --- |
| `experiments_v5/generate_traffic.py` | 生成合法查询、七类攻击、五类合法流量变化场景及 DDiDD 训练统计 |
| `experiments_v5/download_ddidd.py`、`prepare_ddidd.py`、`build_ddidd.sh`、`ddidd_adapter/` | 获取、适配和构建官方 DDiDD 0.1；将查询转换成不含评估标签的输入 |
| `experiments_v5/run_ddidd.py` | 独立运行 DDiDD，不依赖 RAPID 的二进制程序或判决文件 |
| `experiments_v5/results/` | 论文使用的各次实验指标、逐秒计数、统计汇总及 DDiDD 版本记录 |
| `experiments_v5/analyze_results.py` | 从公开计数核算指标，检查逐秒结果并重算均值和置信区间 |
| `experiments_v5/PROTOCOL.md` | 合成流量与评估方案 |
| `PUBLIC_FILES.txt`、`check_public_release.py` | 公开文件白名单与发布检查 |

CSV/JSON 保留原始方法标识，便于对应原实验。例如 `rtl_n4` 表示 RAPID 的主配置，并不表示本仓库提供了 RTL。
RAPID 的结果由私有实现产生。公开部分可以复核结果统计，**不能独立重跑 RAPID、其组件/参数实验或硬件吞吐测试**。
1.1 Tb/s 来自独立硬件测试，不能与合成查询实验的拦截率组合成同一次测量。

## 使用方法

需要 Python 3.11 或更高版本及 NumPy 2.3.5；运行 DDiDD 还需要 C++11 编译器，以及 Linux/macOS 环境。
在仓库根目录执行：

```sh
python3 -m pip install -r experiments_v5/requirements.txt
python3 experiments_v5/analyze_results.py
```

该命令核对 750 行指标及 5,400 行逐秒计数，并将重算结果写入 `experiments_v5/recomputed/summary.json`。
这属于结果的数值一致性检查，不是重新执行私有检测器。

生成一个完整场景并运行 DDiDD：

```sh
python3 experiments_v5/download_ddidd.py
sh experiments_v5/build_ddidd.sh
python3 experiments_v5/generate_traffic.py --seeds 20260611 --scenarios adaptive_mixed
python3 experiments_v5/run_ddidd.py --seeds 20260611 --scenarios adaptive_mixed
```

建议先激活 Python 虚拟环境；构建脚本默认调用 `python3`，也可用 `PYTHON` 环境变量指定解释器。
离线获取时，可向下载程序传入 `--from-file /path/to/ddidd-0.1.tar.gz`，程序会检查固定的 SHA-256。

同时省略生成命令与评估命令中的 `--seeds` 和 `--scenarios`，即可执行全部五个种子、十二个场景。
全量输入约占 30 GB，另需基线运行的临时空间，建议至少预留 40 GB。默认串行处理以控制内存和临时文件规模。
新生成的数据及结果不纳入 Git，基线新结果单独保存于 `recomputed/`，不会覆盖论文使用的结果。

20260611–20260615 是伪随机数初始化参数，不是流量采集日期。数据为受控合成查询，不是运营商实测流量。
同一种子下七个攻击场景使用相同的合法背景；评估标签不传给 DDiDD。

## 发布前检查

```sh
python3 check_public_release.py --git-index
```

暂存准备发布的修改后执行此检查。仅允许 `PUBLIC_FILES.txt` 中明确列出的文件；`.gitignore` 默认排除其余路径。
保密开发目录、内部归档及旧仓库历史都不能合并到这个公开仓库。

原创公开工具适用根目录的 LICENSE；DDiDD 等第三方内容见 `THIRD_PARTY_NOTICES.md`。
公开许可证不授予未发布 FPGA 保密实现的访问权或使用权。
