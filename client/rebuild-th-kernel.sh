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
	for pkg in $*; do
		echo >&2 "$pkg... "
		if [ ! -e  $pkg/$pkg.spec ]; then
			$rpmdir/builder -g $pkg -ns -r HEAD
		fi
		spec=$(autotag $pkg/$pkg.spec)
		echo >&2 "... $spec"
		echo $spec
	done
}

case "$1" in
	head)
		cd $rpmdir
		for pkg in $pkgs_head; do
			$rpmdir/builder -g $pkg -ns
			echo ./relup.sh -ui $a/$a.spec && make-request.sh -d th $a.spec
		done
		;;
	longterm)
		cd $rpmdir
		echo "Fetching package tags..."
		specs=$(get_last_tags $pkgs_longterm)
		set -x
		$dir/make-request.sh -r -d $dist --kernel longterm --without userspace $specs
#		for pkg in $pkgs_longterm_only; do
#			echo ./relup.sh -ui $a/$a.spec && make-request.sh -d th --kernel longterm $a.spec
#		done
		;;
	*)
		echo "UNKNOWN CRAP $1 !"
		;;
esac
