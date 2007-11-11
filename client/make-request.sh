#!/bin/sh

builders=
specs=
with=
without=
flags=
command=
command_flags=
gpg_opts=

if [ -n "$HOME_ETC" ]; then
	USER_CFG=$HOME_ETC/.requestrc
else
	USER_CFG=$HOME/.requestrc
fi;

if [ -f "$USER_CFG" ]; then
	. $USER_CFG
else
	echo "Creating config file $USER_CFG. You *must* edit it."
	cat >$USER_CFG <<EOF
priority=2
requester=deviloper
default_key=deviloper@pld-linux.org
builder_email=builderth@ep09.pld-linux.org
mailer="/usr/sbin/sendmail -t"
default_builders="th-*"
gpg_opts=""

# defaults:
f_upgrade=yes

EOF
exit
fi

die () {
  echo "$0: $*" 1>&2
  exit 1
}

usage() {
  echo "Usage: make-request.sh [OPTION] ... [SPECFILE] ...."
  echo ""
  echo "Mandatory arguments to long options are mandatory for short options too."
  echo "  -C  --config-file /path/to/config/file"
  echo "       Source additional config file (after $USER_CFG), useful when"
  echo "       when sending build requests to Ac/Th from the same account"
  echo "  -b 'BUILDER BUILDER ...'  --builder='BUILDER BUILDER ...'"
  echo "       Sends request to given builders"
  echo "  --with VALUE --without VALUE"
  echo "       Build package with(out) a given bcond"
  echo "  --kernel VALUE"
  echo "       set alt_kernel to VALUE"
  echo "  -t   --test-build"
  echo "       Performs a test build. No upgrades on builders, no tagging."
  echo "  -r   --ready-build"
  echo "       Ac compatibility. \"Ready\" build"
  echo "  -u   --upgrade"
  echo "       Forces package upgrade"
  echo "  -n   --no-upgrade"
  echo "       Disables package upgrade"
  echo "  -ni  -no-install-br"
  echo "       Do not install missing BuildRequires (--nodeps)"
  echo "  -f   --flag"
  echo "  -cf  --command-flag"
  echo "       Not yet documented"
  echo "  -c   --command"
  echo "       Executes a given command on builders"
  echo "       --cvsup"
  echo "       Updates builders infrastructure (outside chroot)"
  echo "  -g   --gpg-opts \"opts\""
  echo "       Pass additional options to gpg binary"
  echo "  -p   --priority VALUE"
  echo "       sets request priority (default 2)"
  echo "  -h   --help"
  echo "       Displays this help message"
  exit 0;
}


while [ $# -gt 0 ] ; do
  case "$1" in
    --config-file | -C )
      [ -f $2 ] && . $2 || die "Config file not found"
      shift
      ;;
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
	  f_upgrade=yes
	  ;;

    --kernel )
      kernel=$2
      shift
      ;;

    --priority | -p )
      priority=$2
      shift
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

    --gpg-opts | -g )
       gpg_opts="$2"
       shift
       ;;
	  
    --help | -h )
      usage
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

if [[ "$requester" != *@* ]] ; then
    requester="$requester@pld-linux.org"
fi

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
    echo "     <kernel>$kernel</kernel>"
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
From: $requester
To: $builder_email
Subject: build request
Message-Id: <$id@$(hostname)>
X-New-PLD-Builder: request
X-Requester-Version: \$Id$

$(gen_req | gpg --clearsign --default-key $default_key $gpg_opts)
EOF
}

gen_email | $mailer
