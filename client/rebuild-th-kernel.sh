#!/bin/sh

dir=$(cd "$(dirname "$0")"; pwd)
rpmdir=$(rpm -E %_topdir)
dist=th

pkgs_head="
	dahdi-linux
   	ipset
   	iscsitarget
   	lirc
   	madwifi-ng
   	open-vm-tools
   	r8168
   	VirtualBox
   	xorg-driver-video-nvidia
   	xorg-driver-video-nvidia-legacy3
   	xtables-addons
   	xorg-driver-video-fglrx
"

pkgs_longterm="
	$pkgs_head
	openvswitch
"
pkgs_longterm_only="
	e1000e
	igb
"

# autotag from rpm-build-macros
# displays latest used tag for a specfile
autotag() {
	local out s
	for s in "$@"; do
		# strip branches
		s=${s%:*}
		# ensure package ends with .spec
		s=${s%.spec}.spec
		out=$(cvs status -v $s | awk "!/Sticky/&&/auto-$dist-/{if (!a++) print \$1}")
		echo "$s:$out"
	done
}

get_last_tags() {
	local pkg spec

	echo >&2 "Fetching package tags: $*..."
	for pkg in "$@"; do
		echo >&2 "$pkg... "
		if [ ! -e $pkg/$pkg.spec ]; then
			$rpmdir/builder -g $pkg -ns -r HEAD 1>&2
		fi
		if [ ! -e $pkg/$pkg.spec ]; then
			# just print it out, to fallback to base pkg name
			echo "$pkg"
		else
			spec=$(autotag $pkg/$pkg.spec)
			echo >&2 "... $spec"
			echo $spec
		fi
	done
}

cd $rpmdir
case "$1" in
	head)
		for pkg in $pkgs_head; do
			$rpmdir/builder -g $pkg -ns
			echo ./relup.sh -ui $a/$a.spec && make-request.sh -d th $a.spec
		done
		;;
	longterm)
		cd $rpmdir
		specs=$(get_last_tags $pkgs_longterm)
		$dir/make-request.sh -r -d $dist --kernel longterm --without userspace $specs

		specs=$pkgs_longterm_only
		$dir/make-request.sh -r -d $dist --kernel longterm $specs
		;;
	*)
		# try to parse all args, filling them with last autotag
		while [ $# -gt 0 ]; do
			case "$1" in
			--kernel|--with|--without)
				args="$1 $2"
				shift
				;;
			-*)
				args="$args $1"
				;;
			*)
				specs="$specs $1"
				;;
			esac
			shift
		done
		specs=$(get_last_tags $specs)
		$dir/make-request.sh -r -d $dist $args $specs
		;;
esac
