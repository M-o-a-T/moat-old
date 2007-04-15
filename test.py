#!/usr/bin/python
# -*- coding: utf-8 -*-

from homevent.module import Loader,Unloader
from homevent.run import register_worker
from homevent.parser import parse, register_statement, Help
from homevent.config import Load,Unload,WorkerList,ModList
register_worker(Loader())
register_worker(Unloader())

register_statement(Help())
register_statement(Load())
register_statement(Unload())
register_statement(WorkerList())
register_statement(ModList())

def logger(*x):
	print " ".join((str(d) for d in x))

import sys
print """Ready. Type «help» if you don't know what to do."""
while True:
	try:
		parse(sys.stdin, logger=logger)
		sys.exit(1)
	except Exception:
		from homevent.logging import log_exc
		log_exc("Parse error")
		print "Ready (again)."

