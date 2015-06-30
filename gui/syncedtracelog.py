import xml.etree.ElementTree as xml
import loader
import utils
from runinstance import RunInstance
from tracelog import TraceLog, Trace
from exportri import ExportRunInstance, place_counter_name
from table import Table
from Queue import Queue
           
class SyncedTraceLog (TraceLog):
    
    @classmethod
    def fromtracelog(cls, tracelog):
        """ Creates new SyncedTraceLog object from an existing TraceLog object
            
            Arguments:
            tracelog -- TraceLog object
        """
        return cls(fromtracelog=tracelog)
    
    @classmethod
    def fromfile(cls, filename):
        """ Loads existing *.kst file and creates new SyncedTraceLog object
            
            Arguments:
            filename -- Path to a *.kst
        """
        pointer_size = 0
        process_count = 0
        traces = []
        project = 0
        
        with open(filename, "rb") as f:
            pointer_size = int(f.readline())
            process_count = int(f.readline())
            
            i = 0
            processes_length = []
            while i < process_count:
                processes_length.append(int(f.readline()))
                i += 1
            
            i = 0
            for p in processes_length:
                trace = SyncedTrace(f.read(p), i, pointer_size)
                traces.append(trace)
                i += 1
            
            x = xml.fromstring(f.read())
            project = loader.load_project_from_xml(x, "")
        
        return cls(fromfile=(pointer_size, traces, project, True))
    
    def __init__(self, **kwargs):
        """ Creates new SyncedTraceLog object, different method is used 
            according to passed argument
            
            Key: 'fromtracelog' -> Value: TraceLog object
                Creates new SyncedTraceLog object from an existing TraceLog object
            Key: 'fromfile' -> Value: Path to a *.kst
                Loads existing *.kst file and creates new SyncedTraceLog object
        """
        if "fromtracelog" in kwargs:         
            TraceLog.__init__(self, kwargs["fromtracelog"].filename, kwargs["fromtracelog"].export_data)
        elif "fromfile" in kwargs:
            self.filename = ""
            self.export_data = kwargs["fromfile"][3]
    #            self._read_header()
    
    #            self.traces = [None] * self.process_count
    #            for process_id in xrange(self.process_count):
    #                self._read_trace(process_id)
            self.pointer_size = kwargs["fromfile"][0]
            
            self.traces = kwargs["fromfile"][1]
            for t in self.traces:
                t.tracelog = self
            
            self.process_count = len(self.traces)
            self.project = kwargs["fromfile"][2]
    
            self.first_runinstance = RunInstance(self.project, self.process_count)
            
            # Matrix of unprocessed sent messages        
            self.messages = [[Queue() for x in range(self.process_count)] for x in range(self.process_count)]            
            
            self._preprocess()
            
    def _preprocess(self):

        if self.export_data:
            place_counters = [place_counter_name(p)
                              for p in self.project.nets[0].places()
                              if p.trace_tokens]

            ri = ExportRunInstance(
                self,
                [ t for t in self.project.nets[0].transitions() if t.trace_fire ],
                [ (p, i) for p in self.project.nets[0].places()
                         for i, tracing in enumerate(p.trace_tokens_functions)
                         if tracing.return_numpy_type != 'O' ],
                ExportRunInstance.basic_header + place_counters)
        else:
            ri = RunInstance(
                self.project, self.process_count)
        
        index = 0
        timeline = Table([("process", "<i4"), ("pointer", "<i4")], 100)
        full_timeline = Table([("process", "<i4"), ("pointer", "<i4")], 100)
        
        # List of unprocessed processes
        processes = [x for x in range(self.process_count)]
        # A process which will be processed
        current_p = processes[0]
        
        while processes:
            
            working_p = current_p
            trace = self.traces[working_p]
            
            while working_p == current_p:
                if trace.get_next_event_time() is not None:
                    if trace.get_next_event_name() == "Recv ":
                        sender = trace.get_msg_sender()
                        if self.messages[sender][current_p].empty() is False:
                            full_timeline.add_row((trace.process_id, trace.pointer))
                            if trace.is_next_event_visible():
                                timeline.add_row(full_timeline[index])
                            trace.process_event(ri)
                            index += 1
                        else:
                            current_p = sender
                        print "RECV"
                    else:
                        full_timeline.add_row((trace.process_id, trace.pointer))
                        if trace.is_next_event_visible():
                            timeline.add_row(full_timeline[index])
                        trace.process_event(ri)
                        index += 1
                        print "NORMAL"
                else:
                    processes.remove(current_p)
                    #List is empty, stops the loop (avoids break)
                    if not processes:
                        current_p += 1
                    else:
                        current_p = processes[0]
                    print "REMOVE"
         
        print "------TRACES-------"
        for t in self.traces:
            print "TRACE {0}".format(t.process_id)
            for c in t.output:
                print c
#        for t in self.traces:
#            while True:
#                if t.get_next_event_time() is None:
#                    break
#                full_timeline.add_row((t.process_id, t.pointer))
#                if t.is_next_event_visible():
#                    timeline.add_row(full_timeline[index])
#                t.process_event(ri)
#                index += 1
#            print "\n\n"

