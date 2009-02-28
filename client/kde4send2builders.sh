#!/bin/bash
# author: Bartosz �wi�tek (shadzik@pld-linux.org)
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
	echo "  -h   --help"
	echo "     show this help"
	echo ""
	echo "Choose SPECS out of:"
	echo ""
	echo "all - all kde4-* (libs, base, other, koffice)"
	echo "libs - kde4-kdelibs and kde4-kdepimlibs"
	echo "base - kde4-kdebase*"
	echo "other - all other kde4-* except libs and base"
	echo "koffice - kde4-koffice"
	echo "almost-all - all but koffice"
	echo ""
	exit 0
}

DIST=
ATAG=no
SENDPRIO=

LIBS="kde4-kdelibs.spec kde4-kdepimlibs.spec"
BASE="kde4-kdebase-runtime.spec kde4-kdebase-workspace.spec kde4-kdebase.spec"
OTHER="kde4-kdemultimedia.spec kde4-kdegraphics.spec \
kde4-kdenetwork.spec \
kde4-kdeplasma-addons.spec \
kde4-kdepim.spec \
kde4-kdeadmin.spec \
kde4-kdeartwork.spec \
kde4-kdegames.spec \
kde4-kdewebdev.spec \
kde4-kdeutils.spec \
kde4-kdeedu.spec \
kde4-kdesdk.spec \
kde4-kdebindings.spec"
KOFFICE="kde4-koffice.spec"

while [ $# -gt 0 ]; do
	case "$1" in
		--distro | -d )
			DIST=$2
			shift
			;;

		--with-auto-tag | -at )
			ATAG=yes
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
                echo $LIBS $BASE $OTHER $KOFFICE
                ;;
        libs) # kde4 libs and pimlibs
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
        almost-all) # all but koffice
                echo $LIBS $BASE $OTHER
                ;;
        *) # not listed ones
                echo $s
                ;;
        esac
done`


if [ "$ATAG" == "yes" ]; then
	for spec in $specs; do
		LAST_AUTOTAG=$(cvs status -v SPECS/$spec |grep auto-$DIST |head -1 |awk '{print $1}')
		SENDPRIO+="$spec:$LAST_AUTOTAG "
	done
else
	SENDPRIO=$specs
fi


./pld-builder.new/client/make-request.sh -d $DIST -r $SENDPRIO
