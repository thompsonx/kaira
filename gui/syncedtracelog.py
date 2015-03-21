import xml.etree.ElementTree as xml
import loader
from runinstance import RunInstance
from tracelog import TraceLog, Trace
           
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
                trace = Trace(f.read(p), i, pointer_size)
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
            self.process_count = len(self.traces)
            self.project = kwargs["fromfile"][2]
    
            self.first_runinstance = RunInstance(self.project, self.process_count)
    
            self._preprocess()
    
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