all:
	python -c "import compileall; compileall.compile_dir('.')"

clean:
	find -name '*.pyc' | xargs rm -f
