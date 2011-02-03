#!/bin/sh

# prevent "*" from being expanded in builders var
cd /usr/share/empty

builders=
with=
without=
flags=
command=
command_flags=
gpg_opts=
default_branch='HEAD'
distro=
url=
no_depend=no

[ -x /usr/bin/python ] && send_mode="python" || send_mode="mail"

if [ -n "$HOME_ETC" ]; then
	USER_CFG=$HOME_ETC/.requestrc
else
	USER_CFG=$HOME/.requestrc
fi

if [ ! -f "$USER_CFG" ]; then
	echo "Creating config file $USER_CFG. You *must* edit it."
	cat > $USER_CFG <<EOF
priority=2
requester=deviloper@pld-linux.org
default_key=deviloper@pld-linux.org
send_mode="$send_mode"
url="$url"
mailer="/usr/sbin/sendmail -t"
gpg_opts=""
distro=th
url="http://src.th.pld-linux.org:1234/"

# defaults:
f_upgrade=yes
EOF
exit
fi

if [ -f "$USER_CFG" ]; then
	. $USER_CFG
fi

# internal options, not to be overriden
specs=
df_fetch=no
upgrade_macros=no

die() {
	echo >&2 "$0: $*"
	exit 1
}

send_request() {
	# switch to mail mode, if no url set
	[ -z "$url" ] && send_mode="mail"

	case "$send_mode" in
	"mail")
		echo >&2 "* Sending using mail mode"
		cat - | $mailer
		;;
	*)
		echo >&2 "* Sending using http mode to $url"
		cat - | python -c '
import sys, socket, urllib2

try:
        data = sys.stdin.read()
        url = sys.argv[1]
        socket.setdefaulttimeout(10)
        req = urllib2.Request(url, data)
        f = urllib2.urlopen(req)
        f.close()
except Exception, e:
        print >> sys.stderr, "Problem while sending request via HTTP: %s: %s" % (url, e)
        sys.exit(1)
print >> sys.stdout, "Request queued via HTTP."
' "$url"
		;;
	esac
}

# simple df_fetcher, based on packages/fetchsrc_request
# TODO: tcp (smtp) mode
# TODO: adjust for ~/.requestrc config
df_fetch() {
	local specs="$@"

	# Sending by
	local MAILER='/usr/sbin/sendmail'
	# MAILER='/usr/bin/msmtp'
	# Sending via
	local VIA="SENDMAIL"
	#VIA="localhost"
	local VIA_ARGS=""
	#VIA_ARGS="some additional flags"
	# e.g. for msmtp:
	# VIA_ARGS='-a gmail'
	#
	# DISTFILES EMAIL
	local DMAIL="distfiles@pld-linux.org"

	local HOST=$(hostname -f)
	local LOGIN=${requester%@*}

	for spec in $specs; do
		local SPEC=$(echo "$spec" | sed -e 's|:.*||')
		local BRANCH=$(echo "$spec" | sed -e 's|.*:||')
		echo >&2 "Distfiles Request: $SPEC:$BRANCH via $MAILER ${VIA_ARGS:+ ($VIA_ARGS)}"
		cat <<-EOF | "$MAILER" -t -i $VIA_ARGS
			To: $DMAIL
			From: $LOGIN <$LOGIN@$HOST>
			Subject: fetchsrc_request notify
			X-CVS-Module: SPECS
			X-distfiles-request: yes
			X-Login: $LOGIN
			X-Spec: $SPEC
			X-Branch: $BRANCH
			X-Flags: force-reply

			.
			EOF
	done
}

usage() {
	cat <<EOF
Usage: make-request.sh [OPTION] ... [SPECFILE] ....

Mandatory arguments to long options are mandatory for short options too.

      -C, --config-file /path/to/config/file
            Source additional config file (after $USER_CFG), useful when
            when sending build requests to Ac/Th from the same account
      -b 'BUILDER BUILDER ...',  --builder='BUILDER BUILDER ...'
           Sends request to given builders (in 'version-arch' format)
      --with VALUE, --without VALUE
            Build package with(out) a given bcond
      --kernel VALUE
            set alt_kernel to VALUE
      --target VALUE
            set --target to VALUE
      -s BUILD_ID, --skip BUILD_ID[,BUILD_ID][,BUILD_ID]
            mark build ids on src builder to be skipped
      --branch VALUE
            specify default branch for specs in request
      -t, --test-build
            Performs a 'test-build'. Package will be uploaded to hidden .test-builds/
            ftp tree and won't be upgraded on builders.
      -r, --ready-build
            Preforms a 'ready' build. Package will be built and uploaded to test/ ftp tree
            (and later moved by release manager staff to ready/ and main ftp tree)
      -u, --upgrade
            Forces package upgrade (for use with -c or -q, not -t)
      -n, --no-upgrade
            Disables package upgrade (for use with -r)
      -ni, --no-install-br
            Do not install missing BuildRequires (--nodeps)
      -nd, --no-depend
            Do not add dependency of build jobs, each job in batch runs itself
      -j, --jobs
            Number of parallel jobs for single build
      -f, --flag
      -d, --distro DISTRO
            Specify value for \$distro
      -df,  --distfiles-fetch[-request] PACKAGE
            Send distfiles request to fetch sources for PACKAGE
      -cf, --command-flag
            Not yet documented
      -c, --command
            Executes a given command on builders
      --test-remove-pkg
            shortcut for --command poldek -evt ARGS
      --remove-pkg
            shortcut for --command poldek -ev --noask ARGS
      --upgrade-pkg
            shortcut for --command poldek --up -Uv ARGS
      --cvsup
            Updates builders infrastructure (outside chroot)
      --update-macros
            Updates rpm-build-macros on src builder
      -q
            shortcut for --command rpm -q ARGS
      -g, --gpg-opts "opts"
            Pass additional options to gpg binary
      -p, --priority VALUE
            sets request priority (default 2)
      -h, --help
            Displays this help message
EOF
	exit 0
}


