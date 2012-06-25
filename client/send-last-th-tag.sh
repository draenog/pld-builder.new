#!/bin/sh
set -e

dist=th

./make-request.sh -d $dist -r -a "$@"
