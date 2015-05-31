#!/bin/sh

test -f onewire2_in && cd ..

if ! test -f onewire_params ; then
	cat >&2 <<END
You need to create a file named "onewire_params" which contains four
lines:
* the ID of some device on the 1wire bus
  (find one with "owdir"; a thermometer is good, it's named "10.SOMETHING")
  (do not give the path to the device, the test will find it on its own!)
* some parameter to read ("temperature")
* hostname where a owserver daemon is running; default localhost
* port on which the owserver listens (default, 4304)

Forget about all of this if you do not have a 1wire bus.
END
	exit 1
fi

(
	read dev
	read attr
	read attr2
	read val
	read host
	read port

	if test -z "$dev" ; then
		echo "You didn't set a device!"
		exit 2
	fi
	test -n "$attr" || attr=temperature
	test -n "$host" || host=localhost
	test -n "$port" || port=4304

	echo Testing 1wire on $host:$port for $dev/$attr
	sed -e "s/_HOST_/$host/g" -e "s/_PORT_/$port/g" \
	    -e "s/_DEV_/$dev/g"   -e "s/_ATTR_/$attr/g" < test/interactive/onewire_in >test/interactive/onewire
) < onewire_params

export PYTHONPATH=$(pwd)
export MOAT_TEST=1

python test/interactive/main.py test/interactive/onewire
