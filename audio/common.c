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
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

#define COMMON_EXTERN
#include "common.h"
#include "flow.h"

int
set_rate(int argc, char *argv[])
{
	if (!argc) usage(2,stderr);
	rate = atoi(*argv);
	if(rate <= 8000) {
		fprintf(stderr,"rate must be at least 8000.\n");
		usage(2,stderr);
	}
	return 1;
}

int
set_progress(int argc, char *argv[])
{
	progress = 1;
	return 0;
}


/*************** exec some other program **********************/

void
flow_setup(unsigned int *params, char prefix)
{
	FLOW *f;
	FLOW **fp = flows;
	FLOW **fe = flows+MAXFLOW;

	f = flow_create(rate, 10, 8, P_EVEN, 1, prefix);
	if (!f) {
		fprintf(stderr,"Could not create stream (%c)\n", prefix);
		exit(2);
	}
	do_flow_rw(f,params);

	fp = flows;
	while(*fp) {
		if (++fp == fe) {
			fprintf(stderr,"This code does not support more than %d streams\n", MAXFLOW);
			exit(2);
		}
	}
	*fp = f;
	if (!f_log)
		f_log = f;
}

void
init_flows(void)
{
	memset(flows,0,sizeof(flows));
	f_log = NULL;
	rate = 32000;
	progress = 0;
}

void
free_flows(void)
{
	FLOW **f = flows;

	f_log = NULL;
	while(*f) {
		flow_free(*f);
		*(f++) = NULL;
	}
}


