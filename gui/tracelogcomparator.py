#
#    Copyright (C) 2015-2016 Tomas Panoc
#
#    This file is part of Kaira.
#
#    Kaira is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 3 of the License, or
#    (at your option) any later version.
#
#    Kaira is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Kaira.  If not, see <http://www.gnu.org/licenses/>.
#

import sys
import multiprocessing as mp
from tracelog import TraceLog, Trace
from syncedtracelog import SyncedTraceLogLoader
from Queue import Queue
from table import Table

class TracelogComparator(object):
    
    """ Performs an analysis of results of synchronized tracelog by comparing
        it with the original one. """
    
    def __init__(self, tracelog_filepath, syncedtracelog_filepath, weak_sync):
        """ Initialization.
        
            Arguments:
            tracelog_filepath -- path to a *.kth
            syncedtracelog_filepath -- path to a *.kst
            weak_sync -- if True initial weak synchronization is applied
                        to the original tracelog to make it comparable to
                        the synced one where the weak sync was already
                        performed
        """
                
        t_queue = mp.Queue()
        st_queue = mp.Queue()
        tp = mp.Process(target=self._process_t, args=("original", 
                                                      tracelog_filepath,
                                                      t_queue,
                                                      weak_sync))
        stp = mp.Process(target=self._process_t, args=("synced",
                                                      syncedtracelog_filepath,
                                                      st_queue))        
        tp.start()
        stp.start()
        
        t_stats = t_queue.get()
        st_stats = st_queue.get()
        
        tp.join()
        stp.join()
        
        self._process_statistics(t_stats, st_stats)
    
    def get_results(self):
        """ Returns Table of results of the comparison. """
        return self.result_table
     
    def _process_statistics(self, t_stats, st_stats):
        """ Compares tracelogs. 
        
            Arguments:
            t_stats -- Statistics of the original tracelog
            st_stats -- Statistics of the synced tracelog
        """
        rows = []
        rows.append(("Execution time", t_stats.get_execution_time(), 
                     st_stats.get_execution_time()))
        rows.append(("Idle time", t_stats.get_idle_time(), 
                     st_stats.get_idle_time()))
        rows.append(("Average idle time", t_stats.get_idle_average(),
                     st_stats.get_idle_average()))
        
        processes = t_stats.get_processes_number()
        
        q_ints = mp.Queue()
        func = t_stats.get_process_send_events_intervals
        t_ints = [func(p) for p in range(processes) if func(p) is not None]
        func = st_stats.get_process_send_events_intervals
        st_ints = [func(p) for p in range(processes) if func(p) is not None]
        
        
        bp_process = mp.Process(target=self._find_breakpoints, 
                                args=(q_ints, t_ints, st_ints))
        
        bp_process.start()
        
        max_b, avg_b, count_b = q_ints.get()
            
        bp_process.join()
        
        rows.append(("Number of breakpoints", 0, count_b))
        rows.append(("Maximum arisen gap", 0, max_b))
        rows.append(("Average arisen gap", 0, avg_b))
        
        columns = []
        columns.append(("Information", "|S{0}".format(len(max(rows, key=lambda x: len(x[0]))[0]))))
        columns.append(("Tracelog", "<i8"))
        columns.append(("Synced Tracelog", "<i8"))
        self.result_table = Table(columns, len([r[0] for r in rows]))
        for r in rows:
            self.result_table.add_row(r)
        self.result_table.trim()
        
    
    def _find_breakpoints(self, queue, t_ints, st_ints):
        """ Analysis of breakpoints. (Process)
        
            Arguments:
            queue -- Queue for interprocess communication
            t_ints -- original tracelog's 
                    Statistics.get_process_send_events_intervals
            st_ints -- synced tracelog's
                    Statistics.get_process_send_events_intervals
        """
        max_interval = 0
        avg_int = 0
        ints = 0
        if t_ints:
            for p, process in enumerate(t_ints):
                for n, interval in enumerate(process):
                    synced = st_ints[p][n]
                    diff = synced - interval
                    if diff != 0:
                        max_interval = max([max_interval, diff])
                        avg_int += diff
                        ints += 1
            if ints != 0:
                avg_int = avg_int / ints
            
        queue.put((max_interval, avg_int, ints))
    
    def _process_t(self, tracelog_type, filename, queue, weak_sync=False):
        """ A process that performs data gathering in a tracelog. 
            
            Arguments:
            tracelog_type -- original/synced, type of tracelog
            filename -- path to the tracelog
            queue -- Queue for interprocess communication
            weak_sync -- if True the initial weak synchronization is applied,
                    WORKS ONLY FOR THE original TRACELOG
        """
        if tracelog_type == "original":
            tracelog = TComparable(filename)
        elif tracelog_type == "synced":
            tracelog = STComparable(filename)
        tracelog.init()
        if tracelog_type == "original":
            tracelog.process(weak_sync)
        elif tracelog_type == "synced":
            tracelog.process(False)
        
        queue.put(tracelog.get_statistics())

