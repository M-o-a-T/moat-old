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

/* This header defines flow parameters for em. */

#define F_name em
#define F_id 'e'
#define F_bits 4
#define F_parity P_MARK
#define F_msb 0
#define F_r_sync 6
#define F_read_max 10
#define F_w_sync 12
#define F_r_idle 1500
#define F_w_idle 2000

#define T_read \
		[R_MIN+R_ZERO+R_MARK ] = 600, \
		[R_MIN+R_ZERO+R_SPACE] = 250, \
		[R_MIN+R_ONE +R_MARK ] = 250, \
		[R_MIN+R_ONE +R_SPACE] = 600, \
		[R_MAX+R_ZERO+R_MARK ] = 999, \
		[R_MAX+R_ZERO+R_SPACE] = 600, \
		[R_MAX+R_ONE +R_MARK ] = 600, \
		[R_MAX+R_ONE +R_SPACE] = 999, \
		[R_IDLE] = F_r_idle

#define T_write \
		[W_ZERO+W_MARK ] = 855, \
		[W_ZERO+W_SPACE] = 366, \
		[W_ONE +W_MARK ] = 366, \
		[W_ONE +W_SPACE] = 855, \
		[W_IDLE] = F_w_idle
