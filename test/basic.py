#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
import sys

from test import run_logger,SayWorker,SayMoreWorker
run_logger("basic")

startup_ev = h.Event("startup")
hello_ev = h.Event("say","hello")
hello2_ev = h.Event("say more","greeting")
shutdown_ev = h.Event("shutdown")
	
h.register_worker(SayWorker("TellMe"))
h.register_worker(SayMoreWorker("say something"))

h.process_event(startup_ev)

h.process_event(hello_ev)

e = h.collect_event(hello2_ev)
h.log(e)
e.run(hello2_ev)

h.process_event(shutdown_ev)

