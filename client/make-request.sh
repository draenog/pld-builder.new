#!/bin/sh

# FIXME: set with options
priority=2
default_key=builder
builder_email=srpms_builder@roke.freak
mailer="/usr/sbin/sendmail -t"

builders="DEF"
specs=
with=
without=

while [ $# -gt 0 ] ; do
  case "$1" in
    -b )
      if [ "$builders" = DEF ] ; then
        builders=
      fi
      builders="$builders $2"
      shift
      ;;
    
    --with )
      with="$with $2"
      shift
      ;;
      
    --without )
      without="$without $2"
      shift
      ;;
      
    -* )
      echo "unknown knob: $1"
      exit 1
      ;;
      
    *:* )
      specs="$specs $1"
      ;;

    * )
      specs="$specs $1:HEAD"
      ;;
  esac
  shift
done


if [ "$builders" = DEF ] ; then
  builders="i386 i586 i686 athlon ppc"
fi

id=$(uuidgen)

gen_req() {
  echo "<group id='$id' no='0'>"
  echo "  <time>$(date +%s)</time>"
  echo "  <priority>$priority</priority>"
  echo

  for s in $specs ; do
    echo "  <batch>"
    name=$(echo "$s" | sed -e 's|:.*||')
    branch=$(echo "$s" | sed -e 's|.*:||')
    echo "     <spec>$name</spec>"
    echo "     <branch>$branch</branch>"
    echo "     <info>blah..</info>"
    echo
    for b in $with ; do
      echo "     <with>$b</with>"
    done
    for b in $without ; do
      echo "     <without>$b</without>"
    done
    echo
    for b in $builders ; do
      echo "     <builder>$b</builder>"
    done
    echo "  </batch>"
  done
  echo "</group>"
}

gen_email () {
cat <<EOF
From: $requester@pld-linux.org
To: $builder_email
Subject: build request
Message-Id: <$id@$(hostname)>
X-New-PLD-Builder: request
X-Requester-Version: $Id$

$(gen_req | gpg --clearsign --default-key $default_key)
EOF
}

gen_email
#| $mailer
