import os.path

root_dir = os.path.expanduser('~/pld-builder.new/')
conf_dir = root_dir + "config/"
spool_dir = root_dir + "spool/"
lock_dir = root_dir + "lock/"
www_dir = root_dir + "www/"

acl_conf = conf_dir + "acl.conf"
builder_conf = conf_dir + "builder.conf"

# spool/
queue_file = spool_dir + "queue"
req_queue_file = spool_dir + "req_queue"
processed_ids_file = spool_dir + "processed_ids"
buildlogs_queue_dir = spool_dir + "buildlogs/"
ftp_queue_dir = spool_dir + "ftp/"
last_req_no_file = spool_dir + "last_req_no"
got_lock_file = spool_dir + "got_lock"
log_file = spool_dir + "log"

# www/
srpms_dir = www_dir + "srpms/"
req_queue_signed_file = www_dir + "queue.gz"
max_req_no_file = www_dir + "max_req_no"
queue_stats_file = www_dir + "queue.txt"
