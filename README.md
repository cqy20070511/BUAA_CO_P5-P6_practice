# P5 增补内容

在原 P6 分享仓库里新增本目录：29 道往年资料改编题、原 10 道模拟题，以及原 BLZTAL 补充题，每题 24 点，共 960 点。不包含原五道教学题。

从仓库根目录运行：

```sh
python3 co_judge.py list --stage P5
python3 co_judge.py describe P5-cco
python3 co_judge.py run P5-Q01 ../my-p5-cpu --encoding practice --json results/p5-cco.json
python3 co_judge.py run P5-M01 ../my-pcxor-cpu.zip --encoding practice
python3 co_judge.py run P5-X01 ../my-blztal-cpu --encoding practice
```

环境沿用仓库的 Python 3.9+ 和 Icarus（iverilog、vvp）。本目录也可以独立使用 `python3 ai_judge.py run Q01 <源码> --encoding practice`。

仓库以生成器和固定输入保存测试点。首次克隆可在根目录运行 `python3 prepare_cases.py --stage P5`；统一 co_judge.py 入口在 tests 完全缺失时会自动生成。测试文件是本地派生数据，不重复提交 Git。

## 与 P6 的接口区别

P5 顶层为 `mips(clk, reset)`，IM 和 DM 在 CPU 内部，IM 从仿真工作目录的 `code.txt` 读取机器码。GRF 和 DM 的有效写入通过 CPU 中的课程日志输出，格式为 `@PC: $寄存器 <= 数据`、`@PC: *地址 <= 数据`；可保留时间前缀。

评测器忽略工程自带的 testbench，使用本目录的 `p5_judge_tb.v`。不要求改变 CPU 的端口或内部实例名称。P6 的禁止 CPU 打印规则不用于 P5。

## 编号和旧测试点

| 本整合包 | 旧资料中的编号 | 内容 |
|---|---|---|
| P5-Q01—P5-Q29 | 往年题册 Q01—Q29 | 保留编码和题意，补充每题 24 个测试点 |
| P5-M01—P5-M10 | 模拟题册 Q01—Q10 | 原机器码、期望日志、周期上限保留 |
| P5-X01 | BLZTAL | 原 24 个补充测试点保留 |

模拟题和 BLZTAL 的旧测试点编号保存在每点 `legacy_id`，新入口统一使用 01—24。比如旧模拟 Q01 的 0101 对应 P5-M01 的 01。

P5 所有题使用 practice 编码。没有将博客回忆中的编码冒充已经核实的原平台编码，不能选择 original。

## 题目与数据

[往年题目册](P5_往年题目册.md)、[模拟题目册](P5_模拟题目册.md)、[BLZTAL 补充题](P5_BLZTAL补充题.md)、[来源索引](P5_历年课上题_来源索引.md)。题面采用中文描述和展开的 Verilog RTL。

每点目录包括 code.txt、expected.log、program.lst、case.json。所有字地址从 0x3000 开始，IM 填满 4096 个字，DM 每点复位清零。新增往年题点覆盖功能数据、ALU/load 生产者、0/1/2 条间隔、最新值优先、源目的重合、取消写回、动态目的、延迟槽及后向分支。第 24 点还有基础指令回归或动态目的扫描。

`legacy_cases.json` 用于原模拟题的可重建输入；`make_cases.py` 可重建全部 960 点；`model.py` 从机器码计算标准语义；`tools/reference_cpu.v` 是独立的 Verilog 行为模型，供交叉核验数据。它不是五级流水线设计答案。`tools/validate.py` 真实仿真全部 960 点，并检查 CE/WA/TLE。

## 判定与周期

逐点输出 AC、WA、TLE、CE、RE；工具缺失或参数错误显示 NOT_RUN。GRF 与 DM 写入各自按顺序核对 PC、目的和数据。原始编译与仿真输出保存在本目录 runs 下。

P5 没有统一对外写回端口，TB 会仿真至本点周期上限，比较所有写入事件并核对固定 PC 的结束标记。结果中的 cycles 是仿真运行周期，标记出现时间可在 completion_log_time 和原始日志中查看，不当作最短完成周期。周期超限且已有事件前缀正确时判 TLE，写错或多写判 WA。
