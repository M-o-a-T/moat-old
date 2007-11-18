# -*- coding: utf-8 -*-
"""\
This code implements a SSH command line for homevent.

"""

from twisted.cred import credentials
from twisted.conch import error,avatar,recvline
from twisted.conch.ssh import keys, factory, common, session
from twisted.cred import checkers, portal
from twisted.python import failure
from zope.interface import implements
from twisted.conch import interfaces as conchinterfaces
from twisted.conch.insults import insults
from twisted.internet import reactor
from twisted.internet.threads import deferToThread
import base64,os
import sys
from homevent.module import Module
from homevent.logging import log
from homevent.context import Context
from homevent.parser import parser_builder,parse
from homevent.statement import main_words,Statement
from homevent.interpreter import InteractiveInterpreter,Interpreter
from cStringIO import StringIO


class SSHprotocol(recvline.HistoricRecvLine):
	def __init__(self, user):
		self.user = user
		super(SSHprotocol,self).__init__()
	def connectionMade(self):
		super(SSHprotocol,self).connectionMade()
		if not hasattr(self,"transport"):
			self.transport = self.terminal
		self.terminal.write("This is the HomEvenT command line.")
		self.terminal.nextLine()

class SSHavatar(avatar.ConchUser):
	implements(conchinterfaces.ISession)
	def __init__(self, username):
		avatar.ConchUser.__init__(self)
		self.username = username
		self.channelLookup.update({'session':session.SSHSession})
	def openShell(self, protocol):
		serverProtocol = insults.ServerProtocol(parser_builder(SSHprotocol, None), self)
		serverProtocol.makeConnection(protocol)
		protocol.makeConnection(session.wrapProtocol(serverProtocol))
		self.protocol = protocol # for self.eofReceived()
	def getPty(self, terminal, windowSize, attrs):
		return None
	def execCommand(self, protocol, cmd):
		input = StringIO(cmd)
		d = parse(input, Interpreter(Context(out=protocol)),Context())
		d.addErrback(lambda _: _.printTraceback(file=protocol))
		def shut(_):
			protocol.loseConnection()
		d.addBoth(shut)

	def eofReceived(self):
		self.protocol.loseConnection()
	def closed(self):
		pass
	def windowChanged(self,size):
		pass

class SSHrealm:
	implements(portal.IRealm)
	def requestAvatar(self, avatarId, mind, *interfaces):
		if conchinterfaces.IConchUser in interfaces:
			return interfaces[0], SSHavatar(avatarId), lambda: None
		else:
			raise Exception, "No supported interfaces found."

class PublicKeyCredentialsChecker:
	implements(checkers.ICredentialsChecker)
	credentialInterfaces = (credentials.ISSHPrivateKey,)
	def __init__(self, authorizedKeys):
		self.authorizedKeys = authorizedKeys
	def requestAvatarId(self, credentials):
		if self.authorizedKeys.has_key(credentials.username):
			userKey = self.authorizedKeys[credentials.username]
			if not credentials.blob == base64.decodestring(userKey):
				raise failure.failure(error.ConchError("I don't recognize that key"))
			if not credentials.signature:
				return failure.Failure(error.ValidPublicKey( ))
			pubKey = keys.getPublicKeyObject(data=credentials.blob)
			if keys.verifySignature(pubKey, credentials.signature, credentials.sigData):
				return credentials.username
			else:
				return failure.Failure(error.ConchError("Incorrect signature"))
		else:
			return failure.Failure(error.ConchError("No such user"))


NotYet = object()
sshFactory = NotYet
authorizedKeys = {}

