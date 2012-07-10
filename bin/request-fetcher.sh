#!/bin/sh

umask 022
export LC_CTYPE=en_US.iso-8859-1

CONFIG=$HOME/.pldbuilderrc
[ -f "$CONFIG" ] && . $CONFIG
[ -n "$BUILDERPATH" ] || BUILDERPATH="$HOME/pld-builder.new/"
export BUILDERPATH

cd $BUILDERPATH
exec python PLD_Builder/request_fetcher.py
