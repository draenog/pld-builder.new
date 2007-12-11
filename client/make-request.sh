#!/bin/sh

builders=
specs=
with=
without=
flags=
command=
command_flags=
gpg_opts=
default_branch='HEAD'
distro=

if [ -n "$HOME_ETC" ]; then
	USER_CFG=$HOME_ETC/.requestrc
else
	USER_CFG=$HOME/.requestrc
fi

if [ ! -f "$USER_CFG" ]; then
	echo "Creating config file $USER_CFG. You *must* edit it."
	cat >$USER_CFG <<'EOF'
priority=2
requester=deviloper@pld-linux.org
default_key=deviloper@pld-linux.org
mailer="/usr/sbin/sendmail -t"
gpg_opts=""
distro=th

# defaults:
f_upgrade=yes
EOF
exit
fi

if [ -f "$USER_CFG" ]; then
	. $USER_CFG
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
	echo "       Performs a 'test-build'. Package will be uploaded to test/ tree"
	echo "       and won't be upgraded on builders"
	echo "  -r   --ready-build"
	echo "       Build and upgrade package and upload it to ready/ tree"
	echo "  -u   --upgrade"
	echo "       Forces package upgrade (for use with -t)"
	echo "  -n   --no-upgrade"
	echo "       Disables package upgrade (for use with -r)"
	echo "  -ni  -no-install-br"
	echo "       Do not install missing BuildRequires (--nodeps)"
	echo "  -f   --flag"
	echo "  -d   --distro"
	echo "       Specify value for \$distro"
	echo "  -cf  --command-flag"
	echo "       Not yet documented"
	echo "  -c   --command"
	echo "       Executes a given command on builders"
	echo "       --test-remove-pkg"
	echo "       shortcut for --command poldek -evt ARGS"
	echo "       --remove-pkg"
	echo "       shortcut for --command poldek -ev --noask ARGS"
	echo "       --upgrade-pkg"
	echo "       shortcut for --command poldek -uv ARGS"
	echo "       --cvsup"
	echo "       Updates builders infrastructure (outside chroot)"
	echo "  -q   "
	echo "       shortcut for --command rpm -q ARGS"
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
		--distro | -d )
			distro=$2
			shift
			;;

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

		--kernel )
			kernel=$2
			shift
			;;

		--priority | -p )
			priority=$2
			shift
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
			f_upgrade=no
			shift
			;;
		--test-remove-pkg)
			command="poldek -evt $2"
			f_upgrade=no
			shift
			;;
		--remove-pkg)
			command="poldek -ev --noask $2"
			f_upgrade=no
			shift
			;;
		--upgrade-pkg)
			command="poldek -uv $2"
			f_upgrade=no
			shift
			;;
		-q)
			command="rpm -q $2"
			f_upgrade=no
			shift
			;;

		--cvsup )
			command_flags="no-chroot"
			command="cvs up"
			f_upgrade=no
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

		*:* | * )
			specs="$specs $1"
			;;
	esac
	shift
done

case "$distro" in
ac)
	builder_email="builder-ac@pld-linux.org"
	default_builders="ac-*"
	default_branch="AC-branch"
	;;
ac-java) # fake "distro" for java available ac archidectures
	builder_email="builder-ac@pld-linux.org"
	default_builders="ac-i586 ac-i686 ac-athlon ac-amd64"
	default_branch="AC-branch"
	;;
ti)
	builder_email="builderti@ep09.pld-linux.org"
	default_builders="ti-*"
	;;
th)
	builder_email="builderth@ep09.pld-linux.org"
	default_builders="th-*"
	;;
*)
	die "distro \`$distro' not known"
	;;
esac

specs=`for s in $specs; do
	case "$s" in
	*.spec:*) # spec with branch
		echo $s
		;;
	*.spec) # spec without branch
		echo $s:$default_branch
		;;
	*:*) # package name with branch
		echo $s | sed -e 's/:/.spec:/'
		;;
	*) # just package name
		echo $s.spec:$default_branch
		;;
	esac
done`

if [[ "$requester" != *@* ]] ; then
		requester="$requester@pld-linux.org"
fi

if [ -z "$builders" ] ; then
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

if [ -z "$build_mode" ] ; then
	# missing build mode, builders go crazy when you proceed"
	die "please specify build mode"
fi


ok=
for s in $specs; do
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
	echo "	<time>$(date +%s)</time>"
	echo "	<priority>$priority</priority>"
	echo

	if [ "$command" != "" ] ; then
		bid=$(uuidgen)
		echo >&2 "* Command: $command"
		echo "	<batch id='$bid' depends-on=''>"
		echo "		 <command flags='$command_flags'>$command</command>"
		echo "		 <info></info>"
		for b in $builders; do
			echo >&2 "* Builder: $b"
			echo "		 <builder>$b</builder>"
		done
		echo "	</batch>"
	else

	echo >&2 "* Using priority $priority"
	echo >&2 "* Using email $builder_email"
	echo >&2 "* Build mode: $build_mode"
	if [ "$f_upgrade" = "yes" ] ; then
		echo >&2 "* Upgrade mode: $f_upgrade"
	fi
	echo >&2 "* Queue-ID: $id"

	# first id:
	fid=
	i=1
	for s in $specs; do
		bid=$(uuidgen)
		echo "	<batch id='$bid' depends-on='$fid'>"
		[ "$fid" = "" ] && fid="$bid"
		name=$(echo "$s" | sed -e 's|:.*||')
		branch=$(echo "$s" | sed -e 's|.*:||')
		echo >&2 "* Adding #$i $name:$branch"
		echo "		 <spec>$name</spec>"
		echo "		 <branch>$branch</branch>"
		echo "		 ${kernel:+<kernel>$kernel</kernel>}"
		echo "		 <info></info>"
		echo
		for b in $with; do
			echo "		 <with>$b</with>"
		done
		for b in $without; do
			echo "		 <without>$b</without>"
		done
		echo
		for b in $builders; do
			echo >&2 "* Builder: $b"
			echo "		 <builder>$b</builder>"
		done
		echo "	</batch>"
		i=$((i+1))
	done

	fi

	echo "</group>"
}

gen_email () {
	# make request first, so the STDERR/STDOUT streams won't be mixed
	local req=$(gen_req)

cat <<EOF
From: $requester
To: $builder_email
Subject: build request
Message-Id: <$id@$(hostname)>
X-New-PLD-Builder: request
X-Requester-Version: \$Id$

$(echo "$req" | gpg --clearsign --default-key $default_key $gpg_opts)
EOF
}

gen_email | $mailer

# vim:ts=2:sw=2