class SSHdir(Statement):
	name = ("ssh","directory")
	doc = "set the directory where the SSH module stores its files"
	long_doc="""\
Usage: ssh directory "/some/path"
This command sets the directory where SSH stores its keys.
You need to call this exactly once.
"""
	def run(self,ctx,**k):
		global sshFactory
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError(u'Usage: ssh path "‹directory›"')
		path = event[0]
		if not os.path.isdir(path):
			raise RuntimeError("This is not a directory")
		if sshFactory is not NotYet:
			raise RuntimeError("You can set the SSH path only once!")
		sshFactory = None
		d = deferToThread(self._run,ctx,path)
		def ex(_):
			sshFactory = NotYet
			return _
		d.addErrback(ex)
		return d


	def _run(self,ctx,path):
		global sshFactory
		event = self.params(ctx)
		pub_path = os.path.join(path,"host.pub.key")
		priv_path = os.path.join(path,"host.priv.key")

		f = factory.SSHFactory()
		f.portal = portal.Portal(SSHrealm())
		f.portal.registerChecker(PublicKeyCredentialsChecker(authorizedKeys))

		if not (os.path.exists(pub_path) and os.path.exists(priv_path)):
			# generate a RSA keypair
			from Crypto.PublicKey import RSA
			KEY_LENGTH = 1024
			rsaKey = RSA.generate(KEY_LENGTH, common.entropy.get_bytes)
			publicKeyString = keys.makePublicKeyString(rsaKey)
			privateKeyString = keys.makePrivateKeyString(rsaKey)
			# save keys for next time
			file(pub_path, 'w+b').write(publicKeyString)
			mask = os.umask(077)
			try:
				file(priv_path, 'w+b').write(privateKeyString)
			finally:
				os.umask(mask)
		publicKeyString = file(pub_path).read()
		privateKeyString = file(priv_path).read()

		f.publicKeys = {'ssh-rsa': keys.getPublicKeyString(data=publicKeyString)}
		f.privateKeys = {'ssh-rsa': keys.getPrivateKeyObject(data=privateKeyString)}
		sshFactory = f



class SSHlisten(Statement):
	name = ("listen","ssh")
	doc = "listen on a specific port for SSH terminal connections"
	long_doc="""\
This statement causes the HomEvenT process to listen for SSH connections
on a specific port. (There is no default port.)
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError(u'Usage: listen ssh ‹port›')
		if sshFactory is NotYet:
			raise RuntimeError('ssh path has not been set yet')
		if sshFactory is None:
			raise RuntimeError('ssh keys are not ready yet')

		self.parent.displayname = tuple(event)
		reactor.listenTCP(int(event[0]), sshFactory)


class SSHauth(Statement):
	name = ("auth","ssh")
	doc = "authorize a user to connect"
	long_doc=u"""\
Usage: auth ssh ‹username› "‹ssh pubkey›"
This command allows the named used to connect with their SSH key.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 2:
			raise SyntaxError(u'Usage: auth ssh ‹username› "‹ssh pubkey›"')
		pubkey=event[1]
		if " " in pubkey:
			raise SyntaxError(u'The ‹ssh pubkey› does not contain spaces.')
		authorizedKeys[event[0]] = pubkey


class SSHlistauth(Statement):
	name = ("list","auth","ssh")
	doc = "show the list of authorized users"
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event):
			raise SyntaxError('Usage: list auth ssh')
		for u in authorizedKeys.iterkeys():
			print >>ctx.out,u
		print >>ctx.out,"."


class SSHnoauth(Statement):
	name = ("del","auth","ssh")
	doc = "forbid authorize a user to connect"
	long_doc=u"""\
Usage: del auth ssh ‹username›
This command blocks the named user from accessing the server.
Existing connections are not affected.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError(u'Usage: del auth ssh ‹username›')
		del authorizedKeys[event[0]]


class SSHmodule(Module):
	"""\
		This module implements SSH access to the HomEvenT process.
		"""

	info = "SSH access"

	def load(self):
		main_words.register_statement(SSHlisten)
		main_words.register_statement(SSHlistauth)
		main_words.register_statement(SSHauth)
		main_words.register_statement(SSHnoauth)
		main_words.register_statement(SSHdir)
	
	def unload(self):
		main_words.unregister_statement(SSHlisten)
		main_words.unregister_statement(SSHlistauth)
		main_words.unregister_statement(SSHauth)
		main_words.unregister_statement(SSHnoauth)
		main_words.unregister_statement(SSHdir)
	
init = SSHmodule

