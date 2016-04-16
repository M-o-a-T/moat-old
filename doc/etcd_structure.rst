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

  * type

    Data types. See section `types` for details.

  * module

    Loadable modules.

    * ‹name›

      The module name, like ``knx`` or ``onewire``.

      A module is always coded in a single language.

      * language

        "python" (for now).

      * descr

        Some one-line description of the module.

      * doc

        Some multi-line description of the module.

      * code

        The actual module, e.g. ``moat.ext.onewire.Module``.

      * ‹subsys›

        Name of the code entity, e.g. ``moat.ext.onewire.dev.OnewireDevice``.

        Known subsystems:

        * device

          The node for the /device/‹subsys› tree.

        * bus

          The node for the /bus/‹subsys› tree.

        * cmd_ext

          The "moat ext ‹subsys›" subcommand.

        * cmd_dev

          The "moat dev ‹subsys›" subcommand.

        * cmd_bus

          The "moat bus ‹subsys›" subcommand.

  * task

    This section describes possible tasks, for the benefit of external
    configuration editors.

    * whatever …

      This hierarchy describes the task definitions which MoaT knows about.
      The actual structure is not prescribed, though Best Practice is that
      built-in commands start with "moat". External modules should use
      their module name as a prefix as to avoid conflicts.

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

          Describes the code's configuration variables.

          * name …

            Name of the type (/meta/type/name…) of this item.

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
  If an RPC endpoint exists, the device is read directly.

  * <name>

    Some hardware specific interface name.

    In addition to the attributes described here, any attribute of the type
    may be overridden here.

    * name

      Some human-readable name

    * type

      The data type this input has. See `types`, below.

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

  Outputs may be changed by sending an RPC request.

  * <name>

    Some hardware specific interface name.

    In addition to the attributes described here, any attribute of the type
    may be overridden here.

    * name

      Some human-readable name

    * type

      The data type this output has. See `types`, below.

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

Types
......

Types are located at ``/meta/types``. They're tagged with ``:type``.

Types can be subclassed for restrictions, modifications, or display
requirements. Thus, ``/meta/types/float/temperature/:type`` is a
specialization of ``/meta/types/float/:type``. (You could add more levels,
e.g. an indoor temperature for controlling room temperature must be within
3…30 °C.)

The base type contains a JSON schema for the possible values.

* <name> …

  The type (hierarchy).

  * :schema

    Base types only: the type's JSON schema.

  * :type

    The actual type description.

    Top-level entries have a "structure" element which describes the
    data (JSON schema) for the benefit of editors etc. That element
    is set when importing, and is basically immutable. All other
    possible entries are described there.

    The unit conversion code looks for all entries in the next level(s)
    up, thus you should never set a particular value more than once.
    All elements are optional and have sensible default values where
    applicable.

    The following items describe types, not actual entries. Thus,
    the details for the type "bool/on_off" are stored at
    "/moat/meta/type/bool/on_off/:type"; any attribute not detailed
    there will be read from "/moat/meta/type/bool/:type". The entry
    "bool", below, describes the structure of these data.

    Floating point numbers' "display/gamma" entry requires a
    specialized user interface element. Everything else is
    straightforward and can (should!) be implemented using a
    JSON schema interpreter.

    Conflicts between the JSON schema data and the descriptions below
    are a bug.

    * bool

      A bit. Something that can be either "on" or "off".

      * true

        Display value for "on" or "true" state. The default is "true".

      * false

        Display value for "off" or "false" state. The default is "false".

    * float

      Some non-integer number. Temperature, power consumption, percentages, …

      There are standard subtypes like "float/fraction" (between 0 and
      1 inclusive) or "float/temperature" (between -273.15 and a
      million or whatever, though usually limited to -20 to 100).

      The value stored in etcd / used in AMQP messages / whatever is
      the one that's most useful to a *computer*. For instance, the
      volume setting of your stereo goes from zero "silent" to 1 "all
      the way up".

      * min

        The minimum value. Default: None.

        This is the "computer" value. Use the display section, below,
        to convert to something human-readable.

      * max

        The maximum value. Default: None. See "min".

      * display

        This section describes how to convert between "computer" values
        and "human-readable" ones.

        Formula: human_value = (computer_value^gamma)*factor+offset

        For a straight percentage: factor=100 unit=' %' step=1
        For dimmable LED lights: add gamma=1.5
        For Fahrenheit: factor=1.8 offset=32

        For your stereo's volume: factor=10 (you might want to use some
        gamma; also don't forget to set "max" 📢 to something like 0.5,
        i.e. to be compatible with your hearing and/or the neighbors).

        * gamma

          Gamma is useful for modifying a value between 0 and 1 that
          e.g. the difference between 0.1 and 0.2 has the same
          perceived magnitude as that between 0.8 and 0.9.

          Obviously the default is 1. If the change at the low end is
          too granular when you change the value in your UI, decrease
          gamma; if the problem is on the high end, increase it.

          You can visualize gamma as shifting the midpoint of the
          value's range up or down. Thus, if you want to show a slider for
          the gamma value in your front end:

          gamma = 1/(1-ui_value)-1

          ui_value = gamma/(gamma+1)

          which makes an UI value between 0 and 1 (neutral: 0.5)
          corresponds to a gamma between 0 and +∞ (neutral: 1).
          You probably want to restrict the UI to values between
          0.1 and 0.9.

          Never set gamma to zero.

          Negative gamma values invert the value. Do not use them if
          the value can be zero. The only negative gamma which is
          useful in the real world is -1: you can use it to convert
          e.g. l/km (displayed with factor 100, as the customary
          real-world unit is l/100km) to miles per gallon (gamma -1,
          factor 2.352 (liters per gallon divided by kilometers per mile)).

        * factor

          Multiply with this value. For instance, "float/percent" would
          use a factor of 100 here. Your stereo's volume might go up to
          10.

          This value must not be zero, for obvious reasons.

        * offset

          Add this value. For instance, to display temperatures in °F,
          the offset would be 32 (with a factor of 1.8).

        * unit

          The value's unit, as displayed for human consumption.
          "°C" or "kWh" or "%" or whatever makes sense.

        * step

          Some natural increment (for a human) to use, in "human" units.
          The default is 1.

    * int

      Some "naturally-integer" type, like the number of eggs in a basket
      or the number of devices that are switched on.

      Don't use integers just because your device's setting only takes
      integers. You might want to use a different device some day, or
      it might make sense to apply a gamma.

      * min

        Obvious. ;-)

      * max

        Also obvious.

    * str

      Some text.

      * encoding

        This is the encoding which the device wants. The data itself is
        always stored to etcd in UTF-8.

      * maxlen

        The max number of bytes (not characters) which the device
        understands.

