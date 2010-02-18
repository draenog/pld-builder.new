#!/bin/sh
# Authors:
# - Bartosz Świątek (shadzik@pld-linux.org)
# - Elan Ruusamäe (glen@pld-linux.org)
#
# helps sending kde4 specs in proper order with or without autotags

usage() {
	echo "Usage: $0 OPTIONS SPECS"
	echo ""
	echo "Where OPTIONS are:"
	echo ""
	echo "  -d   --distro VALUE"
	echo "     set distro, probably th or ti will fit the most"
	echo "  -at  --with-auto-tag"
	echo "     send with current autotag, default no"
	echo "  -b   --builder VALUE"
	echo "     choose a particular builder, default all"
	echo "  -p   --priority VALUE (default: 2)"
	echo "  -h   --help"
	echo "     show this help"
	echo ""
	echo "Choose SPECS out of:"
	echo ""
	echo "all - all kde4-* (libs, base, other, koffice, l10n)"
	echo "libs - kde4-kdelibs and kde4-kdepimlibs kde4-kdelibs-experimental"
	echo "base - kde4-kdebase* kde4-oxygen-icons"
	echo "other - all other kde4-* except libs and base"
	echo "koffice - kde4-koffice"
	echo "l10n - kde4-l10n"
	echo "almost-all - all but koffice and l10n"
	echo ""
	exit 0
}

DIST=
ATAG=no
SENDPRIO=
BUILDER=
PRIO=2
#SPECDIR=$(rpm -E %_specdir)
SPECDIR=~/rpm

LIBS="kde4-kdelibs.spec kde4-kdepimlibs.spec kde4-kdelibs-experimental.spec"
BASE="kde4-oxygen-icons.spec kde4-kdebase-runtime.spec kde4-kdebase-workspace.spec kde4-kdebase.spec"
OTHER="kde4-kdemultimedia.spec kde4-kdegraphics.spec \
kde4-kwebkitpart.spec \
kde4-kdenetwork.spec \
kde4-kdepim.spec \
kde4-kdepim-runtime.spec \
kde4-kdeartwork.spec \
kde4-kdegames.spec \
kde4-kdewebdev.spec \
kde4-kdeutils.spec \
kde4-kdeaccessibility \
kde4-kdeedu.spec \
kde4-kdeplasma-addons.spec \
kde4-kdesdk.spec \
kde4-kdebindings.spec \
kde4-kdeadmin.spec"
KOFFICE="kde4-koffice.spec"
L10N="kde4-l10n.spec"

while [ $# -gt 0 ]; do
	case "$1" in
		--distro | -d )
			DIST=$2
			shift
			;;

		--with-auto-tag | -at )
			ATAG=yes
			;;

		--builder | -b )
			BUILDER="$BUILDER $2"
			shift
			;;
		
		--priority | -p )
			PRIO=$2
			shift
			;;

		--help | -h )
			usage
			;;

		-* )
			die "Unknow option: $1"
			;;

		*:* | * )
			specs="$specs $1"
			;;
	esac
	shift
done

specs=`for s in $specs; do
	case "$s" in
	all) # all kde4 specs
			echo $LIBS $BASE $OTHER $KOFFICE $L10N
			;;
	libs) # kde4 libs, libs-experimental and pimlibs
			echo $LIBS
			;;
	base) # kde4-kdebase-*
			echo $BASE
			;;
	other) # kde4-*
			echo $OTHER
			;;
	koffice) # kde4-koffice
			echo $KOFFICE
			;;
	l10n) # kde4-l10n
			echo $L10N
			;;
	almost-all) # all but koffice and l10n
			echo $LIBS $BASE $OTHER
			;;
	*) # not listed ones
			echo $s
			;;
	esac
done`


if [ "$ATAG" == "yes" ]; then
	for spec in $specs; do
		PKG=$(echo $spec |sed -e 's/.spec//g')
		LAST_AUTOTAG=$(cd $SPECDIR/packages && ./builder -g -ns $PKG/$spec >/dev/null 2>&1 && cvs status -v $PKG/$spec | awk -vdist=$DIST '!/Sticky/ && $1 ~ "^auto-" dist "-"{if (!a++) print $1}')
		sleep 1
		SENDPRIO="$SENDPRIO $spec:$LAST_AUTOTAG "
	done
else
	SENDPRIO=$specs
fi

dir=$(dirname "$0")
exec $dir/make-request.sh ${DIST:+-d $DIST} ${BUILDER:+-b "$BUILDER"} -p $PRIO -r $SENDPRIO
echo >&2 "Failed to execute ./make-request.sh!"
exit 1
