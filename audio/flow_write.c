/*
 *  Copyright © 2007, Matthias Urlichs <matthias@urlichs.de>
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

#include <stdio.h>
#include <malloc.h>
#include <string.h>
#include <errno.h>
#include "flow_internal.h"

/* Note that care must be taken to keep accurate track of how many bytes
 * per second need to get sent, given that the time a byte requires
 * processing for cannot be represented accurately.
 *
 * Not if you have a sample rate of 44100 bytes/sec, anyway.
 *
 * This code assumes, however, that the sample rate itself
 * *can* be thus represented.
 */

void flow_setup_writer(FLOW_PARAM
                       unsigned int nsync, unsigned int param[W_IDLE])
{
	unsigned int i;
	F_w_sync = nsync;
	for(i=W_IDLE+1; i-- > 0;) {
		F_w_times[i] = flow_rate(f,param[i]);
	}
}

void flow_writer(FLOW_PARAM
                 flow_writeproc proc, void *param, int blocking)
{
	F_writer = proc;
	F_writer_param = param;
	F_blocking = blocking;
}

int flow_write_buf(FLOW_PARAM
                   unsigned char *data, unsigned int len)
{
	unsigned char *bp;
	unsigned char par;

#define M(x) ((F_w_times[x+W_ZERO] > F_w_times[x+W_ONE]) ? \
		F_w_times[x+W_ZERO] : F_w_times[x+W_ONE])
	unsigned int min_len = ((F_bits+1)*len+F_w_sync+2)*(M(R_MARK)+M(R_SPACE))+F_w_times[W_IDLE];
#undef M

	if(F_sendbuf_len < F_sendbuf_used + min_len) {
		unsigned char *buf = realloc(F_sendbuf, F_sendbuf_used + min_len);
		if (buf == NULL) return -1;
		F_sendbuf = buf;
		F_sendbuf_len = min_len;
	}
	bp = F_sendbuf + F_sendbuf_used;

	/* One high/low sequence */
	inline void R(int _x)
	{
		unsigned int _i;
		for(_i=F_w_times[_x+W_MARK];_i>0;_i--) *bp++ = '\xFF';
		for(_i=F_w_times[_x+W_SPACE];_i>0;_i--) *bp++ = '\x00';
	}
	inline void X(unsigned char _y) /* one bit */
	{
		if(_y) {
			R(W_ONE);
			par ^= 1;
		} else
			R(W_ZERO);
	}


	inline void BM(unsigned char _b) /* one byte plus parity, MSB first */ 
	{
		unsigned char _m = 1<<(F_bits-1);

		par=0;
		while(_m) {
			X(_b & _m);
			_m >>= 1;
		}
		X(par); /* parity */
	}

	inline void BL(unsigned char _b) /* one byte plus parity, LSB first */ 
	{
		unsigned char par=0;
		unsigned char _m = F_bits;
		while(_m--) {
			X(_b & 1);
			_b >>= 1;
		}
		X(par); /* parity */
	}

	unsigned int i;

	/* sync sequence */
	for(i=0;i<F_w_sync;i++)
		R(0);
	R(1);

	if(F_msb)
		while(len--) BM(*data++);
	else
		while(len--) BL(*data++);
	R(0); /* one last bit, to mark the end */
	     /* this is because the decoder may just look at the pause lengths */
	for(i=F_w_times[W_IDLE]; i > 0; i--) *bp++ = '\0';
	F_sendbuf_used = bp-F_sendbuf;
	return flow_write_idle(
#ifndef FLOW_STANDALONE
                           flow
#endif
                               );
}

int flow_write_idle(FLOW_PARAM1)
{
	int n;
	struct timeval tn;


	if(F_sendbuf_used) {
		n = (*F_writer)(F_writer_param, F_sendbuf, F_sendbuf_used);
		if (n == F_sendbuf_used) {
			F_sendbuf_used = 0;
			F_bytes_sent += n;
		} else if (n > 0) { /* partial write */
			F_sendbuf_used -= n;
			memcpy(F_sendbuf, F_sendbuf + n, F_sendbuf_used);

			/* Assume that the send buffer is full. Thus, there is no
			   point in keeping track of any accumulated backlog. */
			gettimeofday(&F_last_sent, NULL);
			F_bytes_sent = 0;
			return 0;
		} else if (n == 0) { /* EOF? */
			errno = 0;
			return -1;
		} else if ((errno == EINTR) || (errno == EAGAIN)) {
			return 0;
		} else {
			return -1;
		}
	}

	gettimeofday(&tn, NULL);

	/*
	 * Here we try to figure out whether to send zero fill-up bytes
	 * to keep the sound pipe's send buffer full.
	 */

	if (F_blocking) {
		/*
		 * No need to count anything if the interface is going to block
		 * on us anyway.
		 */
		n = F_rate/20;
		if (F_fillbuf_len < n) {
			free(F_fillbuf);
			F_fillbuf = malloc(n);
			if (!F_fillbuf) return -1;
			F_fillbuf_len = n;
			memset(F_fillbuf,0,n);
		}
		n = (*F_writer)(F_writer_param, F_fillbuf, n);
		if (n == 0) errno = 0;
		if (n <= 0) return -1;
		return 0;
	}
	/*
	 * First, clean up the byte counter..:
	 */
	if (F_bytes_sent > F_rate) {
		F_last_sent.tv_sec += F_bytes_sent/F_rate;
		F_bytes_sent %= F_rate;
	}
	if(timercmp(&F_last_sent, &tn, <)) {
		long long nb = (tn.tv_sec - F_last_sent.tv_sec) * 1000000 + (tn.tv_usec - F_last_sent.tv_usec);
		nb = (nb * F_rate) / 1000000 - F_bytes_sent;
		if (nb > 0) {
			if (nb < F_rate/5) { /* 1/5th second */
				n = nb;
				if (F_fillbuf_len < n) {
					free(F_fillbuf);
					F_fillbuf = malloc(n);
					if (!F_fillbuf) return -1;
					F_fillbuf_len = n;
					memset(F_fillbuf,0,n);
				}
				n = (*F_writer)(F_writer_param, F_fillbuf, n);
				if (n == 0) errno = 0;
				if (n <= 0) return -1;
				if (n == nb) {
					F_bytes_sent += n;
					return 0;
				}
				/* repeat, because the partial writeproc() could have
				 * taken up any amount of time */
				gettimeofday(&tn, NULL);
			}
			/* If we arrive here, either there was a buffer overrun or
			 * too much time has passed since the last call. Either way 
			 * we restart from now.
			 */
			F_last_sent = tn;
			F_bytes_sent = 0;
		}
	}
	return 0;
}

