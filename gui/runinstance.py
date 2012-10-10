#
#    Copyright (C) 2012 Stanislav Bohm
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

import utils
from copy import copy
from drawing import VisualConfig
import runview

class RunInstance:

    def __init__(self, project, process_count, threads_count):
        self.project = project
        self.process_count = process_count
        self.threads_count = threads_count
        self.net = None
        self.net_instances = {}
        self.activites = [None] * (self.process_count * self.threads_count)
        self.last_event = None # "fired" / "finished" / None
        self.last_event_activity = None
        self.last_event_instance = None
        self.send_msg = [ [] for i in xrange(self.process_count * self.threads_count)]

    def add_token(self, place_id, token_pointer, token_value, send_time=None):
        self.last_event_instance.add_token(place_id, token_pointer, token_value, send_time)

    def remove_token(self, place_id, token_pointer):
        self.last_event_instance.remove_token(place_id, token_pointer)

    def clear_removed_and_new_tokens(self):
        for i in self.net_instances:
            self.net_instances[i].clear_removed_and_new_tokens()

    def add_enabled_transition(self, transition_id):
        self.last_event_instance.add_enabled_transition(transition_id)

    def set_activity(self, process_id, thread_id, activity):
        index = process_id * self.threads_count + thread_id
        self.activites[index] = activity
        self.last_event_activity = activity

    def pre_event(self):
        """ This method is called by tracelog before each event_* """
        self.clear_removed_and_new_tokens()

    def event_spawn(self, process_id, thread_id, time, net_id):
        self.net = self.project.find_net(net_id)
        assert self.net.id == net_id
        self.last_event = "spawn"
        if thread_id is not None:
            self.set_activity(process_id, thread_id, None)

        instance = NetInstance(process_id)
        self.net_instances[process_id] = instance
        self.last_event_instance = instance

    def event_quit(self, process_id, thread_id, time):
        self.last_event = "quit"
        self.last_event_process = process_id
        self.last_event_thread = thread_id
        index = process_id * self.threads_count + thread_id
        if self.last_event_activity is not None:
            self.last_event_activity.quit = True
        self.last_event_instance = self.net_instances[process_id]

    def event_send(self, process_id, thread_id, time, msg_id):
        self.send_msg[process_id * self.threads_count + thread_id].append((msg_id, time))

    def event_receive(self, process_id, thread_id, time, msg_id):
        self.last_event = "receive"
        source = msg_id % (self.process_count * self.threads_count)
        send_time = None
        for i, (id, t) in enumerate(self.send_msg[source]):
            if id == msg_id:
                send_time = time - t
                self.send_msg[source].pop(i)
                break

        self.last_event_instance = self.net_instances[process_id]
        self.set_activity(process_id, thread_id, None)
        return send_time

    def transition_fired(self, process_id, thread_id, time, transition_id, values):
        self.last_event = "fired"
        self.last_event_instance = self.net_instances[process_id]
        transition = self.net.item_by_id(transition_id)
        self.last_event_activity = \
            TransitionExecution(time, process_id, thread_id, transition, values)
        for place in transition.get_packing_input_places():
            self.last_event_instance.remove_all_tokens(place.id)
        if transition.has_code():
            self.activites[process_id * self.threads_count + thread_id] = self.last_event_activity

    def transition_finished(self, process_id, thread_id, time):
        self.last_event = "finish"
        self.last_event_process = process_id
        self.last_event_thread = thread_id
        index = process_id * self.threads_count + thread_id
        self.last_event_activity = self.activites[index]
        self.last_event_instance = self.net_instances[process_id]
        self.activites[index] = None

    def copy(self):
        runinstance = RunInstance(self.project,
                                  self.process_count,
                                  self.threads_count)
        for i in self.net_instances:
            n = self.net_instances[i].copy()
            runinstance.net_instances[i] = n

        runinstance.activites = self.activites[:]
        return runinstance

    def get_perspectives(self):
        perspectives = [ Perspective("All", self, self.net_instances) ]
        v = self.net_instances.keys()
        v.sort()
        for i in v:
            perspectives.append(
                Perspective(str(i),
                self, { i : self.net_instances[i] } ))
        return perspectives


