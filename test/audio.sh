#!/bin/sh

##
##  Copyright © 2007-2008, Matthias Urlichs <matthias@urlichs.de>
##
##  This program is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License (included; see the file LICENSE)
##  for more details.
##

set -e 

if test -d audio ; then cd audio
elif test -d ../audio ; then cd ../audio
else echo "No audio subdir"; exit 1; fi

make

./writer rate 32000 fs20 exec cat < ../test/expect/fs20rw | ./reader rate 32000 fs20 exec cat > ../test/real/fs20rw
