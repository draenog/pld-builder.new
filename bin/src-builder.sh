#!/bin/sh

umask 022
export LC_CTYPE=en_US.iso-8859-1
CONFIG=$HOME/.pldbuilderrc
[ -f "$CONFIG" ] && . $CONFIG
if [ -z "$BUILDERPATH" ]; then
	dir=$(dirname "$0")
	BUILDERPATH="$(cd "$dir"/..; pwd)"
fi
export BUILDERPATH

cd $BUILDERPATH
exec python PLD_Builder/srpm_builder.py
