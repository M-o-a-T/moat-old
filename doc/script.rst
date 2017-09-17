User scripts
============

Scripting is an important aspect of MoaT.

Script storage
--------------

MoaT stores user scripts in etcd, under /meta/script/…/:code.

* code

  the actual code.

* language

  python

* created

  Creation date

* timestamp

  Date of last modification

* new-code

  If you want to update the code, this node contains the new version.
  The runtime will check it for syntax errors and auto-replace
  your program with the new version if there are no problems.

* old-code

  After replacing the code, this node contains the previous version so that
  you can revert the last update.

* current

  Marker for which version should be used. Possible values: "old" "new"
  "current".

* error

  Subdirectory with standard error information.

* data

  Directory with types for the script's variables. The contents must
  be subpaths of MoaT types.
  
Script tasks
------------

You actually run scripts by creating (and starting) a task with a taskdef of "script/run"
and a "script" entry containing the ``…`` part of the path to the script.

You can place that task anywhere in MoaTs task hierarchy.

* data

  Directory with (typed) values for your script.

Scripting environment
---------------------

All procedures must be asynchronous and may not sleep.

Your script has access to one global environment object, "moat". Through
this you can access the rest of the MoaT system.

Warning: Do not register your code to the objects accessible through
``moat.root``. Always use the interface provided, which ensures that
your code is re-registered if/when it terminates.

The methods attached to the ``moat`` object are themselves not
asynchronous. Instead, they enqueue their internal actions, to be executed
later. This way your code does not need to be asynchronous.

* moat.start

  This decorator marks code to run when your script starts up.

    @moat.start
    async def init():
        pass

* moat.stop

  This decorator marks code to run when your script terminates.

  You should not depend on this code to actually execute.

    @moat.stop
    async def init():
        pass

* moat.ready

  This decorator marks code to run when your script has finished starting
  up. In particular, all registrations have been successful.

    @moat.start
    async def init():
        pass

* moat.end

  Call this function if your script should terminate normally, some time in
  the future.

  For abnormal termination, simply raise an appropriate exception.
  (When in doubt, subclass ``RuntimeError``.)

  ``moat.end()`` takes no parameters.

* moat.data

  Your task's ``data`` subdirectory. This is accessible with standard ``etcd-tree``
  methods. Be aware that you cannot add new values.

* moat.root

  The complete ``etcd-tree`` hierarchy.

* moat.rpc

  Register a RPC function.

  Usage:

	@moat.rpc("foo.bar.baz")
	async def baz_handler(** kw):
	    …

* moat.on_alert

  Register an event handler.
  Usage: like ``.rpc``.

* 

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
    async def obj_changed():
        …

* moat.logger

  A standard Python logger you can use to report things.

* moat.set_error

  Note the fact that your script found an error condition.

    …
    await moat.set_error("owch", "I had an owie")

  See the chapter on error handling for details.

* moat.clear_error

  Note the fact that the error condition has been fixed, or does not exist.

    …
    await moat.clear_error("owch")

  There is no way to check whether a particular error exists; instead, you
  should simply call set_error / clear_error again.


