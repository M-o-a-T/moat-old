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

/*
 * This code defines the timing handler for FS20.
 */

#include "util.h"
#include "flow_internal.h"
#include "flow_fs20_internal.h"

#define STATIC static
#include "flow_write.c"
#include "flow_read.c"

flow_head fs20_head = {
	.type= 'f', // for fs20
	.write_idle= 2000,
	.write_init= flow_write_init,
	.write_step= flow_write_step,
	.read_reset= flow_init,
	.read_at_work=flow_read_at_work,
	.read_time = flow_read_time,
};

