#ifndef FLOW_INTERNAL_H
#define FLOW_INTERNAL_H

struct _FLOW;
typedef struct _FLOW FLOW;

#include "flow.h"

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
	unsigned int low,mid,high;

	/* read */
	flow_readproc reader;

	int readlen;
	char lasthi;
	int cnt;
	int qsum;

	unsigned char byt,bit;
	char syn;

	unsigned char readbuf[FLOWMAX];

	/* write */
	unsigned long usec_per_byte;
	flow_writeproc writer;
};


#endif
