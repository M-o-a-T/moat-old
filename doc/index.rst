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

See `doc/etc.rst`.

