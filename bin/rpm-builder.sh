#!/bin/sh

export LC_CTYPE=en_US.iso-8859-1
cd ~/pld-builder.new
python PLD_Builder/rpm_builder.py $1