while [ $# -gt 0 ] ; do
	case "$1" in
		--distro | -d)
			distro=$2
			shift
			;;

		--config-file | -C)
			[ -f $2 ] && . $2 || die "Config file not found"
			shift
			;;

		--builder | -b)
			builders="$builders $2"
			shift
			;;

		--with)
			with="$with $2"
			shift
			;;

		--without)
			without="$without $2"
			shift
			;;

		--test-build | -t)
			build_mode=test
			f_upgrade=no
			;;

		--kernel)
			kernel=$2
			shift
			;;

		--target)
			target=$2
			shift
			;;

		-s|--skip)
			skip="$2"
			shift
			;;

		--branch)
			branch=$2
			shift
			;;

		--priority | -p)
			priority=$2
			shift
			;;

		--ready-build | -r)
			build_mode=ready
			;;

		--upgrade | -u)
			f_upgrade=yes
			;;

		--no-upgrade | -n)
			f_upgrade=no
			;;

		--no-depend | -nd)
			no_depend=yes
			;;

		--no-install-br | -ni)
			flags="$flags no-install-br"
			;;

		-j | --jobs)
			jobs="$2"
			shift
			;;

		--flag | -f)
			flags="$flags $2"
			shift
			;;

		--command-flags | -cf)
			command_flags="$2"
			shift
			;;

		--command | -c)
			command="$2"
			if [ "$command" = - ]; then
				echo >&2 "Reading command from STDIN"
				echo >&2 "---"
				command=$(cat)
				echo >&2 "---"
			fi
			f_upgrade=no
			shift
			;;
		--test-remove-pkg)
			command="poldek -evt $2"
			f_upgrade=no
			shift
			;;
		--remove-pkg)
			command="for a in $2; do poldek -ev --noask \$a; done"
			f_upgrade=no
			shift
			;;
		--upgrade-pkg|-Uhv)
			command="poldek --up; poldek -uv $2"
			f_upgrade=no
			shift
			;;
		-q)
			command="rpm -q $2"
			f_upgrade=no
			shift
			;;

		--cvsup)
			command_flags="no-chroot"
			command="cvs up"
			f_upgrade=no
			;;

		--update-macros)
			upgrade_macros="yes"
			;;

		-df | --distfiles-fetch | --distfiles-fetch-request)
			df_fetch=yes
			;;

		--gpg-opts | -g)
			gpg_opts="$2"
			shift
			;;

		--help | -h)
			usage
			;;

		-*)
			die "unknown knob: $1"
			;;

		*:* | *)
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
	url="http://ep09.pld-linux.org:1289/"
	control_url="http://ep09.pld-linux.org/~buildsrc"
	;;
ac-java) # fake "distro" for java available ac architectures
	builder_email="builder-ac@pld-linux.org"
	default_builders="ac-i586 ac-i686 ac-athlon ac-amd64"
	default_branch="AC-branch"
	url="http://ep09.pld-linux.org:1289/"
	;;
ac-xen) # fake "distro" for xen-enabled architectures
	builder_email="builder-ac@pld-linux.org"
	default_builders="ac-i686 ac-athlon ac-amd64"
	default_branch="AC-branch"
	;;
ti)
	builder_email="builderti@ep09.pld-linux.org"
	default_builders="ti-*"
	url="http://ep09.pld-linux.org:1231/"
	control_url="http://ep09.pld-linux.org/~builderti"
	;;
ti-dev)
	builder_email="buildertidev@ep09.pld-linux.org"
	default_builders="ti-dev-*"
	url="http://ep09.pld-linux.org:1232/"
	control_url="http://ep09.pld-linux.org/~buildertidev"
	;;
th)
	builder_email="builderth@pld-linux.org"
	default_builders="th-*"
	url="http://src.th.pld-linux.org:1234/"
	control_url="http://src.th.pld-linux.org"
	;;
th-java) # fake "distro" for java available th architectures
	builder_email="builderth@pld-linux.org"
	default_builders="th-x86_64 th-athlon th-i686"
	url="http://src.th.pld-linux.org:1234/"
	;;
