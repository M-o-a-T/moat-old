# -*- coding: utf-8 -*-
from __future__ import division

##
##  Copyright © 2008, Matthias Urlichs <matthias@urlichs.de>
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

"""\
	This module holds the ssh-related Twisted support stuff.
	"""

# self.client.transport can be None
from twisted.conch.ssh.session import SSHSessionProcessProtocol
from twisted.conch.ssh import session,channel
def tlc(self):
	if self.client and self.client.transport:
		self.client.transport.loseConnection()
	channel.SSHChannel.loseConnection(self)
session.SSHSession.loseConnection = tlc

_ssw = SSHSessionProcessProtocol.write
def sws(self,data):
	if isinstance(data,unicode):
		data = data.encode("utf-8")
	return _ssw(self,data)
SSHSessionProcessProtocol.write = sws

