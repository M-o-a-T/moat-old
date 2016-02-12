================
Hacking the MoaT
================

This chapter is about extending the MoaT system.

Principles
==========

Testing!
--------

Write a couple of testcases which exercise your code. It's not difficult
and *will* save time and frustration. Trust me on this.

Manual debugging is somewhat difficult because MoaT protects itself by
a number of timeouts. dissecting a broken data structure doesn't get any
easier if you're forced to run the main loop every five seconds. Thus,
you can set the environment variable ``MOAT_DEBUG_TIMEOUT`` to the number
of seconds you need for a debugging session. This causes all destructive
timeouts to last at least that long.

Etcd is authoritative
---------------------

The whole system has one "source of truth", and that's the etcd contents.

You want to know the current state of an output? check etcd.

You want to know how warm a room is? check etcd.

You notice that that temperature value is too old? raise an error;
don't try to go and get that value yourself.

Code which polls your system for "structural" changes should always be
separate. Once a home is set up and everything that should be connected to
a bus is present and working, there's no reason to enumerate devices on it.

Etcd is dynamic
---------------

Never require restarting any process. Events get lost when you do that.
Instead, your code needs to listen to any etcd changes which could affect
it, and incorporate them into its data model.

If data you need aren't present, wait for the problem to be fixed.

If etcd is inconsistent, raise an error and exit.

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

This implies that all state-changing commands get transmitted via RPC, not
just with an alert.

If you interface with a pure message-based system, like OpenHAB's MQTT
adapter, wait for the state change to arrive.

Redundancy is good
------------------

Think about what happens when your code runs on two devices at the same
time. Keep in mind that etcd is not synchronous. For instance, let's assume
you have two nodes which receive the radio signal of a switch. Both will
send a "switch pressed" alert message to AMQP; this means that the code
analyzing switch presses needs to compare timestamps – otherwise a single
switch press will turn the light on, then off again immediately afterwards.

Also, both will try to update the switch state in etcd. One of these
updates will fail, which you need to handle gracefully.

Some tasks should not run concurrently. For instance, to poll a 1wire bus
for alerts or new devices by multiple processes in parallel will cause
strange bugs.

The correct way to handle this is to create an expiring etcd node. If it
exists, wait for it to vanish (if you're some long-running code) or exit
with a notification (if you are a one-shot command from the command line).
Do not exit without deleting that node.

Concurrency
-----------

Think about what happens when your code is called by multiple other systems
at the same time. For instance, the RPC handler affecting an output should
have a lock so that two tasks which try to affect the same output don't
conflict. If the state your caller wants to set is set already, don't do
anything. (Exception: you have no way to verify that your command arrived
at the other end.)

Resets
------

Let's face it, sometimes there are power outages, blown fuses, computers
rebooting – you get the picture. Conversely, sometimes one wants to power
down everything (going on vacation, you're on generator and need to
conserve as much as possible) without going through every single output.

XXX TODO: MoaT defines a couple of special, bus-specific alerts for these
situations. Please handle them.

