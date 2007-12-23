#ifndef FLOW_INTERNAL_H
#define FLOW_INTERNAL_H

struct _FLOW;
typedef struct _FLOW FLOW;

#include "flow.h"

#include <time.h>
#include <sys/time.h>

#define FLOWMAX 20 /* allowed packet length */

/**
 * Analyze incoming 868.35MHz signal.
 *
 * Yes I know, this should be a struct instead of a bunch of global
 * variables. If I ever need to parse more than one audio stream in a
 * single program at the same time (or make it Python-callable),
 * I'll be sure to put that in.
 */
struct _FLOW {
	unsigned long rate;

	/* read */
	unsigned int low,mid,high;

	flow_readproc reader;
	void *reader_param;

	int readlen;
	char lasthi;
	int cnt;
	int qsum;

	unsigned char byt,bit;
	char syn;

	unsigned char readbuf[FLOWMAX];

	/* write */
	unsigned int s_zero, s_one;
	struct timeval last_sent;
	unsigned long bytes_sent; /* never more than "rate" */

	flow_writeproc writer;
	void *writer_param;

	unsigned char *sendbuf;
	unsigned int sendbuf_len;
	unsigned int sendbuf_used;

	unsigned char *fillbuf; /* a bunch of zeroes */
	unsigned int fillbuf_len;
};


#endif
