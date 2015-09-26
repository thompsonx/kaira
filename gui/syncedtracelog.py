import xml.etree.ElementTree as xml
import loader
import utils
from runinstance import RunInstance
from tracelog import TraceLog, Trace
from exportri import ExportRunInstance, place_counter_name
from table import Table
from Queue import Queue, Empty
from collections import OrderedDict
           
class SyncedTraceLog (TraceLog):
    
    def __init__(self, **kwargs):
        """ Creates new SyncedTraceLog object, different method is used 
            according to passed argument.
            
            Key: 'fromtracelog' -> Value: Tuple( TraceLog object, Settings tuple(
                                                min_event_diff, min_msg_delay, 
                                                init_times, forward_amort) )
                Creates new SyncedTraceLog object from an existing TraceLog object
            Key: 'fromfile' -> Value: Path to a *.kst
                Loads existing *.kst file and creates new SyncedTraceLog object
        """
        if "fromtracelog" in kwargs:         
            self._from_tracelog(kwargs["fromtracelog"][0], kwargs["fromtracelog"][1])

        elif "fromfile" in kwargs:
            self._from_file(kwargs["fromfile"])
            
        else:
            raise Exception("Unknown keyword argument!")
    
    
    def _from_tracelog(self, tracelog, settings):
        #             TraceLog.__init__(self, kwargs["fromtracelog"].filename, kwargs["fromtracelog"].export_data)
            self.filename = tracelog.filename
#             self.export_data = tracelog.export_data
    #            self._read_header()
    
    #            self.traces = [None] * self.process_count
    #            for process_id in xrange(self.process_count):
    #                self._read_trace(process_id)
            self.pointer_size = tracelog.pointer_size
            
            self.traces = []
            for t in tracelog.traces:
                strace = SyncedTrace(t.data, t.process_id, self.pointer_size)
                strace.tracelog = self
                self.traces.append(strace)
            
            self.process_count = len(self.traces)
            self.project = tracelog.project
            
            self.minimal_event_diff = settings[0]
            self.minimum_msg_delay = settings[1]
            self.forward_amort = settings[3]
            self.backward_amort = True
    
#             self.first_runinstance = RunInstance(self.project, self.process_count)
            
            # Matrix of unprocessed sent messages        
            self.messages = [[SQueue() for x in range(self.process_count)] for x in range(self.process_count)]            
            
            self._synchronize(settings[2])
            
    
    def _from_file(self, filename):
        self.pointer_size = 0
        self.traces = []
        self.project = None
        
        with open(filename, "rb") as f:
            self.pointer_size = int(f.readline())
            self.process_count = int(f.readline())
            
            i = 0
            processes_length = []
            while i < self.process_count:
                processes_length.append(int(f.readline()))
                i += 1
            
            i = 0
            for p in processes_length:
                trace = Trace(f.read(p), i, self.pointer_size)
                self.traces.append(trace)
                i += 1
            
            x = xml.fromstring(f.read())
            self.project = loader.load_project_from_xml(x, "")
        
        self.filename = filename
        self.export_data = True
        self.process_count = len(self.traces)

        self.first_runinstance = RunInstance(self.project, self.process_count)
        
        self._preprocess()
    
    def _preprocess(self):
        
        trace_times = [ trace.get_next_event_time() for trace in self.traces ]

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
        while True:

            # Searching for trace with minimal event time
            minimal_time_index = utils.index_of_minimal_value(trace_times)
            if minimal_time_index is None:
                break

            trace = self.traces[minimal_time_index]

            full_timeline.add_row((minimal_time_index, trace.pointer))

            # Timeline update
            if trace.is_next_event_visible():
                timeline.add_row(full_timeline[index])

            trace.process_event(ri)
            trace_times[minimal_time_index] = trace.get_next_event_time()

            index += 1

        self.data = Table([], 0)
        if self.export_data:
            self.data = ri.get_table()

        timeline.trim()
        full_timeline.trim()
        self.timeline, self.full_timeline = timeline, full_timeline

        self.missed_receives = ri.missed_receives
    
           
    def _synchronize(self, init_times=True):
        """ Main feature of this class. It controls whole synchronization procedure 
            
            Arguments:
            init_times -- True/False - if True it will use processes' init times
                             from tracelog to count their time offsets
        """
        
        # Use processes' init times from tracelog to count their time offsets
        if init_times:
            starttime = min([ trace.get_init_time() for trace in self.traces ])
            for trace in self.traces:
                trace.time_offset = trace.get_init_time() - starttime
        
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
                            if self.backward_amort:
                                #Backward amortization - check refilled receive times
                                if not trace.are_receive_times_refilled():
                                    current_p = trace.missing_receive_time_process_id
                                    break
                                
                                trace.process_next()
                                #Backward amortization - add receive time and maximum offset
                                self.traces[sender].refill_receive_time(trace.last_received_send_time, trace.last_event_time) 
                            else:
                                trace.process_next()                                        
                        else:
                            current_p = sender
                        print "RECV"
                    else:
                        trace.process_next()
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
                
    
    def export_to_file(self, filename):
        """ Saves synchronized tracelog into a file 
            
            Arguments:
            filename -- Path to a *.kst
        """
        data = str(self.pointer_size) + '\n' + str(self.process_count) + '\n'
        
        traces = ""

        for t in self.traces:
            data += str(len(t.data)) + '\n'
            traces += t.data
        
        data += traces
        
        with open(self.filename, "r") as f:
            f.readline()
            data += f.read()
            
        with open(filename, "wb") as f:
            f.write(data)


