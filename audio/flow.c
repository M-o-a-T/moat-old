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
#include <sys/time.h>

#include "flow_internal.h"

FLOW_STRUCT
flow_setup(unsigned int rate, unsigned int maxlen, unsigned char bits, 
           unsigned char parity, unsigned char msb)
{
#ifndef FLOW_STANDALONE
	FLOW *flow = malloc(sizeof(*flow));
	if (!flow) return NULL;
	memset(flow,0,sizeof(*flow));
#endif

	F_rate = rate;
	F_bits = bits;
	F_parity = parity;
	F_msb = msb;
	F_read_max = maxlen;

#ifdef F_last_sent
	gettimeofday(&F_last_sent, NULL);
#endif

#ifndef FLOW_STANDALONE
	return flow;
#endif
}

void flow_free(FLOW_PARAM1)
{
#ifndef FLOW_STANDALONE
	if(!flow) return;
#endif
	free(F_readbuf);
	free(F_sendbuf);
	free(F_fillbuf);
	free(F_logbuf);
#ifndef FLOW_STANDALONE
	free(flow);
#endif
}
