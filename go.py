#!/usr/bin/python

import sys
from PLD_Builder.request import *

xml = """
<group id="d30eb8ae-3c54-4103-9188-69b1114d6ac7">
  <priority>2</priority>
  <requester>malekith</requester>
  <batch>
    <src-rpm>foo-1.2-3.src.rpm</src-rpm>
    <spec>foo.spec</spec>

    <info>foo.spec -r DEVEL blah,blah</info>
    
    <with>foo</with>
    <without>bar</without>
    
    <builder>i386</builder>
    <builder>i586</builder>
    <builder>i686</builder>
    <builder>ppc</builder>
  </batch>
  <batch>
    <src-rpm>bar-1.2-1.src.rpm</src-rpm>
    <spec>bar.spec</spec>

    <info>bar.spec -r HEAD blah,blah</info>
    
    <with>foo</with>
    <without>bar</without>
    
    <builder>i386-security</builder>
    <builder>i586-security</builder>
    <builder>i686-security</builder>
  </batch>
</group>
"""

parse(xml).dump()
