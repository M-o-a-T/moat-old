/*
 *  Copyright © 2007-2008, Matthias Urlichs <matthias@urlichs.de>
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License (included; see the file LICENSE)
 *  for more details.
 */

#ifndef FLOW_H
#define FLOW_H

/* Setup */
#ifndef FLOW_INTERNAL_H
typedef void FLOW;
#endif


#ifdef FLOW_STANDALONE
#define FLOW_PARAM1
#define FLOW_PARAM
#define FLOW_STRUCT void
#define FLOW_ARG1
#define FLOW_ARG
#else
#define FLOW_PARAM1 FLOW *flow
#define FLOW_PARAM FLOW_PARAM1 ,
#define FLOW_STRUCT FLOW *
#define FLOW_ARG1 flow
#define FLOW_ARG FLOW_ARG1 ,
#endif


/* constants for parity */
#define P_NONE 0
#define P_ODD 1
#define P_EVEN 2
#define P_SPACE 4
#define P_MARK 5

/* Initialize the data structure.
 *
 * Rate is in bits/second. maxlen is the max number of bytes in a
 * datagram. Bits/byte must obviously be >=1 and <=8. "msb" is set if
 * the most-significant bit shall be transmitted/received first.
 *
 * You can get mostly-raw access to the data stream by setting bits=1
 * and parity=P_NONE. ("Mostly", because sync bits are still handled
 * internally.)
 *
 * Byte parity is handled by this code; everything else is the job of
 * the application.
 */
FLOW_STRUCT flow_create(unsigned int rate, unsigned int maxlen,
                        unsigned char bits, unsigned char parity,
                        unsigned char msb, char id);

char flow_id(FLOW_PARAM1);

void flow_free(FLOW_PARAM1);

void flow_error(const char *msg);

/*********** reading ***********/

/* Access constants for the timeout buffer. It's initialized like this:

	unsigned int len[R_IDLE+1] = {
		[R_MIN+R_ZERO+R_MARK] = 123,
		[R_MAX+R_ZERO+R_MARK] = 234,
		[...]
		[R_IDLE] = 9999
	};
	flow_setup_reader(f, ..., len)

 * R_IDLE is the max time a signal can be present (or not) before
 * concluding that the datagram is over. It takes precedence over
 * all other timing values.
 * Both MARK (transmitter on) and SPACE (transmitter off) timings are
 * checked. Both need to be within range. Ranges may overlap. The
 * datagram is also considered to be over when a bit value cannot be
 * determined to be either ZERO or ONE.
 *
 * All times are in microseconds.
 */
#define R_MIN 0
#define R_MAX 4

#define R_ZERO 0
#define R_ONE 2

#define R_MARK 0
#define R_SPACE 1

#define R_IDLE 8 /* must be last */

void flow_setup_reader(FLOW_PARAM
                       unsigned int nsync, unsigned int len[R_IDLE+1]);

typedef void(*flow_readproc)(void *param, const unsigned char *buf, unsigned int len);

void flow_reader(FLOW_PARAM
                 flow_readproc proc, void *param);

/* If you have a buffer full of logged data, do this. */
void flow_read_buf(FLOW_PARAM
                   const unsigned char *buf, unsigned int len);

/* Alternately, if you have interrupts when the input changes,
 * re-start a timer after every IRQ and do this.
 * NOTE: 'hi' is a bool and states the *new* signal value. */
void flow_read_time(FLOW_PARAM
                    unsigned int duration, unsigned char hi);

void flow_report(FLOW_PARAM
                 unsigned short low, unsigned short high, unsigned short minlen);
int flow_read_logging(FLOW_PARAM1);

/*********** write ***********/

/* offsets for timing. See read side for explanation, except that we
 * have a fixed time and no min/max :-) */
#define W_MARK 0
#define W_SPACE 2

#define W_ZERO 0
#define W_ONE 1

#define W_IDLE 4 /* must be last */

void flow_setup_writer(FLOW_PARAM
                       unsigned int nsync, unsigned int len[W_IDLE+1]);

typedef void(*flow_writeproc)(void *param, unsigned int hi, unsigned int lo);

void flow_writer(FLOW_PARAM
                 flow_writeproc proc, void *param);

int flow_write_buf(FLOW_PARAM
                   unsigned char *data, unsigned int len);
/* These return -1/errno when the external write fails, or something else
 * goes wrong*/

void flow_write_step(FLOW_PARAM
                     unsigned int *hi, unsigned int *lo);
/* Get the next thing to be done, in terms of W_XXX */


/*
 * There is no read_idle procedure because data is supposed to come in
 * continuously.
 */

#endif /* FLOW_H */
