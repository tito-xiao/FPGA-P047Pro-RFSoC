`timescale 1ns/1ps
// IQ packing: [31:16]=signed Q, [15:0]=signed I. One complex sample/beat.
// Elastic output register, ROM index advances only on input handshake.
module axis_complex_rotator #(
    parameter integer N=64,
    parameter COEFF_FILE="rot_coeff.mem"
)(input logic aclk, input logic aresetn,
  input logic [31:0] s_axis_tdata,input logic s_axis_tvalid,output wire s_axis_tready,input logic s_axis_tlast,
  output logic [31:0] m_axis_tdata,output logic m_axis_tvalid,input logic m_axis_tready,output logic m_axis_tlast,
  output logic framing_error);
    logic [31:0] coeff[0:N-1];
    integer index;
    initial $readmemh(COEFF_FILE,coeff);
    wire signed [15:0] ai=s_axis_tdata[15:0], aq=s_axis_tdata[31:16];
    wire signed [15:0] ci=coeff[index][15:0], cq=coeff[index][31:16];
    wire signed [31:0] p0=ai*ci, p1=aq*cq, p2=ai*cq, p3=aq*ci;
    wire signed [32:0] real_sum={p0[31],p0}-{p1[31],p1};
    wire signed [32:0] imag_sum={p2[31],p2}+{p3[31],p3};
    function automatic [15:0] scaled_sat(input logic signed [32:0] value);
        logic signed [32:0] shifted;
        begin
            shifted=value >>> 15;
            if(shifted>32767) scaled_sat=16'h7fff;
            else if(shifted< -32768) scaled_sat=16'h8000;
            else scaled_sat=shifted[15:0];
        end
    endfunction
    assign s_axis_tready=(!m_axis_tvalid || m_axis_tready);
    always_ff @(posedge aclk) begin
        if(!aresetn) begin
            index<=0;m_axis_tvalid<=0;m_axis_tdata<=0;m_axis_tlast<=0;framing_error<=0;
        end else if(s_axis_tready) begin
            m_axis_tvalid<=s_axis_tvalid;
            if(s_axis_tvalid) begin
                m_axis_tdata<={scaled_sat(imag_sum),scaled_sat(real_sum)};
                m_axis_tlast<=s_axis_tlast;
                if(s_axis_tlast!=(index==N-1)) framing_error<=1;
                if(s_axis_tlast || index==N-1) index<=0;
                else index<=index+1;
            end
        end
    end
endmodule
