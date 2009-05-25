PACKAGE		:= pld-builder
VERSION		:= 0.4
SNAP		:= $(shell date +%Y%m%d)

# for make dist
CVSROOT		:= :pserver:cvs@cvs.pld-linux.org:/cvsroot
CVSMODULE	:= pld-builder.new
CVSTAG		:= HEAD

all:
	python -c "import compileall; compileall.compile_dir('.')"

clean:
	find -name '*.pyc' | xargs rm -f

dist:
	rm -rf $(PACKAGE)-$(VERSION).$(SNAP)
	mkdir -p $(PACKAGE)-$(VERSION).$(SNAP)
	cvs -d $(CVSROOT) export -d $(PACKAGE)-$(VERSION).$(SNAP) -r $(CVSTAG) $(CVSMODULE)
	tar -cjf $(PACKAGE)-$(VERSION).$(SNAP).tar.bz2 $(PACKAGE)-$(VERSION).$(SNAP)
	rm -rf $(PACKAGE)-$(VERSION).$(SNAP)
