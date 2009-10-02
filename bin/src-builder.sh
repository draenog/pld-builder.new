#!/bin/sh

umask 022
export LC_CTYPE=en_US.iso-8859-1
cd ~/pld-builder.new
for i in 1 2 3 4; do
	python PLD_Builder/srpm_builder.py
done
