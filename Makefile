PREFIX      ?= $(HOME)/.local
CONFIG      ?= $(HOME)/.config
REPO        := $(abspath .)

.PHONY: install uninstall udev test

# Development install: the launcher runs the package straight from this
# checkout, and the PipeWire config is linked, so edits apply without
# reinstalling.
install:
	install -d $(PREFIX)/bin $(CONFIG)/pipewire/pipewire.conf.d $(CONFIG)/pipewire/pipewire-pulse.conf.d
	printf '#!/bin/sh\nPYTHONPATH="$(REPO)/src$${PYTHONPATH:+:$$PYTHONPATH}" exec python3 -m evo8.cli "$$@"\n' > $(PREFIX)/bin/evoctl
	chmod +x $(PREFIX)/bin/evoctl
	ln -sfn $(REPO)/config/pipewire/pipewire.conf.d/20-mezcla.conf $(CONFIG)/pipewire/pipewire.conf.d/20-mezcla.conf
	ln -sfn $(REPO)/config/pipewire/pipewire-pulse.conf.d/20-bloquear-volumen-micro.conf $(CONFIG)/pipewire/pipewire-pulse.conf.d/20-bloquear-volumen-micro.conf

uninstall:
	rm -f $(PREFIX)/bin/evoctl
	rm -f $(CONFIG)/pipewire/pipewire.conf.d/20-mezcla.conf
	rm -f $(CONFIG)/pipewire/pipewire-pulse.conf.d/20-bloquear-volumen-micro.conf

udev:
	install -m 644 udev/70-audient-evo8.rules /etc/udev/rules.d/70-audient-evo8.rules
	udevadm control --reload
	udevadm trigger --subsystem-match=usb

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v