class ThreadActivity:

    def __init__(self, time, process_id, thread_id):
        self.time = time
        self.process_id = process_id
        self.thread_id = thread_id


class TransitionExecution(ThreadActivity):

    def __init__(self, time, process_id, thread_id, transition, values):
        ThreadActivity.__init__(self, time, process_id, thread_id)
        self.transition = transition
        self.values = values
        self.quit = False


class NetInstance:

    def __init__(self, process_id, tokens=None):
        self.process_id = process_id
        self.enabled_transitions = None
        self.new_tokens = {}
        self.removed_tokens = {}
        if tokens is None:
            self.tokens = {}
        else:
            self.tokens = tokens

    def add_token(self, place_id, token_pointer, token_value, send_time):
        lst = self.new_tokens.get(place_id)
        if lst is None:
            lst = []
            self.new_tokens[place_id] = lst
        if len(token_value) == 1:
            token_value = token_value[0]
        lst.append((token_pointer, token_value, send_time))

    def clear_removed_and_new_tokens(self):
        """
            'new_tokens' are moved into regular list of tokens and
            'removed_tokens' tokens are emptied
        """
        if self.new_tokens:
            for place_id in self.new_tokens:
                lst = self.tokens.get(place_id)
                if lst is None:
                    lst = []
                    self.tokens[place_id] = lst
                lst += self.new_tokens.get(place_id)
            self.new_tokens = {}

        if self.removed_tokens:
            self.removed_tokens = {}

    def remove_token(self, place_id, token_pointer):
        lst = self.tokens.get(place_id)
        if lst is None:
            return

        removed_lst = self.removed_tokens.get(place_id)
        if removed_lst is None:
            removed_lst = []
            self.removed_tokens[place_id] = removed_lst

        for i in xrange(len(lst)):
            if lst[i][0] == token_pointer:
                removed_lst.append(lst[i])
                del lst[i]
                return

    def remove_all_tokens(self, place_id):
        self.removed_tokens[place_id] = self.tokens.get(place_id)
        self.tokens[place_id] = None

    def add_enabled_transition(self, transition_id):
        if self.enabled_transitions is None:
            self.enabled_transitions = []
        self.enabled_transitions.append(transition_id)

    def copy(self):
        netinstance = NetInstance(self.process_id, copy(self.tokens))
        netinstance.enabled_transitions = copy(self.enabled_transitions)
        return netinstance


class NetInstanceVisualConfig(VisualConfig):

    def __init__(self,
                 transition_executions,
                 transitions_with_values,
                 enabled_transitions,
                 tokens,
                 new_tokens,
                 remove_tokens):
        # transition_id -> [ text_labels ]
        self.transition_executions = transition_executions
        self.tokens = tokens
        self.new_tokens = new_tokens
        self.removed_tokens = remove_tokens
        self.enabled_transitions = enabled_transitions
        self.transitions_with_values = transitions_with_values

    def transition_drawing(self, item):
        drawing = VisualConfig.transition_drawing(self, item)
        executions = self.transition_executions.get(item.id)
        drawing.executions = executions
        if item.id in self.enabled_transitions:
            drawing.highlight = (0, 1, 0)
        if item.id in self.transitions_with_values:
            drawing.with_values = True
        return drawing

    def place_drawing(self, item):
        drawing = VisualConfig.place_drawing(self, item)
        drawing.set_tokens(self.tokens[item.id],
                           self.new_tokens[item.id],
                           self.removed_tokens[item.id])
        return drawing


