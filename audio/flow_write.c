/*
 *  Copyright (C) 2007  Matthias Urlichs <matthias@urlichs.de>
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

void flow_writer(FLOW *f, flow_writeproc proc, void *param)
{
	f->writer = proc;
	f->writer_param = param;
}

int flow_write_buf(FLOW *f, unsigned char *data, unsigned int len)
{
	unsigned int min_len = 2*9*(len+3)*f->high; /* yes, that's more than necessary. */
	unsigned char *bp;
	int n = 0;

	if(f->sendbuf_len < f->sendbuf_used + min_len) {
		unsigned char *buf = realloc(f->sendbuf, f->sendbuf_used + min_len);
		if (buf == NULL) return -1;
		f->sendbuf = buf;
		f->sendbuf_len = min_len;
	}
	bp = f->sendbuf + f->sendbuf_used;

#define R(x) /* One high/low sequence */ \
	do { \
		int _x = (x); \
		unsigned int _i; \
		for(_i=0;_i<_x;_i++) *bp++ = '\xFF'; \
		for(_i=0;_i<_x;_i++) *bp++ = '\0'; \
		n += 2*_x; \
	} while(0)
#define L() R(f->s_zero) /* one short such sequence => 0 bit */
#define H() R(f->s_one) /* one long sequence => 1 bit */
#define X(x) do { if((x)) H(); else L(); } while(0) /* one bit */
#define B(b) /* one byte plus parity */ \
	do { \
		unsigned char _m = 0x80; \
		unsigned char _b = (b); \
		while(_m) { \
			X(_b & _m); \
			_m >>= 1; \
		} \
		_b ^= _b >> 4; \
		_b ^= _b >> 2; \
		_b ^= _b >> 1; \
		X(_b & 1); /* parity */ \
	} while(0) 

	unsigned int i;
	for(i=0;i<12;i++) L();  H(); /* sync sequence */
	while(len--) B(*data++);
	L(); /* one last bit, to mark the end */
	     /* this is because the decoder may just look at the pause lengths */
	for(i=0; i < f->high*3; i++) *bp++ = '\0';
	f->sendbuf_used += n + 3*f->high;
	return flow_write_idle(f);
}

int flow_write_idle(FLOW *f)
{
	int n;
	struct timeval tn;


	if(f->sendbuf_used) {
		n = (*f->writer)(f->writer_param, f->sendbuf, f->sendbuf_used);
		if (n == f->sendbuf_used) {
			f->sendbuf_used = 0;
			f->bytes_sent += n;
		} else if (n > 0) { /* partial write */
			f->sendbuf_used -= n;
			memcpy(f->sendbuf, f->sendbuf + n, f->sendbuf_used);

			/* Assume that the send buffer is full. Thus, there is no
			   point in keeping track of any accumulated backlog. */
			gettimeofday(&f->last_sent, NULL);
			f->bytes_sent = 0;
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
	 *
	 * First, clean up the byte counter..:
	 */
	if (f->bytes_sent > f->rate) {
		f->last_sent.tv_sec += f->bytes_sent/f->rate;
		f->bytes_sent %= f->rate;
	}
	if(timercmp(&f->last_sent, &tn, <)) {
		long long nb = (tn.tv_sec - f->last_sent.tv_sec) * 1000000 + (tn.tv_usec - f->last_sent.tv_usec);
		nb = (nb * f->rate) / 1000000 - f->bytes_sent;
		if (nb > 0) {
			if (nb < f->rate/5) { /* 1/5th second */
				n = nb;
				if (f->fillbuf_len < n) {
					free(f->fillbuf);
					f->fillbuf = malloc(n);
					if (!f->fillbuf) return -1;
					f->fillbuf_len = n;
					memset(f->fillbuf,0,n);
				}
				n = (*f->writer)(f->writer_param, f->fillbuf, n);
				if (n == 0) errno = 0;
				if (n <= 0) return -1;
				if (n == nb) {
					f->bytes_sent += n;
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
			f->last_sent = tn;
			f->bytes_sent = 0;
		}
	}
	return 0;
}

