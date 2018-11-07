SED = sed
TAR = tar
GIT = git

PACKAGE = ldapper
VERSION = $(shell git describe --abbrev=0 --tags)
RELEASE = 1
OS_MAJOR_VERSION = $(shell lsb_release -rs | cut -f1 -d.)
OS := rhel$(OS_MAJOR_VERSION)
DIST_DIR := dist/$(OS)
BUILDROOT := /srv/build/$(OS)

PYTHON = python
CREATEREPO_WORKERS=4
ifeq ($(OS),rhel7)
    YUMREPO_LOCATION=/fs/UMyumrepos/rhel7/stable/Packages/noarch
	CREATEREPO_WORKERS_CMD=--workers=$(CREATEREPO_WORKERS)
endif

REQUIRES := $(PYTHON),$(PYTHON)-ldap >= 2.4.15,$(PYTHON)-inflection

.PHONY: rpm
rpm:
	$(eval TEMPDIR := $(shell mktemp -d /tmp/tmp.XXXXX))
	mkdir -p $(TEMPDIR)/$(PACKAGE)-$(VERSION)
	$(GIT) clone . $(TEMPDIR)/$(PACKAGE)-$(VERSION)
	$(GIT) \
		--git-dir=$(TEMPDIR)/$(PACKAGE)-$(VERSION)/.git \
		--work-tree=$(TEMPDIR)/$(PACKAGE)-$(VERSION) \
		checkout tags/$(VERSION)
	$(TAR) -C $(TEMPDIR) --exclude .git -czf $(BUILDROOT)/SOURCES/$(PACKAGE)-$(VERSION).tar.gz $(PACKAGE)-$(VERSION)
	$(SED) "s/=VERSION=/$(VERSION)/" $(PACKAGE).spec > $(BUILDROOT)/SPECS/$(PACKAGE)-$(VERSION).spec
	rpmbuild -bb $(BUILDROOT)/SPECS/$(PACKAGE)-$(VERSION).spec --define "python ${PYTHON}"
	rm -rf $(TEMPDIR)

.PHONY: package
package:
	@echo ================================================================
	@echo cp /fs/UMbuild/$(PACKAGE)/dist/$(OS)/$(PACKAGE)-$(VERSION)-$(RELEASE).noarch.rpm $(YUMREPO_LOCATION)
	@echo "createrepo $(CREATEREPO_WORKERS_CMD) /fs/UMyumrepos/$(OS)/stable"

.PHONY: docs
docs:
	cd docs && make html && cd ..

.PHONY: build
build: rpm package

.PHONY: tag
tag:
	$(SED) -i 's/__version__ = .*/__version__ = "$(VERSION)"/g' $(PACKAGE)/__init__.py
	$(GIT) add $(PACKAGE)/__init__.py
	$(GIT) commit -m "Tagging $(VERSION)"
	$(GIT) tag -a $(VERSION) -m "Tagging $(VERSION)"

.PHONY: sdist
sdist:
	python setup.py sdist

.PHONY: clean
clean:
	rm -rf dist/
