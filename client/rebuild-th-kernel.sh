#!/bin/sh

dir=$(cd "$(dirname "$0")"; pwd)
rpmdir=$(rpm -E %_topdir)
dist=th

pkgs_head="
	dahdi-linux
	ipset
	lirc
	madwifi-ng
	open-vm-tools
	r8168
	VirtualBox
	xorg-driver-video-fglrx
	xorg-driver-video-nvidia
	xtables-addons
"

pkgs_longterm="
	e1000e
	igb
	iscsitarget
	openvswitch
	xorg-driver-video-nvidia-legacy3
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
			spec=${spec:#*/}
			echo >&2 "... $spec"
			echo $spec
		fi
	done
}

cd $rpmdir
case "$1" in
	head)
		for pkg in $pkgs_head; do
			echo >&2 "Rebuilding $pkg..."
			$rpmdir/builder -g $pkg -ns
			$rpmdir/relup.sh -ui $pkg/$pkg.spec && $dir/make-request.sh -r -d th $pkg.spec
		done
		;;
	longterm)
		cd $rpmdir
		for pkg in $pkgs_longterm; do
			echo >&2 "Rebuilding $pkg..."
			$rpmdir/builder -g $pkg -ns
			$rpmdir/relup.sh -ui $pkg/$pkg.spec && $dir/make-request.sh -r -d th --without kernel $pkg.spec
		done
		specs=$(get_last_tags $pkgs_head $pkgs_longterm)
		for pkg in $specs; do
			echo >&2 "Rebuilding $pkg..."
			$dir/make-request.sh -r -d $dist --kernel longterm --without userspace $pkg
		done
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
