==============================
The Folie/MoaT link to devices
==============================

IoT devices typically require some sort of asynchronous adapter.
This document describes the data structure used to talk to MoaT devices
which run Forth.

The adapter exposes a standard Forth console with some extensions,
activated by ASCII control characters, via a USB or serial interface.
The rate shall be 115200 baud (8n1) by default.

Binary data to and from adapters is transmitted in packetized streams.

Adapters may be chained. Data from chained adapters are forwarded via
channels.

Channel and stream numbers are transmitted in binary and may not be >127.

Console protocol
++++++++++++++++

Adapter-to-server
=================

* 23 (ETB, End Transmission Block)

  Followed by some text (optional) and a CR (mandatory), tell the server
  that the current line has been processed and the next line of input may
  be transmitted.

* 24 (CAN, Cancel)

  Followed by some text and a CR, tell the server that there has been an
  error. Text transmission should terminate. If this occurs during
  programming, the adapter may not be in a consistent state; the
  sender's UI should flag the last transmitted line as having problems.
 
* 26 (SUB, Substitute)

  Followed by a file name and a CR, this is a client-side implementation 
  of file inclusion. The word "include" shall be defined as

    : include token 26 emit type cr ;

  The server, upon receiving this sequence, shall send the named file
  before resuming the current file transfer. This allows client-controlled
  conditional file inclusion using ``[ifndef]`` or similar constructs.

  File names may not contain spaces. Two include statements in the same
  line are not allowed.

Server-to-adapter
=================

* 3 (^C)

  The client will reset.

  Sending this character shall also trigger auto-discovery in the server.

Auto discovery
--------------

Initially the server shall send a CR, wait for a second or so (discarding
any data it receives), and send another CR. If the reply contains an ETB,
extensions are supported. Otherwise the client needs to be programmed.
It's suggested to compile a minimal (non-packet) implementation of the
console protocol to RAM before flashing permanent data.


bidirectional
=============

* 16 (DLE, Data Link Escape)

  A binary packet follows. See below.

* ACK

  The packet has been received and a packet buffer is free; the other
  side may send the next packet.

* NAK

  Followed by some text and a CR: The packet could not be processed.

* DC1/DC3

  Standard flow control (^S/^Q).

  Note that during packet transmission, flow control must be disabled
  because there is no escape mechanism.

Packet flow control
===================

If no ACK has been received after sending a packet, a sender should wait
after sending the next packet's leading DLE. The receiver should
send ^S immediately (or after completing the packet it is itself
transmitting, if any).

The sender needs to wait until a currently-incoming packet is completed,
plus three character times. An ACK reply allows the sender to continue with
packet data but not with the console stream.

If the sender continues transmitting, the receiver shall discard the
incoming packet and then send NAK "BUSY" CR.

Packet structure
++++++++++++++++

Packets are a maximum of 63 characters long. They consist of
 
 * a length byte; the top bit signals the presence of a checksum

 * optionally, any number of channel numbers. The top bit must be set.

 * A stream number. The top bit must be clear.

 * Data bytes
 
   Their semantics depends on the stream.

 * optionally, a checksum (XORing all previous bytes).

Streams
+++++++

Streams are typed. The type is a 4-character (32 bit) mnemonic. All-caps
types are reserved.

Console
-------

Stream #0 is used for forwarding console data. The first byte is a sequence
number for data from the server. The number wraps around (255>1; unnumbered
data have a sequence number of zero). The rest of the packet contains
character data. UTF-8 sequences must not be split. The client's reply
contains the next-expected sequence number.

On serial links, the console stream may be transmitted either via packets
or as inline serial data. The serial receiver is required to accept both.

The console stream itself cannot be configured; its stream number is used
as a way to configure channels. See below.

Discovery
---------

Stream #1 is used for auto-discovery and (possibly) configuration.
The first byte contains the stream# to be configured.

A packet to the device is a request for channel configuration or
information, depending on whether there are additional bytes.
The client replies with an information packet detailing the stream's state.
The reply always starts with a 4-character stream name.

Otherwise the following data configure the stream in question in some way.

Setting the stream number's top bit signals an error packet. A client
receiving such a packet is free to disable the stream in question. When
transmitted by the client, the server should display an error. Textual
information about the problem may be included in addtiional bytes.

The discovery stream's name is 'DISC'.

In a reply packet, the name is followed by a bitmap of allocated streams.
Bit 1 of the first byte is set, obviously.

Channels
--------

Channel discovery and configuration works roughly like that for streams,
except that the first data byte is the channel number. A discovery packet
without data yields a reply with the number of possible channels (high bit
is set to distinguish from single-channel info), followed by a bitmap of
allocated channels.

A new client may, upon successful connection, transmit an unsolicited
sequence of discovery reply packets for the streams it supports.

A client may auto-allocate a channel if a new sub-client connects to it.
In that case it sends an unsolicited channel reply for the channel.


Message routing
+++++++++++++++

AMQP
----

Raw messages are transmitted as QBroker alerts.
The routing key is "link.raw.DEVICE.DIR.CHANNEL….STREAM".

Messages must be encoded as "application/binary", for compatibility with
non-QBroker/MoaT code.

* DEVICE

  The name of the link. Local preference may subdivide this further.

* DIR

  "in" or "out" or "error"

* CHANNEL…

  A possibly-empty sequence of channel numbers

* STREAM

  The stream to use

