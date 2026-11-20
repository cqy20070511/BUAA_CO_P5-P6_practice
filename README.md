# P6 AI Judge

给 AI 使用的北航计组 P6 加指令练习与本地仿真评测包。24 道历史资料改编题、15 道模拟题，每题 24 个独立测试点，共 936 点；另有 216 份原平台编码版本。

把本仓库链接和自己的 CPU 源码路径交给能执行命令的 AI，即可让它读取题面、调用 Icarus 仿真，报告每个测试点的 AC / WA / TLE / CE / RE。不需要启动网页或共享某台电脑的本机端口。

## 直接发给 AI 的话

```text
请克隆这个仓库，先读 README.md 和 AGENTS.md。
我的 CPU 源码位于：<填写源码目录或 ZIP 路径>。
我要测试的指令是：<填写指令名>。
请先读取对应题面并核对 Controller 里的 opcode/funct，明确选择练习编码或原平台编码。
准备 Python 和 Icarus 环境后，真实运行本题全部测试点，保存 JSON，逐点报告结果。
不要修改测试数据或标准答案。如果没有执行仿真的能力，请明确说尚未运行，不要推测 AC。
```

AI 需要能访问源码、执行命令，并安装或调用仿真器。只有文字聊天能力时，不能真正仿真 CPU。

## 环境

需要 Python 3.9 或更新版本，以及 Icarus Verilog 的 `iverilog`、`vvp` 两个命令。本版只使用 Python 标准库，不需要 pip 包、Node.js 或随仓库分发仿真器二进制。

在 Ubuntu / Debian 环境可运行：

```sh
sudo apt-get update
sudo apt-get install -y python3 iverilog
python3 ai_judge.py doctor
```

其他系统按 [Icarus 官方安装说明](https://steveicarus.github.io/iverilog/usage/installation.html) 安装。Windows 可把安装目录加入 PATH；便携版可设置 `P6_IVERILOG` 为含 `bin`、`lib` 的 Icarus 安装根目录。下面的 `python3` 在 Windows 上可换成 `py -3`。

## 使用

```sh
# 先看有哪些指令，不凭题号猜指令
python3 ai_judge.py list
python3 ai_judge.py describe bezal

# 测试自己的完整 RTL：必须明确选择编码
python3 ai_judge.py run bezal ../my-cpu --encoding original --json results/bezal.json
python3 ai_judge.py run Q01 ../blezalc-cpu.zip --encoding practice --json results/blezalc.json

# 单独复现失败点
python3 ai_judge.py run bezal ../my-cpu --encoding original --case 01 14

# 核验测试文件、代码哈希及标准答案，不运行用户 CPU
python3 ai_judge.py check-data
```

`run` 接受源码目录、ZIP、或包含全部模块的单个 `.v`。每题独立实现，不要把不同题的多个 CPU 工程混在同一份提交里。工程 testbench 会被忽略，评测统一采用仓库的 `p6_judge_tb.v`。

## 先对准指令和编码

| 本册题号 | 指令 | 功能 | 练习编码 | 原平台编码 |
|---|---|---|---|---|
| Q01 | blezalc | 有符号 rs 小于等于零时，PC 相对跳转并链接 | opcode=110000 | 未取得可核实的原编码 |
| Q12 | bezal | rt 等于零时，跳到旧 rs 并链接 | opcode=000000，funct=110110 | opcode=000000，funct=110001 |
| Q11 | shl | 交换 HI、LO | opcode=000000，funct=110101 | opcode=000000，funct=111100 |

题号是本册编号，不能直接当作平台编号。Q11—Q19 提供已核实的原平台编码；其余题只提供练习编码。命令行要求明确填写 `--encoding`，不会静默替换指令编码。完整编码和行为以 `describe` 及题目册为准。

## 文件

- `AGENTS.md`：给接手 AI 的评测步骤和报告要求。
- `cases.json`：39 题的机器可读目录，包括题面、编码、测试路径、周期上限、结束 PC。
- `tests/往年题/Qxx/01..24/`、`tests/模拟题/Mxx/01..24/`：按题和测试点分类。
- `code.txt`：练习编码机器码，每行一个 32 位字，从 0x3000 开始，填满 4096 个字。
- `code_original.txt`：有存档题的原平台编码，布局和期望日志与练习版一致。
- `expected.log`：期望的寄存器和内存写入事件，不含时间前缀。
- `case.json`：本点周期、关注 PC、完成 PC、机器码 SHA-256。
- `program.lst`：带 PC 的指令清单。
- `p6_judge_tb.v`：课程 P6 外置 IM/DM 接口的统一 testbench。
- `judge.py`、`ai_judge.py`：仿真与结果比较、AI 命令行入口。
- `model.py`、`make_cases.py`：参考语义和固定种子生成器。
- `tools/reference_cpu.v`：交叉核验数据用的行为模型，不是五级流水线设计答案。

`runs/` 保存每次运行的编译输出、逐点实际日志和 `result.json`，不提交到 Git。机器码统一使用 LF 换行，Git 的换行设置不会改变相应 SHA-256。

## 结果

| 状态 | 含义 |
|---|---|
| AC | 所有写入事件一致，并在周期上限内完成 |
| WA | PC、写入目的或数据不一致，多余事件或未知值等 |
| TLE | 已有事件前缀正确，但在周期或墙钟上限内未完成 |
| CE | 用户 RTL 编译、展开、顶层接口或提交检查失败 |
| RE | 编译器或仿真进程异常退出，或没有正常完成评测协议；需结合诊断检查环境 |
| NOT_RUN | 尚未执行仿真，例如缺少工具或参数错误；不能当作 CPU 的测试结果 |

终端实时输出每点结果，WA 提供首个期望与实际差异。JSON 同时记录题号、指令、编码、全部测试点、通过数和实际日志目录。程序退出码：全部通过为 0，已仿真但有失败点为 1，环境或参数未准备好为 2。

GRF 与 DM 写入分别按顺序比较，每条都核对 PC、目的和数据，允许 M/W 两条事件流正常交错。sb/sh 记录字节合并后的整字。不会仅比较程序结束时的寄存器状态。

PC 复位为 0x3000，GRF、HI、LO 和 DM 清零，IM 16KB、DM 12KB。程序以固定 PC 的 `$30=0xcafe` 写入作为完成标记，然后再观察流水线排空。测试点周期属于本包的练习标准，不代表官方隐藏评测阈值，也不通过内部层次路径直接检查 Busy 波形。

## 题目与题源

[往年题目册](P6_历年课上题_题目册.md)、[模拟题目册](P6_模拟上机题目册.md)、[历史来源索引](P6_历年课上题_来源索引.md)。历史回忆缺少的周期或细节已在各题“其他”注明。15 道模拟题是新编练习，不作为历史原题。

## 放到 GitHub

本目录可直接作为仓库根目录。先在自己的 GitHub 账号下建立空仓库，再把这里的内容提交并推送；具体步骤见 [GitHub 官方导入本地代码说明](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github)。当前目录只是待发布的本地分享版，不包含远程仓库地址。
