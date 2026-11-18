`timescale 1ns/1ps
module tb_all;
    localparam N=64,L=16,FRAMES=3,TOTAL=N*FRAMES;
    logic clk=0,rst=0;
    always #5 clk=~clk;
    logic [31:0] rng=32'h12345678;
    always @(posedge clk) if(rst) rng<={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
    logic [31:0] rot_in[0:TOTAL-1],rot_expect[0:TOTAL-1];
    logic [31:0] tx_in[0:TOTAL-1],tx_expect[0:TOTAL-1],rx_expect[0:TOTAL-1];
    initial begin
        $readmemh("rot_input.mem",rot_in);$readmemh("rot_expected.mem",rot_expect);
        $readmemh("tx_input.mem",tx_in);$readmemh("tx_expected.mem",tx_expect);$readmemh("rx_expected.mem",rx_expect);
        repeat(5) @(negedge clk);rst=1;
    end
    initial begin repeat(150000) @(posedge clk);$fatal(1,"WATCHDOG: stalled or missing beats");end

    logic [31:0] ri=0,ro;logic riv=0,rir,ril=0,rov,ror=0,rol,re;
    integer rin_count=0,rout_count=0;
    axis_complex_rotator rot(clk,rst,ri,riv,rir,ril,ro,rov,ror,rol,re);
    always @(negedge clk) begin
        if(rst) begin
            ror<=rng[1] | rng[3];
            if(rin_count<TOTAL) begin
                riv<= (riv && !rir) || rng[0];ri<=rot_in[rin_count];ril<=((rin_count%N)==N-1);
            end else riv<=0;
        end
    end
    always @(posedge clk) if(rst) begin
        if(riv && rir) rin_count<=rin_count+1;
        if(rov && ror) begin
            if(ro!==rot_expect[rout_count]) $fatal(1,"Rotator mismatch at %0d: got %h expected %h",rout_count,ro,rot_expect[rout_count]);
            if(rol!==((rout_count%N)==N-1)) $fatal(1,"Rotator TLAST mismatch");
            rout_count<=rout_count+1;
        end
    end
    logic rot_stalled=0;logic [32:0] rot_held;
    always @(posedge clk) if(rst) begin
        if(rot_stalled && (!rov || {rol,ro}!==rot_held)) $fatal(1,"Rotator changed stalled output");
        rot_stalled<=rov&&!ror;rot_held<={rol,ro};
    end

    logic [31:0] ti=0,to,rxo,po,strip_data;
    logic tiv=0,tir,til=0,tov,tor,tol,te,rxv,rxr=0,rxl,rxe,pv,pr,pl,pe;
    wire strip_valid,strip_ready,strip_last,strip_error;
    wire [31:0] tsat,rsat;
    integer tin_count=0,tx_count=0,rx_count=0,prefix_count=0;
    axis_afdm_transform #(.COEFF_FILE("tx_coeff.mem")) tx(clk,rst,ti,tiv,tir,til,to,tov,tor,tol,te,tsat);
    axis_block_prefix #(.N(N),.L(L)) prefixer(clk,rst,to,tov,tor,tol,po,pv,pr,pl,pe);
    axis_prefix_strip #(.N(N),.L(L)) stripper(clk,rst,po,pv,pr,pl,strip_data,strip_valid,strip_ready,strip_last,strip_error);
    axis_afdm_transform #(.COEFF_FILE("rx_coeff.mem")) rx(clk,rst,strip_data,strip_valid,strip_ready,strip_last,rxo,rxv,rxr,rxl,rxe,rsat);
    always @(negedge clk) if(rst) begin
        rxr<=rng[7] | rng[11];
        if(tin_count<TOTAL) begin
            tiv<=(tiv && !tir) || rng[4];ti<=tx_in[tin_count];til<=((tin_count%N)==N-1);
        end else tiv<=0;
    end
    integer source_index;
    always @(posedge clk) if(rst) begin
        if(tiv && tir) tin_count<=tin_count+1;
        if(tov && tor) begin
            if(to!==tx_expect[tx_count]) $fatal(1,"TX transform mismatch at %0d: got %h expected %h",tx_count,to,tx_expect[tx_count]);
            if(tol!==((tx_count%N)==N-1)) $fatal(1,"TX TLAST mismatch");
            tx_count<=tx_count+1;
        end
        if(rxv && rxr) begin
            if(rxo!==rx_expect[rx_count]) $fatal(1,"RX transform mismatch at %0d",rx_count);
            if(rxl!==((rx_count%N)==N-1)) $fatal(1,"RX TLAST mismatch");
            rx_count<=rx_count+1;
        end
        if(pv && pr) begin
            source_index=(prefix_count/(N+L))*N+(((prefix_count%(N+L))<L)?N-L+(prefix_count%(N+L)):(prefix_count%(N+L))-L);
            if(po!==tx_expect[source_index]) $fatal(1,"Prefix data mismatch at %0d",prefix_count);
            if(pl!==((prefix_count%(N+L))==N+L-1)) $fatal(1,"Prefix TLAST mismatch");
            prefix_count<=prefix_count+1;
        end
    end
    logic tx_stalled=0,rx_stalled=0,prefix_stalled=0;
    logic [32:0] tx_held,rx_held,prefix_held;
    always @(posedge clk) if(rst) begin
        if(tx_stalled && (!tov || {tol,to}!==tx_held)) $fatal(1,"TX output changed during stall");
        if(rx_stalled && (!rxv || {rxl,rxo}!==rx_held)) $fatal(1,"RX output changed during stall");
        if(prefix_stalled && (!pv || {pl,po}!==prefix_held)) $fatal(1,"Prefix output changed during stall");
        tx_stalled<=tov&&!tor;tx_held<={tol,to};
        rx_stalled<=rxv&&!rxr;rx_held<={rxl,rxo};
        prefix_stalled<=pv&&!pr;prefix_held<={pl,po};
    end

    logic [31:0] rpi=0,rpo,co;
    logic rpiv=0,rpir,rpil=0,rpov,rpor,rpol,loaded,playing,rpe,arm=0,start=0;
    logic cv,cr=0,cl,busy;
    wire [31:0] rejected;
    integer replay_load_count=0,replay_count=0,capture_count=0;
    logic started=0,extra_arm_sent=0;
    axis_iq_replay #(.WORDS(N)) replay(clk,rst,start,1'b0,1'b0,rpi,rpiv,rpir,rpil,rpo,rpov,rpor,rpol,loaded,playing,rpe);
    axis_capture_window #(.WORDS(N)) capture_window(clk,rst,arm,rpo,rpov,rpor,co,cv,cr,cl,busy,rejected);
    always @(negedge clk) if(rst) begin
        cr<=rng[16] | rng[18];
        arm<=0;start<=0;
        if(replay_load_count<N) begin
            rpiv<=(rpiv && !rpir) || rng[14];rpi<=rot_in[replay_load_count];rpil<=(replay_load_count==N-1);
        end else rpiv<=0;
        if(loaded && !started) begin arm<=1;start<=1;started<=1;end
        else if(playing && replay_count==10 && !extra_arm_sent) begin arm<=1;extra_arm_sent<=1;end
    end
    always @(posedge clk) if(rst) begin
        if(rpiv && rpir) replay_load_count<=replay_load_count+1;
        if(rpov && rpor) begin
            if(rpo!==rot_in[replay_count] || rpol!==(replay_count==N-1)) $fatal(1,"Replay mismatch");
            replay_count<=replay_count+1;
        end
        if(cv && cr) begin
            if(co!==rot_in[capture_count] || cl!==(capture_count==N-1)) $fatal(1,"Capture mismatch");
            capture_count<=capture_count+1;
        end
    end
    logic capture_stalled=0;logic [32:0] capture_held;
    always @(posedge clk) if(rst) begin
        if(capture_stalled && (!cv || {cl,co}!==capture_held)) $fatal(1,"Capture output changed during stall");
        capture_stalled<=cv&&!cr;capture_held<={cl,co};
    end
    always @(posedge clk) if(rst && rout_count==TOTAL && rx_count==TOTAL && prefix_count==FRAMES*(N+L) && capture_count==N) begin
        if(re || te || rxe || pe || strip_error || rpe || tsat!=0 || rsat!=0) $fatal(1,"Unexpected framing or saturation flags");
        if(rejected!=1) $fatal(1,"Busy capture arm was not reported");
        $display("RTL PASS: bit-exact TX/RX, rotator saturation vectors, prefix, replay/capture, TLAST and randomized backpressure");
        $finish;
    end
endmodule
