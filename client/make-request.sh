#!/bin/sh

builders=
specs=
with=
without=
flags=
command=
command_flags=

if [ -f "$HOME/.requestrc" ]; then
	. $HOME/.requestrc
else
	echo "Creating config file ~/.requestrc. You *must* edit it."
	cat >$HOME/.requestrc <<EOF
priority=2
requester=deviloper
default_key=deviloper@pld-linux.org
builder_email=builder-ac@pld-linux.org
mailer="/usr/sbin/sendmail -t"
default_builders="ac-*"

# defaults:
build_mode=ready
f_upgrade=yes

EOF
exit
fi

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
      f_upgrade=no
      ;;

    --ready-build | -r )
      build_mode=ready
      ;;

    --upgrade | -u )
      f_upgrade=yes
      ;;

    --no-upgrade | -n )
      f_upgrade=no
      ;;

    --no-install-br | -ni )
	  flags="$flags no-install-br" 
	  ;;
	  
    --flag | -f )
      flags="$flags $2"
      shift
      ;;

    --command-flags | -cf )
      command_flags="$2"
      shift
      ;;

    --command | -c )
      command="$2"
      shift
      ;;

	--cvsup )
	  command_flags="no-chroot"
	  command="cvs up"
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

specs=`for s in $specs ; do
  case "$s" in
    *.spec:* ) echo "$s" ;;
    * ) echo "$s" | sed -e 's/:/.spec:/' ;;
  esac
done`

if [ "$builders" = "" ] ; then
  builders="$default_builders"
fi

if [ "$f_upgrade" = "yes" ] ; then
  flags="$flags upgrade"
fi

if [ "$build_mode" = "test" ] ; then
  if [ "$f_upgrade" = "yes" ] ; then
    die "--upgrade and --test-build are mutually exclusive"
  fi
  flags="$flags test-build"
fi

ok=
for s in $specs ; do
  ok=1
done

if [ "$ok" = "" ] ; then
  if [ "$command" = "" ] ; then
    die "no specs passed"
  fi
else
  if [ "$command" != "" ] ; then
    die "cannot pass specs and --command"
  fi
fi

id=$(uuidgen)

gen_req() {
  echo "<group id='$id' no='0' flags='$flags'>"
  echo "  <time>$(date +%s)</time>"
  echo "  <priority>$priority</priority>"
  echo

  if [ "$command" != "" ] ; then
    bid=$(uuidgen)
    echo "  <batch id='$bid' depends-on=''>"
    echo "     <command flags='$command_flags'>$command</command>"
    echo "     <info></info>"
    for b in $builders ; do
      echo "     <builder>$b</builder>"
    done
    echo "  </batch>"
  else
  
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
    echo "     <info></info>"
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

  fi
  
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
