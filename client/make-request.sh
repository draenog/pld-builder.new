#!/bin/sh

# prevent "*" from being expanded in builders var
set -f

builders=
with=
without=
flags=
command=
command_flags=
gpg_opts=
default_branch='HEAD'
dist=
url=
no_depend=no
verbose=no
autotag=no

if [ -x /usr/bin/python ]; then
	send_mode="python"
else
	echo "No python present, using mail mode"
	send_mode="mail"
fi

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
dist=th
url="http://src.th.pld-linux.org:1234/"

# defaults:
f_upgrade=yes
EOF
exit
fi

if [ -f "$USER_CFG" ]; then
	. $USER_CFG
	# legacy fallback
	if [ "${distro:+set}" = "set" ]; then
		dist=$distro
	fi
fi

# internal options, not to be overriden
specs=
df_fetch=no
upgrade_macros=no

# Set colors
c_star=$(tput setaf 2)
c_red=$(tput setaf 1)
c_norm=$(tput op)
msg() {
	echo >&2 "${c_star}*${c_norm} $*"
}
red() {
	echo "${c_red}$*${c_norm}"
}

die() {
	echo >&2 "$0: $*"
	exit 1
}

send_request() {
	# switch to mail mode, if no url set
	[ -z "$url" ] && send_mode="mail"

	case "$send_mode" in
	"mail")
		msg "Sending using mail mode"
		cat - | $mailer
		;;
	*)
		msg "Sending using http mode to $url"
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

# autotag from rpm-build-macros
# displays latest used tag for a specfile
autotag() {
	local out s
	for s in "$@"; do
		# strip branches
		s=${s%:*}
		# ensure package ends with .spec
		s=${s%.spec}.spec
		local gitdir=$(dirname $s)/.git
		out=$(git --git-dir="$gitdir" for-each-ref --count=1 --sort=-authordate refs/tags/auto/$dist \
			--format='%(refname:short)')
		echo "$s:$out"
	done
}

# get autotag for specs
# WARNING: This may checkout some files from CVS
get_autotag() {
	local pkg spec rpmdir

	rpmdir=$(rpm -E %_topdir)
	cd $rpmdir
	for pkg in "$@"; do
		# strip branches
		pkg=${pkg%:*}
		# strip .spec extension
		pkg=${pkg%.spec}
		# checkout only if missing
		if [ ! -e $pkg/$pkg.spec ]; then
			$rpmdir/builder -g $pkg -ns -r HEAD 1>&2
		fi
		if [ ! -e $pkg/$pkg.spec ]; then
			# just print it out, to fallback to base pkg name
			echo "$pkg"
		else
			autotag $pkg/$pkg.spec
		fi
	done
}

usage() {
	cat <<EOF
Usage: make-request.sh [OPTION] ... [SPECFILE] ....

Mandatory arguments to long options are mandatory for short options too.

      --config-file /path/to/config/file
            Source additional config file (after $USER_CFG), useful when
            when sending build requests to Ac/Th from the same account
      -a
            Try to use latest auto-tag for the spec when building
            WARNING: This will checkout new files to your packages dir
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
      -d, --dist DISTRIBUTION_ID
            Specify value for \$dist
      -df,  --distfiles-fetch[-request] PACKAGE
            Send distfiles request to fetch sources for PACKAGE
      -cf, --command-flag
            Not yet documented
      -c, --command
            Executes a given command on builders (prepended to build jobs if build jobs included)
      -C, --post-command
            Executes a given command on builders (appended to build jobs if build jobs included)
      --test-remove-pkg
            shortcut for --command poldek -evt ARGS
      --remove-pkg
            shortcut for --command poldek -ev --noask ARGS
      --upgrade-pkg
            shortcut for --command poldek --up -Uv ARGS
      --pull
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

# validate distro, set $dist
set_dist() {
	case "$1" in
	ac)
		;;
	ac-java|ac-xen)
		;;
	ti)
		;;
	ti-dev)
		;;
	th)
		;;
	th-java)
		;;
	aidath)
		;;
	*)
		die "dist \`$1' not known"
		;;
	esac

	dist=$1
}

while [ $# -gt 0 ] ; do
	case "$1" in
		-d | --dist | --distro)
			set_dist $2
			shift
			;;

		--config-file)
			[ -f "$2" ] && . $2 || die "Config file not found"
			shift
			;;

		--builder | -b)
			for b in $2; do
				builders="$builders ${b%:*}"
			done
			shift
			;;

		-a)
			autotag=yes
			;;

		--with)
			with="$with $(echo "$2" | tr ',' ' ')"
			shift
			;;

		--without)
			without="$without $(echo "$2" | tr ',' ' ')"
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

		-j*)
			jobs="${1#-j}"
			;;

		-v)
			verbose=yes
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
			shift
			;;
		--post-command | -C)
			post_command="$2"
			if [ "$post_command" = - ]; then
				echo >&2 "Reading post_command from STDIN"
				echo >&2 "---"
				post_command=$(cat)
				echo >&2 "---"
			fi
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

		--pull)
			command_flags="no-chroot"
			command="git pull"
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

