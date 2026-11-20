`timescale 1ns/1ps
// 日志只由评测 testbench 输出，提交的 CPU 不需要添加任何打印。
module p6_judge_tb;
    reg clk = 0;
    reg reset = 1;
    wire [31:0] i_inst_addr, m_data_addr, m_data_wdata, m_inst_addr;
    wire [31:0] w_inst_addr, w_grf_wdata;
    wire [4:0] w_grf_addr;
    wire w_grf_we;
    wire [3:0] m_data_byteen;
    reg [31:0] inst [0:4095];
    reg [31:0] data [0:3071];
    wire [31:0] i_inst_rdata = (i_inst_addr >= 32'h3000 && i_inst_addr < 32'h7000) ?
                               inst[(i_inst_addr - 32'h3000) >> 2] : 32'b0;
    wire [31:0] m_data_rdata = m_data_addr < 32'h3000 ? data[m_data_addr >> 2] : 32'b0;
    reg [31:0] merged;
    integer i, lane, budget, cycles, finish_pc, drain;
    reg completed;
    mips dut(.clk(clk), .reset(reset), .i_inst_rdata(i_inst_rdata), .m_data_rdata(m_data_rdata),
        .i_inst_addr(i_inst_addr), .m_data_addr(m_data_addr), .m_data_wdata(m_data_wdata),
        .m_data_byteen(m_data_byteen), .m_inst_addr(m_inst_addr), .w_grf_we(w_grf_we),
        .w_grf_addr(w_grf_addr), .w_grf_wdata(w_grf_wdata), .w_inst_addr(w_inst_addr));
    always #5 clk = ~clk;
    initial begin
        if (!$value$plusargs("budget=%d", budget)) budget = 1000;
        if (!$value$plusargs("finish_pc=%h", finish_pc)) finish_pc = 0;
        $readmemh("code.txt", inst);
        for (i = 0; i < 3072; i = i+1) data[i] = 0;
        cycles = 0; completed = 0; drain = 0;
        repeat (2) @(negedge clk);
        reset = 0;
    end
    always @(posedge clk) begin
        if (!reset) begin
            cycles = cycles + 1;
            if ((^m_data_byteen) === 1'bx) begin
                $display("JUDGE_UNKNOWN byteen cycle=%0d", cycles); $finish;
            end
            if (|m_data_byteen) begin
                if ((^m_data_addr) === 1'bx || m_data_addr >= 32'h3000) begin
                    $display("JUDGE_BAD_ADDRESS %h", m_data_addr); $finish;
                end
                merged = data[m_data_addr >> 2];
                for (lane = 0; lane < 4; lane = lane+1)
                    if (m_data_byteen[lane]) merged[lane*8 +: 8] = m_data_wdata[lane*8 +: 8];
                data[m_data_addr >> 2] <= merged;
                $display("%0d@%h: *%h <= %h", cycles, m_inst_addr, m_data_addr & 32'hfffffffc, merged);
            end
            if (w_grf_we === 1'bx) begin
                $display("JUDGE_UNKNOWN grf_we cycle=%0d", cycles); $finish;
            end
            if (w_grf_we && (w_grf_addr !== 5'b0)) begin
                $display("%0d@%h: $%0d <= %h", cycles, w_inst_addr, w_grf_addr, w_grf_wdata);
                if (w_inst_addr === finish_pc && w_grf_addr === 5'd30 && w_grf_wdata === 32'hcafe) begin
                    completed = 1; drain = 4;
                end
            end
        end
    end
    // 在下降沿终止，保证同一上升沿的内存和寄存器事件全部记录。
    always @(negedge clk) begin
        if (!reset) begin
            if (completed && drain == 0) begin
                $display("JUDGE_DONE cycles=%0d", cycles); $finish;
            end
            if (completed) drain = drain - 1;
            if (!completed && cycles >= budget) begin
                $display("JUDGE_LIMIT cycles=%0d", cycles); $finish;
            end
        end
    end
endmodule
