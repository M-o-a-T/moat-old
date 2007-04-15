#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
import sys
from homevent.module import Loader,Unloader
from homevent.run import process_event

from test import mainloop, run_logger,SayWorker,SayMoreWorker
run_logger("modules")

load_ev = h.Event("load","homevent.sample_module")
unload_ev = h.Event("say more","greeting")
	
h.register_worker(Loader())
h.register_worker(Unloader())

def main():
	d = h.process_event(load_ev)
	d.addCallback(lambda _: process_event(load_ev))
	d.addCallback(lambda _: process_event(unload_ev))

mainloop(main)

