import tracelog
import xml.etree.ElementTree as xml
import loader
from runinstance import RunInstance

class SyncedTraceLog:
    """ Merges all tracelogs to one including also the header file"""
    
    def __init__(self, tracelog, filename=None):
        """ Initializes the object
        
            Arguments:
            tracelog -- TraceLog object which SyncedTraceLog will be formed from
            filename -- Use if you want to load existing SyncedTracelog from a file, tracelog arg should be None
        """
        if tracelog == None:
            self.load_from_file(filename)
        else:
            self.tracelog = tracelog
        
    def load_from_file(self, filename):
        """ Loads existing *.kst file 
            
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
                trace = tracelog.Trace(f.read(p), i, pointer_size)
                traces.append(trace)
                i += 1
            
            x = xml.fromstring(f.read())
            project = loader.load_project_from_xml(x, "")
        
        self.tracelog = LoadedTraceLog(pointer_size, traces, project, True)
            
        
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
 
           
class LoadedTraceLog (tracelog.TraceLog):
        """ Supporting class for SyncedTraceLog. It is an extension of TraceLog class where no files are loaded"""
        
        def __init__(self, pointer_size, traces, project, export_data=False):
            """ Initialize TraceLog from loaded data in Kaira 
                
                Arguments:
                pointer_size -- Pointer size
                traces -- List of Trace objects (one represents one process)
                project -- Loaded XML data of a project
                export_data -- Should be true to be able to visualize the tracelog
            """
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

            self._preprocess()