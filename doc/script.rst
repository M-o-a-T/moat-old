User scripts
============

Scripting is an important aspect of MoaT.

Script storage
--------------

MoaT stores user scripts in etcd, under /meta/script/…/:code.

See `etcd_strucure` for details.

The command to control this is ``moat script def …``.

Script tasks
------------

You actually run scripts by creating (and starting) a task with a taskdef of "task/script"
and a "script" entry containing the script's subpath. That way, scripts
serve as a template and may run multiple times, with different values.

You can place that task anywhere in MoaTs task hierarchy.

The command to add script tasks is ``moat script …``.

Scripting environment
---------------------

Your script has access to one global environment object, "moat". Through
this you can access the rest of the MoaT system.

Warning: Do not register your code to the objects accessible through
``moat.root``. Always use the interface provided, which ensures that
your code is cleanly de-registered if/when it terminates.

The methods you pass to the ``moat`` object must be asynchronous.
Your code *must not* sleep, or use external services, except by using
asyncio-compatible code.

Scripts are isolated from each other; if you need to exchange messages or
invoke procedures, use AMQP.

You may check whether another task or script invocation is (most likely to
be) running by checking whether ``/status/run/…/:task/running`` exists, but
you shouldn't need to.

Only data stored in etcd are retained across script invocations.

* moat.setup(…)

  Your top-level code shall call this procedure before doing anything else.
  This might allow you to customize your scripting environment in the future.

  You must call ``moat.setup()`` exactly once.

* moat.on_start

  This decorator marks code to run when your script starts up.

      @moat.on_start
      def start_fn():
          pass

  Procedures running due to on_start() may add new such functions.

* moat.on_stop

  This decorator marks code to run when your script terminates.

  You should not depend on this code to actually execute, though MoaT will
  do its best to do so.

      @moat.on_stop
      def stop_fn():
          pass

  Calls will run in reverse order of registration.

* moat.run

  This decorator marks the function thus decorared as your script's main
  code. Not using this is equivalent to

      @moat.run
      async def _main():
          await moat.stopping

  There may only be one procedure marked with ``moat.run``.

* moat.wait

  Wait until some specific time.

      … whenever …
      await moat.wait("12 hr")
      … it is now 12 o'clock exactly

  The time specification's meaning can be modified with the "current"
  parameter:

  * True

    Delay until the timespec matches as given. For instance, "12 hr" would
    match at 12:45, thus the code would run immediately.

  * False

    Delay until the timespec does not match. For instance, at 12:45 "12 hr"
    would delay fifteen minutes.

  * None (Default)

    Wait until the timespec starts to match; at 12:45 "12 hr" would delay
    23 hours and 15 minutes. This is equivalent to calling first
    ``moat.wait(…, current=False)``, followed by ``moat.wait(…,
    current=True)``, though nested callbacks like this are needlessly
    complicated.

  Instead of a single string, you may pass the values as an array, i.e.

      @moat.wait("12","hr","10","min")
      def twelve_ten():
          …

  See `times` for which time specifications are supported.

  You may pass the base time as the '`now`` parameter. If that is the sole
  argument, ``moat.wait`` will wait until that time is reached.

  ``moat.wait`` cannot remember execution across invocations. If you need
  that, store the timestamp in some data variable which you check at the
  start of the script. It also cannot trigger execution when your script is
  not running in the first place.

* moat.run_at

  Like ``moat.wait``, but registers a callback which remembers to call the
  function.

      moat.run_at("12 hr", fn=my_func)

  The return value is a timer object with a ``.cancel()`` method.

* moat.time_at

  Like ``moat.wait``, but instead of waiting for the specified time, returns
  the corresponding Unix timestamp. This allows you to implement more
  involved time scenarios.

* moat.end()

  Call this function if your script should terminate normally.

  For abnormal termination, simply raise an appropriate exception.
  (When in doubt, subclass ``RuntimeError``.)

  ``moat.end()`` takes no parameters.

* moat.stopping

  This Future marks the fact that your script is terminating, triggered
  either by a call to ``moat.end()`` or by an exception in any of your code.

* moat.data

  Your task's ``data`` subdirectory. This is accessible with standard ``etcd-tree``
  methods. Be aware that you cannot add new values.

* moat.tree

  The complete ``etcd-tree`` hierarchy. Note that this hierarchy may be
  incomplete, i.e. there may be an EtcAwaiter node instead of a sub-tree.

* moat.rpc

  Register a RPC function.

  Usage:

	@moat.rpc("foo.bar.baz")
	async def baz_handler(** kw):
	    …

* moat.on_alert

  Register an event handler.
  Usage: like ``.rpc``.

* moat.debug_obj

  Register a debug object. Debug objects are accessed via ``qbroker``'s
  debug mechanism: the ``task`` member contains a ``script`` hash with your
  script's path as the key to look up the value you pass in here.

      …
      moat.debug_obj(infodir)

* moat.monitor(obj)

  Monitors an object for changes.

  Typically you don't store the path to the object in your script.
  Instead, create a data member of "str/ref" which holds the object's name.
  This way you may re-use the script, instead of copying it.

      …
      # etcd: /moat/script/…/:code/data/device contains "str/ref"
      obj = moat.data['device']
      @moat.monitor(obj)
      def obj_changed():
          …

      The object's ``is_new`` variable is ``True`` when ``obj_changed()``
      is first invoked, ``False`` thereafter, and ``None`` if the object is
      deleted.

      If you want to know about an object's creation, watch its parent; the
      name of the new child node is a member of the object's ``.added``
      set variable. Likewise, ``.deleted`` contains the names of removed
      children, though by the time the callback is running these no longer
      exist.

* moat.logger

  A standard Python logger (with ``.debug``, ``.info`` etc. methods) which
  you can use to report things.

* moat.set_error

  Note the fact that your script found an error condition.

      …
      moat.set_error("owch", "I had an owie")

  See `error handling` for details.

* moat.clear_error

  Note the fact that the error condition has been fixed, or does not exist.

    …
    moat.clear_error("owch")

  There is no way to check whether a particular error exists; instead, you
  should simply call set_error / clear_error again.

+* moat.load
 
  Load another script.
 
  This code behaves, roughly, as if the loaded script was copied into the
  current one at this point. If the included script needs to be fetched
  from etcd, loading your script will be restarted. Your script will also
  be restarted if the included script is modified; it will be terminated if
  the included script is deleted.

      moat.load("some/library")

  Any call to ``moat.run()`` in the included script is ignored; the
  parameters of the ``moat.setup()`` calls need not be identical.

TODO
====

* add a helper function to run some code in a separate thread

