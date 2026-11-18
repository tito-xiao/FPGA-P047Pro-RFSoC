# OOC synthesis only. Does not create or modify a vendor project or program a board.
set root [file normalize [file join [file dirname [info script]] ..]]
set out [file normalize [pwd]]
create_project -in_memory -part xczu47dr-ffve1156-2-i
set sources [glob [file join $root hardware rtl *.sv]]
read_verilog -sv $sources
foreach top {axis_complex_rotator afdm_tx_block afdm_rx_block axis_iq_replay axis_capture_window} {
    synth_design -top $top -part xczu47dr-ffve1156-2-i -mode out_of_context
    create_clock -name core_clk -period 10.0 [get_ports aclk]
    report_utilization -file [file join $out ${top}_utilization.txt]
    report_timing_summary -file [file join $out ${top}_synth_timing.txt]
    write_checkpoint -force [file join $out ${top}.dcp]
    close_design
}
puts "OOC SYNTHESIS COMPLETE: not placed/routed, not a board bitstream"
