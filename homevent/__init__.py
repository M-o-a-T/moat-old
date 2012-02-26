# -*- coding: utf-8 -*-

## 
##  Copyright © 2007-2008, Matthias Urlichs <matthias@urlichs.de>
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

"""\
This is the core of the event dispatcher.
"""

from homevent import geventreactor
geventreactor.install()

from gevent import monkey
monkey.patch_all()
del monkey


from homevent.context import Context
from homevent.event import Event
from homevent.worker import Worker,SeqWorker,WorkSequence
from homevent.run import process_event,register_worker,collect_event
from homevent.logging import log
from homevent.reactor import start_up,shut_down, mainloop
from homevent.statement import main_words,global_words
from homevent.check import register_condition

#import homevent.twist # for side effects

VERSION = "0.2.20"

__all__ = ("Event","Worker","SeqWorker","WorkSequence",
	"collect_event","process_event", "register_worker", "mainloop")
# Do not export "log" by default; it's too generic.

