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
import datatypes
import settingswindow
import gtk
from gtk import RESPONSE_APPLY
from tracelogverif import VTraceLog

class TracelogVerifier(extensions.Operation):

    name = "Tracelog verifier"
    description = "Scans tracelog and inspects clock condition violations (send-receive mismatch)"

    parameters = [ ] #extensions.Parameter("Tracelog", datatypes.t_tracelog)
    
#     def display_settings(self, app):
#         assistant = settingswindow.BasicSettingAssistant(1, 
#                                                          "Tracelog verification",
#                                                           app.window)
#         assistant.set_size_request(700, 400)
#         
#         def page(setting):
#             w = settingswindow.SettingWidget()
#             w.add_entry("path", 
#                       "Path to a tracelog: ",
#                        "")
#             return w
#         
#         assistant.append_setting_widget("Tracelog verification", page)
#         
#         if assistant.run() != RESPONSE_APPLY:
#             return
#         
#         return assistant.get_setting("path")
    
    
    def display_result(self, app, results):
        assistant = settingswindow.BasicSettingAssistant(1, 
                                                         "Verification results",
                                                          app.window)
        assistant.set_size_request(700, 400)
        
        def page(setting):
            w = settingswindow.SettingWidget()
            w.add_int("total", 
                      "Total number of sent messages: ",
                       str(results[0]))
            w.add_int("violations", 
                      "Clock condition violations (mismatched sends and receives): ", 
                      str(results[1]))
            w.add_int("mdelay", 
                              "Maximum delay [ns]: ", 
                              str(results[2]))
            w.add_int("adelay", 
                              "Average delay [ns]: ", 
                              str(results[3]))
            return w
        
        assistant.append_setting_widget("Verification results", page)
        
        if assistant.run() != RESPONSE_APPLY:
            return

    def run(self, app):
        
        dialog = gtk.FileChooserDialog("Choose a tracelog for verification",
                                       app.window,
                                       gtk.FILE_CHOOSER_ACTION_OPEN,
                                       (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                       gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)

        dialog.add_filter(datatypes.get_load_file_filter(datatypes.get_type_by_suffix("kth")))

        filename = None
        try:
            response = dialog.run()
            if response == gtk.RESPONSE_OK:
                filename = dialog.get_filename()                
        finally:
            dialog.destroy()
        
        if filename is not None:
            t = VTraceLog(filename)
            self.display_result(app, t.get_results())
                

extensions.add_operation(TracelogVerifier)

