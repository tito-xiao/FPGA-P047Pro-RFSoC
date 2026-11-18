`timescale 1ns/1ps
// Triggered finite window for a non-throttleable ADC stream, same clock only.
// Input is always ready. Samples outside the armed window are intentionally
// ignored. The completed window is buffered, then drained with a single TLAST.
module axis_capture_window #(parameter integer WORDS=64)(
 input logic aclk,input logic aresetn,input logic arm,
 input logic [31:0] s_axis_tdata,input logic s_axis_tvalid,output wire s_axis_tready,
 output wire [31:0] m_axis_tdata,output wire m_axis_tvalid,input logic m_axis_tready,output wire m_axis_tlast,
 output wire busy,output logic [31:0] rejected_arms);
    typedef enum logic [1:0] {IDLE,CAPTURE,DRAIN} state_t;
    state_t state;
    logic [31:0] memory[0:WORDS-1];
    integer index;
    assign s_axis_tready=1;
    assign m_axis_tvalid=(state==DRAIN);
    assign m_axis_tdata=memory[index];
    assign m_axis_tlast=(state==DRAIN && index==WORDS-1);
    assign busy=(state!=IDLE);
    always_ff @(posedge aclk) begin
        if(!aresetn) begin state<=IDLE;index<=0;rejected_arms<=0;end
        else begin
            if(arm && state!=IDLE) rejected_arms<=rejected_arms+1;
            case(state)
                IDLE: if(arm) begin state<=CAPTURE;index<=0;end
                CAPTURE: if(s_axis_tvalid) begin
                    memory[index]<=s_axis_tdata;
                    if(index==WORDS-1) begin state<=DRAIN;index<=0;end
                    else index<=index+1;
                end
                DRAIN: if(m_axis_tready) begin
                    if(index==WORDS-1) begin state<=IDLE;index<=0;end
                    else index<=index+1;
                end
                default: state<=IDLE;
            endcase
        end
    end
endmodule
