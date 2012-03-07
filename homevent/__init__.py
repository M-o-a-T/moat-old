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

import os
if "HOMEVENT_TEST" in os.environ:
	from homevent.testreactor import install
else:
	from homevent.geventreactor import install
install()
del install

from gevent import monkey
monkey.patch_all()
del monkey

# Convenience imports
from homevent.context import Context
from homevent.event import Event
from homevent.worker import Worker,SeqWorker,WorkSequence
from homevent.run import process_event,register_worker,collect_event
from homevent.logging import log
from homevent.reactor import start_up,shut_down, mainloop
from homevent.statement import main_words,global_words
from homevent.check import register_condition

from homevent import twist # for side effects

VERSION = "0.3"

__all__ = ("Context", "Event", "Worker","SeqWorker","WorkSequence",
	"collect_event","process_event","register_worker", "mainloop",
	"main_words","global_words", "register_condition")
# Do not export "log" by default; it's too generic.