class ComparableTraceLog(object):
    
    """ Abstract class. Gathers data from tracelog. """
    
    def __init__(self, filename):
        """ Initialization.
         
            Arguments:
            filename -- path to a tracelog file
        """
        self._initialized = False
        self._filename = filename
        self._type = "original"
        
    def init(self):
        """ Preparation for the gathering. """
        self._load_file(self._filename)
        self.messages = [[Queue() for x in range(self.process_count)] for x in range(self.process_count)]
        self._init_traces()
        self._initialized = True
        
    def _load_file(self, filename):
        """ Reserved for tracelog loading.
            
            Arguments:
            filename -- path to a tracelog file
        """
        pass
    
    def _init_traces(self):
        """ Initializes individual traces. """
        vtraces = []
        self._statistics = Statistics()
        for t in self.traces:
            vtraces.append(self._init_trace(t.data, t.process_id, 
                                            self.pointer_size, self.messages,
                                            self._statistics))
        self.traces = vtraces
    
    def _init_trace(self, data, process_id, pointer_size, messages, statistics):
        """ Returns trace object. """
        return ComparableTrace(data, process_id, pointer_size, messages,
                               statistics, "original")
    
    def process(self, weak_sync=False):
        """ Performs data gathering.
        
            Arguments:
            weak_sync -- if True the initial weak synchronization is applied,
                    WORKS ONLY FOR THE original TRACELOG
        """
        if not self._initialized:
            return

        if self._type == "original":
            if weak_sync:
                maxspawntrace = max( self.traces, key=lambda x: x.get_next_event_time() )
                for trace in self.traces:
                    trace.time_offset = maxspawntrace.get_next_event_time() - trace.get_next_event_time()
            else:
                starttime = min([ trace.get_init_time() for trace in self.traces ])
                for trace in self.traces:
                    trace.time_offset = trace.get_init_time() - starttime
        for t in self.traces:
            t.record_first_event()
        # List of unprocessed processes
        processes = [x for x in range(self.process_count)]
        # A process which will be processed
        current_p = processes[0]
        
        # Traverse algorithm goes through every event of a process,
        # it jumps to another process if a send event of reached receive event
        # is found to be unprocessed or if the end of process is reached
        while processes:
            
            working_p = current_p
            trace = self.traces[working_p]
            
            while working_p == current_p:
                if trace.get_next_event_time() is not None:
                    if trace.get_next_event_name() == "Recv ":
                        sender = trace.get_msg_sender()
                        if self.messages[sender][current_p].empty() is False:
                            trace.process_event()                                        
                        else:
                            current_p = sender
                    else:
                        trace.process_event()
                else:
                    processes.remove(current_p)
                    #List is empty, stops the loop
                    if not processes:
                        current_p += 1
                    else:
                        current_p = processes[0]
    
    def get_statistics(self):
        return self._statistics

