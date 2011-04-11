#!/bin/sh

DIST="th"
DISTTAG="PLD 3.0 (Th)"

die () {
  echo "$0: $*" 1>&2
  cat 1>&2 <<EOF
USAGE: $0 name1=val2 name2=val2 ...

Variables:
  chroot_type=src or chroot_type=bin 	 (required)
  chroot_dir=/path/to/chroot 		 (required)
  arch=i386 				 (required)
  cvs_root=:pserver:<user>:<password>@<host>:<cvsroot>
  					 (required in src builder)
  builder_uid=2000 			 (optional, uid of builder user 
  					  in chroot; defaults to current uid)
EOF
  exit 1
}

default_config () {
  builder_pkgs="rpm-build poldek pwdutils net-tools which rpm-perlprov rpm-php-pearprov rpm-pythonprov bash vim"
  builder_uid=`id -u`
  dist_url="ftp://ftp.$DIST.pld-linux.org"

  case "$chroot_type" in
  src )
    builder_arch_pkgs="cvs wget"
    ;;
  bin )
    builder_arch_pkgs="mount"
    ;;
  esac
}

check_conf () {
  test "$chroot_dir" || die "no chroot_dir"
  test "$arch" || die "no arch"
  test "$dist_url" || die "no dist_url"
  
  case "$chroot_type" in
  src )
    test "$cvs_root" || die "no cvs_root"
    ;;
  bin )
    ;;
  * )
    die "evil chroot_type: $chroot_type"
    ;;
  esac
}

poldek_src () {
  if test "$1" ; then
    echo "source = local,pri=1 /spools/ready/"
  fi
  cat <<EOF
source = main-test,noauto,pri=2 $dist_url/dists/$DIST/test/$arch/RPMS/
source = main-test,noauto,pri=2 $dist_url/dists/$DIST/test/noarch/RPMS/
#source = main-ready,pri=3 $dist_url/dists/$DIST/ready/$arch/RPMS/
#source = main-ug,pri=4 $dist_url/dists/$DIST/updates-general/$arch/RPMS/
#source = main-us,pri=5 $dist_url/dists/$DIST/updates-security/$arch/RPMS/
source = main,pri=6 $dist_url/dists/$DIST/PLD/$arch/RPMS/
source = main,pri=6 $dist_url/dists/$DIST/PLD/noarch/RPMS/
EOF
}

common_poldek_opt () {
  cat <<EOF
particle_install = no
greedy = yes
rpmdef = _excludedocs 1
EOF
}

chr() {
  sudo chroot $chroot_dir su - root -c "$*"
}

chb() {
  sudo chroot $chroot_dir su - builder -c "$*"
}

install_SPECS_builder () {
  cat >install-specs <<EOF
set -x
rm -rf rpm
mkdir rpm
cvs -d $cvs_root login
cd rpm
cvs -d $cvs_root co SPECS/builder
cvs -d $cvs_root co SOURCES/.cvsignore
mkdir SRPMS RPMS BUILD
cd SPECS
cvs up additional-md5sums mirrors
echo "%packager       PLD bug tracking system ( http://bugs.pld-linux.org/ )">~/.rpmmacros
echo "%vendor         PLD">>~/.rpmmacros
echo "%distribution   $DISTTAG">>~/.rpmmacros
EOF
  chb "sh" < install-specs
  rm install-specs
}

install_build_tree () {
  cat >install-bt <<EOF
set -x
rm -rf rpm
mkdir rpm
cd rpm
mkdir SPECS SOURCES SRPMS RPMS BUILD
echo "%packager       PLD bug tracking system ( http://bugs.pld-linux.org/ )">~/.rpmmacros
echo "%vendor         PLD">>~/.rpmmacros
echo "%distribution   $DISTTAG">>~/.rpmmacros
EOF
  chb "sh" < install-bt
  rm install-bt
}




eval "$*" || usage
default_config
eval "$*"
check_conf

rm -rf tmp-chroot
mkdir tmp-chroot
cd tmp-chroot

cat >poldek.conf <<EOF
$(poldek_src)
$(common_poldek_opt)
cachedir = $chroot_dir/spools/poldek
keep_downloads = no
EOF

cat > install-$chroot_name.sh <<EOF
#!/bin/sh
set -x
cd $PWD
rm -rf $chroot_dir
mkdir -p $chroot_dir/spools/poldek
mkdir $chroot_dir/dev
mknod $chroot_dir/dev/null -m 666 c 1 3
rpm --root $chroot_dir --initdb
poldek --root $chroot_dir -i\
	$builder_pkgs $builder_arch_pkgs
EOF
chmod 755 install-$chroot_name.sh

echo "About to remove '$chroot_dir' and install it again, using"
echo "install-$chroot_name.sh:"
echo 
cat install-$chroot_name.sh
echo 
cat <<EOF
what to do?
  r) the script was already ran; continue,
  s) run it using sudo, 
  a) abort"
EOF
echo -n "[r/s/a]: "
read ans
case "$ans" in
  r )
    ;;
  s )
    sudo ./install-$chroot_name.sh
    ;;
  * )
    echo "bye"
    exit 1
esac

chr "ldconfig"

echo "OK"
echo "installing conf..."
cat >poldek.conf <<EOF
$(poldek_src local)
$(common_poldek_opt)
cachedir = /spools/poldek
keep_downloads = no
EOF

chr "cat > /etc/poldek.conf" < poldek.conf
chr "useradd -u "$builder_uid" -c 'PLD $chroot_name builder' -d /home/users/builder -m -g users -s /bin/sh builder"
chr "cat > /etc/resolv.conf" < /etc/resolv.conf
chr "cat > /etc/mtab" < /dev/null
chr "mkdir -p /spools/ready/" < /dev/null
chr "mkdir -p /spools/poldek/" < /dev/null
chr "sed -e 's,^\(root:.*\)/bin/sh$,\1/bin/bash,' -i~ /etc/passwd"


case $chroot_type in
  src )
    install_SPECS_builder
    ;;
  bin )
    install_build_tree
    ;;
esac
