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

# This is a heavily modified copy (no shadowing of stderr, no interactive
# use, no instantiation of subcommands before they're actually used, use a
# logger instance instead of command-local debug etc. methods) of
# https://thomas.apestaart.org/moap/trac/browser/trunk/moap/extern/command/command.py?order=name
# Downloaded on 2015-11-14
# This file is released under the standard PSF license, superseding the above boilerplate.

"""
Command class.
"""

import optparse
import sys
import logging
import asyncio
from types import CoroutineType

class CommandHelpFormatter(optparse.IndentedHelpFormatter):
	"""
	I format the description as usual, but add an overview of commands
	after it if there are any, formatted like the options.
	"""

	_commands = None
	_aliases = None
	_klass = None

	def addCommand(self, name, description):
		if self._commands is None:
			self._commands = {}
		self._commands[name] = description

	def addAlias(self, alias):
		if self._aliases is None:
			self._aliases = []
		self._aliases.append(alias)

	def setClass(self, klass):
		self._klass = klass

	### override parent method

	def format_description(self, description):
		# textwrap doesn't allow for a way to preserve double newlines
		# to separate paragraphs, so we do it here.
		ret = description

		# add aliases
		if self._aliases:
			ret += "\nAliases: " + ", ".join(self._aliases) + "\n"

		# add subcommands
		if self._commands:
			commandDesc = []
			commandDesc.append("Commands:")
			keys = sorted(k for k,v in self._commands.items() if v is not None)
			length = 0
			for key in keys:
				if len(key) > length:
					length = len(key)
			for name in keys:
				formatString = "  %-" + "%d" % length + "s  %s"
				commandDesc.append(formatString % (name, self._commands[name]))
			ret += "\n" + "\n".join(commandDesc) + "\n"

#		# add class info
#		ret += "\nImplemented by: %s.%s\n" % (
#			self._klass.__module__, self._klass.__name__)

		return ret


class CommandOptionParser(optparse.OptionParser):
	"""
	I parse options as usual, but I explicitly allow setting stdout
	so that our print_help() method (invoked by default with -h/--help)
	defaults to writing there.

	I also override exit() so that I can be used in interactive shells.

	@ivar help_printed:  whether help was printed during parsing
	@ivar usage_printed: whether usage was printed during parsing
	"""
	help_printed = False
	usage_printed = False

	_stdout = sys.stdout

	def set_stdout(self, stdout):
		self._stdout = stdout

	def parse_args(self, args=None, values=None):
		self.help_printed = False
		self.usage_printed = False
		return optparse.OptionParser.parse_args(self, args, values)
	# we're overriding the built-in file, but we need to since this is
	# the signature from the base class
	__pychecker__ = 'no-shadowbuiltin'

	def print_help(self, file=None):
		# we are overriding a parent method so we can't do anything about file
		__pychecker__ = 'no-shadowbuiltin'
		if file is None:
			file = self._stdout
		file.write(self.format_help())
		self.help_printed = True

	def print_usage(self, file=None):
		optparse.OptionParser.print_usage(self, file)
		self.usage_printed = True

	def exit(self, status=0, msg=None):
		if msg:
			sys.stderr.write(msg) # pragma: no cover ## called by the parser

		return status


