OUTPUT ?= $(shell basename "$(shell dirname "$(INPUT)")")
OUTPUT_DIRECTORY = $(shell pwd)/build
LATEXMK_ARGS ?= -f -file-line-error -shell-escape -logfilewarninglist -interaction=nonstopmode -halt-on-error -norc -pdflatex="xelatex %O %S" -pdfxe
TEXINPUTS = ""
TEXLIVE_RUN = TEXINPUTS=$(TEXINPUTS)
LATEXMK_COMMAND = $(TEXLIVE_RUN) latexmk $(LATEXMK_ARGS)
UV ?= uv
CTFP_PARSE = $(UV) run --package ctfp-latex-tools ctfp-parse

ASCIIDOC_ROOT = src/content
ASCIIDOC_OUTPUT_DIR = out/asciidoc
ASCIIDOC_SNIPPET_LANGUAGE ?= ocaml
ASCIIDOC_FORMAT ?= asciidoc
ASCIIDOC_CHAPTERS = \
	0.0 \
	1.1 1.2 1.3 1.4 1.5 1.6 1.7 1.8 1.9 1.10 \
	2.1 2.2 2.3 2.4 2.5 2.6 \
	3.1 3.2 3.3 3.4 3.5 3.6 3.7 3.8 3.9 3.10 3.11 3.12 3.13 3.14 3.15
ASCIIDOC_TARGETS = $(addprefix $(ASCIIDOC_OUTPUT_DIR)/,$(addsuffix .adoc,$(ASCIIDOC_CHAPTERS)))
ASCIIDOC_TARGET_ALIASES = $(addprefix asciidoc-,$(ASCIIDOC_CHAPTERS))

# Make does not offer a recursive wildcard function, so here's one:
rwildcard=$(wildcard $1$2) $(foreach d,$(wildcard $1*),$(call rwildcard,$d/,$2))

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

.PHONY: asciidoc asciidoc-clean $(ASCIIDOC_TARGET_ALIASES) ctfp-html

asciidoc: $(ASCIIDOC_TARGETS)

asciidoc-clean:
	rm -f $(ASCIIDOC_OUTPUT_DIR)/*.adoc

$(foreach chapter,$(ASCIIDOC_CHAPTERS),$(eval asciidoc-$(chapter): $(ASCIIDOC_OUTPUT_DIR)/$(chapter).adoc))

.SECONDEXPANSION:
$(ASCIIDOC_OUTPUT_DIR)/%.adoc: $$(call rwildcard,$(ASCIIDOC_ROOT)/%/,*)
	@mkdir -p $(dir $@)
	$(CTFP_PARSE) --root $(ASCIIDOC_ROOT)/$*/ --expand-snippet-language $(ASCIIDOC_SNIPPET_LANGUAGE) --format $(ASCIIDOC_FORMAT) --output $@

ctfp-html: asciidoc
	$(UV) run asciidoctor -r asciidoctor-diagram -a pdflatex=/usr/local/texlive/2025/bin/x86_64-linux/xelatex -a data-uri -a mathjax -a 'stem=latexmath' -a 'source-highlighter=pygments' -a 'pygments-style=github' -a nocache -o out/html/ctfp.html src/ctfp.adoc
