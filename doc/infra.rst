=========================
Describing Infrastructure
=========================

The best IoT system doesn't help when the network connection between the
display and the actual system is down. Many homes have "interesting"
network infrastructure, so finding a problem is somwhat nontrivial.

MoaT has a display subsystem which helps with that. The basic idea is
to save a machine-readable documentation of your network infrastructure in
etcd. Your display console runs a local checker which traces the connection
to your critical infrastructure. It then shows you where the problem seems
to be.

The display is web-based. The web server is local, as it cannot rely on any
external service being reachable.

On the etcd side, the infrastructure description looks like this:

	moat
		infra
			:static
				rsync: RSYNCDIR
				data: some default key/value pairs for the templating
			HOSTNAME:
				ports:
					NAME:
						dest: HOSTNAME
						index: 12 -- interface, for SNMP
				page: path/in/static
				data: some key/value pairs for the templating system
				prio: 123 -- lower is more important
				essential: true -- possibly
				snmp:
					read: test123
				services:
					http:
						port: 80 -- or whatever is required to check this
						page: path/in/static -- describe this service
						essential: true
						prio: 1 -- lower is more important

A display system does this, when it starts up:

* read this structure (plus keeps it cached locally, plus subscribe to updates)

* periodically rsync new versions from RSYNCDIR

* cache current IP addresses for host names

* build a connectivity structure (with itself at the root)

* find paths from itself to each host marked as essential

* ping everything on that path, periodically

* if everything checks out, no problem

* otherwise, find the path(s) from itself to the lowest-priority
  essential host or service thing that's unreachable, and display
  its information page

* That page hopefully contains sufficient instructions to get the affected
  device back up (power cycle, reset fuse, replace power supply, install
  and configure a replacement device (where is the configuration backup /
  device dump?)).

This means that a local terminal running Firefox in kiosk mode will do the
right thing: you get your MoaT web page if sufficiently many things work
for you to get there, and a useful error page otherwise.

