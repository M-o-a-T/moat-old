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
import base64,os
import sys
from homevent.module import Module
from homevent.logging import log
from homevent.parser import parser_builder
from homevent.statement import main_words,Statement
from homevent.interpreter import InteractiveInterpreter

class SSHDemoProtocol(recvline.HistoricRecvLine):
	def __init__(self, user):
		self.user = user
		super(SSHDemoProtocol,self).__init__()
	def connectionMade(self):
		super(SSHDemoProtocol,self).connectionMade()
		if not hasattr(self,"transport"):
			self.transport = self.terminal
		self.terminal.write("This is the HomEvenT command line.")
		self.terminal.nextLine()

class SSHDemoAvatar(avatar.ConchUser):
	implements(conchinterfaces.ISession)
	def __init__(self, username):
		avatar.ConchUser.__init__(self)
		self.username = username
		self.channelLookup.update({'session':session.SSHSession})
	def openShell(self, protocol):
		serverProtocol = insults.ServerProtocol(parser_builder(SSHDemoProtocol, None), self)
		serverProtocol.makeConnection(protocol)
		protocol.makeConnection(session.wrapProtocol(serverProtocol))
	def getPty(self, terminal, windowSize, attrs):
		return None
	def execCommand(self, protocol, cmd):
		raise NotImplementedError
	def closed(self):
		pass

class SSHDemoRealm:
	implements(portal.IRealm)
	def requestAvatar(self, avatarId, mind, *interfaces):
		if conchinterfaces.IConchUser in interfaces:
			return interfaces[0], SSHDemoAvatar(avatarId), lambda: None
		else:
			raise Exception, "No supported interfaces found."
def getRSAKeys():
	if not (os.path.exists('public.key') and os.path.exists('private.key')):
		# generate a RSA keypair
		print "Generating RSA keypair..."
		from Crypto.PublicKey import RSA
		KEY_LENGTH = 1024
		rsaKey = RSA.generate(KEY_LENGTH, common.entropy.get_bytes)
		publicKeyString = keys.makePublicKeyString(rsaKey)
		privateKeyString = keys.makePrivateKeyString(rsaKey)
		# save keys for next time
		file('public.key', 'w+b').write(publicKeyString)
		file('private.key', 'w+b').write(privateKeyString)
		print "done."
	else:
		publicKeyString = file('public.key').read()
		privateKeyString = file('private.key').read()
	return publicKeyString, privateKeyString

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

sshFactory = factory.SSHFactory()
sshFactory.portal = portal.Portal(SSHDemoRealm())
authorizedKeys = {
		"smurf": "AAAAB3NzaC1kc3MAAACBAOvddksPhkNQIxJWTvWh6+NYR2yUBSMs2lwC4PSbmUOdjyoU9pwcF1ARJNIUxPrFBfT6bsP1W4RY/FAbS8rNsIwiaTqbqtiE8Dm9ea1ofIRBQFjsECRKjsWxBIOSOpQLhAin0CFmzZBJd4GZYVc6MV1j3uvi8pprqC5DkOMmq5wxAAAAFQD+uUSzVO526t0smxAi2eyDQMhmZQAAAIBhc6+jU7kNxv9dFaZ2QlqzhYiD4h3flWg1x4dMhkLIoZqYryOtSu+Cj2cda4ES94N/cRir3fTEKvjHA9Lpw0Ul4kdLdoebu8Kum6jspTRqTMi9CrAZ5Ub27P4jy/N/ahVUtGWQZAdxeNQEEXo8z6b+oCul5H8aFYxr1rvbtpdK8wAAAIEAx1zIfnMecvXNcxa1tVruWFXU6bN0GC1Z0scYhjaYCgZPOZwlywIDd4ui4t9DyPxh+ZyPjcyDtqjOABFU5qVR0QoyIH7DRBzBi91ovDM2Fu+k2kfng4ewhUbN6If2jgX6DBwqS6HhCmA210+P+G+K9+RarStL/43TgQvog5zDDLM="
	}
sshFactory.portal.registerChecker(PublicKeyCredentialsChecker(authorizedKeys))
pubKeyString, privKeyString = getRSAKeys()
sshFactory.publicKeys = {'ssh-rsa': keys.getPublicKeyString(data=pubKeyString)}
sshFactory.privateKeys = {'ssh-rsa': keys.getPrivateKeyObject(data=privKeyString)}



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
			raise SyntaxError('Usage: listen ssh ‹port›')
		self.parent.displayname = tuple(event)
		reactor.listenTCP(int(event[0]), sshFactory)


class SSHauth(Statement):
	name = ("auth","ssh")
	doc = "authorize a user to connect"
	long_doc="""\
Usage: auth ssh ‹username› "‹ssh pubkey›"
This command allows the named used to connect with their SSH key.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 2:
			raise SyntaxError('Usage: auth ssh ‹username› "‹ssh pubkey›"')
		pubkey=event[1]
		if " " in pubkey:
			raise SyntaxError('The ‹ssh pubkey› does not contain spaces.')
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
	name = ("no","auth","ssh")
	doc = "forbid authorize a user to connect"
	long_doc="""\
Usage: no auth ssh ‹username›
This command blocks the named user from accessing the server.
Existing connections are not affected.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError('Usage: no auth ssh ‹username›')
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
	
	def unload(self):
		main_words.unregister_statement(SSHlisten)
		main_words.unregister_statement(SSHlistauth)
		main_words.unregister_statement(SSHauth)
		main_words.unregister_statement(SSHnoauth)
	
init = SSHmodule

