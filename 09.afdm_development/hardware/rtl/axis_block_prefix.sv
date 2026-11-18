`timescale 1ns/1ps
// CP insertion for DEFAULT AFDM parameters: N even and 2*N*c1 integer.
// Not a general CPP phase multiplier. Source block is fully buffered first.
module axis_block_prefix #(parameter integer N=64,parameter integer L=16)(
 input logic aclk,input logic aresetn,
 input logic [31:0] s_axis_tdata,input logic s_axis_tvalid,output wire s_axis_tready,input logic s_axis_tlast,
 output wire [31:0] m_axis_tdata,output wire m_axis_tvalid,input logic m_axis_tready,output wire m_axis_tlast,
 output logic framing_error);
    logic [31:0] samples[0:N-1];
    integer load_index,emit_index;
    logic emitting;
    initial if(L<0 || L>N) $fatal(1,"Invalid prefix length");
    assign s_axis_tready=!emitting;
    assign m_axis_tvalid=emitting;
    assign m_axis_tlast=emitting && (emit_index==N+L-1);
    assign m_axis_tdata=samples[(emit_index<L)?N-L+emit_index:emit_index-L];
    always_ff @(posedge aclk) begin
        if(!aresetn) begin load_index<=0;emit_index<=0;emitting<=0;framing_error<=0;end
        else if(!emitting && s_axis_tvalid) begin
            samples[load_index]<=s_axis_tdata;
            if(s_axis_tlast!=(load_index==N-1)) framing_error<=1;
            if(load_index==N-1) begin emitting<=1;emit_index<=0;end
            else load_index<=load_index+1;
        end else if(emitting && m_axis_tready) begin
            if(emit_index==N+L-1) begin emitting<=0;load_index<=0;end
            else emit_index<=emit_index+1;
        end
    end
endmodule