class STComparable(ComparableTraceLog):
    
    def __init__(self, filename):
        ComparableTraceLog.__init__(self, filename)
        self._type = "synced"
        
    def _load_file(self, filename):
        self.process_count, self.pointer_size, self.traces, project = \
            SyncedTraceLogLoader(filename).load()
    
    def _init_trace(self, data, process_id, pointer_size, messages, statistics):
        return ComparableTrace(data, process_id, pointer_size, messages,
                               statistics, "synced")

class TComparable(ComparableTraceLog):
    
    def __init__(self, filename):
        ComparableTraceLog.__init__(self, filename)
        
    def _load_file(self, filename):
        tracelog = TraceLog(filename, False, True, False)
        self.pointer_size = tracelog.pointer_size
        self.process_count = tracelog.process_count
        self.traces = tracelog.traces


class ComparableTrace(Trace):
    
    def __init__(self, data, process_id, pointer_size, messages, statistics, 
                 trace_type):
        """ VTrace initialization
            
            Arguments:
            data -- content of a *.ktt file
            process_id -- id (rank) of the process logged in trace
            pointer_size -- 4 or 8, type of binary data within the *.ktt file
            messages -- shared variable among VTraces, 2-dimensional array
                        of Queues, first coordinate is a sender of message,
                        second is the recipient, Queues stores sent times.
        """
        
        Trace.__init__(self, data, process_id, pointer_size)
        
        self._messages = messages
        self._type = trace_type
        self._statistics = statistics
        self._statistics.register_process()
        self._last_event_type = ""
        self._current_event_type = ""
        self._last_event_time = 0
    
    def record_first_event(self):
        self._statistics.set_init(self.get_next_event_time())
    
    def get_msg_sender(self):
        """ Returns None or the id of a process, who is the sender of 
            the received message, if the next event is receive event
        """
        if self.get_next_event_name() == "Recv ":
            tmp_pointer = self.pointer
            self.pointer += 1
            origin_id = self._read_struct_receive()[1]
            self.pointer = tmp_pointer
            return origin_id
        else:
            return None
    
    def _extra_event(self, event):
        self._current_event_type = event
    
    def _extra_event_send(self, time, target_id):
        """ Saves sent time in shared variable of messages """
        self._messages[self.process_id][target_id].put(time + self.time_offset)
    
    def _extra_time(self, time, pointer, receive=False, origin_id=None):
        """ Resolves the violation and counts delay """
        if self._last_event_type == "I":
            self._statistics.add_idle_interval(time + self.time_offset - self._last_event_time)
        elif self._last_event_type == "M":
            self._statistics.add_send_event_interval(self.process_id, 
                                                     time + self.time_offset \
                                                      - self._last_event_time)
        self._last_event_time = time + self.time_offset
        self._last_event_type = self._current_event_type
        self._statistics.set_finish(time + self.time_offset)
        return time
        
        
class Statistics(object):
    
    def __init__(self):
        self._first_event = sys.maxint
        self._last_event = 0
        self._idle_time = 0
        self._idle_counter = 0
        self._send_event_intervals = {}
        self._processes = 0

    def register_process(self):
        self._processes += 1
    
    def add_idle_interval(self, interval):
        self._idle_time += interval
        self._idle_counter += 1
    
    def add_send_event_interval(self, process_id, interval):
        if process_id in self._send_event_intervals.keys():
            self._send_event_intervals[process_id].append(interval)
        else:
            self._send_event_intervals[process_id] = [interval]
    
    def get_process_send_events_intervals(self, process_id):            
        if process_id in self._send_event_intervals.keys():
            return self._send_event_intervals[process_id]
        return None
    
    def set_init(self, time):
        if time < self._first_event:
            self._first_event = time
    
    def set_finish(self, time):
        if time > self._last_event:
            self._last_event = time 
    
    def get_execution_time(self):
        return self._last_event - self._first_event
    
    def get_idle_average(self):
        if self._idle_counter != 0:
            return self._idle_time / self._idle_counter
        return 0
    
    def get_idle_time(self):
        return self._idle_time
    
    def get_processes_number(self):
        return self._processes
    