class SyncedTrace(Trace):
    
    def __init__(self, data, process_id, pointer_size, tracelog=None):
        Trace.__init__(self, data, process_id, pointer_size)
        self.tracelog = tracelog
        self.output = []
        self.last_event_time = 0
        self.send_events = OrderedDict()
        self.last_received_send_time = 0
        self.last_refilled_send_time = None
        self._missing_receive_time_process_id = None
        
    def _clock_check(self, time, start_pointer, end_pointer, is_receive=False, send_time=0):
        """ Checks, computes and repairs an event's timestamp
            
            Arguments:
            time -- a timestamp to be checked
            start_pointer -- a pointer value before an event unpacking/reading
            end_pointer -- a pointer value after an event unpacking/reading
            is_receive -- marks a receive event
            send_time -- a timestamp of corresponding send event
         """
        newtime = 0
        
        if not is_receive:
            newtime = self._clock(time + self.time_offset)
        else:
            newtime = self._clock_receive(time + self.time_offset, send_time)
        
        if newtime != time:
            self.pointer = start_pointer
            self._repair_time(newtime)
            self.pointer = end_pointer
        
        return newtime            
    
    def _clock(self, time):
        """ Computes a new time for a process' internal event 
            
            Arguments:
            time -- the time to be fixed
        """
        newtime = 0
        if self.last_event_time != 0:
            newtime = max([time, self.last_event_time + \
                           self.tracelog.minimal_event_diff])
        else:
            newtime = time
        
        self.last_event_time = newtime
        
        return newtime
    
    def _clock_receive(self, time, send_time):
        """ Computes a new time for a process' receive event 
            
            Arguments:
            time -- the time to be fixed
            send_time -- time of the corresponding send event
        """
        newtime = 0
        if self.last_event_time != 0:
            newtime = max([send_time + self.tracelog.minimum_msg_delay, time, \
                           self.last_event_time + \
                           self.tracelog.minimal_event_diff])
        else:
            newtime = max([send_time + self.tracelog.minimum_msg_delay, time])
        
        if self.tracelog.forward_amort:
            self._forward_amortization(time, newtime)
        
        self.last_event_time = newtime
        
        return newtime
        
    def _forward_amortization(self, origin_time, new_time):
        """ Checks shift of a receive event. If a shift exists the time offset 
            is increased to keep the spacing between two events """
        if new_time > origin_time or new_time > \
        (self.last_event_time + self.tracelog.minimal_event_diff):
            self.time_offset += (new_time - origin_time)
    
    def _backward_amortization(self, origin_time, new_time):
        if not (new_time > origin_time and new_time > \
                (self.last_event_time + self.tracelog.minimal_event_diff)):
            return
        offset = new_time - origin_time
        
    def is_backward_amortization(self):
        """ Returns True if the backward amortization is going to be done """
        if not self.get_next_event_name() == "Recv ":
            return False
        
        send_time = 0
        sender = self.get_msg_sender()
        try:
            send_time = self.tracelog.messages[sender][self.process_id].get_and_keep()
        except Empty:
            return False
        
        origin_time = self.get_next_event_time() + self.time_offset
        new_time = max([send_time + self.tracelog.minimum_msg_delay, origin_time, \
                           self.last_event_time + \
                           self.tracelog.minimal_event_diff])
        if new_time > origin_time and new_time > \
                (self.last_event_time + self.tracelog.minimal_event_diff):
            return True
        else:
            return False
    
    def are_receive_times_refilled(self):
        """ Returns True if all current send events (SendEvent send_events) have 
        refilled the receive time field """
        if not self.is_backward_amortization():
            return True
        times = self.send_events.keys()
        if self.last_refilled_send_time:
            start = times.index(self.last_refilled_send_time)
            times = times[start:]
        for t in times:
            for e in self.send_events[t]:
                if e.receive == 0:
                    self._missing_receive_time_process_id = e.receiver
                    return False
        return True
    
    def refill_receive_time(self, send_time, receive_time):
        """ Backward amortization - adds receive time for a specific send time 
            and compute maximum offset
            
            Arguments:
            send_time -- time of a corresponding send event
            receive_time -- time of a receipt of the msg to be filled
        """
        for event in self.send_events[send_time]:
            if event.receive == 0:
                event.receive = receive_time
                event.offset = receive_time - \
                    self.tracelog.minimum_msg_delay - send_time
                self.last_refilled_send_time = send_time
                break
    
    @property
    def missing_receive_time_process_id(self):
        """ Get the id of a process of which the time of a receive event was 
        missing during the are_receive_times_refilled() method"""
        return self._missing_receive_time_process_id
            
    def get_msg_sender(self):
        if self.get_next_event_name() == "Recv ":
            tmp_pointer = self.pointer
            self.pointer += 1
            origin_id = self._read_struct_receive()[1]
            self.pointer = tmp_pointer
            return origin_id
        else:
            return None
    
    def _repair_time(self, time):
        """ Overwrites original time in tracelog's data string with new one 
            
            Arguments:
            time -- a new time to be saved
        """
        self.data = self.data[:self.pointer] + self.struct_basic.pack(time) + \
                    self.data[self.pointer + self.struct_basic.size:]
    
    def _process_end(self):
        t = self.data[self.pointer]
        if t != "X":
            return
        self.pointer += 1
        pointer1 = self.pointer
        values = self.struct_basic.unpack_from(self.data, self.pointer)
        self.pointer += self.struct_basic.size
        
        time = self._clock_check(values[0], pointer1, pointer1 + self.struct_basic.size)
        
        
        self.output.append(str(self.process_id) + ' ' + t + ' ' + str(time))
        print str(self.process_id) + ' ' + t + ' ' + str(time)
        

    def _process_event_transition_fired(self):        
        ptr = self.pointer                    
        time, transition_id = self._read_struct_transition_fired()
        pointer1 = self.pointer
        time = self._clock_check(time, ptr, pointer1)
        
        self._read_transition_trace_function_data()
        pointer2 = self.pointer
        self.pointer = pointer1
        
        self.output.append(str(self.process_id) + " TransS " + str(transition_id) + ' ' + str(time))
        print str(self.process_id) + " TransS " + str(transition_id) + ' ' + str(time)
        
        self.process_tokens_remove()
        self.pointer = pointer2
        self._process_event_quit()
        self.process_tokens_add()
        self._process_end()

    def _process_event_transition_finished(self):
        pointer1 = self.pointer
        time = self._read_struct_transition_finished()[0]
        
        time = self._clock_check(time, pointer1, pointer1 + self.struct_basic.size)
        
        self.output.append(str(self.process_id) + " TransF " + str(time))
        print str(self.process_id) + " TransF " + str(time)
                                              
        self._process_event_quit()
        self.process_tokens_add()
        self._process_end()

    def _process_event_send(self):
        pointer1 = self.pointer
        time, size, edge_id, target_ids = self._read_struct_send()
        pointer2 = self.pointer
        
        time = self._clock_check(time, pointer1, pointer2)
        
        for target_id in target_ids:
            self.tracelog.messages[self.process_id][target_id].put(time)
            send_event = SendEvent()
            send_event.receiver = target_id
            if time not in self.send_events.keys():
                self.send_events[time] = [send_event]
            else:
                self.send_events[time].append(send_event)
            
        self.output.append(str(self.process_id) + " Send " + str(target_id) + ' ' + str(edge_id) + ' ' + str(time))
        print str(self.process_id) + " Send " + str(target_id) + ' ' + str(edge_id) + ' ' + str(time)

    def _process_event_spawn(self):
        pointer1 = self.pointer
        time, net_id = self._read_struct_spawn()
        pointer2 = self.pointer
        
        time = self._clock_check(time, pointer1, pointer2)
        
        self.output.append(str(self.process_id) + " Spawn " + ' ' + str(net_id) + ' ' +str(time))
        print str(self.process_id) + " Spawn " + ' ' + str(net_id) + ' ' +str(time)
        
        self.process_tokens_add()

    def _process_event_quit(self):
        t = self.data[self.pointer]
        if t != "Q":
            return
        self.pointer += 1
        
        pointer = self.pointer
        time = self._read_struct_quit()[0]
        
        time = self._clock_check(time, pointer, pointer + self.struct_basic.size)
        
        self.output.append(str(self.process_id) + " Quit " + str(time))
        print str(self.process_id) + " Quit " + str(time)

    def _process_event_receive(self):
        pointer1 = self.pointer
        time, origin_id = self._read_struct_receive()
        pointer2 = self.pointer
        
        send_time = self.tracelog.messages[origin_id][self.process_id].get()
        time = self._clock_check(time, pointer1, pointer2, True, send_time)
        self.last_received_send_time = send_time
        
        self.output.append(str(self.process_id) + " Recv " + str(origin_id) + ' ' + str(time))
        print str(self.process_id) + " Recv " + str(origin_id) + ' ' + str(time)
        
        self.process_tokens_add(send_time)
        self._process_end()
        

    def _process_event_idle(self):
        pointer = self.pointer
        time = self._read_struct_quit()[0]
        time = self._clock_check(time, pointer, pointer + self.struct_basic.size)
        
        self.output.append(str(self.process_id) + " Idle " + str(time))
        print str(self.process_id) + " Idle " + str(time)
        
    # New runinstance-free methods
    
    def process_next(self):
        t = self.data[self.pointer]
        self.pointer += 1
        if t == "T":
            self._process_event_transition_fired()
        elif t == "F":
            self._process_event_transition_finished()
        elif t == "R":
            return self._process_event_receive()
        elif t == "S":
            return self._process_event_spawn()
        elif t == "I":
            return self._process_event_idle()
        elif t == "Q":
            # This is called only when transition that call ctx.quit is not traced
            self.pointer -= 1 # _process_event_quit expect the pointer at "Q"
            self._process_event_quit()
        else:
            raise Exception("Invalid event type '{0}/{1}' (pointer={2}, process={3})"
                                .format(t, ord(t), hex(self.pointer), self.process_id))
    
    def process_tokens_add(self, send_time=0):
        values = []
        while not self.is_pointer_at_end():
            t = self.data[self.pointer]
            if t == "t":
                values = []
                self.pointer += 1
                self._read_struct_token()
            elif t == "i":
                self.pointer += 1
                value = self._read_struct_int()
                values.append(value)
            elif t == "d":
                self.pointer += 1
                value = self._read_struct_double()
                values.append(value)
            elif t == "s":
                self.pointer += 1
                value = self._read_cstring()
                values.append(value)
            elif t == "M":
                self.pointer += 1
                self._process_event_send()
            else:
                break
    
    def process_tokens_remove(self):
        while not self.is_pointer_at_end():
            t = self.data[self.pointer]
            if t == "r":
                self.pointer += 1
                self._read_struct_token()
            else:
                break
    
class SQueue(Queue):
    def __init__(self):
        Queue.__init__(self)
    
    def get_and_keep(self):
        value = self.get()
        self.queue.appendleft(value)
        return value
        

class SendEvent(object):
    def  __init__(self):
        self.receive = 0
        self.receiver = None
        self.offset = 0
    