class Perspective(utils.EqMixin):

    def __init__(self, name, runinstance, net_instances):
        self.name = name
        self.runinstance = runinstance
        self.net_instances = net_instances

    def get_tokens(self, place):
        tokens = []
        for net_instance in self.net_instances.values():
            t = net_instance.tokens.get(place.id)
            if t is not None:
                for token_pointer, token_value, token_time in t:
                    tokens.append("{0}@{1}".format(token_value, net_instance.process_id))
        return tokens

    def get_new_tokens(self, place):
        tokens = []
        for net_instance in self.net_instances.values():
            t = net_instance.new_tokens.get(place.id)
            if t is not None:
                for token_pointer, token_value, token_time in t:
                    if token_time:
                        tokens.append("{0}@{1} --> {2}".format(token_value,
                                                               net_instance.process_id,
                                                               runview.time_to_string(token_time, seconds=True)))
                    else:
                        tokens.append("{0}@{1}".format(token_value, net_instance.process_id))
        return tokens

    def get_removed_tokens(self, place):
        tokens = []
        for net_instance in self.net_instances.values():
            t = net_instance.removed_tokens.get(place.id)
            if t is not None:
                for token_pointer, token_value, token_time in t:
                    tokens.append("{0}@{1}".format(token_value, net_instance.process_id))
        return tokens

    def get_transition_trace_values(self, transition):
        if self.runinstance.net is None:
            return None

        values = []
        runinstance = self.runinstance
        for i in range(runinstance.threads_count * runinstance.process_count):
            activity = runinstance.activites[i]
            if isinstance(activity, TransitionExecution) \
                and activity.transition.id == transition.id:
                    run_on = "{0}/{1} --> ".format(i // runinstance.threads_count,
                                                   i % runinstance.threads_count)
                    values.append(run_on + "; ".join(map(str, activity.values)) + ";")

        return values

    def get_visual_config(self):
        if self.runinstance.net is None:
            return VisualConfig()
        activies_by_transitions = {}
        for tr in self.runinstance.net.transitions():
            activies_by_transitions[tr.id] = []

        runinstance = self.runinstance
        transitions_with_values = []
        for i in range(runinstance.threads_count * runinstance.process_count):
            activity = runinstance.activites[i]
            if isinstance(activity, TransitionExecution):
                if activity.transition.id in activies_by_transitions:
                    if isinstance(runinstance.last_event_activity, TransitionExecution) \
                        and runinstance.last_event_activity.quit:

                        color = (0.5, 0.5, 0.5, 0.8)
                        activies_by_transitions[activity.transition.id].append((activity, color))

                    if activity != runinstance.last_event_activity:
                        color = (1.0, 1.0, 0, 0.8)
                        activies_by_transitions[activity.transition.id].append((activity, color))

                if activity.values:
                    transitions_with_values.append(activity.transition.id)

        if (runinstance.last_event == "fired" or runinstance.last_event == "finish") \
            and runinstance.last_event_activity.transition.id \
                in activies_by_transitions:
            color = (0, 1, 0, 0.8) if runinstance.last_event == "fired" else (1, 0, 0, 0.8)
            activies_by_transitions[runinstance.last_event_activity.transition.id].append(
                (runinstance.last_event_activity, color))

        transition_executions = {}
        for transition_id, lst in activies_by_transitions.items():
            lst.sort(key=lambda pair: pair[0].time) # Sort by time
            transition_executions[transition_id] = [
                ("{0.process_id}/{0.thread_id}".format(activity), color)
                for activity, color in lst ]

        tokens = {}
        for place in self.runinstance.net.places():
            tokens[place.id] = self.get_tokens(place)

        new_tokens = {}
        for place in self.runinstance.net.places():
            new_tokens[place.id] = self.get_new_tokens(place)

        removed_tokens = {}
        for place in self.runinstance.net.places():
            removed_tokens[place.id] = self.get_removed_tokens(place)

        enabled = set()
        enabled.update(*[ net_instance.enabled_transitions
                          for net_instance in self.net_instances.values()
                          if net_instance.enabled_transitions is not None ])

        return NetInstanceVisualConfig(transition_executions,
                                       transitions_with_values,
                                       enabled,
                                       tokens,
                                       new_tokens,
                                       removed_tokens)
