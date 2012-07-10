#!/bin/sh
arg="$@"

specs=""
opt=""

for i in $arg; do
	case "$i" in
		*.spec)
		specs="$specs $1"
		shift
		;;
		*)
		opt="$opt $i"
		shift
		;;
	esac
done

for i in $specs; do
	dir=$(dirname $i)
	pkg=$(basename $i)
	cd $dir || exit 1
	specfile="$pkg"
	tag=$(cvs status -v $specfile |grep "th-" | head -n 1 | awk ' { print $1 } ')
	if [ -z "$tag" ]; then
		echo "Th tag not found for $specfile."
		continue
	fi
	echo "Rebuilding $i from tag $tag..."
	set -x
	make-request.sh -d th $opt $pkg:$tag
	set +x
done

