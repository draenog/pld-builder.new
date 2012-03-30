#!/bin/sh

case "$1" in
	longterm)
		cd ~/rpm/packages
		for a in dahdi-linux ipset iscsitarget lirc madwifi-ng open-vm-tools r8168 VirtualBox xorg-driver-video-nvidia xorg-driver-video-nvidia-legacy3 xtables-addons xorg-driver-video-fglrx openvswitch; do
			~/bin/send-last-th-tag.sh -d th --kernel longterm --without userspace $a/$a.spec
		done
		for a in e1000e igb; do
			./relup.sh -ui $a/$a.spec && make-request.sh -d th --kernel longterm $a.spec
		done
		;;
	head)
		cd ~/rpm/packages
		for a in dahdi-linux ipset iscsitarget lirc madwifi-ng open-vm-tools r8168 VirtualBox xorg-driver-video-nvidia xorg-driver-video-nvidia-legacy3 xtables-addons xorg-driver-video-fglrx; do
			./relup.sh -ui $a/$a.spec && make-request.sh -d th $a.spec
		done
		;;
	*)
		echo "UNKNOWN CRAP $1 !"
		;;
esac