aidath)
	builder_email="builderaidath@ep09.pld-linux.org"
	default_builders="aidath-*"
	;;
*)
	die "distro \`$distro' not known"
	;;
esac

# need to do this after distro selection
if [ "$skip" ]; then
	skip=$(skip="$skip" control_url="$control_url" python -c '
import urllib2
import sys
import StringIO
import gzip
import re
import os
import string
from xml.dom import minidom

skip = os.environ.get("skip").split(",");
control_url = os.environ.get("control_url")

print >> sys.stderr, "* Check queue_id-s against %s" % control_url

try:
	headers = { "Cache-Control": "no-cache", "Pragma": "no-cache" }
	req = urllib2.Request(url=control_url + "/queue.gz", headers=headers)
	f = urllib2.urlopen(req)
except Exception, e:
	print >> sys.stderr, "Fetch error %s: %s" % (control_url + "/queue.gz", e)
	sys.exit(1)

sio = StringIO.StringIO()
sio.write(f.read())
f.close()
sio.seek(0)
f = gzip.GzipFile(fileobj = sio)

xml = re.compile("(<queue>.*?</queue>)", re.DOTALL).match(f.read()).group(1)
d = minidom.parseString(xml)

q = []
for c in d.documentElement.childNodes:
	if c.nodeName != "group":
		continue
	q.append(c.attributes["id"].value)

err = 0
for s in skip:
	if s not in q:
		print >> sys.stderr, "- Check %s: ERROR: Not valid queue-id" % s
		err = 1
	else:
		print >> sys.stderr, "- Check %s: OK" % s
if err == 1:
	sys.exit(1)
print string.join(skip, ",")
') || exit $?
	f_upgrade=no
	build_mode=test
	priority=-1
	command="skip:$skip"
	command_flags="no-chroot"
	builders="$distro-src"
fi

branch=${branch:-$default_branch}

specs=`for s in $specs; do
	case "$s" in
	^)
		# skip marker
		echo $s
		;;
	*.spec:*) # spec with branch
		basename $s
		;;
	*.spec) # spec without branch
		echo $(basename $s):$branch
		;;
	*:*) # package name with branch
		basename $s | sed -e 's/:/.spec:/'
		;;
	*) # just package name
		echo $(basename $s).spec:$branch
		;;
	esac
done`

if [ "$df_fetch" = "yes" ]; then
	df_fetch $specs
	exit 0
fi

if [ "$upgrade_macros" = "yes" ]; then
	command="poldek --up; poldek -uv rpm-build-macros"
	builders="$distro-src"
	f_upgrade=no
	build_mode=test
fi

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
	if [ -z "$command" ]; then
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
	echo >&2 "* Using priority $priority"
	echo "	<priority>$priority</priority>"
	if [ -n "$jobs" ]; then
		echo >&2 "* Using jobs $jobs"
		echo "	<maxjobs>$jobs</maxjobs>"
	fi
	echo >&2 "* Build mode: $build_mode"
	if [ -z "$url" ]; then
		echo >&2 "* Using email $builder_email"
	else
		echo >&2 "* Using URL $url"
	fi
	echo >&2 "* Queue-ID: $id"
	echo

	if [ "$command" != "" ] ; then
		bid=$(uuidgen)
		echo -E >&2 "* Command: $command"
		echo "	<batch id='$bid' depends-on=''>"
		echo "		 <command flags='$command_flags'>"
		echo -E "$command" | sed -e 's,&,\&amp;,g;s,<,\&lt;,g;s,>,\&gt;,g'
		echo "</command>"
		echo "		 <info></info>"
		local b
		for b in $builders; do
			echo >&2 "* Builder: $b"
			echo "		 <builder>$b</builder>"
		done
		echo "	</batch>"
	else

		if [ "$f_upgrade" = "yes" ] ; then
			echo >&2 "* Upgrade mode: $f_upgrade"
		fi

		# job to depend on
		local depend=
		local b i=1
		local name branch
		for b in $builders; do
			echo >&2 "* Builder: $b"
		done

		for s in $specs; do
			# skip marker
			if [ "$s" = "^" ] || [ "$no_depend" = yes ]; then
				depend=
				continue
			fi
			bid=$(uuidgen)
			echo "	<batch id='$bid' depends-on='$depend'>"

			name=$(echo "$s" | sed -e 's|:.*||')
			branch=$(echo "$s" | sed -e 's|.*:||')
			echo >&2 "* Adding #$i $name:$branch${kernel:+ alt_kernel=$kernel}${target:+ target=$target}${depend:+ depends on $depend}"
			echo "		 <spec>$name</spec>"
			echo "		 <branch>$branch</branch>"
			echo "		 ${kernel:+<kernel>$kernel</kernel>}"
			echo "		 ${target:+<target>$target</target>}"
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
				echo "		 <builder>$b</builder>"
			done
			echo "	</batch>"
			i=$((i+1))

			# let next job depend on previous
			depend=$bid
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

$(echo -E "$req" | gpg --clearsign --default-key $default_key $gpg_opts)
EOF
}

gen_email | send_request
