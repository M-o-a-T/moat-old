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

import string, re, os
from token import *
import tokenize as t
from twisted.internet.defer import inlineCallbacks, returnValue, maybeDeferred
from homevent.logging import log,TRACE

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


Name = r'\w+'
Number = group(Floatnumber, Intnumber)

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
tokenprog, pseudoprog, namestart, numstart = map(
    _comp, (Token, PseudoToken, r'\w', r'\d'))

tabsize = 8

class tokizer(object):
	def __init__(self, input,output):
		self.input = input
		self._output = output
		self.init()
	
	def init(self):
		self.lnum = self.parenlev = self.continued = 0
		self.contstr, self.needcont = '', 0
		self.contline = None
		self.indents = [0]

	def output(self,*a,**k):
		log("token",TRACE,repr(a))
		r = maybeDeferred(self._output,*a,**k)
		def orep(_):
			log("token",TRACE,"TOKEN::",_)
			return _
		def orepf(_):
			if _.check(StopIteration):
				log("token",TRACE,"TOKEN:: STOP_INPUT")
			else:
				log("token",TRACE,"TOKEN::",_)
			return _
		r.addCallbacks(orep,orepf)
		return r
		
	@inlineCallbacks
	def run(self):
		while True:                                # loop over lines in stream

			try:
				line = (yield self.input())+"\n"
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
					yield self.output(STRING, self.contstr + line[:end],
							strstart, (self.lnum, end), self.contline + line)
					self.contstr, self.needcont = '', 0
					self.contline = None
				elif self.needcont and line[-2:] != '\\\n' and line[-3:] != '\\\r\n':
					yield self.output(ERRORTOKEN, self.contstr + line,
							strstart, (self.lnum, len(line)), self.contline)
					self.contstr = ''
					self.contline = None
					continue
				else:
					self.contstr += line
					self.contline += line
					continue

			elif self.parenlev == 0 and not self.continued:  # new statement
				if not line: break
				column = 0
				while pos < max:                   # measure leading whitespace
					if line[pos] == ' ': column = column + 1
					elif line[pos] == '\t': column = (column/tabsize + 1)*tabsize
					elif line[pos] == '\f': column = 0
					else: break
					pos = pos + 1
				if pos == max: break

				if line[pos] in '#\r\n':           # skip comments or blank lines
					yield self.output((NL, COMMENT)[line[pos] == '#'], line[pos:],
							(self.lnum, pos), (self.lnum, len(line)), line)
					continue

				if column > self.indents[-1]:           # count indents or dedents
					self.indents.append(column)
					yield self.output(INDENT, line[:pos], (self.lnum, 0), (self.lnum, pos), line)
				while column < self.indents[-1]:
					if column not in self.indents:
						raise IndentationError(
							"unindent does not match any outer indentation level",
							("<tokenize>", self.lnum, pos, line))
					self.indents = self.indents[:-1]
					yield self.output(DEDENT, '', (self.lnum, pos), (self.lnum, pos), line)

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

					if numstart.match(initial) or \
					(initial == '.' and token != '.'):      # ordinary number
						yield self.output(NUMBER, token, spos, epos, line)
					elif initial in '\r\n':
						yield self.output(self.parenlev > 0 and NL or NEWLINE,
								token, spos, epos, line)
					elif initial == '#':
						yield self.output(COMMENT, token, spos, epos, line)
					elif token in triple_quoted:
						endprog = endprogs[token]
						endmatch = endprog.match(line, pos)
						if endmatch:                           # all on one line
							pos = endmatch.end(0)
							token = line[start:pos]
							yield self.output(STRING, token, spos, (self.lnum, pos), line)
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
							yield self.output(STRING, token, spos, epos, line)
					elif namestart.match(initial):                 # ordinary name
						yield self.output(NAME, token, spos, epos, line)
					elif initial == '\\':                      # continued stmt
						self.continued = 1
					else:
						if initial in '([{': self.parenlev = self.parenlev + 1
						elif initial in ')]}': self.parenlev = self.parenlev - 1
						yield self.output(OP, token, spos, epos, line)
				else:
					yield self.output(ERRORTOKEN, line[pos],
							(self.lnum, pos), (self.lnum, pos+1), line)
					pos = pos + 1

		for indent in self.indents[1:]:                 # pop remaining indent levels
			yield self.output(DEDENT, '', (self.lnum, 0), (self.lnum, 0), '')
		yield self.output(ENDMARKER, '', (self.lnum, 0), (self.lnum, 0), '')

