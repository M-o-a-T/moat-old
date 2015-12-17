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

Main tree
.........

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

    * restart

      Default value for the time until restarting a job when it ends
      normally. If zero, no restart.

    * retry
    
      Initial value for the time until restarting a job when it fails, i.e.
      raises an exception. If zero, the task will not be retried.

      If a job fails again, the value is increased by a factor of 1.1.

    * max_retry

      This is the upper limit for the retry interval.

  * testing

    A flag to indicate that we're testing.

* status

  * errors

    Error state counters. MoaT tries to keep them accurate, given that etcd doesn't
    have transactions.

  * run

    Running programs note their presence here. Each task's entry is under
    "/status/run/TASKPATH/:task", with these items:

    * started

      Unix timestamp.

    * running
      
      Unix timestamp. This entry shall be equipped with a TTL and updated often enough so that it won't time out.
      If a task discovers that its entry has in fact timed out, it must abort immediately.

    * state

      The last state (ok/warn/error/fail) the task has exited with. The
      task writes this when ending, just before removing its "running"
      status.

    * stopped

      Unix timestamp. Date when "state" was written. This may have been
      done by a cleanup process which noted the expired "running" entry.

    * message

      The error message the task has died with, if applicable.

* task

  * whatever …

    This hierarchy describes the tasks which MoaT knows about. The actual
    structure is up to you. "moat run foo" will run all jobs in the
    /task/HOSTNAME/foo/… hierarchy.

    * :task

      This directory describes an actual task to run.

      * task

        The name of this task's definition, stored at /meta/task/NAME/:taskdef.

      * name

        Some human-readable name for this task.

        Not used as an index or similar.

      * summary

        Human-readable description of what this particular job does.

      * data
    
        Task-specific configuration, passed to the task. TODO; probably JSON.

      * ttl, refresh, …

        You can override the values from /config/run here.

      * :ref (TODO)

        Get any value not described here from /task/REF/:task.

    * :ref (TODO)

      Attach the sub-tree under /task/REF here. Sub-trees are joined, but
      :task directories are not, thus you can selectively disable a task.

* meta

  This section describes data about the MoaT installation itself.

  * task

    This section describes possible tasks, for the benefit of external
    configuration editors. It is optional.

    * whatever …

      This hierarchy describes the task definitions which MoaT knows about.
      The actual structure is up to you. "moat task list foo" will display
      all definitions in the /task/HOSTNAME/foo/… hierarchy.
      
      * :taskdef

        * name

          Human-readable name for this task.

          Please keep it unique.

        * language

          The programming language the code is written in.
          Probably "python", for now.
          
        * code

          Python: Full name of the Task object to run. Typically
          ``moat.task.MODULE.CLASS``, though you can use any callable that
          returns a ``moat.script.task.Task`` object.

        * summary

          This is a one-line description of the code.

        * description

          This is a multi-line description of the code. Please include
          information about the data fields which the user may set.
          
        * data

          Describes the code's configuration. TODO. Probably JSON, i.e.
          a json-schema structure.

* device

  * <dev_type>

    * <dev_id>

      * :dev

        Standard device node. See below.

        * path

          servername bus path…

          If this attribute is not present, the device currently cannot
          be found on any bus.

* bus

  * onewire

    * name

      * host

        Host name of this server

      * port

        TCP Port to connect to.

      * info

        Some sort of human-readable text

      * bus

        The collection of buses this server knows.

        * <unique>

          * path
          
            The bus path, like bus.0 or bus.1/1F.12345678/main
          
          * broken

            Counter for an unreachable bus. If too high, mark its
            devices as inaccessible.
          
          * devices

            * <dev_type>

              * <dev_id>

                Counter for a vanished device. If too high, mark the device
                as inaccessible.

      * scanning

        A lock for periodic bus scanning, to make sure two scanners
        don't step on each other's toes.


Device
.....

Devices are located under /device/TYPE/…/:dev with some common attributes.

* name

  Some human-readable name for whatever it is.
 
* attr

  Possible attributes.
 
* input

  An ``input`` subtree. See below.

* output

  An ``output`` subtree. See below.

Input
.....

Physical inputs are described by this generic structure.

Inputs are either polled, or they signal their change independently.
If polling is desired, set the ``poll`` attribute. If more than one input
uses an ``alert`` endpoint, they may be combined in a single message.

* input

  * name

    Some hardware specific interface name
    the device may have more than one input

    * type

      whichever data type this emits

    * alert

      AMQP: destination for signalling change

      If this attribute is not present, the input is ignored.

    * poll

      if present, an interval (seconds) telling how often the
      input's value should be read

Output
......

Physical outputs are described by this generic structure.

Outputs are accessed by sending an RPC request to the RPC address, with the
data-to-send in the ``data.‹name›`` element. If a device has more than one
output, all of them may be triggered in the same request.

* output

  * name

    Some hardware specific interface name
    the device may have more than one output

    * type
               
      whichever data type this understands

    * rpc

      AMQP: code to switch the device

