`timescale 1ns/1ps
// Assumes an already synchronized block including its prefix; detection stays
// in CPU software. This wrapper is not an autonomous RF frame receiver.
module afdm_rx_block #(parameter integer N=64,parameter integer L=16,parameter COEFF_FILE="rx_coeff.mem")(
 input logic aclk,input logic aresetn,
 input logic [31:0] s_axis_tdata,input logic s_axis_tvalid,output wire s_axis_tready,input logic s_axis_tlast,
 output wire [31:0] m_axis_tdata,output wire m_axis_tvalid,input logic m_axis_tready,output wire m_axis_tlast,
 output wire framing_error,output wire [31:0] saturation_words);
    wire [31:0] data;
    wire valid,ready,last,e1,e2;
    axis_prefix_strip #(.N(N),.L(L)) stripper(
      aclk,aresetn,s_axis_tdata,s_axis_tvalid,s_axis_tready,s_axis_tlast,data,valid,ready,last,e1);
    axis_afdm_transform #(.N(N),.COEFF_FILE(COEFF_FILE)) transform(
      aclk,aresetn,data,valid,ready,last,m_axis_tdata,m_axis_tvalid,m_axis_tready,m_axis_tlast,e2,saturation_words);
    assign framing_error=e1|e2;
endmodule
