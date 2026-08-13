SHELL := /bin/sh

.PHONY: all figures english korean check clean

all: figures english korean check

figures:
	cd ../.. && uv run python scripts/generate_paper_figures.py
	for svg in figures/*.svg; do \
		rsvg-convert -f png -o "$${svg%.svg}.png" "$$svg"; \
		magick "$${svg%.svg}.png" -units PixelsPerInch -density 144 "$${svg%.svg}.pdf"; \
	done

english: figures
	cd en && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

korean: figures
	cd ko && latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex

# IEEE ToG Short Paper band is 6-8 pages, with overlength charges above 6 and the count
# including references (source: transactions.games author information, retrieved 2026-08-13).
# Assert the band rather than a fixed count so a legibility fix cannot silently push the
# paper out of its article type; anything above 6 is in-band but billable.
check:
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