class Command(object):
	"""
	I am a class that handles a command for a program.
	Commands can be nested underneath a command for further processing.

	@cvar name:		name of the command, lowercase;
					   defaults to the lowercase version of the class name
	@cvar aliases:	 list of alternative lowercase names recognized
	@type aliases:	 list of str
	@cvar usage:	   short one-line usage string;
					   %command gets expanded to a sub-command or [commands]
					   as appropriate.  Don't specify the command name itself,
					   it will be added automatically.  If not set, defaults
					   to name.
	@cvar summary:	 short one-line summary of the command
	@cvar description: longer paragraph explaining the command
	@cvar subCommands: dict of name -> commands below this command
	@type subCommands: dict of str  -> L{Command}
	@cvar parser:	  the option parser used for parsing
	@type parser:	  L{optparse.OptionParser}
	"""
	name = None
	aliases = None
	usage = None
	summary = None # hidden command # "… you forgot to set the 'summary' attribute."
	description = "… you forgot to set the 'description' attribute."
	parent = None
	subCommands = None
	subCommandClasses = None
	aliasedSubCommands = None
	parser = None

	def __init__(self, parent=None, stdout=None):
		"""
		Create a new command instance, with the given parent.
		Allows for redirecting stdout if needed.
		This redirection will be passed on to child commands.
		"""
		if not self.name:
			self.name = self.__class__.__name__.lower()

		if parent is not None:
			self.fullname = parent.fullname+'.'+self.name
		else:
			self.fullname = self.name

		self._stdout = stdout
		self.parent = parent

		self.log = logging.getLogger(self.name)

		# create subcommands if we have them
		self.subCommands = {}
		self.aliasedSubCommands = {}
		if self.subCommandClasses:
			for c in self.subCommandClasses:
				self.subCommands[c.name] = c
				if c.aliases:
					for alias in c.aliases:
						self.aliasedSubCommands[alias] = c

		# create our formatter and add subcommands if we have them
		formatter = CommandHelpFormatter()
		formatter.setClass(self.__class__)
		if self.subCommands:
			if not self.description: # pragma: no cover
				if self.summary:
					self.description = self.summary
				else:
					raise AttributeError(
						"%s needs a summary or description " \
						"for help formatting" % repr(self))

			for name, command in self.subCommands.items():
				if command.summary:
					formatter.addCommand(name, command.summary)

		if self.aliases:
			for alias in self.aliases:
				formatter.addAlias(alias)

		# expand %command for the bottom usage
		usage = self.usage or ''
		if not usage:
			# if no usage, but subcommands, then default to showing that
			if self.subCommands:
				usage = "%command"

		# the main program name shouldn't get prepended, because %prog
		# already expands to the name
		if not usage.startswith('%prog'):
			usage = self.name + ' ' + usage

		usages = [usage, ]
		if usage.find("%command") > -1:
			if self.subCommands:
				usage = usage.split("%command")[0] + '[command]'
				usages = [usage, ]
			else: 
				# %command used in a leaf command
				usages = usage.split("%command")
				usages.reverse()

		# FIXME: abstract this into getUsage that takes an optional
		# parent on where to stop recursing up
		# useful for implementing subshells

		# walk the tree up for our usage
		c = self.parent
		while c:
			usage = c.usage or c.name
			if usage.find(" %command") > -1:
				usage = usage.split(" %command")[0]
			usages.append(usage)
			c = c.parent
		usages.reverse()
		usage = " ".join(usages)

		# create our parser
		description = self.description or self.summary
		if description:
			description = description.strip()
		self.parser = CommandOptionParser(
			usage=usage, description=description,
			formatter=formatter)
		self.parser.set_stdout(self.stdout)
		self.parser.disable_interspersed_args()

		# allow subclasses to add options
		self.addOptions()

	def addOptions(self):
		"""
		Override me to add options to the parser.
		"""
		pass

	async def do(self, args): # pragma: no cover
		"""
		Override me to implement the functionality of the command asynchronously.

		@param    args: list of remaining non-option arguments
		@type     args: list of unicode
		@rtype:   int
		@returns: an exit code, or None if no actual action was taken.
		"""
		raise NotImplementedError('Implement %s.do()' % self.__class__)

	async def parse(self, argv):
		"""
		Parse the given arguments and act on them.

		@param argv: list of arguments to parse
		@type  argv: list of unicode

		@rtype:   int
		@returns: an exit code, or None if no actual action was taken.
		"""
		# note: no arguments should be passed as an empty list, not a list
		# with an empty str as ''.split(' ') returns
		self.log.debug('calling %r.parse_args(%r)' % (self, argv))
		self.options, args = self.parser.parse_args(argv)
		self.log.debug('called %r.parse_args' % self)

		# if we were asked to print help or usage, we are done
		if self.parser.usage_printed or self.parser.help_printed:
			return None

		self.log.debug('calling %r.handleOptions(%r)' % (self, self.options))
		ret = self.handleOptions()
		self.log.debug('called %r.handleOptions, returned %r' % (self, ret))

		if ret:
			return ret # pragma: no cover ## if necessary, we raise

		# if we don't have args or don't have subcommands,
		# defer to our do() method
		# allows implementing a do() for commands that also have subcommands
		if not args or not self.subCommands:
			self.log.debug('no args or no subcommands, calling %r.do(%r)' % (
				self, args))
			try:
				ret = await self.do(args)
				self.log.debug('done ok, returned %r', ret)
#			except CommandOk as e:
#				self.log.debug('done with exception, raised %r', e)
#				ret = e.status
#				self.stdout.write(e.output + '\n')
			except CommandExited as e:
				self.log.debug('done with exception, raised %r', e)
				ret = e.status
				sys.stderr.write(e.output + '\n')
			except NotImplementedError:
				self.log.debug('done with NotImplementedError')
				self.parser.print_usage(file=sys.stderr)
				sys.stderr.write("Use --help to get a list of commands.\n")
				return 1


			# if everything's fine, we return 0
			if not ret:
				ret = 0

			return ret

		# as we have a subcommand, defer to it
		command = args[0]

		C = self.subCommands.get(command,None)
		if C is None:
			C = self.aliasedSubCommands.get(command,None)
		if C is not None:
			c = C(self)
			return (await c.parse(args[1:]))

		self.log.error("Unknown command '%s'.\n", command)
		self.parser.print_usage(file=sys.stderr)
		return 1

	def handleOptions(self):
		"""
		Handle the parsed options.
		"""
		pass

	def outputUsage(self, file=None):
		"""
		Output usage information.
		Used when the options or arguments were missing or wrong.
		"""
		__pychecker__ = 'no-shadowbuiltin'
		self.log.debug('outputUsage')
		if not file:
			file = sys.stderr
		self.parser.print_usage(file=file)

	@property
	def root(self):
		"""
		Return the top-level command, which is typically the program.
		"""
		c = self
		while c.parent:
			c = c.parent
		return c

	def _getStd(self, what):

		ret = getattr(self, '_' + what, None)
		if ret:
			return ret

		# if I am the root command, default
		if not self.parent:
			return getattr(sys, what)

		# otherwise delegate to my parent
		return getattr(self.parent, what)

	@property
	def stdout(self):
		return self._getStd('stdout')

class CommandExited(Exception):

	def __init__(self, status, output):
		self.args = (status, output)
		self.status = status
		self.output = output

## unused
#class CommandOk(CommandExited):
#
#	def __init__(self, output):
#		CommandExited.__init__(self, 0, output)


class CommandError(CommandExited):

	def __init__(self, output):
		CommandExited.__init__(self, 3, output)

