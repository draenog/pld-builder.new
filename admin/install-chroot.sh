#!/bin/sh

die () {
  echo "$0: $*" 1>&2
  cat 1>&2 <<EOF
USAGE: $0 name1=val2 name2=val2 ...

Variables:
  chroot_type=src or chroot_type=bin 	 (required)
  chroot_dir=/path/to/chroot 		 (required)
  dist_url=ftp://ftp.nest.pld-linux.org/ (required)
  arch=i386 				 (required)
  cvs_root=:pserver:<user>:<password>@<host>:<cvsroot>
  					 (required in src builder)
  builder_uid=2000 			 (optional, uid of builder user 
  					  in chroot)
EOF
  exit 1
}

default_config () {
  builder_pkgs="rpm-build poldek shadow net-tools which"
  builder_uid=2000

  case "$chroot_type" in
  src )
    builder_arch_pkgs="cvs wget rpm-perlprov rpm-php-pearprov rpm-pythonprov"
    ;;
  bin )
    builder_arch_pkgs=""
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

eval "$*" || usage
default_config
eval "$*"
check_conf

poldek_src () {
  if test "$1" ; then
    echo "source = local,pri=1 /spools/ready/"
  fi
  cat <<EOF
source = main-test,noauto,pri=2 $dist_url/test/$arch/
source = main-ready,pri=3 $dist_url/ready/$arch/
source = main-ug,pri=4 $dist_url/updates/general/$arch/
source = main-us,pri=5 $dist_url/updates/security/$arch/
source = main,pri=6 $dist_url/PLD/$arch/PLD/RPMS/
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
poldek --conf poldek.conf --mkdir --install-dist $chroot_dir \
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
chr "useradd -c 'PLD $chroot_name builder' -d /home/users/builder -m -g users -s /bin/sh builder"
chr "cat > /etc/resolv.conf" < /etc/resolv.conf
chr "cat > /etc/mtab" < /dev/null
chr "mkdir -p /spools/ready/" < /dev/null

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
EOF
  chb "sh" < install-bt
  rm install-bt
}

case $chroot_type in
  src )
    install_SPECS_builder
    ;;
  bin )
    install_build_tree
    ;;
esac
