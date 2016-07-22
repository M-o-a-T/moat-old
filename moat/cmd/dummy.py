# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2016 by Matthias Urlichs <matthias@urlichs.de>,
##  it is licensed under the GPLv3. See the file `README.rst` for details,
##  including optimistic statements by the author.
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
##  This header is auto-generated and may self-destruct at any time,
##  courtesy of "make update". The original is in ‘scripts/_boilerplate.py’.
##  Thus, do not remove the next line, or insert any blank lines above.
##BP

"""List of known Tasks"""

import os
from moat.script import Command as _Command

class Command(_Command):
	name = "dummy"
	usage = "[no options]"
	summary = "A command that does not do anything"
	description = """\
This command does not do anything. It is used for testing.
"""

	foo = (
		"I told you that this does not do anything.",
		"Please listen to me next time.",
		"Stop adding verbosity!",
		"The error is intentional.",
	)
	async def do(self,args):
		n = 0
		if args:
			if args[0] == "nope":
				raise NotImplementedError("nope")
			self.outputUsage()
			return 1
		while n < self.root.verbose:
			print(self.foo[n], file=self.stdout)
			n += 1
		return self.root.verbose # test exit values
