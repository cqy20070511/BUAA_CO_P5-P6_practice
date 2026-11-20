`timescale 1ns/1ps
// 数据交叉核验用的顺序行为模型，不是五级流水线答案。
`ifndef P5_PROBLEM
`define P5_PROBLEM 1
`endif
module mips(input clk,input reset);
    localparam P=`P5_PROBLEM;
    reg [31:0] rom[0:4095],mem[0:3071],r[0:31];
    reg [31:0] pc,instruction,pending_target;
    reg pending;
    integer rs,rt,rd,op,fn,destination,code;
    integer i,count,run_length,best,remaining,high_count,low_count;
    reg is_r,custom,branch,annul,taken,old_slot;
    reg [31:0] a,b,imm,address,word_value,value,tmp,other,amount,target,mixed;
    reg [15:0] halfword;
    reg [7:0] data_byte;
    reg signed [32:0] sum33;
    reg signed [31:0] arithmetic_result;
    integer n;
    initial $readmemh("code.txt",rom);

    function [31:0] pop;
        input [31:0] x;
        integer j;
        begin pop=0;for(j=0;j<32;j=j+1)pop=pop+x[j];end
    endfunction
    function [31:0] leading;
        input [31:0] x;
        input bit_value;
        integer j;
        reg stopped;
        begin
            leading=0;stopped=0;
            for(j=31;j>=0;j=j-1)begin
                if(!stopped && x[j]==bit_value)leading=leading+1;
                else stopped=1;
            end
        end
    endfunction

    always @(posedge clk)begin
        if(reset)begin
            pc=32'h3000;pending=0;pending_target=0;
            for(n=0;n<32;n=n+1)r[n]=0;
            for(n=0;n<3072;n=n+1)mem[n]=0;
        end else begin
            instruction=rom[(pc-32'h3000)>>2];
            op=instruction[31:26];fn=instruction[5:0];rs=instruction[25:21];rt=instruction[20:16];rd=instruction[15:11];
            a=r[rs];b=r[rt];imm={{16{instruction[15]}},instruction[15:0]};
            address=a+imm;destination=0;value=0;branch=0;annul=0;taken=0;target=pc+8;
            sum33=$signed({a[31],a})+$signed({b[31],b});
            code=0;is_r=0;
            case(P)
              1:begin is_r=1;code='h30;end 2:code='h30;3:code='h31;
              4:begin is_r=1;code='h31;end 5:code='h32;6:code='h33;
              7:begin is_r=1;code='h32;end 8:code='h34;9:code='h35;10:code='h36;11:code='h37;12:code='h38;
              13:begin is_r=1;code='h33;end 14:code='h39;15:code='h3a;
              16:begin is_r=1;code='h34;end 17:code='h3b;18:code='h3c;19:code='h3d;
              20:begin is_r=1;code='h35;end 21:code='h3e;22:code='h3f;23:code='h10;24:code='h11;25:code='h12;
              26:begin is_r=1;code='h36;end 27:code='h13;28:code='h15;29:code='h16;
              201:begin is_r=1;code='h38;end 202:begin is_r=1;code='h39;end
              203:code='h30;204:code='h31;205:code='h32;206:code='h33;207:code='h34;208:code='h35;209:code='h36;210:code='h37;
              301:code='h27;
            endcase
            custom=is_r?(op==0 && fn==code):(op==code);
            if(custom)begin
                case(P)
                  1:begin destination=rd;value=pop(a&b);end
                  4:begin
                      count=0;best=0;
                      for(i=31;i>=0;i=i-1)begin
                          if(a[i])count=count+1;else count=0;
                          if(count>best)best=count;
                      end
                      destination=rd;value=best;
                  end
                  7:begin
                      amount=b&31;destination=rd;
                      if(amount==0)value=a;
                      else if(b[0])value=(a<<amount)|(a>>(32-amount));
                      else value=(a>>amount)|(a<<(32-amount));
                  end
                  11:begin
                      tmp={16'hffff,instruction[15:0]};
                      sum33=$signed({a[31],a})+$signed({1'b1,tmp});
                      destination=rt;value=(sum33[32]==sum33[31])?sum33[31:0]:tmp;
                  end
                  13:begin
                      tmp=a;remaining=0;
                      // 不用有符号 integer 存放可能为 0xffffffff 的剩余数量。
                      other=b;
                      for(i=0;i<32;i=i+1)if(!tmp[i] && other!=0)begin tmp[i]=1;other=other-1;end
                      destination=rd;value=tmp;
                  end
                  16:begin destination=rd;value=a^(b&32'h55555555);end
                  19:begin
                      tmp=a+imm;other=-tmp;
                      mixed=other[31]?-other:other;
                      destination=rt;value={other[31],mixed[30:0]};
                  end
                  20:begin
                      destination=rd;
                      value=leading(a,0)>leading(b,1)?{a[31:16],b[15:0]}:{b[31:16],a[15:0]};
                  end
                  23:begin
                      arithmetic_result=$signed(b)>>>instruction[4:0];
                      destination=rs;value=(b<<instruction[15:11])^arithmetic_result;
                  end
                  26:begin destination=rd;value=a+b;end
                  201:begin destination=rd;value=pop(a^b);end
                  202:begin tmp=a>>(b&31);destination=rd;value={{24{tmp[7]}},tmp[7:0]};end
                  203:begin
                      sum33=$signed({a[31],a})+$signed({{17{instruction[15]}},instruction[15:0]});
                      destination=rt;
                      if(sum33>33'sd2147483647)value=32'h7fffffff;
                      else if(sum33 < -33'sd2147483648)value=32'h80000000;
                      else value=sum33[31:0];
                  end
                  3,6,9,12,15,18,22,25,29,207,208,209,210:begin
                      if(P==18 || P==25 || P==210)address=a+(imm<<2);
                      word_value=mem[address>>2];
                      halfword=address[1]?word_value[31:16]:word_value[15:0];
                      tmp=word_value>>(8*address[1:0]);data_byte=tmp[7:0];
                      case(P)
                        3:begin
                            sum33=$signed({r[31][31],r[31]})+$signed({word_value[31],word_value});
                            if(sum33[32]==sum33[31])begin destination=31;value=sum33[31:0];end
                        end
                        6:begin destination=word_value[4:0];value=b;end
                        9:begin destination=pop({16'b0,halfword})>8?rt:31;value=pop({16'b0,halfword})>8?{16'b0,halfword}:pc+4;end
                        12,208:begin destination=data_byte[7]?rs:rt;value={{24{data_byte[7]}},data_byte};end
                        15:begin destination=word_value[3:0];value=rt;end
                        18:begin destination=word_value[31]?rt:word_value[3:0];value=word_value;end
                        22:begin
                            high_count=pop({16'b0,word_value[31:16]});low_count=pop({16'b0,word_value[15:0]});
                            destination=high_count>low_count?31:high_count;value=word_value^b;
                        end
                        25:begin
                            mixed=word_value^b;destination=0;
                            if(mixed[31:16]==mixed[15:0])begin for(i=0;i<32;i=i+1)if(mixed[i])destination=i;end
                            else destination=31;
                            value=word_value;
                        end
                        29:begin destination=word_value[0]?31:rt;value=word_value;end
                        207:if(word_value!=0)begin destination=rt;value=word_value;end
                        209:begin
                            sum33=$signed({word_value[31],word_value})+$signed({b[31],b});
                            if(sum33[32]==sum33[31] && sum33[0])begin destination=rt;value=sum33[31:0];end
                        end
                        210:begin mixed=word_value^b;destination=mixed[31]?rt:mixed[3:0];value=word_value;end
                      endcase
                  end
                  default:begin
                      branch=1;tmp=pc+4+(imm<<2);
                      case(P)
                        2:begin taken=$signed(a)>=0;destination=31;value=pc+8;annul=!taken;end
                        5:begin taken=$signed(a)<=0;if(taken)begin destination=31;value=pc+8;end end
                        8:begin taken=sum33==0;destination=31;value=pc+8;annul=!taken;end
                        10:begin taken=$signed(a)<0;destination=31;value=pc+8;tmp=tmp+((32'b1<<b[1:0])<<2);end
                        14:begin other=$signed(a)<$signed(b)?a:b;taken=!other[0];destination=31;value=pc+8;annul=!taken;end
                        17:begin taken=tmp<(a+b);destination=31;value=pc+8;annul=!taken;end
                        21:begin other=a>>instruction[2:0];taken=other[7:0]>21;annul=!taken;if(taken)begin destination=rt;value=pc+8;end end
                        24:begin taken=leading(a,1)>(b&63);destination=31;value=pc+8;end
                        27:begin taken=$signed(a)<=0;destination=31;value=pc+8;end
                        28:begin taken=sum33[32]!=sum33[31];if(taken)begin destination=31;value=pc+8;end end
                        204:begin taken=sum33<0;annul=!taken;end
                        205:begin taken=a[15:0]<=b[15:0];if(taken)begin destination=31;value=pc+8;end end
                        206:begin taken=a[0];destination=31;value=pc+8;annul=!taken;end
                        301:begin taken=$signed(a)<0;tmp=pc+4+(imm<<(2+b[1:0]));if(taken)begin destination=31;value=pc+8;end end
                      endcase
                      target=taken?tmp:(P==17?a+b:(P==206?b+(a&12):pc+8));
                  end
                endcase
            end else if(instruction==0)begin end
            else if(op==0)begin
                case(fn)
                  'h20,'h21:begin destination=rd;value=a+b;end
                  'h22,'h23:begin destination=rd;value=a-b;end
                  8:begin branch=1;target=a;end
                endcase
            end else begin
                case(op)
                  'hf:begin destination=rt;value={instruction[15:0],16'b0};end
                  'hd:begin destination=rt;value=a|{16'b0,instruction[15:0]};end
                  'h23:begin destination=rt;value=mem[address>>2];end
                  'h2b:begin mem[address>>2]=b;$display("%0d@%h: *%h <= %h",$time,pc,address,b);end
                  4:begin branch=1;target=a==b?pc+4+(imm<<2):pc+8;end
                  2,3:begin branch=1;target={pc[31:28],instruction[25:0],2'b00};if(op==3)begin destination=31;value=pc+8;end end
                endcase
            end
            if(destination!=0)begin r[destination]=value;$display("%0d@%h: $%0d <= %h",$time,pc,destination,value);end
            old_slot=pending;
            if(old_slot)begin pc=pending_target;pending=0;end
            else if(branch && annul)begin pc=target;pending=0;end
            else begin pc=pc+4;if(branch)begin pending=1;pending_target=target;end end
        end
    end
endmodule
