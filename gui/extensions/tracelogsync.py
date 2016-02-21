import settingswindow
import extensions
import datatypes
from syncedtracelog import SyncedTraceLog
from gtk import RESPONSE_APPLY

class TracelogSync(extensions.Operation):

    name = "Tracelog synchronization"
    description = "Connect and synchronize tracelogs to one"

    parameters = [ extensions.Parameter("Tracelog", datatypes.t_tracelog) ]
    
    def display_settings(self, app):
        assistant = settingswindow.BasicSettingAssistant(1, 
                                                         "Synchronization settings",
                                                          app.window)
        assistant.set_size_request(700, 400)
        
        def page(setting):
            w = settingswindow.SettingWidget()
            w.add_positive_int("min_event_diff", 
                      "Minimal difference between 2 events in a process [ns]: ",
                       "10")
            w.add_positive_int("min_msg_delay", 
                      "Minimum message delay of messages from one process to another [ns]: ", 
                      "10")
            w.add_checkbutton("forward_amort", 
                              "Apply the forward amortization", 
                              True)
            w.add_checkbutton("backward_amort", 
                              "Apply the backward amortization", 
                              True)
            return w
        
        assistant.append_setting_widget("Synchronization settings", page)
        
        if assistant.run() != RESPONSE_APPLY:
            return
        
        return (assistant.get_setting("min_event_diff"), 
                assistant.get_setting("min_msg_delay"), 
                assistant.get_setting("forward_amort"),
                assistant.get_setting("backward_amort"))

    def run(self, app, tracelog):
        
        settings = self.display_settings(app)
        if settings is None:
            return
        
        syncedtracelog = SyncedTraceLog(fromtracelog=(tracelog, settings))
        
        source = extensions.Source("Synchronized tracelog",
                                 datatypes.t_syncedtracelog,
                                 syncedtracelog)
        sourceView = extensions.SourceView(source, app)
        
        sourceView._cb_store()
        
        sourceView._cb_delete()
        

extensions.add_operation(TracelogSync)

