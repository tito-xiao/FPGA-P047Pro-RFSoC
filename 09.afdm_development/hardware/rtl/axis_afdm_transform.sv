`timescale 1ns/1ps
// Functional fixed-point DAFT/IDAFT: dense coefficient ROM, one complex MAC/clk.
// COEFF_FILE stores the FULL unitary matrix (including 1/sqrt(N)), Q1.15.
// Sequential reference core; no claim of a 20 MS/s or RFDC line-rate design.
module axis_afdm_transform #(
    parameter integer N=64,
    parameter COEFF_FILE="tx_coeff.mem"
)(input logic aclk,input logic aresetn,
  input logic [31:0] s_axis_tdata,input logic s_axis_tvalid,output wire s_axis_tready,input logic s_axis_tlast,
  output logic [31:0] m_axis_tdata,output logic m_axis_tvalid,input logic m_axis_tready,output logic m_axis_tlast,
  output logic framing_error,output logic [31:0] saturation_words);
    typedef enum logic [1:0] {LOAD,MAC,EMIT} state_t;
    state_t state;
    logic [31:0] samples[0:N-1],coeff[0:N*N-1];
    integer load_index,input_index,output_index;
    logic signed [47:0] acc_i,acc_q;
    initial $readmemh(COEFF_FILE,coeff);
    wire [31:0] sample_word=samples[input_index];
    wire [31:0] coeff_word=coeff[output_index*N+input_index];
    wire signed [15:0] ai=sample_word[15:0],aq=sample_word[31:16];
    wire signed [15:0] ci=coeff_word[15:0],cq=coeff_word[31:16];
    wire signed [31:0] p0=ai*ci,p1=aq*cq,p2=ai*cq,p3=aq*ci;
    wire signed [32:0] product_i={p0[31],p0}-{p1[31],p1};
    wire signed [32:0] product_q={p2[31],p2}+{p3[31],p3};
    wire signed [47:0] total_i=acc_i+{{15{product_i[32]}},product_i};
    wire signed [47:0] total_q=acc_q+{{15{product_q[32]}},product_q};
    wire signed [47:0] shifted_i=total_i >>> 15,shifted_q=total_q >>> 15;
    function automatic [15:0] saturate(input logic signed [47:0] value);
        if(value>32767) saturate=16'h7fff;
        else if(value< -32768) saturate=16'h8000;
        else saturate=value[15:0];
    endfunction
    assign s_axis_tready=(state==LOAD);
    always_ff @(posedge aclk) begin
        if(!aresetn) begin
            state<=LOAD;load_index<=0;input_index<=0;output_index<=0;
            acc_i<=0;acc_q<=0;m_axis_tdata<=0;m_axis_tvalid<=0;m_axis_tlast<=0;
            framing_error<=0;saturation_words<=0;
        end else case(state)
            LOAD: if(s_axis_tvalid) begin
                samples[load_index]<=s_axis_tdata;
                if(s_axis_tlast!=(load_index==N-1)) framing_error<=1;
                if(load_index==N-1) begin
                    input_index<=0;output_index<=0;acc_i<=0;acc_q<=0;state<=MAC;
                end else load_index<=load_index+1;
            end
            MAC: if(input_index==N-1) begin
                m_axis_tdata<={saturate(shifted_q),saturate(shifted_i)};
                m_axis_tlast<=(output_index==N-1);m_axis_tvalid<=1;
                if(shifted_i>32767 || shifted_i< -32768 || shifted_q>32767 || shifted_q< -32768)
                    saturation_words<=saturation_words+1;
                state<=EMIT;
            end else begin
                acc_i<=total_i;acc_q<=total_q;input_index<=input_index+1;
            end
            EMIT: if(m_axis_tready) begin
                m_axis_tvalid<=0;
                if(output_index==N-1) begin state<=LOAD;load_index<=0;end
                else begin
                    output_index<=output_index+1;input_index<=0;acc_i<=0;acc_q<=0;state<=MAC;
                end
            end
            default: state<=LOAD;
        endcase
    end
endmodule
