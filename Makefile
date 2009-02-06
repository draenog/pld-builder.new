PACKAGE		:= pld-builder
VERSION		:= 0.3

# for make dist
CVSROOT		:= :pserver:cvs@cvs.pld-linux.org:/cvsroot
CVSMODULE	:= pld-builder.new
CVSTAG		:= HEAD

all:
	python -c "import compileall; compileall.compile_dir('.')"

clean:
	find -name '*.pyc' | xargs rm -f

dist:
	rm -rf $(PACKAGE)-$(VERSION)
	mkdir -p $(PACKAGE)-$(VERSION)
	cvs -d $(CVSROOT) export -d $(PACKAGE)-$(VERSION) -r $(CVSTAG) $(CVSMODULE)
	tar -cjf $(PACKAGE)-$(VERSION).tar.bz2 $(PACKAGE)-$(VERSION)
	rm -rf $(PACKAGE)-$(VERSION)
