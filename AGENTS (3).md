# 给执行评测的 AI

本仓库在原 P6 分享版基础上增补 P5，用于真实编译、仿真 CPU 并比较逐条写入日志。P6 原入口 ai_judge.py 保留；新增统一入口 co_judge.py，推荐使用 P5-Q01、P5-M01、P6-Q01 等带阶段的标识。

GitHub 使用按需生成的数据布局：首次克隆可运行 `python3 prepare_cases.py`。co_judge.py 的 run/check-data 也会在对应 tests 目录完全缺失时自动生成。已有目录缺少部分文件时保留现场并报错，不默默覆盖；重建须明确调用 prepare_cases.py --force。生成是恢复固定测试集，不是修改答案使 CPU 通过。不要将派生的 tests/ 和 p5/tests/ 重新上传。

1. 读取 README.md。用 `python3 co_judge.py list` 和 `describe P5-cco` 或 `describe P6-bezal` 查找对应题目。必须先确定是 P5 还是 P6；P5 子目录有其专用说明。
2. 阅读用户提交的 Controller，确认指令行为与 opcode/funct。P6-Q01=blezalc、P6-Q12=bezal；P5-Q01=cco、P5-M01=原模拟题 pcxor。不要仅根据 ZIP 文件名或用户工程中的 Qxx 文件夹名选题。若编码或题意无法确认，先给出具体差异，再请用户澄清。
3. 用 `python3 ai_judge.py doctor` 检查环境。允许的环境内安装 Python/Icarus 或使用已有工具；若工具、权限或源码缺失，明确报告尚未运行，不能猜测 AC/WA。
4. 先保持用户源码和测试数据不变，运行 `python3 co_judge.py run <带P5或P6前缀的题号或指令名> <源码目录或ZIP> --encoding <practice或original> --json results/<名称>.json`。P5 全部使用 practice；P6 的已核实题允许 original。正常评测全题 24 点，不只挑能通过的点。
5. 结果必须包含题号、指令名、编码模式、通过数，以及每点 AC/WA/TLE/CE/RE。WA 提供首个不一致的 PC、目的、期望值和实际值；CE 提供编译诊断；说明日志位置。
6. 只能把实际执行的仿真结果报告为测试结果。`check-data` 验证的是测试集和参考模型，不证明用户 CPU 正确；阅读源码和推理也不能替代仿真。
7. 执行评测时，不为获得 AC 改写 code.txt、expected.log、case.json、周期限制或比较器。若发现测试集错误，应保留证据，明确区分测试集修正与 CPU 修正。用户授权修复 CPU 后，记录源码改动并重新运行受影响测试。
8. P6 顶层接口符合 p6_judge_tb.v 的外置 IM/DM 连接，CPU 内不打印日志。P5 顶层为 mips(clk, reset)，内部 IM/DM 读取 code.txt，CPU 的 GRF/DM 按课程格式打印写入日志，使用 p5/p5_judge_tb.v；不要把 P6 的禁止打印规则套到 P5。不把生成的 runs、用户提交的 RTL/ZIP 或本机路径写进提交到仓库的材料。

所有路径以克隆到的本仓库为准，无需依赖资料整理者的桌面、ISE 工程或其他本地目录。Python 仅使用标准库，运行仿真需要 Icarus 的 iverilog 和 vvp。
