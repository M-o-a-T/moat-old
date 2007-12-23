# -*- coding: utf-8 -*-

##
##  Copyright (C) 2007  Matthias Urlichs <matthias@urlichs.de>
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

def tokenlogwrap(tx):
	def txw(inp,outp):
		def iw():
			r = maybeDeferred(inp)
			def irep(_):
				log("token",TRACE,"IN",_)
				return _
			r.addBoth(irep)
			return r
		def ow(*a,**k):
			log("token",TRACE,repr(a))
			r = maybeDeferred(outp,*a,**k)
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
		res = tx(iw,ow)
		def rep(_):
			log("token",TRACE,"TOKEN END::",_)
			return _
		res.addBoth(rep)
		return res
	return txw
	
@tokenlogwrap
@inlineCallbacks
def tokizer(input,output):
    """see tokenize.generate_tokens."""

    lnum = parenlev = continued = 0
    contstr, needcont = '', 0
    contline = None
    indents = [0]

    while 1:                                   # loop over lines in stream
        try:
            line = (yield input())+"\n"
        except StopIteration:
            line = ''
        lnum = lnum + 1
        pos, max = 0, len(line)

        if contstr:                            # continued string
            if not line:
                raise TokenError, ("EOF in multi-line string", strstart)
            endmatch = endprog.match(line)
            if endmatch:
                pos = end = endmatch.end(0)
                yield output(STRING, contstr + line[:end],
                           strstart, (lnum, end), contline + line)
                contstr, needcont = '', 0
                contline = None
            elif needcont and line[-2:] != '\\\n' and line[-3:] != '\\\r\n':
                yield output(ERRORTOKEN, contstr + line,
                           strstart, (lnum, len(line)), contline)
                contstr = ''
                contline = None
                continue
            else:
                contstr = contstr + line
                contline = contline + line
                continue

        elif parenlev == 0 and not continued:  # new statement
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
                yield output((NL, COMMENT)[line[pos] == '#'], line[pos:],
                           (lnum, pos), (lnum, len(line)), line)
                continue

            if column > indents[-1]:           # count indents or dedents
                indents.append(column)
                yield output(INDENT, line[:pos], (lnum, 0), (lnum, pos), line)
            while column < indents[-1]:
                if column not in indents:
                    raise IndentationError(
                        "unindent does not match any outer indentation level",
                        ("<tokenize>", lnum, pos, line))
                indents = indents[:-1]
                yield output(DEDENT, '', (lnum, pos), (lnum, pos), line)

        else:                                  # continued statement
            if not line:
                raise TokenError, ("EOF in multi-line statement", (lnum, 0))
            continued = 0

        while pos < max:
            pseudomatch = pseudoprog.match(line, pos)
            if pseudomatch:                                # scan for tokens
                start, end = pseudomatch.span(1)
                spos, epos, pos = (lnum, start), (lnum, end), end
                token, initial = line[start:end], line[start]

                if numstart.match(initial) or \
                   (initial == '.' and token != '.'):      # ordinary number
                    yield output(NUMBER, token, spos, epos, line)
                elif initial in '\r\n':
                    yield output(parenlev > 0 and NL or NEWLINE,
                               token, spos, epos, line)
                elif initial == '#':
                    yield output(COMMENT, token, spos, epos, line)
                elif token in triple_quoted:
                    endprog = endprogs[token]
                    endmatch = endprog.match(line, pos)
                    if endmatch:                           # all on one line
                        pos = endmatch.end(0)
                        token = line[start:pos]
                        yield output(STRING, token, spos, (lnum, pos), line)
                    else:
                        strstart = (lnum, start)           # multiple lines
                        contstr = line[start:]
                        contline = line
                        break
                elif initial in single_quoted or \
                    token[:2] in single_quoted or \
                    token[:3] in single_quoted:
                    if token[-1] == '\n':                  # continued string
                        strstart = (lnum, start)
                        endprog = (endprogs[initial] or endprogs[token[1]] or
                                   endprogs[token[2]])
                        contstr, needcont = line[start:], 1
                        contline = line
                        break
                    else:                                  # ordinary string
                        yield output(STRING, token, spos, epos, line)
                elif namestart.match(initial):                 # ordinary name
                    yield output(NAME, token, spos, epos, line)
                elif initial == '\\':                      # continued stmt
                    continued = 1
                else:
                    if initial in '([{': parenlev = parenlev + 1
                    elif initial in ')]}': parenlev = parenlev - 1
                    yield output(OP, token, spos, epos, line)
            else:
                yield output(ERRORTOKEN, line[pos],
                           (lnum, pos), (lnum, pos+1), line)
                pos = pos + 1

    for indent in indents[1:]:                 # pop remaining indent levels
        yield output(DEDENT, '', (lnum, 0), (lnum, 0), '')
    yield output(ENDMARKER, '', (lnum, 0), (lnum, 0), '')