case "$dist" in
ac)
	builder_email="builder-ac@pld-linux.org"
	default_builders="ac-*"
	default_branch="AC-branch"
	url="http://ep09.pld-linux.org:1289/"
	control_url="http://ep09.pld-linux.org/~buildsrc"
	;;
ac-java) # fake "dist" for java available ac architectures
	builder_email="builder-ac@pld-linux.org"
	default_builders="ac-i586 ac-i686 ac-athlon ac-amd64"
	default_branch="AC-branch"
	url="http://ep09.pld-linux.org:1289/"
	;;
ac-xen) # fake "dist" for xen-enabled architectures
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
th-java) # fake "dist" for java available th architectures
	builder_email="builderth@pld-linux.org"
	default_builders="th-x86_64 th-athlon th-i686"
	url="http://src.th.pld-linux.org:1234/"
	;;
aidath)
	builder_email="builderaidath@ep09.pld-linux.org"
	default_builders="aidath-*"
	;;
*)
	die "dist \`$dist' not known"
	;;
esac

# need to do this after dist selection
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
	builders="$dist-src"
fi

branch=${branch:-$default_branch}

specs=`for s in $specs; do
	case "$s" in
	^)
		# skip marker - pass it along
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

if [ "$autotag" = "yes" ]; then
	msg "Auto autotag build enabled"
	specs=$(get_autotag $specs)
fi

if [ "$df_fetch" = "yes" ]; then
	df_fetch $specs
	exit 0
fi

if [ "$upgrade_macros" = "yes" ]; then
	command="poldek --up; poldek -uv rpm-build-macros"
	builders="$dist-src"
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

if [ -z "$specs" -a -z "$command" ]; then
	die "no packages to build or command to invoke specified"
fi

id=$(uuidgen)

gen_req() {
	echo "<group id='$id' no='0' flags='$flags'>"
	echo "	<time>$(date +%s)</time>"
	msg "Using priority $priority"
	echo "	<priority>$priority</priority>"
	if [ -n "$jobs" ]; then
		msg "Using jobs $jobs"
		echo "	<maxjobs>$jobs</maxjobs>"
	fi
	if [ -z "$url" ]; then
		msg "Using email $builder_email"
	else
		msg "Using URL $url"
	fi

	if [ "$build_mode" = "ready" ]; then
		msg "Build mode: $(tput setaf 2)$build_mode$c_norm"
	else
		msg "Build mode: $(tput setaf 3)$build_mode$c_norm"
	fi

	msg "Queue-ID: $id"
	echo

	# job to depend on
	local depend=
	local b i=1
	local name branch builders_xml

	for b in $builders; do
		msg "Builder: $(red $b)"
		builders_xml="$builders_xml <builder>$b</builder>"
	done

	if [ "$command" ]; then
		bid=$(uuidgen)
		echo -E >&2 "* Command: $command"
		echo "	<batch id='$bid' depends-on=''>"
		echo "		 <command flags='$command_flags'>"
		echo -E "$command" | sed -e 's,&,\&amp;,g;s,<,\&lt;,g;s,>,\&gt;,g'
		echo "</command>"
		echo "		 <info></info>"
		echo "$builders_xml"
		echo "	</batch>"
		depend=$bid
	fi

	if [ "$f_upgrade" = "yes" ] ; then
		msg "Upgrade mode: $f_upgrade"
	fi

	for s in $specs; do
		# skip marker
		if [ "$s" = "^" ]; then
			depend=
			continue
		fi
		if [ "$no_depend" = yes ]; then
			depend=
		fi
		bid=$(uuidgen)
		echo "	<batch id='$bid' depends-on='$depend'>"

		name=$(echo "$s" | sed -e 's|:.*||')
		branch=$(echo "$s" | sed -e 's|.*:||')
		msg "Adding #$i $name:$branch${kernel:+ alt_kernel=$kernel}${target:+ target=$target}${depend:+ depends on $depend}"
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
		echo "$builders_xml"
		echo "	</batch>"
		i=$((i+1))

		# let next job depend on previous
		depend=$bid
	done

	if [ "$post_command" ]; then
		bid=$(uuidgen)
		if [ "$no_depend" = yes ]; then
			depend=
		fi
		echo -E >&2 "* Post-Command: $post_command"
		echo "	<batch id='$bid' depends-on='$depend'>"
		echo "		 <command flags='$command_flags'>"
		echo -E "$post_command" | sed -e 's,&,\&amp;,g;s,<,\&lt;,g;s,>,\&gt;,g'
		echo "</command>"
		echo "		 <info></info>"
		echo "$builders_xml"
		echo "	</batch>"
		depend=$bid
	fi

	echo "</group>"
}

gen_email () {
	# make request first, so the STDERR/STDOUT streams won't be mixed
	local tmp req
	tmp=$(mktemp)
	gen_req > $tmp

	if [ "$verbose" = "yes" ]; then
		cat $tmp >&2
	fi

	cat <<-EOF
	From: $requester
	To: $builder_email
	Subject: build request
	Message-Id: <$id@$(hostname)>
	X-New-PLD-Builder: request
	X-Requester-Version: \$Id$

	EOF

	gpg --clearsign --default-key $default_key $gpg_opts --output=- $tmp
	rm -f $tmp
}

gen_email | send_request
