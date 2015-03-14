import extensions
import datatypes
from syncedtracelog import SyncedTraceLog

class TracelogSync(extensions.Operation):

    name = "Tracelog synchronization"
    description = "Connect and synchronize tracelogs to one"

    parameters = [ extensions.Parameter("Tracelog", datatypes.t_tracelog) ]

    def run(self, app, tracelog):

        syncedtracelog = SyncedTraceLog(tracelog)
        
        return extensions.Source("Synchronized tracelog",
                                 datatypes.t_syncedtracelog,
                                 syncedtracelog)

extensions.add_operation(TracelogSync)

