# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2016 by Matthias Urlichs <matthias@urlichs.de>,
##  it is licensed under the GPLv3. See the file `README.rst` for details,
##  including optimistic statements by the author.
##
##  This program is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License (included; see the file LICENSE)
##  for more details.
##
##  This header is auto-generated and may self-destruct at any time,
##  courtesy of "make update". The original is in ‘scripts/_boilerplate.py’.
##  Thus, do not remove the next line, or insert any blank lines above.
##BP

from moat.types.module import BaseModule

## DO NOT change the numbers
modes = {
    0: ('ignore', "keep data of this type, but ignore them"),
    1: ('delete', "remove values of this type"),
    2: ('store', "Continuous value (power use, temperature, humidity)"),
    3: ('count', "Increasing discrete value (rain gauge, lightning counter)"),
    4: ('cont', "Increasing continuous value (power meter)"),
    5: ('event', "Single event (button pressed)"),
    6: ('cycle', "Cyclic value (wind direction)"),
    7: ('notice', "Continuous event (movement detected)"),
    8: ('persist', "persistent changes (light switch)"),

# The difference between "count" and "cont" is that values for the former
# get credited to the interval in which they appear, while the latter gets
# distributed evenly

# The difference between "event" and "notice" is that level 0 will count
# the latter only once
}

modenames = {}
for a,b in modes.items():
    modenames[b[0]] = a

class GraphModule(BaseModule):
    """\
        This module logs stuff to SQL (like mysql) and aggregates things.
        """

    prefix = "graph"
    summary = "Log+aggregate graph data"
    
    @classmethod
    def entries(cls):
        yield from super().entries()
        # yield "cmd_conn","moat.ext.onewire.cmd.conn.ServerCommand"
        yield "cmd_ext","moat.ext.graph.cmd.GraphCommand"
        # yield "cmd_dev","moat.ext.graph.cmd.GraphCommand"
        # yield "bus","moat.ext.onewire.bus.OnewireBusBase"
        # yield "device","moat.ext.extern.dev.ExternDeviceBase"

    @classmethod
    def task_types(cls):
        """Enumerate taskdef classes"""
        from moat.task import task_types as ty
        return ty('moat.ext.extern.task')

