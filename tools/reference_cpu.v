`timescale 1ns/1ps
// 验证数据用的行为模型，不是五级流水线作业答案。
// 与 Python 模型独立执行机器码；通过 PROBLEM 和 ORIGINAL 选择一题。
`ifndef PROBLEM
`define PROBLEM 11
`endif
`ifndef ORIGINAL
`define ORIGINAL 0
`endif
module mips(input clk, input reset, input [31:0] i_inst_rdata, m_data_rdata,
    output [31:0] i_inst_addr, m_data_addr, m_data_wdata, output [3:0] m_data_byteen,
    output [31:0] m_inst_addr, output w_grf_we, output [4:0] w_grf_addr,
    output [31:0] w_grf_wdata, w_inst_addr);
    localparam P = `PROBLEM;
    localparam ORIGINAL = `ORIGINAL;
    reg [31:0] r[0:31];
    reg [31:0] pc,hi,lo,pending_target,pending_hi,pending_lo;
    reg in_slot;
    integer busy;
    wire [5:0] op=i_inst_rdata[31:26], fn=i_inst_rdata[5:0];
    wire [4:0] rs=i_inst_rdata[25:21],rt=i_inst_rdata[20:16],rd=i_inst_rdata[15:11];
    wire [31:0] a=r[rs],b=r[rt];
    wire [31:0] immediate={{16{i_inst_rdata[15]}},i_inst_rdata[15:0]};
    reg [31:0] address,write_data,reg_data,nh,nl,target,word_value,value32,tmp32,sum_a,sum_b,rot_a,rot_b;
    reg [3:0] byteen;
    reg [4:0] destination;
    reg transfer,hilo,reads_hilo,stalled,custom;
    reg [63:0] product,result64;
    reg signed [63:0] signed_product;
    reg signed [32:0] diff;
    reg [32:0] abs_diff;
    reg [7:0] bytes[0:3],tmp_byte,chosen;
    reg [15:0] halfword;
    reg [31:0] larger,smaller;
    integer counts[0:3];
    integer i,j,k,count,best,temp_count,highest,lowest,flip,latency,number,dest_num;
    integer code,form;
    reg found;
    // form: 0=R, 1=I, 2=J。题号 101..115 是 M01..M15。
    always @* begin
        code=0;form=0;
        case(P)
          1:begin form=1;code='h30;end 2:code='h30;
          3:begin form=1;code='h31;end 4:code='h31;5:code='h32;
          6:begin form=1;code='h32;end 7:code='h33;
          8:begin form=1;code='h33;end 9:code='h34;
          10:begin form=1;code='h34;end 11:code=ORIGINAL?'h3c:'h35;
          12:code=ORIGINAL?'h31:'h36;13:code=ORIGINAL?'h31:'h37;
          14:begin form=1;code=ORIGINAL?'h2c:'h35;end
          15:begin form=2;code='h36;end 16:code=ORIGINAL?'h2c:'h38;
          17:begin form=1;code=ORIGINAL?'h2a:'h37;end
          18:begin form=1;code=ORIGINAL?'h2c:'h38;end
          19:begin form=1;code=ORIGINAL?'h19:'h39;end
          20:code='h39;21:begin form=1;code='h3a;end
          22:code='h3a;23:begin form=1;code='h3b;end 24:code='h3b;
          101:code='h30;102:code='h31;103:code='h32;
          104:begin form=1;code='h30;end 105:begin form=2;code='h31;end
          106:code='h33;107:code='h34;108:code='h35;109:code='h36;
          110:begin form=1;code='h32;end 111:begin form=1;code='h33;end
          112:begin form=1;code='h34;end 113:begin form=1;code='h35;end
          114:begin form=1;code='h36;end 115:begin form=1;code='h37;end
        endcase
        custom=(form==0) ? op==0 && fn==code : op==code;
    end
    always @* begin
        address=a+immediate;write_data=b;byteen=0;destination=0;reg_data=0;
        target=pc+8;transfer=0;hilo=0;reads_hilo=0;nh=hi;nl=lo;latency=0;
        word_value=m_data_rdata;
        halfword=address[1] ? word_value[31:16] : word_value[15:0];
        value32=word_value>>(address[1:0]*8);
        product=0;signed_product=0;result64=0;larger=0;smaller=0;
        tmp32=0;diff=0;abs_diff=0;sum_a=0;sum_b=0;rot_a=0;rot_b=0;
        tmp_byte=0;chosen=0;found=0;
        count=0;best=0;temp_count=0;highest=0;lowest=0;flip=0;number=0;dest_num=0;
        for(i=0;i<4;i=i+1) begin bytes[i]=0;counts[i]=0;end
        if(custom) begin
            case(P)
              1:begin transfer=1;if($signed(a)<=0) begin destination=31;reg_data=pc+8;target=pc+4+(immediate<<2);end end
              2:begin reads_hilo=1;if($signed(a)>0) begin
                  signed_product=$signed(a)*$signed(b);{nh,nl}=signed_product;hilo=1;latency=5;end end
              3:begin destination=(word_value>='h3000 && word_value[1:0]==0)?31:rt;reg_data=word_value;end
              4:begin transfer=1;destination=rd;reg_data=pc+8;if($signed(a)>=0)target=b;end
              5,24:begin reads_hilo=1;hilo=1;latency=5;signed_product=$signed(a)*$signed(b);
                  if(P==5) result64={hi,lo}-signed_product;else result64={hi,lo}+signed_product;
                  {nh,nl}=result64;end
              6:begin if(!address[0]) begin destination=rt;reg_data={{24{value32[7]}},value32[7:0]};end end
              7:begin destination=rd;count=0;found=0;
                  for(i=31;i>=0;i=i-1) begin if(!found && !a[i])count=count+1;if(a[i])found=1;end
                  reg_data=count;end
              8:begin if(!address[0]) begin destination=rt;reg_data={{16{halfword[15]}},halfword};end end
              9:begin reads_hilo=1;hilo=1;latency=10;larger=a>=b?a:b;smaller=a>=b?b:a;nh=larger%smaller;nl=larger/smaller;end
              10:begin count=0;for(i=0;i<16;i=i+1)count=count+halfword[i];
                   destination=count>8?rt:31;reg_data=count>8?{{16{halfword[15]}},halfword}:pc+4;end
              11:begin reads_hilo=1;hilo=1;nh=lo;nl=hi;end
              12:begin transfer=1;if(b==0)begin target=a;destination=31;reg_data=pc+8;end end
              13:begin
                  for(i=0;i<4;i=i+1) begin bytes[i]=a>>(8*i);counts[i]=0;
                      for(k=0;k<8;k=k+1)counts[i]=counts[i]+bytes[i][k];end
                  for(i=0;i<3;i=i+1)for(j=0;j<3-i;j=j+1)
                    if((b[0] && counts[j]>counts[j+1]) || (!b[0] && counts[j]<counts[j+1]))begin
                        tmp_byte=bytes[j];bytes[j]=bytes[j+1];bytes[j+1]=tmp_byte;
                        temp_count=counts[j];counts[j]=counts[j+1];counts[j+1]=temp_count;end
                  destination=rd;reg_data={bytes[3],bytes[2],bytes[1],bytes[0]};end
              14:begin address={address[31:2],2'b00};tmp32=word_value-b;destination=tmp32[4:0];reg_data=word_value;end
              15,105:begin
                  address=(P==15)?r[29]:r[29]-4;write_data=pc+8;byteen=15;
                  destination=29;reg_data=r[29]-4;transfer=1;target={pc[31:28],i_inst_rdata[25:0],2'b00};end
              16:begin reads_hilo=1;hilo=1;latency=3;nh=$signed(a)%$signed(b);nl=$signed(a)/$signed(b);end
              17:begin address={address[31:2],2'b00};destination=$signed(word_value)>$signed(b)?5:4;reg_data=word_value;end
              18:begin transfer=1;diff=$signed({a[31],a})-$signed({b[31],b});abs_diff=diff<0?-diff:diff;
                   target=pc+4+(immediate<<2)+{abs_diff[29:0],2'b00};end
              19:begin address={address[31:2],2'b00};tmp32=(word_value+b)&32'h1e;destination=tmp32[4:0];reg_data=word_value;end
              20:begin reads_hilo=1;hilo=1;latency=3;product={32'b0,a}*{32'b0,b};
                   if(product[63:32]!=0)begin
                     found=0;
                     for(i=0;i<64;i=i+1)begin
                       if(product[i])highest=i;
                       if(!found && !product[i])begin lowest=i;found=1;end end
                     flip=highest>=lowest?highest-lowest:lowest-highest;product=product^(64'b1<<flip);end
                   {nh,nl}=product;end
              21:begin transfer=1;tmp32=a+b;target=pc+4+(immediate<<2)+{tmp32[30:1],2'b00};end
              22:begin rot_a=a;rot_b=b;sum_a=0;sum_b=0;
                   for(i=0;i<32;i=i+1)begin sum_a=sum_a+rot_a;sum_b=sum_b+rot_b;
                     rot_a={rot_a[0],rot_a[31:1]};rot_b={rot_b[0],rot_b[31:1]};end
                   destination=rd;reg_data=$signed(sum_a)<$signed(sum_b)?32'hffffffff:($signed(sum_a)>$signed(sum_b)?1:0);end
              23,115:begin address={address[31:2],2'b00};tmp32=P==23?word_value:(word_value^b);number=tmp32[4:0];
                   if(number>=2)dest_num=2;if(number>=3)dest_num=3;if(number>=5)dest_num=5;
                   if(number>=7)dest_num=7;if(number>=11)dest_num=11;if(number>=13)dest_num=13;
                   if(number>=17)dest_num=17;if(number>=19)dest_num=19;if(number>=23)dest_num=23;
                   if(number>=29)dest_num=29;if(number>=31)dest_num=31;
                   destination=dest_num;reg_data=word_value;end
              101:begin destination=rd;count=0;found=0;
                   for(i=0;i<32;i=i+1)begin if(!found && !a[i])count=count+1;if(a[i])found=1;end reg_data=count;end
              102:begin best=-1;
                   for(i=0;i<4;i=i+1)begin tmp_byte=a>>(8*i);count=0;
                     for(j=0;j<8;j=j+1)count=count+tmp_byte[j];
                     if(count>best || (b[0] && count==best))begin best=count;chosen=tmp_byte;end end
                   destination=rd;reg_data={{24{chosen[7]}},chosen};end
              103:begin transfer=1;if($signed(a)>=0)begin target=b;destination=31;reg_data=pc+8;end end
              104:begin transfer=1;tmp32=a^b;if(!(^tmp32))begin destination=31;reg_data=pc+8;target=pc+4+(immediate<<2);end end
              106:begin reads_hilo=1;if(a[0])begin hilo=1;latency=5;product={32'b0,a}*{32'b0,b};{nh,nl}={hi,lo}+product;end end
              107:begin reads_hilo=1;hilo=1;{nh,nl}=64'b0-{hi,lo};end
              108:begin reads_hilo=1;hilo=1;latency=5;larger=a[31]?(~a+1):a;smaller=b[31]?(~b+1):b;
                   nh=larger%smaller;nl=larger/smaller;end
              109:begin reads_hilo=1;hilo=1;latency=3;product={32'b0,a}*{32'b0,b};
                   {nh,nl}=product[0]?{product[31:0],product[63:32]}:product;end
              110:begin if(value32[7:0]!=0)begin destination=rt;reg_data={{24{value32[7]}},value32[7:0]};end end
              111:begin if(b[0])begin byteen=address[1]?12:3;write_data={b[15:0],b[15:0]};end end
              112:begin destination=halfword[15]?31:rt;reg_data={{16{halfword[15]}},halfword};end
              113:begin address={address[31:2],2'b00};tmp32=word_value^b;destination=tmp32[4:0];reg_data=word_value;end
              114:begin address={address[31:2],2'b00};destination=word_value>b?rt:rs;reg_data=word_value;end
            endcase
        end else if(op==0) begin
            case(fn)
              'h20:begin destination=rd;reg_data=a+b;end
              'h22:begin destination=rd;reg_data=a-b;end
              'h24:begin destination=rd;reg_data=a&b;end
              'h25:begin destination=rd;reg_data=a|b;end
              'h2a:begin destination=rd;reg_data=$signed(a)<$signed(b);end
              'h2b:begin destination=rd;reg_data=a<b;end
              8:begin transfer=1;target=a;end
              'h10:begin reads_hilo=1;destination=rd;reg_data=hi;end
              'h12:begin reads_hilo=1;destination=rd;reg_data=lo;end
              'h11:begin reads_hilo=1;hilo=1;nh=a;end
              'h13:begin reads_hilo=1;hilo=1;nl=a;end
              'h18:begin reads_hilo=1;hilo=1;latency=5;signed_product=$signed(a)*$signed(b);{nh,nl}=signed_product;end
              'h19:begin reads_hilo=1;hilo=1;latency=5;{nh,nl}={32'b0,a}*{32'b0,b};end
              'h1a:begin reads_hilo=1;hilo=1;latency=10;nh=$signed(a)%$signed(b);nl=$signed(a)/$signed(b);end
              'h1b:begin reads_hilo=1;hilo=1;latency=10;nh=a%b;nl=a/b;end
            endcase
        end else begin
            case(op)
              'hf:begin destination=rt;reg_data={i_inst_rdata[15:0],16'b0};end
              8:begin destination=rt;reg_data=a+immediate;end
              'hc:begin destination=rt;reg_data=a&{16'b0,i_inst_rdata[15:0]};end
              'hd:begin destination=rt;reg_data=a|{16'b0,i_inst_rdata[15:0]};end
              'h20:begin destination=rt;reg_data={{24{value32[7]}},value32[7:0]};end
              'h21:begin destination=rt;reg_data={{16{halfword[15]}},halfword};end
              'h23:begin destination=rt;reg_data=word_value;end
              'h28:begin byteen=1<<address[1:0];write_data={4{b[7:0]}};end
              'h29:begin byteen=address[1]?12:3;write_data={2{b[15:0]}};end
              'h2b:begin byteen=15;write_data=b;end
              4,5:begin transfer=1;if((a==b)==(op==4))target=pc+4+(immediate<<2);end
              3:begin transfer=1;destination=31;reg_data=pc+8;target={pc[31:28],i_inst_rdata[25:0],2'b00};end
            endcase
        end
        stalled=reads_hilo && busy!=0;
        if(stalled || reset)begin destination=0;byteen=0;end
    end
    assign i_inst_addr=pc;
    assign m_data_addr=address;
    assign m_data_wdata=write_data;
    assign m_data_byteen=byteen;
    assign m_inst_addr=pc;
    assign w_grf_we=destination!=0;
    assign w_grf_addr=destination;
    assign w_grf_wdata=reg_data;
    assign w_inst_addr=pc;
    integer n;
    always @(posedge clk)begin
        if(reset)begin
            pc<=32'h3000;hi<=0;lo<=0;busy<=0;in_slot<=0;
            pending_target<=0;pending_hi<=0;pending_lo<=0;
            for(n=0;n<32;n=n+1)r[n]<=0;
        end else begin
            if(busy!=0)begin busy<=busy-1;if(busy==1)begin hi<=pending_hi;lo<=pending_lo;end end
            if(!stalled)begin
                if(destination!=0)r[destination]<=reg_data;
                if(hilo)begin
                    if(latency>1)begin busy<=latency;pending_hi<=nh;pending_lo<=nl;end
                    else begin hi<=nh;lo<=nl;end
                end
                if(in_slot)begin pc<=pending_target;in_slot<=0;end
                else begin pc<=pc+4;if(transfer)begin pending_target<=target;in_slot<=1;end end
            end
        end
    end
endmodule
