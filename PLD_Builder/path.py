import os.path

root_dir = os.path.expanduser('~/pld-builder.new/')
conf_dir = root_dir + "config/"
spool_dir = root_dir + "spool/"
lock_dir = root_dir + "lock/"

acl_conf = conf_dir + "acl.conf"

queue_file = spool_dir + "queue"
processed_ids_file = spool_dir + "processed_ids"
counter_file = spool_dir + "counter"
