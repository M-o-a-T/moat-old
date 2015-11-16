========
The MoaT
========

------------
What's that?
------------

`MoaT` stands for "Master of all Things". It's an open control and data gathering framework for the "Internet of Things" … well, almost.

What's the problem?
-------------------

There are a few.

Most things out there speak their own protocol, so you need something to
bind it all together.

Other "bind it all together" frameworks are monolithic programs; if you
need to extend them, you have to do it on their terms and in their language.

They run on exactly one machine. If that machine dies, or just needs to get
updated, you lose.

When they do something wrong, you need invasive methods (instrument code
with debug statements, enable debugging and restart, dig through verbose
logs …) all of which disrupts the parts that work.

When you reconfigure something, you need to remember to reload the daemons
in question.

When an error happens, it's silent, you need to dig through logs.

The MoaT is different
---------------------

It uses an external messaging bus (AMQP) in a way that can be passively
monitored, for *all* of its communication.

It uses an external configuration storage (etcd) for *all* of its state.

Thus you can write extensions in any programming language you like.

All MoaT processes should dynamically reconfigure themselves to adhere to
that state if/when it changes.

The MoaT's messaging system is written in a way that enables redundant
processes on multiple machines to not interfere with each other.

The messaging systems (RabbitMQ and etcd) can be configured to run
redundantly, on multiple systems.

The inevitable errors get tagged, so that one problem triggers one message
and you can check current state without digging through logs.

This means that there's no single point of failure on either the machine's
or the human's side. 

-----
Usage
-----

First, you configure etcd and RabbitMQ the way you like.

In AMQP, the default virtual host is "/moat". Likewise, MoaT's etcd subtree
defaults to "/moat". Modify the included ``test.cfg.sample`` file as
appropriate, and copy it to ``/etc/moat.cfg``.

Then, run the "moat test" command.

--------------
Implementation
--------------

Data structures
+++++++++++++++

config
------

The configuration file is a `YAML` file. It contains enough information to
connect to etcd, wich in turn contains the information to connect to AMQP.

etcd
----

The MoaT data is completely contained in a sub-tree, by default ``/moat``.

* config

  Configuration.

  * amqp

    Parameters for AMQP (host name, exchange and queue names, etc.)
    This is mostly self-explaining. See the `dabroker` documentation for
    details.

  * special/DOMAIN/config

    These entries augment the global configuration. Specifically, if your
    host name is "foo.bar.example", then these entries are looked up:
    
    * special/example/config

    * special/example/bar/config

    * special/example/bar/foo/config

    and overwrite the respective global entries. Anythign not specified is
    left alone.

  * run

    Various constants for task processing.

    * ttl

      how long until the "running" indicator expires

    * refresh

      how often to refresh the TTL. This is expressed as a fraction of the
      ``ttl`` value.

  * testing

    A flag to indicate that we're testing.

* status

  * errors

    Error state counters. MoaT tries to keep them accurate, given that etcd doesn't
    have transactions.

  * run

    Running programs note their presence here. Each task's entry is under
    "/status/run/APPNAME/TASKNAME", with these items:

    * started

      Unix timestamp.

    * running
      
      Unix timestamp. This entry shall be equipped with a TTL and updated often enough so that it won't time out.
      If a task subsequently finds that its entry has in fact timed out, it must abort.

    * state

      The last state (ok/warn/error/fail) the task has exited with. The
      task writes this when ending, just before removing its "running"
      status.

    * stopped

      Unix timestamp. Date when "state" was written. This may have been
      done by a cleanup process which noted the expired "running" entry.

    * message

      The error message it has died with, if applicable.


