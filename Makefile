PREFIX ?= /usr
BINDIR ?= $(PREFIX)/bin
DATADIR ?= $(PREFIX)/share
MANDIR ?= $(DATADIR)/man/man1
COMPDIR ?= $(DATADIR)/bash-completion/completions
ZSHCOMPDIR ?= $(DATADIR)/zsh/site-functions
SYSTEMD_USER_DIR ?= $(PREFIX)/lib/systemd/user
PYTHON ?= python3

.PHONY: install uninstall deb repo clean

install:
	$(PYTHON) -m pip install --root=$(DESTDIR)/ --no-deps .
	install -Dm755 displayctl.sh $(DESTDIR)$(BINDIR)/displayctl
	install -Dm644 displayctl.1 $(DESTDIR)$(MANDIR)/displayctl.1
	install -Dm644 completions/bash/displayctl $(DESTDIR)$(COMPDIR)/displayctl
	install -Dm644 completions/zsh/_displayctl $(DESTDIR)$(ZSHCOMPDIR)/_displayctl
	install -Dm644 displayctl-watch.service $(DESTDIR)$(SYSTEMD_USER_DIR)/displayctl-watch.service
	gzip -f $(DESTDIR)$(MANDIR)/displayctl.1 2>/dev/null || true

uninstall:
	-$(PYTHON) -m pip uninstall -y displayctl 2>/dev/null || true
	-rm -f $(DESTDIR)$(BINDIR)/displayctl
	-rm -f $(DESTDIR)$(MANDIR)/displayctl.1.gz
	-rm -f $(DESTDIR)$(COMPDIR)/displayctl
	-rm -f $(DESTDIR)$(ZSHCOMPDIR)/_displayctl
	-rm -f $(DESTDIR)$(SYSTEMD_USER_DIR)/displayctl-watch.service

deb:
	scripts/build-deb.sh

repo:
	scripts/setup-apt-repo.sh

clean:
	rm -rf build/ dist/ *.egg-info/ .pybuild/
	rm -f debian/.debhelper/ debian/debhelper-build-stamp
	rm -f debian/displayctl.debhelper.log debian/files
	rm -rf debian/displayctl/
	rm -rf apt-repo/pool/ apt-repo/dists/
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
