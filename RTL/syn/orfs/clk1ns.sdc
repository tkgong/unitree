current_design $::env(DESIGN_NAME)
set clk_name clk
set clk_port_name clk
set clk_period 1.0
set clk_port [get_ports $clk_port_name]
create_clock -name $clk_name -period $clk_period $clk_port
set_input_delay 0.1 -clock $clk_name [delete_from_list [all_inputs] $clk_port]
set_output_delay 0.1 -clock $clk_name [all_outputs]
