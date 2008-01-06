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

/* Common stuff for reader and writer */

#ifndef COMMON_H
#define COMMON_H

#include <stdio.h>

#ifndef COMMON_EXTERN
#define COMMON_EXTERN extern
#endif

COMMON_EXTERN int rate;
COMMON_EXTERN char *progname;
COMMON_EXTERN int progress;

#include "flow.h"

#define MAXFLOW 2
COMMON_EXTERN FLOW *f_log;
COMMON_EXTERN FLOW *flows[MAXFLOW+1];

int set_rate(int argc, char *argv[]);
int set_progress(int argc, char *argv[]);
void flow_setup(unsigned int *params, unsigned char bits, unsigned char parity, unsigned char msb, char prefix);

typedef int (*pcall)(int,char **);
struct work {
	const char *what;
	pcall code;
};
__attribute__((noreturn))
void parse_args(int argc, char *argv[], struct work **works);

/* This needs to be implemented by the main code! */
void do_flow_rw(FLOW *f, unsigned int *params);

__attribute__((noreturn))
void usage(int exitcode, FILE *out);

#endif
