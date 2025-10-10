OUTPUT ?= $(shell basename "$(shell dirname "$(INPUT)")")
OUTPUT_DIRECTORY = $(shell pwd)/build
LATEXMK_ARGS ?= -f -file-line-error -shell-escape -logfilewarninglist -interaction=nonstopmode -halt-on-error -norc -pdflatex="xelatex %O %S" -pdfxe
TEXINPUTS = ""
TEXLIVE_RUN = TEXINPUTS=$(TEXINPUTS)
LATEXMK_COMMAND = $(TEXLIVE_RUN) latexmk $(LATEXMK_ARGS)

# Make does not offer a recursive wildcard function, so here's one:
rwildcard=$(wildcard $1$2) $(foreach d,$(wildcard $1*),$(call rwildcard,$d/,$2))

CST_DIR := out/cst
TEX_SOURCES := $(shell git ls-files 'src/**.tex')
CST_OUTPUTS := $(patsubst src/%.tex,$(CST_DIR)/%.scm,$(TEX_SOURCES))
CST_POSTPROCESS := scripts/postprocess_cst.py

.PHONY: ctfp ctfp-ocaml ctfp-scala ctfp-print ctfp-print-ocaml ctfp-print-scala lint cst cst-clean

ctfp:
	cd src; $(LATEXMK_COMMAND) -jobname=ctfp ctfp-reader.tex

ctfp-ocaml:
	cd src; $(LATEXMK_COMMAND) -jobname=ctfp-ocaml ctfp-reader-ocaml.tex

ctfp-scala:
	cd src; $(LATEXMK_COMMAND) -jobname=ctfp-scala ctfp-reader-scala.tex

ctfp-print:
	cd src; $(LATEXMK_COMMAND) -jobname=ctfp-print ctfp-print.tex

ctfp-print-ocaml:
	cd src; $(LATEXMK_COMMAND) -jobname=ctfp-print-ocaml ctfp-print-ocaml.tex

ctfp-print-scala:
	cd src; $(LATEXMK_COMMAND) -jobname=ctfp-print-scala ctfp-print-scala.tex

lint:
	$(foreach file, $(call rwildcard,$(shell dirname "$(INPUT)"),*.tex), latexindent -l -w $(file);)

cst: $(CST_OUTPUTS)

$(CST_DIR)/%.scm: src/%.tex
	@mkdir -p $(dir $@)
	@tmp=$$(mktemp); \
		err=$$(mktemp); \
		log="$(patsubst %.scm,%.err,$@)"; \
	if tree-sitter parse $< > $$tmp 2> $$err; then \
		mv $$tmp $@; \
		rm -f $$err $$log; \
	else \
		status=$$?; \
		if [ $$status -eq 1 ]; then \
			python3 $(CST_POSTPROCESS) $< $$tmp $@ $$log $$err; \
			rm -f $$tmp $$err; \
			echo "tree-sitter parse reported recoverable errors in $< (see $$log)" >&2; \
		else \
			cat $$err >&2; \
			rm -f $$tmp $$err $$log; \
			exit $$status; \
		fi; \
	fi

cst-clean:
	rm -rf $(CST_DIR)

