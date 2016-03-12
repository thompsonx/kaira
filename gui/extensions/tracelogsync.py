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

import settingswindow
import extensions
import datatypes
from syncedtracelog import SyncedTraceLog
from gtk import RESPONSE_APPLY

class TracelogSync(extensions.Operation):

    name = "Tracelog synchronization"
    description = "Corrects and synchronizes events' times in a chosen tracelog. Individual trace files are merged into one output file."

    parameters = []
    
    def display_settings(self, app):
        assistant = settingswindow.BasicSettingAssistant(1, 
                                                         "Synchronization settings",
                                                          app.window)
        assistant.set_size_request(700, 400)
        
        def page(setting):
            w = settingswindow.SettingWidget()
            w.add_filebutton("file", 
                      "Tracelog (*.kth): ",
                       "kth")
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
                assistant.get_setting("backward_amort"),
                assistant.get_setting("file"))

    def run(self, app):
        
        settings = self.display_settings(app)
        if settings is None:
            return
        if settings[4] is None:
            print "No file chosen!"
            return
        
        syncedtracelog = SyncedTraceLog(fromtracelog=(settings[4], settings))
        
        source = extensions.Source("Synchronized tracelog",
                                 datatypes.t_syncedtracelog,
                                 syncedtracelog)
        sourceView = extensions.SourceView(source, app)
        
        sourceView._cb_store()
        
        sourceView._cb_delete()
        

extensions.add_operation(TracelogSync)

