# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2015 by Matthias Urlichs <matthias@urlichs.de>,
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

from moat.logging import log, TRACE,ERROR

def running(event):
    log(TRACE,"PY Event called",event)

def not_running(event):
    log(ERROR,"PY bad event called",event)
    
def called(env,*a,**k):
    log(TRACE,"PY Proc called",env,a,k)
    env.on("test","me", doc="Test me harder",name="foo test bar")(running)
    env.on("test","me","not", doc="dummy")(not_running)
    env.trigger("test","it", what="ever")
    env.do("log DEBUG 'do' works")
    env.do.log('DEBUG', "'do.log' works")
    log(TRACE,"PY Proc done")
