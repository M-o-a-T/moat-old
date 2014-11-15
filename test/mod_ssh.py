#!/usr/bin/python
# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2012, Matthias Urlichs <matthias@urlichs.de>
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

from homevent import patch;patch()
from homevent.reactor import ShutdownHandler
from homevent.module import load_module,Load
from homevent.statement import global_words,main_words
from test import run

global_words.register_statement(Load)


input = """\
load ssh
block:
	if exists directory "keys":
		ssh directory "keys"
	else:
		ssh directory "../keys"

# TODO: run an external test ‽
listen ssh 50922
auth ssh smurf "AAAAB3NzaC1kc3MAAACBAOvddksPhkNQIxJWTvWh6+NYR2yUBSMs2lwC4PSbmUOdjyoU9pwcF1ARJNIUxPrFBfT6bsP1W4RY/FAbS8rNsIwiaTqbqtiE8Dm9ea1ofIRBQFjsECRKjsWxBIOSOpQLhAin0CFmzZBJd4GZYVc6MV1j3uvi8pprqC5DkOMmq5wxAAAAFQD+uUSzVO526t0smxAi2eyDQMhmZQAAAIBhc6+jU7kNxv9dFaZ2QlqzhYiD4h3flWg1x4dMhkLIoZqYryOtSu+Cj2cda4ES94N/cRir3fTEKvjHA9Lpw0Ul4kdLdoebu8Kum6jspTRqTMi9CrAZ5Ub27P4jy/N/ahVUtGWQZAdxeNQEEXo8z6b+oCul5H8aFYxr1rvbtpdK8wAAAIEAx1zIfnMecvXNcxa1tVruWFXU6bN0GC1Z0scYhjaYCgZPOZwlywIDd4ui4t9DyPxh+ZyPjcyDtqjOABFU5qVR0QoyIH7DRBzBi91ovDM2Fu+k2kfng4ewhUbN6If2jgX6DBwqS6HhCmA210+P+G+K9+RarStL/43TgQvog5zDDLM="

list ssh auth
del ssh auth smurf
list ssh auth

shutdown
"""

main_words.register_statement(ShutdownHandler)
load_module("block")
load_module("path")
load_module("data")
load_module("ifelse")

run("ssh",input)