#        while True:
#
#            # Searching for trace with minimal event time
#            minimal_time_index = utils.index_of_minimal_value(trace_times)
#            if minimal_time_index is None:
#                break
#
#            trace = self.traces[minimal_time_index]
#
#            full_timeline.add_row((minimal_time_index, trace.pointer))
#
#            # Timeline update
#            if trace.is_next_event_visible():
#                timeline.add_row(full_timeline[index])
#
#            trace.process_event(ri)
#            trace_times[minimal_time_index] = trace.get_next_event_time()
#
#            index += 1

        self.data = Table([], 0)
        if self.export_data:
            self.data = ri.get_table()

        timeline.trim()
        full_timeline.trim()
        self.timeline, self.full_timeline = timeline, full_timeline

        self.missed_receives = ri.missed_receives
    
    def export_to_file(self, filename):
        """ Merges and saves merged TraceLog to a *.kst file 
            
            Arguments:
            filename -- Path to a *.kst
        """
        data = str(self.tracelog.pointer_size) + '\n' + str(self.tracelog.process_count) + '\n'
        
        traces = ""

        for t in self.tracelog.traces:
            data += str(len(t.data)) + '\n'
            traces += t.data
        
        data += traces
        
        with open(self.tracelog.filename, "r") as f:
            f.readline()
            data += f.read()
            
        with open(filename, "wb") as f:
            f.write(data)


class SyncedTrace(Trace):
    
    def __init__(self, data, process_id, pointer_size, tracelog=None):
        Trace.__init__(self, data, process_id, pointer_size)
        self.tracelog = tracelog
        self.clock = 1
        self.output = []
        
    def _tick(self):
        tmp_clock = self.clock
        self.clock += 1
        return tmp_clock
        
    def _tick_receive(self, send_time):
        """ Tick for received messages according to Lamport's logical clocks """
        time = max([self.clock - 1, send_time]) + 1
        self.clock = time + 1
        return time
        
    def get_msg_sender(self):
        if self.get_next_event_name() == "Recv ":
            tmp_pointer = self.pointer
            self.pointer += 1
            time, origin_id = self._read_struct_receive()
            self.pointer = tmp_pointer
            return origin_id
        else:
            return None
        
    def _process_end(self, runinstance):
        t = self.data[self.pointer]
        if t != "X":
            return
        self.pointer += 1
        values = self.struct_basic.unpack_from(self.data, self.pointer)
        self.pointer += self.struct_basic.size
        runinstance.event_end(self.process_id, self.clock - 1)
        
        self.output.append(str(self.process_id) + ' ' + t + ' ' + str(self.clock - 1))
        print str(self.process_id) + ' ' + t + ' ' + str(self.clock - 1)
        

    def _process_event_transition_fired(self, runinstance):
        time, transition_id = self._read_struct_transition_fired()
        time = self._tick()
        pointer1 = self.pointer
        values = self._read_transition_trace_function_data()
        pointer2 = self.pointer
        self.pointer = pointer1
        runinstance.transition_fired(self.process_id,
                                     time,
                                     transition_id,
                                     values)
        
        self.output.append(str(self.process_id) + " TransS " + str(transition_id) + ' ' + str(time))
        print str(self.process_id) + " TransS " + str(transition_id) + ' ' + str(time)
        
        self.process_tokens_remove(runinstance)
        self.pointer = pointer2
        self._process_event_quit(runinstance)
        self.process_tokens_add(runinstance)
        self._process_end(runinstance)

    def _process_event_transition_finished(self, runinstance):
        time = self._read_struct_transition_finished()[0]
        time = self._tick()
        runinstance.transition_finished(self.process_id,
                                        time)
        
        self.output.append(str(self.process_id) + " TransF " + str(time))
        print str(self.process_id) + " TransF " + str(time)
                                              
        self._process_event_quit(runinstance)
        self.process_tokens_add(runinstance)
        self._process_end(runinstance)

    def _process_event_send(self, runinstance):
        time, size, edge_id, target_ids = self._read_struct_send()
        time = self._tick()
        
        for target_id in target_ids:
            self.tracelog.messages[self.process_id][target_id].put(time)
            runinstance.event_send(self.process_id,
                                   time,
                                   target_id,
                                   size,
                                   edge_id)
            
            self.output.append(str(self.process_id) + " Send " + str(target_id) + ' ' + str(edge_id) + ' ' + str(time))
            print str(self.process_id) + " Send " + str(target_id) + ' ' + str(edge_id) + ' ' + str(time)

    def _process_event_spawn(self, runinstance):
        time, net_id = self._read_struct_spawn()
        time = self._tick()
        runinstance.event_spawn(self.process_id,
                                time,
                                net_id)
        
        self.output.append(str(self.process_id) + " Spawn " + ' ' + str(net_id) + ' ' +str(time))
        print str(self.process_id) + " Spawn " + ' ' + str(net_id) + ' ' +str(time)
        
        self.process_tokens_add(runinstance)

    def _process_event_quit(self, runinstance):
        t = self.data[self.pointer]
        if t != "Q":
            return
        self.pointer += 1
        time = self._read_struct_quit()[0]
        time = self._tick()
        runinstance.event_quit(self.process_id,
                               time)
        
        self.output.append(str(self.process_id) + " Quit " + str(time))
        print str(self.process_id) + " Quit " + str(time)

    def _process_event_receive(self, runinstance):
        time, origin_id = self._read_struct_receive()
        send_time =  self.tracelog.messages[origin_id][self.process_id].get()
        time = self._tick_receive(send_time)
        runinstance.event_receive(
            self.process_id,
            time,
            origin_id)
        
        self.output.append(str(self.process_id) + " Recv " + str(origin_id) + ' ' + str(time))
        print str(self.process_id) + " Recv " + str(origin_id) + ' ' + str(time)
        
        self.process_tokens_add(runinstance, send_time)
        self._process_end(runinstance)
        

    def _process_event_idle(self, runinstance):
        time = self._read_struct_quit()[0]
        time = self._tick()
        runinstance.event_idle(self.process_id,
                               time)
        
        self.output.append(str(self.process_id) + " Idle " + str(time))
        print str(self.process_id) + " Idle " + str(time)
        