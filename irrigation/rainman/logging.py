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

"""\
	This module holds a few random utility functions.
	"""

from rainman.models import Log, Site,Controller,Valve,EnvGroup
import sys, os, traceback

_me = None
def log(dev, text):
	v = c = s = None
	if isinstance(dev,Valve):
		v = dev
	elif isinstance(dev,Controller):
		c = dev
	elif isinstance(dev,Site):
		s = dev
	elif isinstance(dev,EnvGroup):
		s = dev.site
		text = "EnvGroup "+dev.name+": "+text
	else:
		raise RuntimeError("Cannot log: %s" % (repr(dev),))
	if v: c = v.controller
	if c: s = c.site
	print("%s: %s" % (dev,text), file=sys.stderr)

	global _me
	if _me is None:
		_me = os.path.splitext(os.path.basename(sys.argv[0]))[0]
	
	Log(site=s,controller=c,valve=v, text=text, logger=_me).save()

def log_error(dev):
	log(dev,traceback.format_exc())
