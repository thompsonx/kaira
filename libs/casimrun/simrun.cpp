
#include "simrun.h"
#include "state.h"
#include <net.h>
#include <iostream>

namespace ca {
	extern ca::NetDef **defs;
	extern int defs_count;
	extern int process_count;
	extern char *project_description_string;
	extern size_t tracelog_size;
}


namespace casr {

State *state = NULL;

void main(RunConfiguration &run_configuration)
{
	ControlledTimeTraceLog::init();
	ca::check_parameters();
	ca::NetDef *net_def = ca::defs[0]; // Take first definition
	state = new State(run_configuration, net_def);
	state->run();
	std::cerr << "Kaira: Time = " << state->get_global_time() / 1e6 << "ms\n";
	delete state;
	state = NULL;
}

}