#!/bin/sh

if [ "$1" != "y" ] ; then
  echo "this scripts kills current queue and installs new"
  echo "run '$0 y' to run it"
  exit 1
fi

mkdir -p spool www/srpms log lock
echo 1 > www/counter
echo -n > spool/processed_ids
echo '<queue/>' > spool/queue
echo '<queue/>' > spool/req_queue
