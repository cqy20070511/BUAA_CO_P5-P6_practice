`timescale 1ns/1ps
// P5 使用 CPU 内部的 IM/DM 与课程规定的写入日志，不依赖层次名称。
module p5_judge_tb;
    reg clk=0;
    reg reset=1;
    integer budget;
    mips dut(.clk(clk),.reset(reset));
    always #5 clk=~clk;
    initial begin
        if (!$value$plusargs("budget=%d",budget)) budget=1000;
        repeat(2) @(negedge clk);
        reset=0;
        repeat(budget) @(negedge clk);
        $display("JUDGE_END cycles=%0d",budget);
        $finish;
    end
endmodule
