#!/bin/sh

# FIXME: set with options
priority=2
requester=malekith
default_key=builder
builder_email=srpms_builder@roke.freak
mailer="/usr/sbin/sendmail -t"
default_builders="roke-athlon"

builders=
specs=
with=
without=
flags=

# defaults:
build_mode=ready
f_upgrade=yes

die () {
  echo "$0: $*" 1>&2
  exit 1
}

while [ $# -gt 0 ] ; do
  case "$1" in
    --builder | -b )
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

    --test-build | -t )
      build_mode=test
      f_upgrade=
      ;;

    --ready-build | -r )
      build_mode=ready
      ;;

    --upgrade | -u )
      f_upgrade=yes
      ;;

    --no-upgrade | -n )
      f_upgrade=
      ;;

    --flag | -f )
      flags="$flags $2"
      shift
      ;;
      
    -* )
      die "unknown knob: $1"
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


if [ "$builders" = "" ] ; then
  builders="$default_builders"
fi

if [ "$f_upgrade" ] ; then
  flags="$flags upgrade"
fi

if [ "$build_mode" = "test" ] ; then
  if [ "$f_upgrade" ] ; then
    die "--upgrade and --test-build are mutually exclusive"
  fi
  flags="$flags test-build"
fi

ok=
for s in $specs ; do
  ok=1
done

if [ "$ok" = "" ] ; then
  die "no specs passed"
fi

id=$(uuidgen)

gen_req() {
  echo "<group id='$id' no='0' flags='$flags'>"
  echo "  <time>$(date +%s)</time>"
  echo "  <priority>$priority</priority>"
  echo

  # first id:
  fid=
  for s in $specs ; do
    bid=$(uuidgen)
    echo "  <batch id='$bid' depends-on='$fid'>"
    [ "$fid" = "" ] && fid="$bid"
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

gen_email | $mailer
