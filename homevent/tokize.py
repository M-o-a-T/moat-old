# -*- coding: utf-8 -*-

##
##  Copyright © 2007, Matthias Urlichs <matthias@urlichs.de>
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

"""Tokenization help for Python-like HomEvenT programs."""

__author__ = 'Matthias Urlichs <matthias@urlichs.de>'
__credits__ = \
    'GvR, ESR, Tim Peters, Thomas Wouters, Fred Drake, Skip Montanaro, Ka-Ping Yee'

import string, re, os, sys
from token import *
import tokenize as t
from twisted.internet.defer import maybeDeferred, Deferred
from homevent.logging import log,TRACE
from homevent.event import StopParsing
from gevent.queue import Channel,Empty
import gevent

COMMENT = t.COMMENT
NL = t.NL
group = t.group
any = t.any
maybe = t.maybe
Whitespace = t.Whitespace
Comment = t.Comment
Ignore = t.Ignore
TokenError = t.TokenError
StopTokenizing = t.StopTokenizing
Intnumber = t.Intnumber
Floatnumber = t.Floatnumber
ContStr = t.ContStr
PseudoExtras = t.PseudoExtras
single3prog = t.single3prog
double3prog = t.double3prog
endprogs = t.endprogs
triple_quoted = t.triple_quoted
single_quoted = t.single_quoted

import token
__all__ = [x for x in dir(token) if x[0] != '_'] + ["COMMENT","NL",
           "generate_tokens"]
del x
del token

PlusMinus = r"[+\-]"
Name = r'\w+'
Number = maybe(PlusMinus) + group(Floatnumber, Intnumber)

# Because of leftmost-then-longest match semantics, be sure to put the
# longest operators first (e.g., if = came before ==, == would get
# recognized as two instances of =).
#Operator = group(r"\*\*=?", r">>=?", r"<<=?", r"<>", r"!=",
#                 r"//=?", r"[+\-*/%&|^=<>]=?", r"~")
Operator =  r"[+\-]"

Var = group(r"\*"+maybe(Name), r"\$"+Name)

Funny = group(Var, Operator, t.Bracket, t.Special)

PlainToken = group(Number, Funny, t.String, Name)
Token = Ignore + PlainToken

# First (or only) line of ' or " string.
PseudoToken = Whitespace + group(PseudoExtras, Number, Funny, ContStr, Name)

def _comp(exp):
	return re.compile(exp, re.UNICODE)
tokenprog, pseudoprog, namestart, num = map(
    _comp, (Token, PseudoToken, r'\w', Number))

tabsize = 8

