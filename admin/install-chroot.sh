#!/bin/sh

# ------------------ functions
conf_dir="$HOME/pld-builder.new/config"

die () {
  echo "$0: $*" 1>&2
  exit 1
}

default_config () {
  builder_pkgs="rpm-build poldek shadow"
  spools_dir="/spools/"
  builder_uid=2000

  case "$1" in
  src* )
    builder_arch_pkgs="cvs wget rpm-perlprov rpm-php-pearprov rpm-pythonprov"
    ;;
  esac
}

load_config () {
  test -d $conf_dir || die "cannot find $conf_dir"
  test "$1" = "" && die "USAGE: $0 chroot-name"
  test -f $conf_dir/global || die "no global conf ($conf_dir/global)"
  test -f $conf_dir/$1 || die "no local conf ($conf_dir/$1)"
  
  default_config "$1"

  . $conf_dir/global
  . $conf_dir/$1

  test "$chroot_name" != "$1" && die "config is for '$chroot_name' not for '$1'"
}
# ------------------ end functions

load_config "$1"

poldek_src () {
  if test "$1" ; then
    echo "source = local,pri=1 $spools_dir/local-ready/"
  fi
  cat <<EOF
source = main-test,noauto,pri=2 $dist_url/test/$arch/
source = main-ready,pri=3 $dist_url/ready/$arch/
source = main-ug,pri=4 $dist_url/updates/general/$arch/
source = main-us,pri=5 $dist_url/updates/security/$arch/
source = main,pri=6 $dist_url/PLD/$arch/RPMS/
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
cachedir = $chroot_dir$spools_dir/poldek
keep_downloads = no
EOF

cat > install-$chroot_name.sh <<EOF
#!/bin/sh
set -x
cd $PWD
rm -rf $chroot_dir
mkdir -p $chroot_dir/$spools_dir/poldek
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
  r) run already run the script, 
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

echo "OK"
echo "installing conf..."
cat >poldek.conf <<EOF
$(poldek_src)
$(common_poldek_opt)
cachedir = $spools_dir/poldek
keep_downloads = yes
EOF

chr "cat > /etc/poldek.conf" < poldek.conf
chr "useradd -c 'PLD $chroot_name builder' -d /home/users/builder -m -g users -s /bin/sh builder"
chr "cat > /etc/resolv.conf" < /etc/resolv.conf
chr "cat > /etc/mtab" < /dev/null

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

case $chroot_name in
  src* )
    install_SPECS_builder
    ;;
  * )
    install_build_tree
    ;;
esac
