# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

from config import config, init_conf

def handle_src():
    print config.arch

def handle_bin():
    print config.arch

if __name__ == '__main__':
    init_conf()
    bb=config.binary_builders[:]
    if config.src_builder:
        try:
            init_conf(config.src_builder)
        except:
            pass
        else:
            handle_src()
    for b in bb:
        try:
            init_conf(b)
        except:
            continue
        else:
            handle_bin()

