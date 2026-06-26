# ADL Lite Coq formalisation Makefile
# Regenerates Makefile.coq from _CoqProject if needed, then delegates.

COQ_MAKEFILE ?= coq_makefile
COQPROJECT   := _CoqProject
GENERATED    := Makefile.coq

all: $(GENERATED)
	$(MAKE) -f $(GENERATED) all

$(GENERATED): $(COQPROJECT)
	$(COQ_MAKEFILE) -f $(COQPROJECT) -o $(GENERATED)

install: $(GENERATED)
	$(MAKE) -f $(GENERATED) install

clean: $(GENERATED)
	$(MAKE) -f $(GENERATED) clean
	$(RM) $(GENERATED) $(GENERATED).conf

html: $(GENERATED)
	$(MAKE) -f $(GENERATED) html

.PHONY: all install clean html
