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

import tracelogexport
import datatypes
import extensions

class SyncedTracelogExport(tracelogexport.TracelogExport):
    
    name = "Synced tracelog export"
    
    parameters = [ extensions.Parameter("Synced Tracelog", \
                                        datatypes.t_syncedtracelog) ]
    def _output_name(self):
        return "Synced Tracelog Table"

extensions.add_operation(SyncedTracelogExport)