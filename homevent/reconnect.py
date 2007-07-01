# *-* coding: utf-8 *-*

"""\
This is a somewhat-mangled version of the ReconnectingClientFactory
from Twisted.
"""

from twisted.internet import interfaces, error, protocol
from homevent.logging import TRACE,log
from twisted.internet import reactor

class ReconnectingClientFactory(protocol.ClientFactory):
	"""My clients auto-reconnect with an exponential back-off.

	Note that clients should call my resetDelay method after they have
	connected successfully.

	@ivar maxDelay: Maximum number of seconds between connection attempts.
	@ivar initialDelay: Delay for the first reconnection attempt.
	@ivar factor: a multiplicitive factor by which the delay grows
	@ivar jitter: percentage of randomness to introduce into the delay length
		to prevent stampeding.
	"""
	maxDelay = 3600
	initialDelay = 1.0
	# Note: These highly sensitive factors have been precisely measured by
	# the National Institute of Science and Technology.  Take extreme care
	# in altering them, or you may damage your Internet!
	factor = 2.7182818284590451 # (math.e)
	# Phi = 1.6180339887498948 # (Phi is acceptable for use as a
	# factor if e is too large for your application.)
	jitter = 0.11962656492 # molar Planck constant times c, Jule meter/mole

	delay = initialDelay
	retries = 0
	maxRetries = None
	_callID = None
	connector = None

	continueTrying = 1

	def finalFailure(self):
		"""The max number of retries has been reached.
		"""

	def clientConnectionFailed(self, connector, reason):
		self.connector = connector
		if self.continueTrying:
			self.retry()

	def clientConnectionLost(self, connector, unused_reason):
		self.connector = connector
		if self.continueTrying:
			self.retry()

	def tryNow(self, connector=None):
		if self._callID:
			return

		self.resetDelay()

		if connector is None:
			if self.connector is None:
				return # in progress
			else:
				connector = self.connector

		log(TRACE,"Try %s immediately" % (connector,))
		self.connector = None
		connector.connect()

	def retry(self, connector=None):
		"""Have this connector connect again, after a suitable delay.
		"""
		if not self.continueTrying:
			log(TRACE,"Abandoning %s on explicit request" % (connector,))
			return

		if connector is None:
			if self.connector is None:
				raise ValueError("no connector to retry")
		else:
			self.connector = connector

		self.retries += 1
		if self.maxRetries is not None and (self.retries > self.maxRetries):
			log(INFO,"Abandoning %s after %d retries." %
						(connector, self.retries))
			return self.finalFailure()

		self.delay = min(self.delay * self.factor, self.maxDelay)
		if self.jitter:
			self.delay = random.normalvariate(self.delay,
												self.delay * self.jitter)

		log(DEBUG,"%s will retry in %d seconds" % (connector, self.delay,))

		def reconnector():
			log(DEBUG,"%s retrying now" % (connector,))
			self._callID = None
			self.connector.connect()
			self.connector = None
		self._callID = reactor.callLater(self.delay, reconnector)

	def stopTrying(self):
		"""I put a stop to any attempt to reconnect in progress.
		"""
		# ??? Is this function really stopFactory?
		if self._callID:
			self._callID.cancel()
			self._callID = None
		if self.connector:
			# Hopefully this doesn't just make clientConnectionFailed
			# retry again.
			try:
				self.connector.stopConnecting()
			except error.NotConnectingError:
				pass
		self.continueTrying = 0

	def resetDelay(self):
		"""Call me after a successful connection to reset.

		I reset the delay and the retry counter.
		"""
		self.delay = self.initialDelay
		self.retries = 0
		self.continueTrying = 1

		if self._callID:
			self._callID.cancel()
			self._callID = None

