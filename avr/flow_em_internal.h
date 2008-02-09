/*
 *  Copyright © 2008, Matthias Urlichs <matthias@urlichs.de>
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

/* This header implements basic flow parameters. */

#ifndef FLOW_EM_I_H
#define FLOW_EM_I_H

#define FLOW_STANDALONE

#include "flow.h"
#include "flow_data.h"
#include "flow_internal.h"
#include "qtask.h"

#	define F_bits 4
#	define F_id 'e'
#	define F_parity P_MARK
#	define F_msb 0
static const short F_r_times[R_IDLE+1] = {
#include "timing.em.read.h"
};
#	define F_r_sync 6

#	define F_reader read_data
#	define F_reader_param 'e'

static unsigned char F_readlen;
static unsigned char F_lasthi;
static unsigned char F_r_mark_one;
static unsigned char F_r_space_one;
static unsigned char F_r_mark_zero;
static unsigned char F_r_space_zero;
static unsigned char F_qsum;

static unsigned char F_byt;
static unsigned char F_bit;
static unsigned char F_syn;

#	define F_read_max 10
static unsigned char F_readbuf[F_read_max];

	/* read tracing */
#undef F_LOG

	/* write */
static unsigned const short F_w_times[W_IDLE+1] = {
#include "timing.em.write.h"
};

#	define F_w_sync 12

#	define F_writer NULL
#	define F_writer_param NULL

	/* writer state */
	/* in flow.h, as we only have one writer */


#endif /* FLOW_EM_I_H */
