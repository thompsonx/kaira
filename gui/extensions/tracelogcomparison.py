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

import extensions
import settingswindow
import datatypes
from gtk import RESPONSE_APPLY
from tracelogcomparator import TracelogComparator
from table import Table

class TracelogComparison(extensions.Operation):

    name = "Tracelog comparison"
    description = "Compare original tracelog and synchronized tracelog. Output is a table of statistics. "

    parameters = [ ]
    
    def display_settings(self, app):
        assistant = settingswindow.BasicSettingAssistant(1, 
                                                         TracelogComparison.name,
                                                          app.window)
        assistant.set_size_request(700, 400)
        
        def page(setting):
            w = settingswindow.SettingWidget()
            w.add_filebutton("tracelog", 
                      "Tracelog (*.kth): ",
                       "kth")
            w.add_filebutton("syncedtracelog", 
                             "Synchronized tracelog (*.kst): ", 
                             "kst")
            w.add_checkbutton("weaksync",
                              "Apply initial weak synchronization",
                              False)
            return w
        
        assistant.append_setting_widget(TracelogComparison.name, page)
        
        if assistant.run() != RESPONSE_APPLY:
            return
        
        return (assistant.get_setting("tracelog"), 
                assistant.get_setting("syncedtracelog"),
                assistant.get_setting("weaksync"))
                

    def run(self, app):
        settings = self.display_settings(app)
        if settings is None:
            return
        
        comparator = TracelogComparator(settings[0], settings[1], settings[2])
        
        source = extensions.Source("Tracelog comparison results",
                                 datatypes.t_table,
                                 comparator.get_results())
        return source
        
                

extensions.add_operation(TracelogComparison)

