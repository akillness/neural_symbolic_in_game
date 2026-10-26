SHELL := /bin/sh

# Pin timestamps and PDF identifiers so identical sources rebuild byte-identically.
SOURCE_DATE_EPOCH ?= $(shell git -C ../.. log -1 --format=%ct 2>/dev/null || printf '0')
export SOURCE_DATE_EPOCH
export FORCE_SOURCE_DATE := 1
export TZ := UTC

NPC_PAPER_EVIDENCE_ROOT ?=
NPC_PAPER_EVIDENCE_ARG = $(if $(strip $(NPC_PAPER_EVIDENCE_ROOT)),--evidence-root "$(NPC_PAPER_EVIDENCE_ROOT)",)

.PHONY: all generated figures english korean supplements check clean

all: check

generated:
	cd ../.. && uv run python scripts/generate_paper_results.py
	cd ../.. && uv run python scripts/generate_npc_paper_results.py $(NPC_PAPER_EVIDENCE_ARG)
	cd ../.. && uv run python scripts/generate_disclosure_paper_results.py
	cd ../.. && uv run python scripts/generate_runtime_comparison_publication.py
	cd ../.. && uv run python scripts/run_kg_ontology_simulation.py --check --no-database

figures: generated
	cd ../.. && uv run python scripts/generate_paper_figures.py
	set -e; for svg in figures/*.svg; do \
		base="$${svg%.svg}"; \
		hash=$$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$$svg"); \
		rsvg-convert -f png -o "$$base.png.tmp" "$$svg"; \
		rsvg-convert -f eps -o "$$base.eps.tmp" "$$svg"; \
		printf '\n[ /Title (source-sha256:%s) /DOCINFO pdfmark\n' "$$hash" >> "$$base.eps.tmp"; \
		ps2pdf -dEPSCrop -dOmitInfoDate=true -dOmitID=true -dOmitXMP=true "$$base.eps.tmp" "$$base.pdf.tmp"; \
		mv "$$base.png.tmp" "$$base.png"; \
		mv "$$base.pdf.tmp" "$$base.pdf"; \
		rm -f "$$base.eps.tmp"; \
	done

english: figures
	cd en && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

korean: figures
	cd ko && latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex

supplements: generated
	cd en && latexmk -pdf -interaction=nonstopmode -halt-on-error traceability-supplement.tex
	cd ko && latexmk -xelatex -interaction=nonstopmode -halt-on-error traceability-supplement.tex

# Keep the project's fee-free full-paper target at 10 pages including references.
# Official guidance permits overlength papers with mandatory charges above 10:
# https://transactions.games/submit/submission-guidelines (checked 2026-10-26).
# Preserve proof and legibility; complete supplementary material is built separately.
check: english korean supplements
	@for lang in en ko; do \
		info=$$(pdfinfo "$$lang/main.pdf") || exit $$?; \
		pages=$$(printf '%s\n' "$$info" | awk '/^Pages:/ {print $$2}'); \
		case "$$pages" in ''|*[!0-9]*) echo "Cannot inspect $$lang/main.pdf page count"; exit 1;; esac; \
		if [ "$$pages" -lt 1 ] || [ "$$pages" -gt 10 ]; then \
			echo "$$lang/main.pdf is $$pages pages, above the 10-page project ceiling"; \
			exit 1; \
		fi; \
	done
	@for pdf in figures/*.pdf en/main.pdf ko/main.pdf en/traceability-supplement.pdf ko/traceability-supplement.pdf; do \
		fonts=$$(pdffonts "$$pdf") || exit $$?; \
		if [ "$$(printf '%s\n' "$$fonts" | awk 'NR > 2 && $$2 == "Type" && $$3 == "3" {count++} END {print count+0}')" != 0 ]; then \
			echo "$$pdf contains Type 3 fonts"; exit 1; \
		fi; \
	done
	@status=0; \
	grep -Eq 'Overfull|undefined references|undefined citations|Missing character|LaTeX Error' \
		en/main.log ko/main.log en/traceability-supplement.log ko/traceability-supplement.log || status=$$?; \
	case "$$status" in \
		1) ;; \
		0) echo "Paper logs contain forbidden diagnostics"; exit 1;; \
		*) echo "Paper log scan could not complete (status $$status)"; exit "$$status";; \
	esac

clean:
	cd en && latexmk -C
	cd ko && latexmk -C
