`timescale 1ns/1ps
// Fixed-length waveform memory. Load via MM2S, then pulse start.
// repeat_frame loops the stored waveform; stop takes effect at a TLAST boundary.
module axis_iq_replay #(parameter integer WORDS=64)(
 input logic aclk,input logic aresetn,input logic start,input logic stop,input logic repeat_frame,
 input logic [31:0] s_axis_tdata,input logic s_axis_tvalid,output wire s_axis_tready,input logic s_axis_tlast,
 output wire [31:0] m_axis_tdata,output wire m_axis_tvalid,input logic m_axis_tready,output wire m_axis_tlast,
 output wire loaded,output wire playing,output logic framing_error);
    typedef enum logic [1:0] {LOAD,ARMED,PLAY} state_t;
    state_t state;
    logic [31:0] memory[0:WORDS-1];
    integer index;
    logic stop_pending;
    assign s_axis_tready=(state==LOAD);
    assign m_axis_tvalid=(state==PLAY);
    assign m_axis_tdata=memory[index];
    assign m_axis_tlast=(state==PLAY && index==WORDS-1);
    assign loaded=(state!=LOAD);
    assign playing=(state==PLAY);
    always_ff @(posedge aclk) begin
        if(!aresetn) begin state<=LOAD;index<=0;stop_pending<=0;framing_error<=0;end
        else case(state)
            LOAD: if(s_axis_tvalid) begin
                memory[index]<=s_axis_tdata;
                if(s_axis_tlast!=(index==WORDS-1)) framing_error<=1;
                if(index==WORDS-1) begin state<=ARMED;index<=0;end
                else index<=index+1;
            end
            ARMED: if(start) begin state<=PLAY;index<=0;stop_pending<=0;end
            PLAY: begin
                if(stop) stop_pending<=1;
                if(m_axis_tready) begin
                    if(index==WORDS-1) begin
                        index<=0;
                        if(!repeat_frame || stop_pending || stop) state<=ARMED;
                    end else index<=index+1;
                end
            end
            default: state<=LOAD;
        endcase
    end
endmodule
