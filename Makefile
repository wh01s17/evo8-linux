PREFIX      ?= $(HOME)/.local
CONFIG      ?= $(HOME)/.config
REPO        := $(abspath .)

.PHONY: install uninstall udev test

# Development install: the launcher runs the package straight from this
# checkout, and the PipeWire config is linked, so edits apply without
# reinstalling.
# A config dir that is itself a symlink (stow folds whole directories) is
# unfolded into a real directory of per-file links first, so our links never
# land inside someone else's tree.
UNFOLD = d="$(1)"; if [ -L "$$d" ]; then t=$$(readlink -f "$$d"); rm "$$d"; mkdir -p "$$d"; \
	for f in "$$t"/* "$$t"/.[!.]*; do [ -e "$$f" ] && ln -s "$$f" "$$d/"; done; fi; mkdir -p "$$d"

install:
	install -d $(PREFIX)/bin
	@$(call UNFOLD,$(CONFIG)/pipewire/pipewire.conf.d)
	@$(call UNFOLD,$(CONFIG)/pipewire/pipewire-pulse.conf.d)
	printf '#!/bin/sh\nPYTHONPATH="$(REPO)/src$${PYTHONPATH:+:$$PYTHONPATH}" exec python3 -m evo8.cli "$$@"\n' > $(PREFIX)/bin/evoctl
	printf '#!/bin/sh\nPYTHONPATH="$(REPO)/src$${PYTHONPATH:+:$$PYTHONPATH}" exec python3 -m evo8.gui.app "$$@"\n' > $(PREFIX)/bin/evo8-mixer
	chmod +x $(PREFIX)/bin/evoctl $(PREFIX)/bin/evo8-mixer
	@$(call UNFOLD,$(CONFIG)/systemd/user)
	install -m 644 src/evo8/data/systemd/evo8-restore.service $(CONFIG)/systemd/user/evo8-restore.service
	-systemctl --user daemon-reload
	install -d $(PREFIX)/share/applications
	install -m 644 src/evo8/data/applications/evo8-mixer.desktop $(PREFIX)/share/applications/evo8-mixer.desktop
	install -Dm644 src/evo8/data/evo8-mixer.svg $(PREFIX)/share/icons/hicolor/scalable/apps/evo8-mixer.svg
	-gtk-update-icon-cache -q $(PREFIX)/share/icons/hicolor 2>/dev/null
	ln -sfn $(REPO)/src/evo8/data/pipewire/pipewire.conf.d/20-mezcla.conf $(CONFIG)/pipewire/pipewire.conf.d/20-mezcla.conf
	ln -sfn $(REPO)/src/evo8/data/pipewire/pipewire-pulse.conf.d/20-bloquear-volumen-micro.conf $(CONFIG)/pipewire/pipewire-pulse.conf.d/20-bloquear-volumen-micro.conf

uninstall:
	rm -f $(PREFIX)/bin/evoctl $(PREFIX)/bin/evo8-mixer $(PREFIX)/share/applications/evo8-mixer.desktop
	rm -f $(PREFIX)/share/icons/hicolor/scalable/apps/evo8-mixer.svg
	rm -f $(CONFIG)/systemd/user/evo8-restore.service
	rm -f $(CONFIG)/pipewire/pipewire.conf.d/20-mezcla.conf
	rm -f $(CONFIG)/pipewire/pipewire-pulse.conf.d/20-bloquear-volumen-micro.conf

udev:
	install -m 644 src/evo8/data/udev/70-audient-evo8.rules /etc/udev/rules.d/70-audient-evo8.rules
	udevadm control --reload
	udevadm trigger --subsystem-match=usb

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v
