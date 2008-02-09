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
static unsigned char F_readbuf[F_read_max];

static const short F_r_times[R_IDLE+1] = {
	T_read
};
static const unsigned short F_w_times[W_IDLE+1] = {
	T_write
};

