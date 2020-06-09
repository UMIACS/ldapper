PACKAGE = ldapper
PYTHON = python3

.PHONY: tag
tag:
	sed -i 's/__version__ = .*/__version__ = "$(VERSION)"/g' $(PACKAGE)/__init__.py
	git add $(PACKAGE)/__init__.py
	git commit -m "Tagging $(VERSION)"
	git tag -a $(VERSION) -m "Tagging $(VERSION)"

.PHONY: build
build: clean
	$(PYTHON) setup.py sdist bdist_wheel

.PHONY: upload
upload:
	twine upload dist/*

.PHONY: clean
clean:
	rm -rf dist/
