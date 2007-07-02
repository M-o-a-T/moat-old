# *-* coding: utf-8 *-*

"""\
This is the core of the event dispatcher.
"""

from homevent.context import Context
from homevent.event import Event
from homevent.worker import Worker,SeqWorker,WorkSequence
from homevent.run import process_event,register_worker,collect_event
from homevent.logging import log,register_logger
from homevent.reactor import start_up,shut_down, mainloop
from homevent.statement import main_words,global_words

__all__ = ("Event","Worker","SeqWorker","WorkSequence",
	"collect_event","process_event", "register_worker", "mainloop")
# Do not export "log" by default; it's too generic.

from twisted.internet import reactor
def wake_up(old_call):
	
	def do_call(t,p,*a,**k):
		r = old_call(t,p,*a,**k)
		reactor.wakeUp()
		return r
	return do_call

reactor.callLater = wake_up(reactor.callLater)

