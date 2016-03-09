#
#    Copyright (C) 2012-2016 Tomas Panoc
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

from tracelog import TraceLog, Trace
from Queue import Queue

class VTraceLog(TraceLog):
    
    """ Tracelog verifier - Scans traces and finds clock condition violations and maximum and average delay """
    
    def __init__(self, tracelog):
        """ VTraceLog initialization
        
            Arguments:
            tracelog -- a TraceLog object to be verified
        """
        
        TraceLog.__init__(self, None, False, False)
        
        self.filename = tracelog
        self._read_header()

        self.traces = [None] * self.process_count
        for process_id in xrange(self.process_count):
            self._read_trace(process_id)
        
        self.messages = [[Queue() for x in range(self.process_count)] for x in range(self.process_count)]
        
        self.vtraces = []
        for t in self.traces:
            self.vtraces.append(VTrace(t.data, t.process_id, self.pointer_size, 
                                      self.messages))
        self.traces = self.vtraces
        
        self._verify()
        
    def _verify(self):
        """ Scans traces and finds clock condition violations and maximum and average delay """
        
        # Make an init time of the process with the lowest init time reference
        # time for all events from all processes
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
        
        self.violations = max([t.get_violations_number() for t in self.traces])
        self.receives = max([t.get_receives_number() for t in self.traces])
        self.max_delay = 0
        self.avrg_delay = 0
        if self.violations > 0:
            self.max_delay = max([t.get_maximum_delay() for t in self.traces])
            self.avrg_delay = []
            for t in self.traces:
                delay_list = t.get_delays_list()
                if delay_list is not None:
                    self.avrg_delay += t.get_delays_list()
            self.avrg_delay = sum(self.avrg_delay) / self.violations
    
    def get_results(self):
        """ Returns results of verification in a tuple:
            1. Total number of sent messages
            2. Clock condition violations (mismatched sends and receives)
            3. Maximum delay [ns]
            4. Average delay [ns]
         """
        return (self.receives, self.violations, self.max_delay, self.avrg_delay)
        


class VTrace(Trace):
    
    """ Represents one trace (*.ktt) file. Reveals clock condition violations
        and counts the delays for one trace. """
    
    def __init__(self, data, process_id, pointer_size, messages):
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
        self._receives = 0
        self._ccviolations = 0
        self._delays = []

    def get_msg_sender(self):
        """ Returns None or the id of a process, who is the sender of the received
            message, if the next event is receive event
        """
        if self.get_next_event_name() == "Recv ":
            tmp_pointer = self.pointer
            self.pointer += 1
            origin_id = self._read_struct_receive()[1]
            self.pointer = tmp_pointer
            return origin_id
        else:
            return None

    def get_maximum_delay(self):
        """ Returns maximum delay of violated receives within trace """
        if self._delays:
            return max(self._delays)
        return None
    
    def get_delays_list(self):
        """ Returns list of delays of violated receives within trace """
        return self._delays

    def get_violations_number(self):
        """ Returns number of violations within trace """
        return self._ccviolations
    
    def get_receives_number(self):
        """ Returns total number of received messages within trace """
        return self._receives
        
    def _extra_event_send(self, time, target_id):
        """ Saves sent time in shared variable of messages """
        self._messages[self.process_id][target_id].put(time + self.time_offset)
        
    def _extra_time(self, time, pointer, receive=False, origin_id=None):
        """ Resolves the violation and counts delay """
        if receive:
            if origin_id is None:
                raise Exception("Origin_id for a receive event not entered!")
            self._receives += 1
            sent_time = self._messages[origin_id][self.process_id].get()
            if time + self.time_offset < sent_time:
                self._ccviolations += 1
                self._delays.append(sent_time - time + self.time_offset)
        return time
    