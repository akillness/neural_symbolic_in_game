SHELL := /bin/sh

# Pin timestamps and PDF identifiers so identical sources rebuild byte-identically.
SOURCE_DATE_EPOCH ?= $(shell git -C ../.. log -1 --format=%ct 2>/dev/null || printf '0')
export SOURCE_DATE_EPOCH
export FORCE_SOURCE_DATE := 1
export TZ := UTC

.PHONY: all generated figures english korean check clean

all: check

generated:
	cd ../.. && uv run python scripts/generate_paper_results.py
	cd ../.. && uv run python scripts/run_kg_ontology_simulation.py --check --no-database

figures: generated
	cd ../.. && uv run python scripts/generate_paper_figures.py
	for svg in figures/*.svg; do \
		base="$${svg%.svg}"; \
		hash=$$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$$svg"); \
		rsvg-convert -f png -o "$$base.png" "$$svg"; \
		rsvg-convert -f eps -o "$$base.eps.tmp" "$$svg"; \
		printf '\n[ /Title (source-sha256:%s) /DOCINFO pdfmark\n' "$$hash" >> "$$base.eps.tmp"; \
		ps2pdf -dEPSCrop -dOmitInfoDate=true -dOmitID=true -dOmitXMP=true "$$base.eps.tmp" "$$base.pdf"; \
		rm -f "$$base.eps.tmp"; \
	done

english: figures
	cd en && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

korean: figures
	cd ko && latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex

# IEEE ToG Short Paper band is 6-8 pages, with overlength charges above 6 and the count
# including references (source: transactions.games author information, retrieved 2026-08-13).
# Assert the band rather than a fixed count so a legibility fix cannot silently push the
# paper out of its article type; anything above 6 is in-band but billable.
check: english korean
	@for lang in en ko; do \
		pages=$$(pdfinfo $$lang/main.pdf | awk '/^Pages:/ {print $$2}'); \
		if [ "$$pages" -lt 6 ] || [ "$$pages" -gt 8 ]; then \
			echo "$$lang/main.pdf is $$pages pages, outside the 6-8 short-paper band"; \
			exit 1; \
		fi; \
	done
	@for pdf in figures/*.pdf; do \
		test "$$(pdffonts "$$pdf" | awk 'NR > 2 && $$2 == "Type" && $$3 == "3" {count++} END {print count+0}')" = 0; \
	done
	@test "$$(pdffonts en/main.pdf | awk 'NR > 2 && $$2 == "Type" && $$3 == "3" {count++} END {print count+0}')" = 0
	@test "$$(pdffonts ko/main.pdf | awk 'NR > 2 && $$2 == "Type" && $$3 == "3" {count++} END {print count+0}')" = 0
	@! grep -Eq 'Overfull|undefined references|undefined citations|Missing character|LaTeX Error' en/main.log ko/main.log

clean:
	cd en && latexmk -C
	cd ko && latexmk -C
