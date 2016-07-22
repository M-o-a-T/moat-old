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
import asyncio
from types import CoroutineType

from moat.types import MODULE_DIR

import logging
logger = logging.getLogger(__name__)

class CommandHelpFormatter(optparse.IndentedHelpFormatter):
	"""
	I format the description as usual, but add an overview of commands
	after it if there are any, formatted like the options.
	"""

	def __init__(self,parent):
		super().__init__()
		self._parent = parent

	### override parent method

	def format_description(self, description):
		# textwrap doesn't allow for a way to preserve double newlines
		# to separate paragraphs, so we do it here.
		ret = description.strip()+'\n'

		# add subcommands
		if self._parent._commands:
			commandDesc = []
			commandDesc.append("Commands:")
			length = 0
			for name,desc in self._parent._commands:
				if len(name) > length:
					length = len(name)
			for name,desc in sorted(self._parent._commands):
				formatString = "  %-" + str(length) + "s  %s"
				commandDesc.append(formatString % (name, desc))
			ret += "\n" + "\n".join(commandDesc) + "\n"

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
	logged = False

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

		# create our parser
		description = self.description or self.summary
		usage = self.usage or ''
		formatter = CommandHelpFormatter(self)

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
		raise CommandError("Not implemented. Use '--help' to show sub-commands.")

	async def finish(self):
		"""
		Override me to clean up after myself.

		This usually involves freeing async resources.
		"""
		pass

	async def parse(self, argv):
		"""
		Parse the given arguments and act on them.

		@param argv: list of arguments to parse
		@type  argv: list of unicode

		@rtype:   int
		@returns: an exit code, or None if no actual action was taken.
		"""
		# cache, in case the ars parser needs to emit help
		self._commands = await self.list_commands()

		# note: no arguments should be passed as an empty list, not a list
		# with an empty str as ''.split(' ') returns
		self.options, args = self.parser.parse_args(argv)

		# if we were asked to print help or usage, we are done
		if self.parser.usage_printed or self.parser.help_printed:
			return None

		ret = self.handleOptions()

		if ret:
			return ret # pragma: no cover ## if necessary, we raise

		self._parse_hook()

		# if we don't have args or don't have subcommands,
		# defer to our do() method
		# allows implementing a do() for commands that also have subcommands

		self.log.debug('calling %r.do(%r)', self, args)
		try:
			ret = await self.do(args)
			self.log.debug('done ok, returned %r', ret)
#			except CommandOk as e:
#				self.log.exception('done with exception, raised %r', e)
#				ret = e.status
#				self.stdout.write(e.output + '\n')
		except CommandExited as e:
			ret = e.status
			logger.error(e.output)
		except NotImplementedError:
			self.parser.print_usage(file=sys.stderr)
			print("Use --help to get a list of commands.", file=sys.stderr)
			return 1

		# if everything's fine, we return 0
		if not ret:
			ret = 0

		return ret

	def _parse_hook(self):
		"""Overridden in test"""
		pass

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

	async def list_commands(self):
		"""dummy"""
		return ()

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

class SubCommand(Command):
	"""
	I am a class that dispatches to a nested command.
	"""

	async def do(self, args):
		"""
		Dispatch to sub-command.
		"""
		
		if not args:
			self.parser.print_help(file=sys.stderr)
			return 8

		c = None
		try:
			try:
				c = await self.resolve_command(args[0])
			except KeyError as e:
				raise CommandError("Unknown command: '%s'" % args[0]) from e
			c = c(parent=self)

			r = await c.parse(args[1:])
			if not self.root.logged:
				if r:
					logger.info("Error:%s:%s",r, " ".join(args))
				else:
					logger.debug("Done:%s", " ".join(args))
				self.root.logged = True
			return r
		except CommandExited as e:
			raise
		except Exception:
			if not self.root.logged:
				logger.exception("Error:%s", " ".join(args))
				self.root.logged = True
			raise
		finally:
			if c is not None:
				await c.finish()

	async def resolve_command(self, name):
		"""Return the command object corresponding to this name"""
		raise NotImplementedError("You need to override %s.resolve_command" % type(self))

	async def list_commands(self):
		"""Return a list of command,descr tuples"""
		raise NotImplementedError("You need to override %s.list_commands" % type(self))

class ModuleCommand(SubCommand):
	kind = None # module: cmd_KIND

	async def resolve_command(self, name):
		tree = await self.root._get_tree()
		t = await tree.lookup(MODULE_DIR)[name]['cmd_'+self.kind]
		return t.code

	async def list_commands(self):
		tree = await self.root._get_tree()
		t = await tree.lookup(*MODULE_DIR)
		t = await t.names_for('cmd_'+self.kind)
		res = []
		for cmd in t:
			res.append((cmd.name, cmd['descr']))

		return res

class SubCommand(SubCommand):
	subCommandClasses = None

	def __init__(self, *a,**k):
		super().__init__(*a,**k)

		self.subCommands = {}
		for c in self.subCommandClasses:
			self.subCommands[c.name] = c

	async def resolve_command(self, name):
		return self.subCommands[name]

	async def list_commands(self):
		res = []
		for name,cmd in sorted(self.subCommands.items()):
			res.append((name,cmd.summary))
		return res

