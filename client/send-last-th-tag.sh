#!/bin/sh
set -e

dist=th

dir=$(dirname $0)

$dir/make-request.sh -d $dist -r -a "$@"
