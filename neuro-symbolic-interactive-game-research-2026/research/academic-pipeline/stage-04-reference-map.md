# Stage 4 IEEE Reference Map

Status: **citation database assembled; submission-time conditional checks remain**  
Audit date: 2026-08-12  
Canonical database: `paper/latex/references.bib`

## Verification policy

- Every approved Stage 2 source has one stable BibTeX key beginning with its `S01`--`S36` evidence ID.
- DOI metadata was checked against Crossref where a publisher DOI exists.
- DOI-free ICLR, NeurIPS 2021, and JMLR records use official proceedings or journal pages.
- Preprints and future/conditional records are explicitly labelled in the BibTeX `note` field.
- Unknown page ranges are omitted rather than inferred.
- The database preserves the distinction between evidence identity and citation order: IEEE numbering is assigned by first citation in the manuscript, not by the S-ID.

## S-ID to BibTeX key map

| S-ID | BibTeX key | Record class | Primary identity check | State |
| --- | --- | --- | --- | --- |
| S01 | `S01_vaucher2026ivie` | arXiv preprint / forthcoming | arXiv 2606.13348; ICCC 2026 non-archival pre-proceedings notice | PREPRINT-CONDITIONAL |
| S02 | `S02_figueiredo2025scaffolded` | arXiv preprint | arXiv 2510.25820 | PREPRINT |
| S03 | `S03_weir2024ontologically` | EMNLP 2024 | DOI 10.18653/v1/2024.emnlp-main.520 | VERIFIED |
| S04 | `S04_he2024gretriever` | NeurIPS 2024 | DOI 10.52202/079017-4224 | VERIFIED |
| S05 | `S05_gutierrez2024hipporag` | NeurIPS 2024 | DOI 10.52202/079017-1902 | VERIFIED |
| S06 | `S06_chhikara2025mem0` | ECAI 2025 | DOI 10.3233/FAIA251160 | VERIFIED-PAGES-OPEN |
| S07 | `S07_park2023generative` | UIST 2023 | DOI 10.1145/3586183.3606763 | VERIFIED |
| S08 | `S08_shao2023character` | EMNLP 2023 | DOI 10.18653/v1/2023.emnlp-main.814 | VERIFIED |
| S09 | `S09_geng2023grammar` | EMNLP 2023 | DOI 10.18653/v1/2023.emnlp-main.674 | VERIFIED |
| S10 | `S10_beurerkellner2023prompting` | PACMPL/PLDI 2023 | DOI 10.1145/3591300 | VERIFIED |
| S11 | `S11_cote2019textworld` | Springer book chapter | DOI 10.1007/978-3-030-24337-1_3 | VERIFIED |
| S12 | `S12_wang2022scienceworld` | EMNLP 2022 | DOI 10.18653/v1/2022.emnlp-main.775 | VERIFIED |
| S13 | `S13_fan2022minedojo` | NeurIPS 2022 | DOI 10.52202/068431-1333 | VERIFIED |
| S14 | `S14_perezliebana2019gvgai` | IEEE Transactions on Games | DOI 10.1109/TG.2019.2901021 | VERIFIED |
| S15 | `S15_liu2024agentbench` | ICLR 2024 | official ICLR proceedings/BibTeX | VERIFIED-NO-DOI |
| S16 | `S16_ma2024agentboard` | NeurIPS 2024 | DOI 10.52202/079017-2365 | VERIFIED |
| S17 | `S17_zhou2024sotopia` | ICLR 2024 | official ICLR proceedings/BibTeX | VERIFIED-NO-DOI |
| S18 | `S18_paglieri2025balrog` | ICLR 2025 | official ICLR proceedings/BibTeX | VERIFIED-NO-DOI |
| S19 | `S19_lepelletier2022playtesting` | AIIDE 2022 | DOI 10.1609/aiide.v18i1.21958 | VERIFIED |
| S20 | `S20_ashby2023personalized` | CHI 2023 | DOI 10.1145/3544548.3581441 | VERIFIED |
| S21 | `S21_akoury2023player` | Findings EMNLP 2023 | DOI 10.18653/v1/2023.findings-emnlp.151 | VERIFIED |
| S22 | `S22_hochreiter2026beyond` | IUI 2026 | DOI 10.1145/3742413.3789221 | VERIFIED |
| S23 | `S23_yin2026contextualized` | Entertainment Computing online/future issue | DOI 10.1016/j.entcom.2026.101194 | ONLINE-CONDITIONAL |
| S24 | `S24_yannakakis2011experiencedriven` | IEEE TAFFC | DOI 10.1109/T-AFFC.2011.6 | VERIFIED |
| S25 | `S25_melhart2020engagement` | FDG 2020 | DOI 10.1145/3402942.3402958 | VERIFIED |
| S26 | `S26_wang2026engagement` | arXiv preprint | arXiv 2603.18480 | PREPRINT |
| S27 | `S27_vanderlee2019best` | INLG 2019 | DOI 10.18653/v1/W19-8643 | VERIFIED |
| S28 | `S28_karpinska2021perils` | EMNLP 2021 | DOI 10.18653/v1/2021.emnlp-main.97 | VERIFIED |
| S29 | `S29_zheng2023judging` | NeurIPS 2023 | DOI 10.52202/075280-2020 | VERIFIED |
| S30 | `S30_chen2024judgement` | EMNLP 2024 | DOI 10.18653/v1/2024.emnlp-main.474 | VERIFIED |
| S31 | `S31_agarwal2021precipice` | NeurIPS 2021 | official NeurIPS proceedings/BibTeX | VERIFIED-NO-DOI |
| S32 | `S32_lakens2018equivalence` | AMPPS 2018 | DOI 10.1177/2515245918770963 | VERIFIED |
| S33 | `S33_pineau2021reproducibility` | JMLR 2021 | official JMLR article/BibTeX | VERIFIED-NO-DOI |
| S34 | `S34_henderson2020energy` | JMLR 2020 | official JMLR article/BibTeX | VERIFIED-NO-DOI |
| S35 | `S35_barr2013random` | Journal of Memory and Language | DOI 10.1016/j.jml.2012.11.001 | VERIFIED |
| S36 | `S36_scholak2021picard` | EMNLP 2021 | DOI 10.18653/v1/2021.emnlp-main.779 | VERIFIED |

