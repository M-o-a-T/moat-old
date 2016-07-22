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
This code implements the Help command.

"""

from moat.module import Module
from moat.logging import log
from moat.statement import Statement, global_words, HelpSub
from moat.base import Name,SName

def _ErrKey(x):
	raise KeyError(x)

class Help(Statement):
	name="help"
	doc="show doc texts"
	long_doc="""\
The "help" command shows which words are recognized at each level.
"help foo" also shows the sub-commands, i.e. what would be allowed
in place of the "XXX" in the following statement:

	foo:
		XXX

Statements may be multi-word and follow generic Python syntax.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		words = ctx.words

		wl = event[:]
		while wl:
			try:
				wlist = words.__getitem__
			except AttributeError:
				wlist = _ErrKey

			n = len(wl)
			while n >= 0:
				try:
					words = wlist(Name(*wl[:n]))
				except KeyError:
					try:
						words = words.registry[SName(wl[:n])]
					except (KeyError, AttributeError):
						n = n-1
						continue
				break
			if n < 0:
				break
			wl = wl[n:]

		if wl:
			# this may be for a type registry
			print("Not a command in %s:" % (words.name,)," ".join(wl), file=self.ctx.out)

		try:
			doc = ":\n"+words.long_doc.rstrip("\n")
		except AttributeError:
			doc = " : "+words.doc
		if words.name:
			print(" ".join(words.name)+doc, file=self.ctx.out)
		else:
			print(doc, file=self.ctx.out)

		# this is for common sub-statements
		try:
			wl = words.items
		except AttributeError: # it's empty
			pass
		else:
			maxlen=0
			for n,d in wl():
				hlen = len(" ".join(n))
				if hlen > maxlen: maxlen = hlen
			if maxlen:
				n = getattr(words,"helpsubname","word")
				print("Known "+n+"s:", file=self.ctx.out)

				for n,d in sorted(wl()):
					hname = " ".join(n)
					print(hname+(" "*(maxlen+1-len(hname)))+": "+d.doc, file=self.ctx.out)

		# this is for a type registry
		try:
			wl = words.registry.items
		except AttributeError:
			pass
		else:
			maxlen=0
			for n,d in wl():
				hlen = len(n)
				if hlen > maxlen: maxlen = hlen
			if maxlen:
				print("Known types:", file=self.ctx.out)

				for n,d in sorted(wl()):
					print(" ".join(n)+(" "*(maxlen+1-len(hname)))+": "+d.doc, file=self.ctx.out)

class HelpModule(Module):
	"""\
		This module implements the Help command.
		"""

	info = "implements the 'help' statement"

	def load(self):
		global_words.register_statement(Help)
	
	def unload(self):
		global_words.unregister_statement(Help)
	
init = HelpModule
