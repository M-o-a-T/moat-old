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

#ifndef FLOW_STANDALONE
FLOW_STRUCT
flow_create(unsigned int rate, unsigned int maxlen, unsigned char bits, 
            unsigned char parity, unsigned char msb, char id)
{
	FLOW *flow = malloc(sizeof(*flow));
	if (!flow) return NULL;
	memset(flow,0,sizeof(*flow));

	F_rate = rate;
	F_bits = bits;
	F_parity = parity;
	F_msb = msb;
	F_read_max = maxlen;
	F_id = id;

#ifdef F_last_sent
	gettimeofday(&F_last_sent, NULL);
#endif

	return flow;
}

void flow_free(FLOW_PARAM1)
{
	free(F_readbuf);
	free(F_logbuf);
	free(flow);
}

char flow_id(FLOW_PARAM1)
{
	return F_id;
}

#endif
