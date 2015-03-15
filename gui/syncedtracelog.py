import tracelog
import xml.etree.ElementTree as xml
import loader
from runinstance import RunInstance

class SyncedTraceLog:
    
    def __init__(self, tracelog, filename=None):
        if tracelog == None:
            self.load_from_file(filename)
        else:
            self.tracelog = tracelog
        
    def load_from_file(self, filename):
        pointer_size = 0
        process_count = 0
        processes = []
        project = 0
        
        with open(filename, "rb") as f:
            pointer_size = int(f.readline())
            process_count = int(f.readline())
            
            i = 0
            processes_length = []
            while i < process_count:
                processes_length.append(int(f.readline()))
                i += 1
            
            for p in processes_length:
                processes.append(f.read(p))
            
            x = xml.fromstring(f.read())
            project = loader.load_project_from_xml(x, "")
        
        self.tracelog = LoadedTraceLog(pointer_size, processes, project)
            
        
    def export_to_file(self, filename):
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
 
           
class LoadedTraceLog (tracelog.TraceLog):
        
        def __init__(self, pointer_size, traces, project, export_data=False):
            self.filename = ""
            self.export_data = export_data
#            self._read_header()
    
#            self.traces = [None] * self.process_count
#            for process_id in xrange(self.process_count):
#                self._read_trace(process_id)
            self.pointer_size = pointer_size
            self.traces = traces
            self.process_count = len(traces)
            self.project = project
    
            self.first_runinstance = RunInstance(self.project, self.process_count)
