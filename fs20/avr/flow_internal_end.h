#   define F_reader read_data
#   define F_reader_param F_id
#   define F_writer NULL
#   define F_writer_param NULL

#define HEAD(fn) \
flow_head fn ## _head = { \
	.type= F_id, \
	.write_idle= F_w_idle, \
	.write_init= flow_write_init, \
	.write_step= flow_write_step, \
	.read_reset= flow_init, \
	.read_at_work=flow_read_at_work, \
	.read_time = flow_read_time, \
};

