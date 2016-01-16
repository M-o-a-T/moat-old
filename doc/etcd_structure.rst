----
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

    A flag to indicate that we're in test mode.

* status

  * errors

    Error state counters. MoaT tries to keep them accurate, given that etcd doesn't
    have transactions.

  * run

    Running programs note their presence here.
    
    * whatever …
    
      This hierarchy is used for run-time process state, i.e. whether it
      runs at all, when it started, or the error message it exited with.

      Processes have unique names.
      
      * :task

        This directory describes one possibly-running process.

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

        * debug

          Debugging information, e.g. a stack trace.

* task

  * whatever …

    This hierarchy describes the tasks which MoaT knows about. The actual
    structure is up to you. "moat run foo" will run all jobs in the
    /task/HOSTNAME/foo/… hierarchy.

    * :task

      This directory describes an actual task to run.

      * task

        The name of this task's definition, stored at /meta/task/TASK/:taskdef.

      * name

        Some human-readable name for this task.

        Not used as an index.

      * summary

        Human-readable description of what this particular job does.

      * data
    
        Task-specific configuration, passed to the task. TODO; probably JSON.

      * ttl, refresh, …

        You can override the values from /config/run here.

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

  This hierarchy describes all external devices known to MoaT.

  This includes devices behind "foreign" automation systems like FHEM or OpenHAB.

  * <dev_type>

    The type of device, like 'onewire'.

    * dev_id …

      Some device-type-specific naming scheme. 1wire uses class/device.

      * :dev

        Standard device node. See below.

* bus

  This hierarchy describes bus systems, i.e. some common method to talk to
  a group of devices. This may or may not be a server on the same system.

  * onewire

    1wire is a bus which uses a single bi-directional wire for signalling.
    You need two more (ground and power supply).

    * name

      Some unique name for that bus.

      * server

        How to talk to that bus. Default is host/port, i.e. OWSERVER.

        * host

          Host name of this server

        * port

          TCP Port to connect to.

      * info

        Some sort of human-readable text

      * bus

        The collection of buses this server knows.

        * path
          
          The bus path on the server, like "bus.0" or "bus.1 1F.12345678 main". 
          
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
......

Devices are located under /device/BUS/…/:dev with some common attributes.

A device may have more than one independent input or output. If a port is
configurable, auto-discovery should add it as an input.

* name

  Some human-readable name for whatever it is.
 
* attr

  Possible generic attributes, not interpreted by the MoaT core.
 
* path

  Some bus-specific attribute (physical / hardware address) that tells MoaT
  where to find the device. This allows devices to be moved if necessary.

* input

  Physical inputs are described by this generic structure.

  Inputs are either polled, or they signal their change independently.
  If polling is required, set the ``poll`` attribute.

  * <name>

    Some hardware specific interface name

    * name
     
      Some human-readable name

    * type

      whichever data type this input has

    * value

      current value of that input

    * timestamp

      time (Unix seconds) when the input was last received/polled

    * alert

      AMQP: destination for signalling change

      If this attribute is not present, no messages will be sent.

    * rpc

      AMQP: address to read the device

      This request triggers an immediate read of the device in question.
      
      If that is not possible or too disruptive, this endpoint should not
      exist.

    * poll

      An interval (seconds) telling how often the input's value is read or
      transmitted by the device.

      If this entry is not present, current values need to be requested via RPC.

    * attr

      Generic attributes, used by visualizing code or similar

* output

  Physical outputs are described by this generic structure.

  Outputs are only changed by sending an RPC request.

  * <name>

    Some hardware specific interface name

    * name
     
      Some human-readable name

    * type
               
      whichever data type this output understands

    * value

      last transmitted value

    * timestamp

      time (Unix seconds) when the output was last set

    * rpc

      AMQP: destination to set the device

      The RPC reply must be delayed until success is verified, if / as far
      as possible

    * alert

      AMQP: destination for signalling change

      If this attribute is not present, no messages will be sent.

    * attr

      Generic attributes, used by visualizing code or similar

