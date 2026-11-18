`timescale 1ns/1ps
module axis_prefix_strip #(parameter integer N=64,parameter integer L=16)(
 input logic aclk,input logic aresetn,
 input logic [31:0] s_axis_tdata,input logic s_axis_tvalid,output wire s_axis_tready,input logic s_axis_tlast,
 output wire [31:0] m_axis_tdata,output wire m_axis_tvalid,input logic m_axis_tready,output wire m_axis_tlast,
 output logic framing_error);
    integer index;
    assign s_axis_tready=(index<L) || m_axis_tready;
    assign m_axis_tvalid=s_axis_tvalid && (index>=L);
    assign m_axis_tdata=s_axis_tdata;
    assign m_axis_tlast=(index==N+L-1);
    always_ff @(posedge aclk) begin
        if(!aresetn) begin index<=0;framing_error<=0;end
        else if(s_axis_tvalid && s_axis_tready) begin
            if(s_axis_tlast!=(index==N+L-1)) framing_error<=1;
            if(index==N+L-1) index<=0;
            else index<=index+1;
        end
    end
endmodule
