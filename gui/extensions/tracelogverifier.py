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
from tracelogverif import VTraceLog
from table import Table

class TracelogVerifier(extensions.Operation):

    name = "Tracelog verifier"
    description = "Scans chosen tracelog and inspects clock condition violations (i.e. if there exists a send event whose timestamp is greater than a timestamp of the corresponding receive event). Results are stored into a table. "

    parameters = [ ]
    
    def display_settings(self, app):
        assistant = settingswindow.BasicSettingAssistant(1, 
                                                         TracelogVerifier.name,
                                                          app.window)
        assistant.set_size_request(700, 400)
        
        def page(setting):
            w = settingswindow.SettingWidget()
            w.add_filebutton("file", 
                      "Tracelog (*.kth): ",
                       "kth")
            return w
        
        assistant.append_setting_widget(TracelogVerifier.name, page)
        
        if assistant.run() != RESPONSE_APPLY:
            return
        
        return assistant.get_setting("file")
    
    def create_table(self, app, results):
        rows = []
        rows.append(("Total number of sent messages", results[0]))
        rows.append(("Clock condition violations", results[1]))
        rows.append(("Maximum delay [ns]", results[2]))
        rows.append(("Average delay [ns]", results[3]))
        columns = []
        columns.append(("Information", "|S{0}".format(len(max(rows, key=lambda x: len(x[0]))[0]))))
        columns.append(("Value", "<u8"))
        result_table = Table(columns, len([r[0] for r in rows]))
        for r in rows:
            result_table.add_row(r)
        result_table.trim()
        
        source = extensions.Source("Table of tracelog verification results",
                                 datatypes.t_table,
                                 result_table)
        return source
                

    def run(self, app):
        settings = self.display_settings(app)
        if settings is None:
            return
        t = VTraceLog(settings)
        return self.create_table(app, t.get_results())
                

extensions.add_operation(TracelogVerifier)

