import extensions
import datatypes
from syncedtracelog import SyncedTraceLog

class TracelogSync(extensions.Operation):

    name = "Tracelog synchronization"
    description = "Connect and synchronize tracelogs to one"

    parameters = [ extensions.Parameter("Tracelog", datatypes.t_tracelog) ]

    def run(self, app, tracelog):

        syncedtracelog = SyncedTraceLog.fromtracelog(tracelog)
        
        source = extensions.Source("Synchronized tracelog",
                                 datatypes.t_syncedtracelog,
                                 syncedtracelog)
        sourceView = extensions.SourceView(source, app)
        
#         sourceView._cb_store()
        
        return source

extensions.add_operation(TracelogSync)

