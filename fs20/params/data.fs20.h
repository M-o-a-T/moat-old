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

/* This header defines flow parameters for fs20. */

#define F_name fs20
#define F_id 'f'
#define F_bits 8
#define F_parity P_EVEN
#define F_msb 1
#define F_r_sync 6
#define F_read_max 10
#define F_w_sync 12
#define F_r_idle 900
#define F_w_idle 2000

#define T_read \
		[R_MIN+R_ZERO+R_MARK ] = 300, \
		[R_MIN+R_ZERO+R_SPACE] = 300, \
		[R_MIN+R_ONE +R_MARK ] = 500, \
		[R_MIN+R_ONE +R_SPACE] = 500, \
		[R_MAX+R_ZERO+R_MARK ] = 500, \
		[R_MAX+R_ZERO+R_SPACE] = 500, \
		[R_MAX+R_ONE +R_MARK ] = 700, \
		[R_MAX+R_ONE +R_SPACE] = 700, \
		[R_IDLE] = F_r_idle

#define T_write \
		[W_ZERO+W_MARK ] = 400, \
		[W_ZERO+W_SPACE] = 400, \
		[W_ONE +W_MARK ] = 600, \
		[W_ONE +W_SPACE] = 600, \
		[W_IDLE] = F_w_idle