## Manuscript evidence groups

| Use | Citation keys |
| --- | --- |
| Neuro-symbolic game worlds and dialogue | `S01_vaucher2026ivie`, `S02_figueiredo2025scaffolded`, `S03_weir2024ontologically`, `S11_cote2019textworld`, `S12_wang2022scienceworld`, `S20_ashby2023personalized` |
| Graph retrieval, memory, and role simulation | `S04_he2024gretriever`, `S05_gutierrez2024hipporag`, `S06_chhikara2025mem0`, `S07_park2023generative`, `S08_shao2023character` |
| Structural constraint versus semantic authorization | `S09_geng2023grammar`, `S10_beurerkellner2023prompting`, `S36_scholak2021picard` |
| Interactive and game-agent evaluation | `S13_fan2022minedojo`--`S19_lepelletier2022playtesting` |
| Player experience and affect | `S21_akoury2023player`--`S26_wang2026engagement` |
| Human/LLM evaluation validity | `S27_vanderlee2019best`--`S30_chen2024judgement` |
| Statistics and reproducibility | `S31_agarwal2021precipice`--`S35_barr2013random` |

## Remaining metadata and integrity gaps

1. **S01:** recheck whether ICCC 2026 has issued final archival proceedings, ISBN, page range, and a persistent publication identifier. Until then, cite the arXiv preprint and retain the conditional note.
2. **S02 and S26:** no archival venue or publisher DOI was verified; retain as advisory preprints and do not use either as the sole anchor for a central factual claim.
3. **S06:** Crossref identifies the ECAI 2025 publication and DOI but exposes no page range. The accessible IOS Press path returned HTTP 403; pages are therefore deliberately omitted.
4. **S23:** volume 58 and article number 101194 are registered, but the assigned issue was in the future on the retrieval date. Recheck year/volume/issue status immediately before submission.
5. **S15, S17, S18, S31, S33, and S34:** official records do not assign publisher DOIs. Their official proceedings/journal URLs are the canonical identifiers; do not manufacture DOI fields.
6. **Triangulation:** Semantic Scholar returned HTTP 429 during Stage 2. Metadata is supported by primary pages plus Crossref/OpenAlex where available, but a final three-index identity pass remains advisable before journal submission.

## IEEE use

Use the standard IEEE bibliography style and cite by the mapped keys, for example:

```latex
\cite{S03_weir2024ontologically,S09_geng2023grammar,S36_scholak2021picard}
```

```latex
\bibliographystyle{IEEEtran}
\bibliography{references}
```

The bibliography database contains source identities only. It does not upgrade a preprint to peer-reviewed evidence or widen any source's claim boundary.
