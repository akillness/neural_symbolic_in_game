SHELL := /bin/sh

SOURCE_DATE_EPOCH ?= $(shell git -C ../../.. log -1 --format=%ct 2>/dev/null || printf '0')
export SOURCE_DATE_EPOCH
export FORCE_SOURCE_DATE := 1
export TZ := UTC

XELATEX_KO_VENUES := ieee-tog aiide ieee-cog neurips-db elsevier-kbs-ec
PDFLATEX_KO_VENUES := fdg aamas
VENUES := ieee-tog aiide fdg ieee-cog aamas neurips-db elsevier-kbs-ec

.PHONY: all check anonymous clean $(VENUES)

all: $(VENUES)

$(XELATEX_KO_VENUES):
	@echo "=== Building venue (EN pdflatex + KO xelatex): $@ ==="
	cd $@ && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
	cd $@ && latexmk -xelatex -interaction=nonstopmode -halt-on-error main_ko.tex

$(PDFLATEX_KO_VENUES):
	@echo "=== Building venue (EN pdflatex + KO pdflatex/kotex): $@ ==="
	cd $@ && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
	cd $@ && latexmk -pdf -interaction=nonstopmode -halt-on-error main_ko.tex

anonymous:
	@set -e; \
	for v in $(VENUES); do \
		echo "=== Building anonymous submission PDF: $$v ==="; \
		(cd "$$v" && pdflatex -interaction=nonstopmode -halt-on-error -jobname=main_anon '\def\ANONBUILD{}\input{main.tex}' >/dev/null && bibtex main_anon >/dev/null && pdflatex -interaction=nonstopmode -halt-on-error -jobname=main_anon '\def\ANONBUILD{}\input{main.tex}' >/dev/null && pdflatex -interaction=nonstopmode -halt-on-error -jobname=main_anon '\def\ANONBUILD{}\input{main.tex}' >/dev/null && if grep -q "Rerun to get cross-references right" main_anon.log; then pdflatex -interaction=nonstopmode -halt-on-error -jobname=main_anon '\def\ANONBUILD{}\input{main.tex}' >/dev/null; fi); \
	done

check: all
	@set -e; \
	for v in $(VENUES); do \
		for base in main main_ko; do \
			pdf="$$v/$$base.pdf"; \
			log="$$v/$$base.log"; \
			pages=$$(pdfinfo "$$pdf" | awk '/^Pages:/ {print $$2}'); \
			t3=$$(pdffonts "$$pdf" | awk 'NR > 2 && $$2 == "Type" && $$3 == "3" {c++} END {print c+0}'); \
			errs=$$(grep -Ec 'undefined references|undefined citations|Missing character|LaTeX Error|Fatal error' "$$log" || true); \
			overfull=$$(grep -Ec 'Overfull \\hbox' "$$log" || true); \
			printf "%-18s %-8s pages=%-3s type3=%-2s errs=%-2s overfull=%s\n" "$$v" "$$base" "$$pages" "$$t3" "$$errs" "$$overfull"; \
			test "$$t3" -eq 0; \
			test "$$errs" -eq 0; \
		done; \
	done

clean:
	@for v in $(XELATEX_KO_VENUES); do \
		(cd "$$v" && latexmk -C -pdf main.tex && latexmk -C -xelatex main_ko.tex && rm -f main_anon.*); \
	done
	@for v in $(PDFLATEX_KO_VENUES); do \
		(cd "$$v" && latexmk -C -pdf main.tex && latexmk -C -pdf main_ko.tex && rm -f main_anon.*); \
	done
