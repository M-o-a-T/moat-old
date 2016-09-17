================
Hacking the MoaT
================

This chapter is about extending the MoaT system.

Principles
==========

This chapter details some of the basic principles you should adhere to when
writing a MoaT extension.

Testing!
--------

Write a couple of testcases which exercise your code. It's not difficult
and *will* save time and frustration. Trust me on this.

Manual debugging is somewhat difficult because MoaT protects itself by
a number of timeouts. Dissecting a broken data structure doesn't get any
easier if you're forced to run the main loop every five seconds. Thus,
you can set the environment variable ``MOAT_DEBUG_TIMEOUT`` to the number
of seconds you need for a debugging session. This causes all destructive
timeouts to last at least that long. This does mean that if you force-quit
a MoaT script, you may need to wait that long before retrying.

Etcd is authoritative
---------------------

The whole system has one "source of truth", and that's the etcd contents.

You want to know the current state of an output? check etcd.

You want to know how warm a room is? check etcd.

You notice that that temperature value is too old? raise an error;
don't try to go and get that value yourself.

Code which polls your system for "structural" changes should always be
separate. Once the system is set up and everything that should be connected
to is present and working, there's no reason to enumerate any devices.

Etcd is dynamic
---------------

Never require restarting a process. Events get lost when you do that.
Instead, your code needs to listen to all etcd changes which could affect
it, and incorporate these changes into its data model.

If data you need isn't present, raise an error and exit.

If etcd is inconsistent, raise an error and exit.

Logging error conditions is a big TODO.
Don't forget to remove the error condition when a problem is fixed!

Etcd is not useful for real-time events
---------------------------------------

Yes, you write the fact that somebody pressed a switch (and the time) to
etcd, simply because it's state and you write all state to etcd as a matter
of principle.

No, you don't listen to that switch's state in etcd to determine whether to
turn on the light. That's too slow. Low-power systems may take a
significant fraction of a second to propagate changes to etcd state to
every listener.

Real-time is what AMQP is for.

External state changes must be verified
---------------------------------------

If at all possible, check that some external state in fact changed before
you answer the RPC command that triggered the change. If your code emits
a radio signal, wait for an ACK, or ask the device that the command has
arrived, or (if the radio is unidirectional) add a second receiver which
reports that the signal has been sent successfully.

All state-changing commands must be transmitted via RPC. Don't just blast
off an alert and hope that a receiver will be present.

If you interface with a pure message-based system, like OpenHAB's MQTT
adapter, wait for the state change to arrive.

Redundancy is good
------------------

Think about what happens when your code runs on two devices at the same
time. Keep in mind that etcd is not synchronous. For instance, let's assume
you have two nodes which receive the radio signal of a wall button. Both will
send a "button pressed" alert message to AMQP; this means that the code
that's analyzing these presses needs to compare timestamps – otherwise a
single press will turn the light on, then off again immediately afterwards.

Also, both will try to update the switch state in etcd. One of these
updates will probably fail, which you need to handle gracefully.

Don't try to update etcd first if you want to protect yourself against
multiple messages for one event. This may or may not work: the task
monitoring etcd may or may not have been fast enough.

Some tasks should not run concurrently. For instance, to poll a 1wire bus
for alerts or new devices by multiple processes in parallel will cause
strange bugs.

