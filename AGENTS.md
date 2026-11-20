# 给执行评测的 AI

本仓库用于真实编译、仿真用户的 P6 CPU，并比较逐条写入日志。

1. 读取 README.md。用 `python3 ai_judge.py list` 和 `describe <指令名>` 查找对应题目。
2. 阅读用户提交的 Controller，确认指令行为与 opcode/funct。Q01=blezalc，Q12=bezal，二者不能互换。不要仅根据 ZIP 文件名或用户工程中的 Qxx 文件夹名选题。若编码或题意无法确认，先给出具体差异，再请用户澄清。
3. 用 `python3 ai_judge.py doctor` 检查环境。允许的环境内安装 Python/Icarus 或使用已有工具；若工具、权限或源码缺失，明确报告尚未运行，不能猜测 AC/WA。
4. 先保持用户源码和测试数据不变，运行 `python3 ai_judge.py run <题号或指令名> <源码目录或ZIP> --encoding <practice或original> --json results/<名称>.json`。正常评测全题 24 点，不只挑能通过的点。
5. 结果必须包含题号、指令名、编码模式、通过数，以及每点 AC/WA/TLE/CE/RE。WA 提供首个不一致的 PC、目的、期望值和实际值；CE 提供编译诊断；说明日志位置。
6. 只能把实际执行的仿真结果报告为测试结果。`check-data` 验证的是测试集和参考模型，不证明用户 CPU 正确；阅读源码和推理也不能替代仿真。
7. 执行评测时，不为获得 AC 改写 code.txt、expected.log、case.json、周期限制或比较器。若发现测试集错误，应保留证据，明确区分测试集修正与 CPU 修正。用户授权修复 CPU 后，记录源码改动并重新运行受影响测试。
8. 用户 CPU 顶层接口必须符合 p6_judge_tb.v 中的 mips 连接。CPU 内不打印日志，评测 TB 负责打印。不把生成的 runs、用户提交的 RTL/ZIP 或本机路径写进提交到仓库的材料。

所有路径以克隆到的本仓库为准，无需依赖资料整理者的桌面、ISE 工程或其他本地目录。Python 仅使用标准库，运行仿真需要 Icarus 的 iverilog 和 vvp。
