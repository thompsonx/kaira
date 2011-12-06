
#include "cailie.h"
#include "listener.h"

#include <getopt.h>
#include <assert.h>
#include <stdarg.h>

#ifdef CA_MPI
#include <mpi.h>
#endif

int ca_threads_count = 1;
int ca_process_count = 1;
const char *ca_project_description_string = NULL;
int ca_log_on = 0;
std::string ca_log_default_name = "";
int ca_listen_port = -1;
int ca_block_on_start = 0;

void ca_project_description(const char *str) {
	ca_project_description_string = str;
}

static CaListener * ca_init_listener(int process_count, CaProcess **processes)
{
	CaListener *listener = new CaListener(process_count, processes);
	pthread_barrier_t start_barrier;

	listener->init(ca_listen_port);
	if (ca_listen_port == 0) {
		printf("%i\n", listener->get_port());
		fflush(stdout);
	}

	if (ca_block_on_start) {
		pthread_barrier_init(&start_barrier, NULL, 2);
		listener->set_start_barrier(&start_barrier);
	}

	listener->start();

	if (ca_block_on_start) {
		pthread_barrier_wait(&start_barrier);
		pthread_barrier_destroy(&start_barrier);
	}

	return listener;
}

int ca_main(int defs_count, CaNetDef **defs)
{
	#ifdef CA_MPI
		int process_count, process_id;
		MPI_Comm_rank(MPI_COMM_WORLD, &process_id);
		MPI_Comm_size(MPI_COMM_WORLD, &ca_process_count);
	#endif

	CaListener *listener = NULL;

	CaProcess **processes = (CaProcess**) alloca(sizeof(CaProcess*) * ca_process_count);

	int t;
	for (t = 0; t < ca_process_count; t++) {
		processes[t] = new CaProcess(t, ca_process_count, ca_threads_count, defs_count, defs);
		processes[t]->set_processes(processes);
	}

	if (ca_listen_port != -1) {
		listener = ca_init_listener(ca_process_count, processes);
	}

	for (t = 0; t < ca_process_count; t++) {
		processes[t]->start();
	}

	for (t = 0; t < ca_process_count; t++) {
		processes[t]->join();
	}

	if (listener != NULL) {
		delete listener;
	}

	for (t = 0; t < ca_process_count; t++) {
		delete processes[t];
	}
	return 0;
}

static int ca_set_argument(int params_count, const char **param_names, int **param_data, char *name, char *value)
{
	int t;
	for (t = 0; t < params_count; t++) {
		if (!strcmp(name, param_names[t])) {
			char *err = NULL;
			int i = strtol(value, &err, 10);
			if (*err != '\0') {
				fprintf(stderr, "Invalid parameter value\n");
				exit(1);
			}
			(*param_data[t]) = i;
			return t;
		}
	}
	fprintf(stderr, "Unknown parameter '%s'\n", name);
	exit(1);
}

#ifdef CA_MPI
void ca_finalize()
{
	MPI_Finalize();
}
#endif

void ca_init(int argc, char **argv, size_t params_count, const char **param_names, int **param_data, const char **param_descs)
{
	size_t t;
	int c;
	struct option longopts[] = {
		{ "help",	0,	NULL, 'h' },
		{ "threads",	1,	NULL, 't' },
		{ NULL,		0,	NULL,  0}
	};

	bool setted[params_count];
	for (t = 0; t < params_count; t++) {
		setted[t] = false;
	}

	#ifdef CA_MPI
	MPI_Init(&argc, &argv);
	atexit(ca_finalize);
	#endif

	while ((c = getopt_long (argc, argv, "hp:t:l:s:br:", longopts, NULL)) != -1)
		switch (c) {
			case 'h': {
				size_t max_len = 0;
				for (t = 0; t < params_count; t++) {
					if (max_len > strlen(param_names[t])) {
						max_len = strlen(param_names[t]);
					}
				}
				for (t=0; t < params_count; t++) {
					printf("Parameters:\n");
					printf("%s", param_names[t]);
					for (size_t s = strlen(param_names[t]); s < max_len; s++) { printf(" "); }
					printf(" - %s\n", param_descs[t]);
				}
				exit(0);
			}
			case 't': {
			      ca_threads_count = atoi(optarg);
			      break;
			}
			case 'r': {
			      ca_process_count = atoi(optarg);
			      break;
			}
			case 'p': {
				char str[strlen(optarg) + 1];
				strcpy(str, optarg);
				char *s = str;
				while ( (*s) != 0 && (*s) != '=') { s++; }
				if ((*s) == 0) {
					fprintf(stderr, "Invalid format of -p\n");
					exit(1);
				}
				*s = 0;
				s++;
				int r = ca_set_argument(params_count, param_names, param_data, str, s);
				setted[r] = true;
			} break;
			case 'l': {
				ca_log_on = 1;
				ca_log_default_name = optarg;
			} break;
			case 's': {
				if (!strcmp(optarg, "auto")) {
					ca_listen_port = 0;
					break;
				}
				ca_listen_port = atoi(optarg);
				if (ca_listen_port == 0) {
					fprintf(stderr, "Invalid value for -s\n");
					exit(1);
				}
				break;
			}
			case 'b': {
				ca_block_on_start = 1;
			} break;
			case '?':
			default:
				exit(1);
			}
	bool exit_f = false;
	for (t = 0; t < params_count; t++) {
		if (!setted[t]) {
			exit_f = true;
			fprintf(stderr, "Mandatory parameter '%s' required\n", param_names[t]);
		}
	}
	if (exit_f) { exit(1); }
}

std::vector<int> ca_range(int from, int upto)
{
	std::vector<int> v;
	int t;
	for (t = from; t <= upto; t++) {
		v.push_back(t);
	}
	return v;
}