The mostly-correct way to handle this is to create an expiring etcd node.
If it exists, wait for it to vanish (if you're some long-running code) or
exit with a notification (if you are a one-shot command from the command
line). Do not exit without deleting that node.

The really correct way to handle this is using a separate, well-named task.
These are guaranteed to only run on one node.

Concurrency
-----------

Think about what happens when your code is called by multiple other systems
at the same time. For instance, the RPC handler affecting an output should
have a lock so that two tasks which try to affect the same output don't
conflict. If the state your caller wants to set is set already, don't do
anything.

Resets
------

Let's face it, sometimes there are power outages, blown fuses, computers
rebooting – you get the picture. Conversely, sometimes one wants to power
down everything (going on vacation, you're on generator and need to
conserve as much as possible) without going through every single output.

XXX TODO: MoaT defines a couple of special, bus-specific alerts for these
situations. Please handle them.

Tasks
=====

Tasks are central to MoaT. Tasks are used to talk to external devices,
monitor AMQP and etcd, and execute schedules.

etcd structure
--------------

Tasks are described at three places within the etcd hierarchy.

* the task definition at ``/meta/task/…/:taskdef`` names the class that's
  implementing a task, the programming language it's written in, and the
  type of any data associated with tasks of this type.

  In Python, the class must be a subclass of ``moat.script.task.Task``.

* the task declaration at ``/task/…/:task`` contains a pointer to the task
  definition (the ``taskdef`` entry) and actual values for the task's data.

* the status directory at ``/status/run/…/:task`` (same sub-path as the
  task declaration) describes whether the task is actually running, when it
  was started, and why it died last.

Data creation
-------------

Task definitions are created when MoaT is installed or when modules are
added, by scanning for subclasses of ``moat.script.task.Task``.

The task declarations necessary for the system to run are auto-created as
needed. An etcd directory which requires tasks has a ``task_monitor``
attribute with an async iterator which reports task requirements. The
parent object should create a monitoring task (task definition
``moat/task/monitor``) that translates these into actual task entries. A
task to do that for the root object is created when running ``moat test``.

A task's status directory is auto-created when the task is first started.
The ``running`` entry in that directory is updated every couple of seconds
and gets auto-deleted when the task (or the machine it runs on) dies.

Declaring tasks
---------------

As described above, new task definitions should only be auto-created based
on data within etcd. You should never scan a bus or check a remote website
from within a task scanner.

Instead, the bus scanner / site scraper should be a separate task which
reports its data to etcd, where a directory scanner task notices your
devices and creates the tasks required to manage them.

Rationale
---------

* redundancy. Tasks may run on multiple machines; MoaT ensures that they
  won't step on each other's toes. MoaT will restart a task somewhere else
  if the original system should die.

* efficiency. The tasks which directly control something must, in most
  cases, run on the device to which that something is attached. Since
  embedded systems frequently have low memory or network bandwidth, doing
  any other work on them does not make sense.

* discoverability. One guiding principle of MoaT is that the entire state
  of the whole system shall be visible and (if possible) changeable by
  accessing etcd.

* reliability. Some connections are intermittent or unreliable; scanning
  some bus systems takes time and/or slows the bus down unacceptably.
  By moving all "scan the bus" operations to distinct tasks that only run
  intermittently or at installation time, MoaT isolates the rest of the
  system from having to deal with devices that randomly come and go.

The details
-----------

It's best to demonstrate all of this by way of an example. We'll examine
the 1wire bus and look at the mechanics of adding a device to it.

The system pre-creates a single scanning task (``task/moat/scan``)
which monitors the MoaT etcd root directory. It statically registers a
sub-scanner for the ``bus`` directory (at ``task/moat/scan/bus``; the
scanner for path ``/X`` always is at ``task/moat/scan/X``, and it always is
of type ``task/collect``), which will add a bustype-specific scanner to
each entry there.

The scanner on ``bus/onewire`` simply watches for subdirectories.
When triggered (presumably, you added a new 1wire server using the command
line), it will add a `OnewireBusSub` scanner to the
``bus/inewire/NAME/bus`` subdirectory, *and* add a ``onewire/scan`` task
which enumerates the buses on that server (named
``task/onewire/SERVERNAME/scan``).

That task will scan the owserver at that host and add each bus it finds as
a subdirectory of ``bus/onewire/SERVERNAME/bus``, which will be picked up
by `OnewireBusSub`, which will then start a ``onewire/scan/bus`` task to
enumerate the devices on that bus, *and* another scanner to decide what to
do with them once they appear in etcd.

That scanner looks at the types of all devices on the bus and basically
asks them which job(s) they need to register. For instance, if there's a
thermometer on the bus then a periodic request to start temperature
conversion will be put on the bus, followed by reading all of them. (This
minimized bus traffic; more importantly, it prevents directly reading the
temperature from blocking the bus for a whole second.) If there are any
alarm-capable devices, an alarm handler will be installed which does
high-frequency polling for devices which require service. And so on.

Devices typically have inputs and/or outputs, represented by TypedInputDir
/ TypedOutputDir objects. These install AMQP handlers for read / write
requests.

Device handlers are tasks below ``task/onewire/SERVERNAME/run``. They do not
depend on any bus- or etcd-scanning tasks. In other words, once the
scanning tasks have run their course, they are no longer required (as long
as you don't add new devices to your bus).

Since each handler has one specific job to do and does not depend on any
other tasks running on the same machine, failing jobs can be debugged on an
isolated system.

However, there is one exception to this rule, which the onewire subsystem
exhibits: The alarm poll runs every tenth of a second; it requires the
alarm condition to be cleared as quickly as possible but it can't do
that within its own task (a fault there would block polling the whole bus).
It also can't send an AMQP message or set a notification in etcd: both
would be too slow.

To handle this case, a system that handles alarms has multiple tasks which
directly communicate with each other. Isolated debugging is still possible,
of course, as the default is "handle any open alarms now, wait later".


