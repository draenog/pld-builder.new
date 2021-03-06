# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import os

root_dir = os.getenv('BUILDERPATH')
if root_dir is None:
    root_dir = os.path.expanduser('~/pld-builder.new')
conf_dir = root_dir + "/config"
spool_dir = root_dir + "/spool"
lock_dir = root_dir + "/lock"
www_dir = root_dir + "/www"

acl_conf = conf_dir + "/acl.conf"
builder_conf = conf_dir + "/builder.conf"
rsync_password_file = conf_dir + "/rsync-passwords"

# spool/
queue_file = spool_dir + "/queue"
req_queue_file = spool_dir + "/req_queue"
processed_ids_file = spool_dir + "/processed_ids"
notify_queue_dir = spool_dir + "/notify"
buildlogs_queue_dir = spool_dir + "/buildlogs"
ftp_queue_dir = spool_dir + "/ftp"
build_dir = spool_dir + "/builds"
last_req_no_file = spool_dir + "/last_req_no"
got_lock_file = spool_dir + "/got_lock"
log_file = spool_dir + "/log"

# www/
srpms_dir = www_dir + "/srpms"
req_queue_signed_file = www_dir + "/queue.gz"
max_req_no_file = www_dir + "/max_req_no"
queue_stats_file = www_dir + "/queue.txt"
queue_html_stats_file = www_dir + "/queue.html"
