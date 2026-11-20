# P5 / P6 AI Judge

在原 P6 GitHub 分享版上补充 P5，保留原 P6 的题目、编码、测试点和命令入口。新增内容位于 p5/，不包含 P5 的五道教学题。

| 阶段 | 题目 | 独立测试点 |
|---|---|---|
| P5 | 29 道往年资料改编题、原 10 道模拟题、原 BLZTAL 补充题 | 40 × 24 = 960 |
| P6 | 原 24 道往年题、15 道模拟题 | 39 × 24 = 936 |
| 合计 | 79 题 | 1896 点，另有 216 份 P6 原平台编码版本 |

## 直接交给别人的 AI

```text
请克隆这个仓库，阅读 README.md 和 AGENTS.md。
我的阶段是：P5 或 P6。
我要测试的指令是：<指令名>。
CPU 源码目录或 ZIP 位于：<路径>。
请先用 co_judge.py describe 核对题意、opcode/funct，再选择编码。
准备 Python 和 Icarus 环境，真实仿真本题全部 24 点，保存 JSON，逐点报告 AC/WA/TLE/CE/RE。
保持原始测试和标准答案不变，不能把源码阅读或 check-data 当作 CPU 仿真通过。
```

AI 需要有源码访问和命令执行能力，以及 Python 3.9+、Icarus Verilog 的 iverilog 和 vvp。只有文字聊天能力不能真实评测。无需网页、Node.js、发布者的电脑或固定本机路径。

## 首次克隆：准备测试点

GitHub 仓库保存生成器、固定输入和题目索引，省去重复上传数千份派生文件。首次使用可以运行：

```sh
python3 prepare_cases.py
```

它会在本机生成 P5 的 960 点和 P6 的 936 点及 216 份原编码版本。已有完整数据会直接复用；已有目录不完整时会保留现场并提示明确重建。推荐的 co_judge.py run/check-data 入口也能在目录完全缺失时自动准备对应数据。

## 统一入口

```sh
python3 co_judge.py doctor
python3 co_judge.py prepare
python3 co_judge.py list
python3 co_judge.py list --stage P5
python3 co_judge.py describe P5-cco
python3 co_judge.py describe P6-bezal
python3 co_judge.py run P5-Q01 ../my-p5-cpu --encoding practice --json results/p5-cco.json
python3 co_judge.py run P5-M01 ../my-pcxor-cpu.zip --encoding practice
python3 co_judge.py run P5-X01 ../my-blztal-cpu --encoding practice
python3 co_judge.py run P6-bezal ../my-p6-cpu --encoding original --json results/p6-bezal.json
python3 co_judge.py check-data
```

Windows 可将 python3 替换为 py -3。Ubuntu/Debian 可安装 python3、iverilog 包；其他系统参见 [Icarus 官方安装说明](https://steveicarus.github.io/iverilog/usage/installation.html)。便携 Windows Icarus 可用 P6_IVERILOG 环境变量指定安装根目录。

统一入口要求 P5- 或 P6- 前缀，也可用冒号分隔，比如 P5:cco。所有命令必须明确提供编码模式，单点重现使用 --case 01 02。

## 编号与编码

- P5-Q01—P5-Q29：往年题；P5-M01—P5-M10：原模拟题 Q01—Q10；P5-X01：原 BLZTAL。
- P6-Q01—P6-Q24、P6-M01—P6-M15：原 P6 分享版，编号保持不变，只在统一入口加阶段前缀。
- P5 全部使用 practice，题册中的编码是练习协议，没有已核实的 original 模式。
- P6 保留 practice/original 两种模式；只有 P6-Q11—P6-Q19 提供原平台编码。

P5-Q01 是 cco，P5-M01 是 pcxor，P6-Q01 是 blezalc，P6-Q12 是 bezal，不能仅凭 Q01 或工程文件夹名称选题。原模拟题和 BLZTAL 的旧测试点编号记录在 legacy_id，机器码、日志和周期限制保留。

## 两种 CPU 接口

P5 的顶层为 mips(clk, reset)，IM/DM 位于 CPU 内部，IM 读取仿真目录的 code.txt，GRF/DM 按课程格式打印写入日志，使用 p5/p5_judge_tb.v。

P6 使用原 p6_judge_tb.v，IM/DM 外置，通过 mips 顶层端口采集写入。P6 CPU 内不打印日志。两个阶段分别编译和仿真，不把 P6 的接口或禁止打印规则用于 P5。

## 原 P6 入口保留

原有命令继续使用，题号只解释为 P6：

```sh
python3 prepare_cases.py --stage P6
python3 ai_judge.py run bezal ../my-p6-cpu --encoding original
python3 ai_judge.py run Q11 ../my-p6-cpu --encoding practice
```

原 P6 数据仍在根目录 tests/，原 cases.json 仍是 P6 目录。新增 P5 数据与脚本在 p5/。catalog.json 为统一题目索引，bundle.json 记录整合包结构。

## 资料与判定

[P5 使用说明](p5/README.md)、[P5 往年题册](p5/P5_往年题目册.md)、[P5 模拟题册](p5/P5_模拟题目册.md)、[P5 BLZTAL](p5/P5_BLZTAL补充题.md)、[P5 来源索引](p5/P5_历年课上题_来源索引.md)。

[P6 往年题册](P6_历年课上题_题目册.md)、[P6 模拟题册](P6_模拟上机题目册.md)、[P6 来源索引](P6_历年课上题_来源索引.md)。

每点都包含 code.txt、expected.log、case.json、program.lst。有原平台编码的 P6 题另含 code_original.txt。逐条核对写入 PC、目的和数据，GRF 与 DM 各自保持事件顺序。日志写入各阶段 runs/，不会提交 Git。

结果为 AC/WA/TLE/CE/RE；环境或参数缺失为 NOT_RUN。JSON 记录 stage、global_id、instruction、encoding、每点状态及首个差异。退出码 0 为全部通过，1 为已经仿真但有失败，2 为尚未运行或参数错误。P5 的 cycles 是仿真运行至预算末尾的周期，实际完成标记时间看日志，不将它冒报为最短完成周期。

题目来自历史资料改编或明确标注的模拟练习，补全规则见题面与来源索引。测试上限是本包的练习标准，不声称等于官方隐藏评测。

更新现有仓库时，同路径文件直接替换，保留原 P6 源码和题目，新增 p5/、统一入口和初始化脚本即可。不要再套一层 P6-AI-Judge 文件夹，也不重复上传本机生成的测试目录；发布步骤见 [发布说明](发布说明.md)。
