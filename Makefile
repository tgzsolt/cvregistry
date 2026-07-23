# cvregistry — build CV PDFs from markdown.
#
#   make cv                      # prompts for the CV name
#   make cv NAME=tar_gabor_zsolt # non-interactive
#   make build                   # every CV under cvs/
#   make clean                   # remove generated PDFs
#
# PYTHON defaults to the .venv virtualenv when present, else python3.
# Override with e.g.  make cv PYTHON=python3

PYTHON ?= $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)

# macOS/Homebrew: let WeasyPrint find pango/cairo. Set on the command line
# (not `export`) because macOS SIP strips DYLD_* from make's environment before
# it reaches the recipe. Harmless on Linux, where DYLD_* is ignored.
LIBPATH ?= /opt/homebrew/lib:/usr/local/lib
RUN = DYLD_FALLBACK_LIBRARY_PATH="$(LIBPATH):$$DYLD_FALLBACK_LIBRARY_PATH" $(PYTHON)

.PHONY: cv build clean help

help:
	@echo "Targets:"
	@echo "  make cv [NAME=<name>]  generate PDFs from cvs/<name>/*.md (prompts if NAME unset)"
	@echo "  make build             generate PDFs for every CV under cvs/"
	@echo "  make clean             remove generated PDFs from build/"

cv:
	@name="$(NAME)"; \
	if [ -z "$$name" ]; then \
		printf 'CV name (cvs/<name>/): '; read -r name; \
	fi; \
	dir="cvs/$$name"; \
	if [ ! -d "$$dir" ]; then \
		echo "Error: directory '$$dir' not found" >&2; exit 1; \
	fi; \
	files=$$(ls "$$dir"/*.md 2>/dev/null); \
	if [ -z "$$files" ]; then \
		echo "Error: no .md files in '$$dir'" >&2; exit 1; \
	fi; \
	$(RUN) src/generate.py $$files

build:
	$(RUN) src/generate.py

clean:
	rm -f build/*.pdf