class tokizer(object):
	def __init__(self, output, parent=None):
		self._output = output
		self.parent = parent
		self.q = Channel()
		self.job = gevent.spawn(self._job)
		self.job.link(self._end)
		self.init()
	
	def init(self):
		self.lnum = self.parenlev = self.continued = 0
		self.contstr, self.needcont = '', 0
		self.contline = None
		self.indents = [0]

	def output(self,*a):
		log("token",TRACE,repr(a))
		self._output(*a)
		
	def feed_end(self):
		for indent in self.indents[1:]:                 # pop remaining indent levels
			self.output(DEDENT, '', (self.lnum, 0), (self.lnum, 0), '')

	def feed(self,line):
		if self.q:
			if line is None:
				q,self.q = self.q,None
				if gevent.getcurrent() is not self.job:
					q.put(None)
			else:
				self.q.put(line)
		elif line is not None:
			raise RuntimeError("reader died: "+repr(line))

	def _end(self, res):
		if self.q:
			q,self.q = self.q,None
			try:
				q.get_nowait()
			except Empty:
				pass

	def _job(self):
		line = "x"
		while line:
			if self.q:
				line = self.q.get()
			else:
				line = None
			self._do_line(line)

	def _do_line(self,line):
		try:
			try:
				if line is None:
					raise StopIteration
				log("token",TRACE,"IN",line)
			except StopIteration:
				line = ''
				log("token",TRACE,"IN_END")
			self.lnum = self.lnum + 1
			pos, max = 0, len(line)

			if self.contstr:                            # continued string
				if not line:
					raise TokenError, ("EOF in multi-line string", strstart)
				endmatch = endprog.match(line)
				if endmatch:
					pos = end = endmatch.end(0)
					self.output(STRING, self.contstr + line[:end],
							strstart, (self.lnum, end), self.contline + line)
					self.contstr, self.needcont = '', 0
					self.contline = None
				elif self.needcont and line[-2:] != '\\\n' and line[-3:] != '\\\r\n':
					self.output(ERRORTOKEN, self.contstr + line,
							strstart, (self.lnum, len(line)), self.contline)
					self.contstr = ''
					self.contline = None
					return
				else:
					self.contstr += line
					self.contline += line
					return

			elif self.parenlev == 0 and not self.continued:  # new statement
				if not line:
					self.feed_end()
					self.output(ENDMARKER, '', (self.lnum, 0), (self.lnum, 0), '')
					return
				column = 0
				while pos < max:                   # measure leading whitespace
					if line[pos] == ' ': column = column + 1
					elif line[pos] == '\t': column = (column/tabsize + 1)*tabsize
					elif line[pos] == '\f': column = 0
					else: break
					pos = pos + 1
				if pos == max:
					self.feed_end()
					return

				if line[pos] in '#\r\n':           # skip comments or blank lines
					self.output((NL, COMMENT)[line[pos] == '#'], line[pos:],
							(self.lnum, pos), (self.lnum, len(line)), line)
					return

				if column > self.indents[-1]:           # count indents or dedents
					self.indents.append(column)
					self.output(INDENT, line[:pos], (self.lnum, 0), (self.lnum, pos), line)
				if column < self.indents[-1]:
					while column < self.indents[-1]:
						self.indents.pop()
						self.output(DEDENT, '', (self.lnum, pos), (self.lnum, pos), line)

					if column != self.indents[-1]:
						raise IndentationError(
							"unindent does not match any outer indentation level",
							("<tokenize>", self.lnum, pos, line))

			else:                                  # continued statement
				if not line:
					raise TokenError, ("EOF in multi-line statement", (self.lnum, 0))
				self.continued = 0

			while pos < max:
				pseudomatch = pseudoprog.match(line, pos)
				if pseudomatch:                                # scan for tokens
					start, end = pseudomatch.span(1)
					spos, epos, pos = (self.lnum, start), (self.lnum, end), end
					token, initial = line[start:end], line[start]

					if num.match(token) or \
					(initial == '.' and token != '.'):      # ordinary number
						self.output(NUMBER, token, spos, epos, line)
					elif initial in '\r\n':
						self.output(NL if self.parenlev > 0 else NEWLINE, token, spos, epos, line)
					elif initial == '#':
						self.output(COMMENT, token, spos, epos, line)
					elif token in triple_quoted:
						endprog = endprogs[token]
						endmatch = endprog.match(line, pos)
						if endmatch:                           # all on one line
							pos = endmatch.end(0)
							token = line[start:pos]
							self.output(STRING, token, spos, (self.lnum, pos), line)
						else:
							strstart = (self.lnum, start)           # multiple lines
							self.contstr = line[start:]
							self.contline = line
							break
					elif initial in single_quoted or \
						token[:2] in single_quoted or \
						token[:3] in single_quoted:
						if token[-1] == '\n':                  # continued string
							strstart = (self.lnum, start)
							endprog = (endprogs[initial] or endprogs[token[1]] or
									endprogs[token[2]])
							self.contstr, self.needcont = line[start:], 1
							self.contline = line
							break
						else:                                  # ordinary string
							self.output(STRING, token, spos, epos, line)
					elif namestart.match(initial):                 # ordinary name
						self.output(NAME, token, spos, epos, line)
					elif initial == '\\':                      # continued stmt
						self.continued = 1
					else:
						if initial in '([{': self.parenlev = self.parenlev + 1
						elif initial in ')]}': self.parenlev = self.parenlev - 1
						self.output(OP, token, spos, epos, line)
				else:
					self.output(ERRORTOKEN, line[pos],
							(self.lnum, pos), (self.lnum, pos+1), line)
					pos = pos + 1

		except StopParsing as e:
			self.q = None
			if self.parent:
				self.parent.kill(e)
			return

