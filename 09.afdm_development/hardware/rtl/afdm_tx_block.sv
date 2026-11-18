`timescale 1ns/1ps
// Payload block transform + CP (valid for the default AFDM chirp parameters).
// Preamble/training/framing, clock crossings and RFDC formatting are external.
module afdm_tx_block #(parameter integer N=64,parameter integer L=16,parameter COEFF_FILE="tx_coeff.mem")(
 input logic aclk,input logic aresetn,
 input logic [31:0] s_axis_tdata,input logic s_axis_tvalid,output wire s_axis_tready,input logic s_axis_tlast,
 output wire [31:0] m_axis_tdata,output wire m_axis_tvalid,input logic m_axis_tready,output wire m_axis_tlast,
 output wire framing_error,output wire [31:0] saturation_words);
    wire [31:0] data;
    wire valid,ready,last,e1,e2;
    axis_afdm_transform #(.N(N),.COEFF_FILE(COEFF_FILE)) transform(
      aclk,aresetn,s_axis_tdata,s_axis_tvalid,s_axis_tready,s_axis_tlast,
      data,valid,ready,last,e1,saturation_words);
    axis_block_prefix #(.N(N),.L(L)) prefixer(
      aclk,aresetn,data,valid,ready,last,m_axis_tdata,m_axis_tvalid,m_axis_tready,m_axis_tlast,e2);
    assign framing_error=e1|e2;
endmodule
