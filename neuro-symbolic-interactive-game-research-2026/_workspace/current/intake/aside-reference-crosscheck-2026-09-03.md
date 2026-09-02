# Aside reference cross-check — 2026-09-03 (D-066)

Second-pass verification of all 55 bibliography entries by three `aside exec --effort high` browser-research sessions, run after the first-pass primary-source agents. Per user instruction the Aside findings were weighted higher; every metadata change below was confirmed against the primary record before being applied to `paper/latex/references.bib`, `research/academic-pipeline/reference-topic-crosswalk.csv`, and `stage-05-citation-verification.json`.

Applied: S01 -> archival ICCC'26 proceedings (ACC 2026, ISBN 978-989-54160-8-0); S06 volume 413 / pages 2993--3000; S12 and S19 title casing per Anthology/OJS; S25 full FDG '20 proceedings title + article 60; S46 -> ICLR 2024 accepted poster (OpenReview archival record); S53 author order (Zeng first); S23/S26/S44/S52 notes re-dated; manuscript wording narrowed for S15 (confirmatory-studies cite removed), S38, S55, S56. Totals: 48 VERIFIED / 7 PREPRINT / 22 rate-limited. Optional suggestions not applied: articleno for S07/S10/S20, track names for S13/S16/S29, publisher for S37, key rename for S53.

# Aside reference cross-check group 1

Retrieval date: 2026-09-03. All records were opened in the browser (no logins, no purchases). Every DOI/URL resolved; the four `10.52202` NeurIPS DOIs resolve to Curran's proceedings.com storefront (free metadata block readable; the official proceedings.neurips.cc pages cross-link the same DOIs but show no page numbers, so the page ranges come from Curran). ICLR page ranges were verified from the proceedings.iclr.cc `/bibtex` records.

## S01_vaucher2026ivie
- key: S01_vaucher2026ivie
- opened: https://arxiv.org/abs/2606.13348 ; https://computationalcreativity.net/iccc26/ ; https://computationalcreativity.net/iccc26/proceedings/ ; https://computationalcreativity.net/iccc26/scientific-program/ ; https://computationalcreativity.net/iccc26/conference-program/ ; https://computationalcreativity.net/iccc26/papers/ICCC26_paper_47.pdf (HTTP 200, PDF, contains "IVIE")
- resolvable: YES (arXiv page shows exact title, four authors, submitted 11 Jun 2026; Comments: "To appear in the Proceedings of the 16th International Conference on Computational Creativity (ICCC'26)")
- metadata: FIX: note: "accepted/forthcoming at ICCC 2026, whose available pre-proceedings were explicitly non-archival and unpublished at retrieval time" -> stale; the official archival ICCC'26 proceedings were published 19 August 2026 (open access, ISBN 978-989-54160-8-0, ACC). Also, the arXiv comment says "16th" but the proceedings page says 17th ICCC. Title/authors/year in the bib match.
- archival: Published in Proceedings of the 17th International Conference on Computational Creativity (ICCC'26), eds. Gonçalo Oliveira, Kantosalo, Toivonen, Machado, Alves; Association for Computational Creativity, 2026; ISBN 978-989-54160-8-0. No DOI is issued (ISBN/ISSN only). Paper PDF: ICCC26_paper_47.pdf; page range not exposed on the site (I did not read the combined PDF for pagination).
- context: FAIR — abstract: "a four-stage incremental generation pipeline that delegates creative decisions ... to LLMs while grounding the world state through symbolic validation", which is exactly what the sentence attributes; but the descriptor "a preprint associated with non-archival ICCC 2026 material" is now factually stale and should be rewritten.
- verdict: REPLACE-WITH-ARCHIVAL

## S02_figueiredo2025scaffolded
- key: S02_figueiredo2025scaffolded
- opened: https://arxiv.org/abs/2510.25820 ; https://dblp.org/search?q=Symbolically+Scaffolded+Play
- resolvable: YES
- metadata: MATCH (title, both authors, 2025, submitted 29 Oct 2025, cs.AI/cs.HC; no journal-ref or comments)
- archival: preprint (DBLP, curated to 2026-09-02, lists only CoRR abs/2510.25820; no venue or publisher DOI found). The note's "as of 2026-08-12" stamp can be advanced to 2026-09-03.
- context: FAIR — abstract states "scaffolding effects were role-dependent: the Interviewer (quest-giver NPC) gained stability, while suspect NPCs lost improvisational believability", i.e. exactly the role-sensitive stability–improvisation trade-off cited.
- verdict: KEEP

## S03_weir2024ontologically
- key: S03_weir2024ontologically
- opened: https://doi.org/10.18653/v1/2024.emnlp-main.520 (-> https://aclanthology.org/2024.emnlp-main.520/)
- resolvable: YES
- metadata: MATCH (six authors in order, EMNLP 2024 main, pp. 9212–9242, ACL; only cosmetic apostrophe in "d'Amore")
- archival: archival as cited
- context: FAIR — abstract: KNUDGE "requires models to produce trees of dialogue between video game characters that accurately reflect quest and entity specifications"; the "context does not authorize canonical mutation" caveat is the manuscript's own framing, not attributed to S03.
- verdict: KEEP

## S04_he2024gretriever
- key: S04_he2024gretriever
- opened: https://doi.org/10.52202/079017-4224 (-> https://www.proceedings.com/079017-4224.html) ; https://proceedings.neurips.cc/paper_files/paper/2024/hash/efaf1c9726648c8ba363a5c927440529-Abstract-Conference.html
- resolvable: YES (official NeurIPS page links back to the same DOI)
- metadata: MATCH (NeurIPS 37, main track, pp. 132876–132907 per Curran; authors verbatim on the NeurIPS page incl. "Nitesh V. Chawla", "Yann LeCun" — Curran's "Yann Lecun"/"Nitesh Chawla" is the degraded rendering, do not copy it)
- archival: archival as cited
- context: FAIR — abstract: "first retrieval-augmented generation (RAG) approach for general textual graphs ... formulating this task as a Prize-Collecting Steiner Tree optimization problem", i.e. subgraph retrieval; the "not a state-transition authority" claim is the manuscript's own argument.
- verdict: KEEP

## S05_gutierrez2024hipporag
- key: S05_gutierrez2024hipporag
- opened: https://doi.org/10.52202/079017-1902 (-> https://www.proceedings.com/079017-1902.html) ; https://proceedings.neurips.cc/paper_files/paper/2024/hash/6ddc001d07ca4f319af96a3024f6dbd1-Abstract-Conference.html
- resolvable: YES
- metadata: MATCH (NeurIPS 37, pp. 59532–59569 per Curran; NeurIPS page lists "Bernal Jiménez Gutiérrez", so the bib's compound surname is correct — Curran truncates it to "Bernal Gutiérrez")
- archival: archival as cited
- context: FAIR — abstract: "a novel retrieval framework inspired by the hippocampal indexing theory of human long-term memory", matching the long-term-memory framing.
- verdict: KEEP

## S06_chhikara2025mem0
- key: S06_chhikara2025mem0
- opened: https://doi.org/10.3233/FAIA251160 (-> https://ebooks.iospress.nl/doi/10.3233/FAIA251160)
- resolvable: YES
- metadata: FIX: pages: (absent) -> 2993--3000; volume: (absent) -> 413 (FAIA Volume 413: ECAI 2025); note: "page range was not exposed ..." -> delete, now false. Title, five authors, series, IOS Press, DOI match.
- archival: archival as cited (ECAI 2025, FAIA vol. 413, open access)
- context: FAIR — abstract: "a scalable memory-centric architecture that ... dynamically extract[s], consolidat[es], and retriev[es] salient information from ongoing conversations", plus a graph-memory variant; matches "long-term memory" usage.
- verdict: FIX-METADATA

## S07_park2023generative
- key: S07_park2023generative
- opened: https://doi.org/10.1145/3586183.3606763 (-> https://dl.acm.org/doi/10.1145/3586183.3606763)
- resolvable: YES
- metadata: MATCH (UIST '23, Article No. 2, Pages 1–22, ACM, 2023). Optional: add `articleno = {2}`. ACM lists "Joseph O'Brien" / "Carrie Jun Cai" — same people, name-form variants only.
- archival: archival as cited
- context: FAIR — abstract: agents store "a complete record of the agent's experiences", "synthesize those memories over time into higher-level reflections, and retrieve them dynamically to plan behavior", with ablations of observation/planning/reflection; matches "memory–reflection–planning" and "behavioral memory".
- verdict: KEEP

## S08_shao2023character
- key: S08_shao2023character
- opened: https://doi.org/10.18653/v1/2023.emnlp-main.814 (-> https://aclanthology.org/2023.emnlp-main.814/)
- resolvable: YES (DOI resolves even though the Anthology page renders "DOI: –")
- metadata: MATCH (four authors in order, EMNLP 2023 main, pp. 13153–13187, ACL)
- archival: archival as cited
- context: FAIR — abstract: "train an agent with the profile, experience, and emotional states of a specific person ... Character-LLM that teach LLMs to act as specific people"; supports "trainable role-playing agents" and "persona".
- verdict: KEEP

## S09_geng2023grammar
- key: S09_geng2023grammar
- opened: https://doi.org/10.18653/v1/2023.emnlp-main.674 (-> https://aclanthology.org/2023.emnlp-main.674/)
- resolvable: YES
- metadata: MATCH (four authors in order, EMNLP 2023 main, pp. 10932–10952, ACL, DOI displayed)
- archival: archival as cited
- context: FAIR — abstract: GCD "control[s] the generation of LMs, guaranteeing that the output follows a given structure"; the "syntactically admissible yet false" caveat is the manuscript's own contrast.
- verdict: KEEP

## S10_beurerkellner2023prompting
- key: S10_beurerkellner2023prompting
- opened: https://doi.org/10.1145/3591300 (-> https://dl.acm.org/doi/10.1145/3591300)
- resolvable: YES
- metadata: MATCH (PACMPL Vol. 7, Issue PLDI, Article No. 186, pp. 1946–1969, 2023). Optional: add `articleno = {186}`.
- archival: archival as cited
- context: FAIR — abstract: "LMP allows constraints to be specified over the language model output" and LMQL "leverages the constraints and control flow ... to generate an efficient inference procedure"; supports "query languages restrict generated structures".
- verdict: KEEP

## S11_cote2019textworld
- key: S11_cote2019textworld
- opened: https://doi.org/10.1007/978-3-030-24337-1_3 (-> https://link.springer.com/chapter/10.1007/978-3-030-24337-1_3) ; https://link.springer.com/book/10.1007/978-3-030-24337-1
- resolvable: YES
- metadata: MATCH (12 authors in order, CCIS 1017, pp. 41–75, 2019). Optional refinements: booktitle "Computer Games. CGW 2018" (full title "Computer Games: 7th Workshop, CGW 2018 ... Revised Selected Papers", eds. Cazenave, Saffidine, Sturtevant); publisher "Springer, Cham".
- archival: archival as cited
- context: FAIR — abstract: TextWorld "handles interactive play-through of text games, as well as backend functions like state tracking and reward assignment"; supports "executable text environment exposing explicit interactive state".
- verdict: KEEP

## S12_wang2022scienceworld
- key: S12_wang2022scienceworld
- opened: https://doi.org/10.18653/v1/2022.emnlp-main.775 (-> https://aclanthology.org/2022.emnlp-main.775/)
- resolvable: YES
- metadata: FIX: title: "ScienceWorld: Is Your Agent Smarter than a 5th Grader?" -> "ScienceWorld: Is your Agent Smarter than a 5th Grader?" (Anthology casing; cosmetic). Authors, EMNLP 2022 main, pp. 11279–11298, ACL all match.
- archival: archival as cited
- context: FAIR — abstract: "a new interactive text environment" where agents must "conduct an experiment in a grounded environment"; supports both the environment and benchmark uses.
- verdict: FIX-METADATA (cosmetic only)

## S13_fan2022minedojo
- key: S13_fan2022minedojo
- opened: https://doi.org/10.52202/068431-1333 (-> https://www.proceedings.com/068431-1333.html) ; https://papers.nips.cc/paper_files/paper/2022 ; https://proceedings.neurips.cc/paper_files/paper/2022/hash/74a67268c5cc5910f64938cac4526a90-Abstract-Datasets_and_Benchmarks.html
- resolvable: YES (official NeurIPS page shows the same DOI)
- metadata: MATCH as written (title, 10 authors in order, NeurIPS 35, pp. 18343–18362 per Curran, 2022). Optional precision: the official page labels it "Datasets and Benchmarks Track"; the bib omits the track.
- archival: archival as cited
- context: FAIR — abstract: "a simulation suite with thousands of diverse open-ended tasks" for "generally capable embodied agents"; exactly "open-ended embodied tasks".
- verdict: KEEP

## S14_perezliebana2019gvgai
- key: S14_perezliebana2019gvgai
- opened: https://doi.org/10.1109/TG.2019.2901021 (-> https://ieeexplore.ieee.org/document/8664126/)
- resolvable: YES
- metadata: MATCH (IEEE ToG vol. 11, no. 3, Sept 2019, pp. 195–214; six authors in order; IEEE strips diacritics, keep the accented form)
- archival: archival as cited
- context: FAIR — abstract: the framework "has been expanded into several tracks" where agents "play multiple unknown games ... or design new game levels or rules"; matches agent/game/content track separation.
- verdict: KEEP

## S15_liu2024agentbench
- key: S15_liu2024agentbench
- opened: https://proceedings.iclr.cc/paper_files/paper/2024/hash/e9df36b21ff4ee211a8b71ee8b7e9f57-Abstract-Conference.html ; https://proceedings.iclr.cc/paper_files/paper/5292-/bibtex ; https://openreview.net/forum?id=zAdUB0aCTQ ; https://www.proceedings.com/search-result/?search_query=AgentBench
- resolvable: YES (abstract page shows title, 22 authors, ICLR 2024 Conference, no DOI; the proceedings bibtex record gives pages = {52989--53046}, matching the bib; OpenReview confirms ICLR 2024 poster)
- metadata: MATCH
- archival: archival as cited (no publisher DOI observed, consistent with the note)
- context: FAIR for contexts 1–2 (abstract: "a multi-dimensional benchmark that consists of 8 distinct environments" over "29 API-based and open-sourced LLMs"); OVERCLAIM for context 3 — AgentBench is a multi-model comparison, but nothing in the record supports preregistration, an independent semantic oracle, blind-retry comparators, matched-validity ablations, power justification, or mixed-effects analysis, so citing it for that confirmatory-study bundle attributes methodology it does not claim.
- verdict: KEEP (bib unchanged; narrow or move the citation in the confirmatory-studies sentence)

## S16_ma2024agentboard
- key: S16_ma2024agentboard
- opened: https://doi.org/10.52202/079017-2365 (-> https://www.proceedings.com/079017-2365.html) ; https://proceedings.neurips.cc/paper_files/paper/2024/hash/877b40688e330a0e2a3fc24084208dfa-Abstract-Datasets_and_Benchmarks_Track.html
- resolvable: YES (official NeurIPS page lists the same DOI)
- metadata: MATCH (nine authors in order, NeurIPS 37, pp. 74325–74362, 2024). Optional precision: official page labels it "Datasets and Benchmarks Track".
- archival: archival as cited
- context: FAIR — abstract: current frameworks "focus on the final success rate, revealing few insights during the process"; AgentBoard "offers a fine-grained progress rate metric that captures incremental advancements"; supports "process-diagnosed", "process metrics motivate retaining intermediate failures", and "measurement concern".
- verdict: KEEP

## S17_zhou2024sotopia
- key: S17_zhou2024sotopia
- opened: https://proceedings.iclr.cc/paper_files/paper/2024/hash/b3075b88e583a0e98d8b24338a613060-Abstract-Conference.html ; https://proceedings.iclr.cc/paper_files/paper/3823-/bibtex
- resolvable: YES
- metadata: MATCH (11 authors in order, ICLR 2024 Conference, bibtex record pages = {40975--41019}, no DOI shown)
- archival: archival as cited
- context: FAIR — abstract: "an open-ended environment to simulate complex social interactions between artificial agents and evaluate their social intelligence"; supports "social" settings.
- verdict: KEEP

## S18_paglieri2025balrog
- key: S18_paglieri2025balrog
- opened: https://proceedings.iclr.cc/paper_files/paper/2025/hash/f0b1515be276f6ba82b4f2b25e50bef0-Abstract-Conference.html ; https://proceedings.iclr.cc/paper_files/paper/1039-/bibtex
- resolvable: YES
- metadata: MATCH (13 authors in order, ICLR 2025 Conference, bibtex record pages = {96666--96702}; page spells "Rocktaeschel", the ASCII form of Rocktäschel; title "On" vs "on" is casing only)
- archival: archival as cited
- context: FAIR — abstract: benchmark of "challenging games" requiring "long-term planning" including NetHack, "tasks ... that may take years to master"; supports "long-horizon game settings" and "benchmarks".
- verdict: KEEP

## S19_lepelletier2022playtesting
- key: S19_lepelletier2022playtesting
- opened: https://doi.org/10.1609/aiide.v18i1.21958 (-> https://ojs.aaai.org/index.php/AIIDE/article/view/21958)
- resolvable: YES
- metadata: FIX: title: "Automated Play-Testing through RL-Based Human-Like Play-Styles Generation" -> "Automated Play-Testing through RL Based Human-Like Play-Styles Generation" (OJS record and its "How to Cite" string have no hyphen in "RL Based"; cosmetic). Authors, vol. 18 no. 1, pp. 146–154, 2022 (published 2022-10-11, Research Track Posters) match.
- archival: archival as cited
- context: FAIR — abstract: CARMI is an RL agent "able to emulate the players play-styles" to "give meaningful feedback to the designers" and "only requires little human data"; "complement rather than replace human evaluation" is a reasonable reading (the paper positions the agent as a designer aid, not a replacement for players).
- verdict: KEEP

## Summary
- KEEP: 15 (S02, S03, S04, S05, S07, S08, S09, S10, S11, S13, S14, S15, S16, S17, S18)
- FIX-METADATA: 3 (S06 add pages 2993–3000 + volume 413 and delete stale note; S12 title casing "your"; S19 title "RL Based")
- REPLACE-WITH-ARCHIVAL: 1 (S01 -> ICCC'26 proceedings, ACC 2026, ISBN 978-989-54160-8-0, no DOI; also rewrite the prose descriptor "preprint associated with non-archival ICCC 2026 material")
- DROP: 0

Keys needing action: S01, S06, S12, S19, plus a prose-only fix for S15 (context 3 is an OVERCLAIM; the bib entry itself is correct). Optional, not required: add `articleno` to S07 (2) and S10 (186); add "Datasets and Benchmarks Track" to S13 and S16; expand S11 booktitle to "Computer Games. CGW 2018".[0m

# Aside reference cross-check group 2

Retrieval date: 2026-09-03. All pages were opened in the browser (no logins, purchases, or posting). "Opened" lists the URL entered plus the final URL it resolved to.

## S20_ashby2023personalized
- key: S20_ashby2023personalized
- opened: https://doi.org/10.1145/3544548.3581441 -> https://dl.acm.org/doi/10.1145/3544548.3581441
- resolvable: YES
- metadata: MATCH (ACM: "Personalized Quest and Dialogue Generation in Role-Playing Games: A Knowledge Graph- and Language Model-based Approach"; Trevor Ashby, Braden K Webb, Gregory Knapp, Jackson Searle, Nancy Fulda; CHI '23: Proceedings of the 2023 CHI Conference on Human Factors in Computing Systems; Article No. 290, Pages 1–20; published 19 April 2023. Bib omits the optional article number 290; only a casing difference "Model-based" vs "Model-Based".)
- archival: archival as cited
- context: FAIR — the abstract describes quest and dialogue generation grounded in a hand-crafted knowledge graph plus in-game context with an LLM for dialogue, which is exactly the "knowledge-graph quest generation" / "quest, entity, and graph context" role attributed to it, and the paper makes no claim about authorizing world-state mutation.
- verdict: KEEP

## S21_akoury2023player
- key: S21_akoury2023player
- opened: https://doi.org/10.18653/v1/2023.findings-emnlp.151 -> https://aclanthology.org/2023.findings-emnlp.151/
- resolvable: YES
- metadata: MATCH (ACL Anthology: title, Nader Akoury / Qian Yang / Mohit Iyyer, Findings of the Association for Computational Linguistics: EMNLP 2023, December 2023, Singapore, ACL, pages 2295–2311, DOI as cited)
- archival: archival as cited
- context: FAIR — the abstract reports a 28-player study of GPT-4 dialogue infilling vs. designers' writing in Disco Elysium via preference judgments and free-form feedback, matching "player-facing studies evaluate preference and perceived dialogue quality".
- verdict: KEEP

## S22_hochreiter2026beyond
- key: S22_hochreiter2026beyond
- opened: https://doi.org/10.1145/3742413.3789221 -> https://dl.acm.org/doi/10.1145/3742413.3789221
- resolvable: YES
- metadata: MATCH (ACM: "Beyond Pre-Defined Scripts: Player Perceptions on Generative Non-Player Character Dialogues"; Manuel Hochreiter, Simone Kriglstein, Günter Wallner; IUI '26: Proceedings of the 31st International Conference on Intelligent User Interfaces; Pages 2004–2018; published 22 March 2026; no article number shown)
- archival: archival as cited
- context: FAIR — the abstract reports an online survey of 62 participants on perceptions of LLM-generated NPC dialogues (benefits such as more natural conversations and undesired side-effects), i.e. a player-facing perceived-dialogue-quality study as cited.
- verdict: KEEP

## S23_yin2026contextualized
- key: S23_yin2026contextualized
- opened: https://doi.org/10.1016/j.entcom.2026.101194 -> https://www.sciencedirect.com/science/article/abs/pii/S1875952126001163?via%3Dihub
- resolvable: YES
- metadata: MATCH (ScienceDirect: "How contextualized generative AI shapes player experience in games"; Ming Yin, Hanzhi Zu, Wenqing Gu, Ziyan Wang, Weijiang She, Yucong Cai, Pan Hui, Tengjia Zuo; Entertainment Computing, Volume 58, September 2026, article 101194; DOI as cited; no issue number displayed). The issue assignment the bib note flagged as provisional is now confirmed (Volume 58, September 2026), so the `note` field can be removed or updated to reflect the 2026-09-03 recheck.
- archival: archival as cited
- context: FAIR — the abstract describes a 2×2 within-subject experiment (N = 72) measuring presence, autonomy, and enjoyment under item-layer and dialogue-layer contextualized generative AI (including adaptive NPC dialogue); its constructs are player-experience measures rather than dialogue-quality ratings per se, but citing it as a player-facing study of generated content is not an overclaim.
- verdict: KEEP

## S24_yannakakis2011experiencedriven
- key: S24_yannakakis2011experiencedriven
- opened: https://doi.org/10.1109/T-AFFC.2011.6 -> https://ieeexplore.ieee.org/document/5740836/
- resolvable: YES
- metadata: MATCH (IEEE Xplore: "Experience-Driven Procedural Content Generation"; Georgios N. Yannakakis, Julian Togelius; IEEE Transactions on Affective Computing, Volume 2, Issue 3, July–Sept. 2011, pages 147–161, DOI as cited)
- archival: archival as cited
- context: FAIR — the abstract introduces the Experience-Driven PCG framework where content is generated/adjusted from computational models of player experience, which is exactly what citing it as motivation for a future adaptation track attributes.
- verdict: KEEP

## S25_melhart2020engagement
- key: S25_melhart2020engagement
- opened: https://doi.org/10.1145/3402942.3402958 -> https://dl.acm.org/doi/10.1145/3402942.3402958
- resolvable: YES
- metadata: FIX: booktitle: "International Conference on the Foundations of Digital Games" -> "FDG '20: Proceedings of the 15th International Conference on the Foundations of Digital Games" (ACM page; also lists Article No. 60, Pages 1–10, published 17 September 2020, publisher Association for Computing Machinery; title and authors David Melhart, Daniele Gravina, Georgios N. Yannakakis match; optionally add articleno = {60}). The bib value is an abbreviation rather than an error, but it drops the ordinal and "Proceedings of".
- archival: archival as cited
- context: FAIR — the abstract reframes gameplay engagement "through the eyes of a game's live audience" and trains engagement predictors on Twitch viewer chat frequency, which is exactly "observer-labelled engagement".
- verdict: FIX-METADATA

## S26_wang2026engagement
- key: S26_wang2026engagement
- opened: https://arxiv.org/abs/2603.18480
- resolvable: YES
- metadata: MATCH (arXiv: "Do Vision Language Models Understand Human Engagement in Games?"; Ziyi Wang, Qizan Guo, Rishitosh Singh, Xiyang Hu; submitted 19 Mar 2026, v1 only; cs.CV; arXiv DOI 10.48550/arXiv.2603.18480 shown and could be added as an optional field)
- archival: preprint (no journal-ref, comments, or publisher DOI on the arXiv page as of 2026-09-03; the bib note's 2026-08-12 statement remains true and can be re-dated)
- context: FAIR — the abstract reports that zero-shot VLM engagement predictions are "generally weak", often fail to beat per-game majority baselines, and that a perception–understanding gap persists, supporting "limits of vision-language engagement inference".
- verdict: KEEP

## S27_vanderlee2019best
- key: S27_vanderlee2019best
- opened: https://doi.org/10.18653/v1/W19-8643 -> https://aclanthology.org/W19-8643/
- resolvable: YES
- metadata: MATCH (ACL Anthology: "Best practices for the human evaluation of automatically generated text"; Chris van der Lee, Albert Gatt, Emiel van Miltenburg, Sander Wubben, Emiel Krahmer; Proceedings of the 12th International Conference on Natural Language Generation, 2019, Tokyo, pages 355–368, ACL, DOI as cited; only title casing differs)
- archival: archival as cited
- context: FAIR — the paper surveys how human NLG evaluation is conducted and derives best practices, so citing it for construct/rater/bias controls and for designing a future human study is accurate; it does not address LLM judges, but the sentences invoke it only for the human-evaluation side alongside other works.
- verdict: KEEP

## S28_karpinska2021perils
- key: S28_karpinska2021perils
- opened: https://doi.org/10.18653/v1/2021.emnlp-main.97 -> https://aclanthology.org/2021.emnlp-main.97/
- resolvable: YES
- metadata: MATCH (ACL Anthology: title, Karpinska / Akoury / Iyyer, Proceedings of the 2021 Conference on Empirical Methods in Natural Language Processing, November 2021, pages 1265–1285, ACL, DOI as cited)
- archival: archival as cited
- context: FAIR — the abstract reports that even qualified AMT workers fail to distinguish model-generated from human text and that judgments improve only when raters are calibrated with references, directly supporting the need for rater, calibration, and bias controls in crowd evaluation.
- verdict: KEEP

## S29_zheng2023judging
- key: S29_zheng2023judging
- opened: https://doi.org/10.52202/075280-2020 -> https://www.proceedings.com/075280-2020.html, https://papers.nips.cc/paper_files/paper/2023/hash/91f18a1287b398d378ef22505bf41832-Abstract-Datasets_and_Benchmarks.html
- resolvable: YES (the Curran DOI resolves to the proceedings.com record for this exact paper: authors Zheng … Stoica, pages 46595–46623, "Advances in Neural Information Processing Systems 36", 10–16 December 2023, publisher Neural Information Processing Systems Foundation, Inc.; the official papers.nips.cc page also lists DOI 10.52202/075280-2020)
- metadata: MATCH (title, 13 authors, booktitle, volume 36, year 2023, pages, publisher, DOI all consistent with both records). Minor: official page spells "Eric P. Xing" and "Joseph E Gonzalez"; it is in the Datasets and Benchmarks Track, which the bib could optionally record.
- archival: archival as cited
- context: FAIR — the abstract explicitly examines "the usage and limitations of LLM-as-a-judge, including position, verbosity, and self-enhancement biases, as well as limited reasoning ability" and verifies agreement with human preferences, supporting the calibration/bias-control claim.
- verdict: KEEP

## S30_chen2024judgement
- key: S30_chen2024judgement
- opened: https://doi.org/10.18653/v1/2024.emnlp-main.474 -> https://aclanthology.org/2024.emnlp-main.474/
- resolvable: YES
- metadata: MATCH (ACL Anthology: "Humans or LLMs as the Judge? A Study on Judgement Bias"; Guiming Hardy Chen, Shunian Chen, Ziche Liu, Feng Jiang, Benyou Wang; Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing, November 2024, pages 8301–8327, ACL, DOI as cited)
- archival: archival as cited
- context: FAIR — the abstract studies Misinformation Oversight, Gender, Authority, and Beauty biases in both human and LLM judges and finds both vulnerable to perturbation, which is exactly the "human and LLM evaluation require bias controls" attribution.
- verdict: KEEP

## S31_agarwal2021precipice
- key: S31_agarwal2021precipice
- opened: https://proceedings.neurips.cc/paper/2021/hash/f514cec81cb148559cf475e7426eed5e-Abstract.html, https://proceedings.neurips.cc/paper_files/paper/13867-/bibtex (official BibTeX; served as a download)
- resolvable: YES
- metadata: MATCH (official BibTeX: Agarwal, Schwarzer, Castro, Courville, Bellemare; booktitle Advances in Neural Information Processing Systems; volume 34; pages 29304–29320; publisher Curran Associates, Inc.; year 2021). The abstract page itself shows no pages and no DOI, consistent with the bib note "no publisher DOI assigned"; the page renders "Aaron C. Courville" and "Marc Bellemare" (bib's "Marc G." middle initial not shown, not a conflict).
- archival: archival as cited
- context: FAIR — the abstract argues that "reliable evaluation in the few run deep RL regime cannot ignore the uncertainty in results" and advocates interval estimates and robust aggregates, supporting both uses (caution against overinterpreting sparse stochastic runs; confirmatory studies needing proper statistical treatment).
- verdict: KEEP

## S32_lakens2018equivalence
- key: S32_lakens2018equivalence
- opened: https://doi.org/10.1177/2515245918770963 -> https://journals.sagepub.com/doi/10.1177/2515245918770963 (including its in-page Cite panel)
- resolvable: YES
- metadata: MATCH (SAGE: "Equivalence Testing for Psychological Research: A Tutorial"; Daniël Lakens, Anne M. Scheel, Peder M. Isager; Advances in Methods and Practices in Psychological Science; Cite panel "2018;1(2):259-269"; first published online June 1, 2018; CC BY 4.0)
- archival: archival as cited
- context: FAIR — the abstract is about equivalence testing (TOST) against a justified smallest effect size of interest and specifying/justifying bounds, so citing it for "non-inferiority analyses require justified margins" is accurate (the paper also explicitly covers inferiority tests in its Fig. 1).
- verdict: KEEP

## S33_pineau2021reproducibility
- key: S33_pineau2021reproducibility
- opened: https://jmlr.org/papers/v22/20-303.html
- resolvable: YES
- metadata: MATCH (JMLR: "Improving Reproducibility in Machine Learning Research (A Report from the NeurIPS 2019 Reproducibility Program)"; Pineau, Vincent-Lamarre, Sinha, Larivière, Beygelzimer, d'Alché-Buc, Fox, Larochelle; "22(164):1−20, 2021". JMLR renders the subtitle in parentheses rather than after a colon, a stylistic difference only. No publisher DOI shown, consistent with the bib note.)
- archival: archival as cited
- context: FAIR — the abstract describes the NeurIPS 2019 reproducibility program (code submission policy, reproducibility challenge, ML Reproducibility checklist) aimed at making results verifiable with the same code and data, supporting its use as motivation for frozen artifacts and code/environment revision.
- verdict: KEEP

## S34_henderson2020energy
- key: S34_henderson2020energy
- opened: https://jmlr.org/papers/v21/20-312.html
- resolvable: YES
- metadata: MATCH (JMLR: "Towards the Systematic Reporting of the Energy and Carbon Footprints of Machine Learning"; Henderson, Hu, Romoff, Brunskill, Jurafsky, Pineau; "21(248):1−43, 2020". No publisher DOI shown, consistent with the bib note.)
- archival: archival as cited
- context: FAIR — the abstract proposes a framework for tracking energy/carbon consumption and generating standardized reporting appendices, so "environmental reporting" and "explicit measurement boundaries" are reasonable attributions; the general artifact-freezing motivation should be read as resting on S33, since this paper is specifically about energy/carbon accounting.
- verdict: KEEP

## S35_barr2013random
- key: S35_barr2013random
- opened: https://doi.org/10.1016/j.jml.2012.11.001 -> https://www.sciencedirect.com/science/article/abs/pii/S0749596X12001180?via%3Dihub
- resolvable: YES
- metadata: MATCH (ScienceDirect: "Random effects structure for confirmatory hypothesis testing: Keep it maximal"; Dale J. Barr, Roger Levy, Christoph Scheepers, Harry J. Tily; Journal of Memory and Language, Volume 68, Issue 3, April 2013, Pages 255–278, DOI as cited; only title casing differs)
- archival: archival as cited
- context: FAIR — the abstract argues that LMEMs used for confirmatory hypothesis testing should include the maximal random-effects structure justified by the design, directly supporting "participant analyses require … random-effects structures" and "mixed-effects analysis".
- verdict: KEEP

## S36_scholak2021picard
- key: S36_scholak2021picard
- opened: https://doi.org/10.18653/v1/2021.emnlp-main.779 -> https://aclanthology.org/2021.emnlp-main.779/
- resolvable: YES
- metadata: MATCH (ACL Anthology: "PICARD: Parsing Incrementally for Constrained Auto-Regressive Decoding from Language Models"; Torsten Scholak, Nathan Schucher, Dzmitry Bahdanau; Proceedings of the 2021 Conference on Empirical Methods in Natural Language Processing, November 2021, pages 9895–9901, ACL, DOI as cited)
- archival: archival as cited
- context: FAIR — the abstract describes constraining auto-regressive decoders via incremental parsing, "rejecting inadmissible tokens at each decoding step" so outputs are valid SQL, which is exactly the "incremental parsers restrict generated structures" role assigned; the manuscript's point that syntactic validity does not guarantee world-state truth is its own claim, not attributed to PICARD.
- verdict: KEEP

## S37_riedl2003managing
- key: S37_riedl2003managing
- opened: https://doi.org/10.1145/860575.860694 -> https://dl.acm.org/doi/10.1145/860575.860694
- resolvable: YES
- metadata: MATCH (ACM: "Managing interaction between users and agents in a multi-agent storytelling environment"; Mark Riedl, C. J. Saretto, R. Michael Young; AAMAS '03: Proceedings of the second international joint conference on Autonomous agents and multiagent systems; published 14 July 2003; pages 741–748; publisher Association for Computing Machinery. Bib's "Mark O." middle initial is not displayed on the page (not a conflict); bib has no publisher field and could add publisher = {ACM}.)
- archival: archival as cited
- context: FAIR — the abstract describes "narrative mediation", which uses a plan-based narrative model to monitor user actions and compute accommodation or intervention responses to actions that would interfere with story structure; "intercepts an action before it executes" is a fair characterization of intervention in this framework.
- verdict: KEEP

## S38_evans2013versu
- key: S38_evans2013versu
- opened: https://doi.org/10.1109/TCIAIG.2013.2287297 -> https://ieeexplore.ieee.org/document/6648395/
- resolvable: YES
- metadata: MATCH (IEEE Xplore: "Versu—A Simulationist Storytelling System" (em dash = bib's "---"); Richard Evans, Emily Short; IEEE Transactions on Computational Intelligence and AI in Games; Volume 6, Issue 2, June 2014; pages 113–130; Date of Publication 25 October 2013; DOI as cited. Bib year 2014 matches the issue date; the key's "2013" reflects the online date. The note about the predecessor title of IEEE Transactions on Games is consistent with the journal name shown.)
- archival: archival as cited
- context: FAIR — the abstract describes Versu as a simulationist interactive drama in which authored "social practices" (reactive joint plans) give affordances to autonomous agents while "it is always the individual agent who decides what to do"; reading this as authored logic governing which utterances a character may make is defensible, though the paper's own emphasis is on suggestion/affordance rather than strict permission, so the claim is fair but at the boundary.
- verdict: KEEP

## Summary
- Entries checked: 19 / 19 (all opened; all DOIs, arXiv ID, and URLs resolved to the claimed works on 2026-09-03).
- KEEP: 18
- FIX-METADATA: 1
- REPLACE-WITH-ARCHIVAL: 0
- DROP: 0
- Context judgments: FAIR 19, OVERCLAIM 0, UNRELATED 0.

Keys that need action:
- S25_melhart2020engagement — booktitle should be the full ACM proceedings title "FDG '20: Proceedings of the 15th International Conference on the Foundations of Digital Games" (optionally add articleno = {60}).

Minor optional housekeeping (no verdict change):
- S23_yin2026contextualized — the `note` is now stale: Volume 58 (September 2026) is assigned on ScienceDirect; drop or re-date the note.
- S26_wang2026engagement — still a preprint (v1, 19 Mar 2026); re-date the note to 2026-09-03 and optionally add doi = {10.48550/arXiv.2603.18480}.
- S20_ashby2023personalized — optionally add articleno = {290}.
- S29_zheng2023judging — optionally record "Datasets and Benchmarks Track".
- S37_riedl2003managing — optionally add publisher = {ACM}.
- S38_evans2013versu — context is fair but at the boundary; if you want to be conservative, soften "governs which utterances a character may make" to "authors the social practices that afford or suggest a character's utterances".[0m

# Aside reference cross-check group 3

Retrieval date: 2026-09-03. All primary records were opened in the browser (no logins). Where an ACM landing page shows no abstract text, the open-access PDF at the same DOI was opened to read it; this is noted per entry.

## S39_fikes1971strips
- key: S39_fikes1971strips
- opened: https://doi.org/10.1016/0004-3702(71)90010-5 → https://www.sciencedirect.com/science/article/abs/pii/0004370271900105
- resolvable: YES
- metadata: MATCH (ScienceDirect: "Strips: A new approach to the application of theorem proving to problem solving"; Richard E. Fikes, Nils J. Nilsson; Artificial Intelligence, Volume 2, Issues 3–4, Winter 1971, pages 189–208; DOI as in bib. Only title casing differs, which the bib's braces preserve.)
- archival: archival as cited
- context: FAIR — the abstract describes STRIPS as searching operator sequences over world models; the paper's operator definition (preconditions plus add/delete effects) is the origin of "applicability through preconditions and effects".
- verdict: KEEP

## S40_schneider2000enforceable
- key: S40_schneider2000enforceable
- opened: https://doi.org/10.1145/353323.353382 → https://dl.acm.org/doi/10.1145/353323.353382
- resolvable: YES
- metadata: MATCH (ACM DL: "Enforceable security policies"; Fred B. Schneider; ACM Transactions on Information and System Security, Volume 3, Issue 1, pages 30–50; published 1 Feb 2000.)
- archival: archival as cited
- context: FAIR — abstract: "A precise characterization is given for the class of security policies enforceable with mechanisms that work by monitoring system execution, and automata are introduced for specifying exactly that class"; execution monitors truncate violating executions, so "admits only permitted transitions" is accurate.
- verdict: KEEP

## S41_ware2021sabre
- key: S41_ware2021sabre
- opened: https://doi.org/10.1609/aiide.v17i1.18896 → https://ojs.aaai.org/index.php/AIIDE/article/view/18896
- resolvable: YES
- metadata: MATCH (AAAI OJS "How to Cite": Ware, S. G., & Siler, C. (2021). Sabre: A Narrative Planner Supporting Intention and Deep Theory of Mind. Proc. AAAI AIIDE, 17(1), 99–106; published 2021-10-04.)
- archival: archival as cited
- context: FAIR — abstract: "every action taken by an agent must make sense according to that agent's individual intentions and limited, possibly wrong beliefs … no arbitrary limit on the depth of theory of mind", which is exactly "belief-aware narrative planning reasons over what characters know".
- verdict: KEEP

## S42_buongiorno2024pangea
- key: S42_buongiorno2024pangea
- opened: https://doi.org/10.1609/aiide.v20i1.31876 → https://ojs.aaai.org/index.php/AIIDE/article/view/31876
- resolvable: YES
- metadata: MATCH (AAAI OJS "How to Cite": Buongiorno, S., Klinkert, L., Zhuang, Z., Chawla, T., & Clark, C. (2024). PANGeA: Procedural Artificial Narrative Using Generative AI for Turn-Based, Role-Playing Video Games. Proc. AAAI AIIDE, 20(1), 156–166; published 2024-11-15. The @article/journal form mirrors AAAI OJS's own citation format; entry type is a style choice.)
- archival: archival as cited
- context: FAIR — abstract: the validation system "aligns LLM generation with the narrative … by evoking the LLM's capabilities to dynamically evaluate the text input against game rules that reinforce the designer's initial criteria"; "judge and refine against designer rules" is a faithful gloss ("refine" slightly extends "evaluate" but matches the described alignment).
- verdict: KEEP

## S44_gongora2026worldstate
- key: S44_gongora2026worldstate
- opened: https://arxiv.org/abs/2605.24719
- resolvable: YES (v1, submitted 23 May 2026)
- metadata: MATCH (title, four authors Góngora / Chiruzzo / Méndez / Gervás, year 2026, eprint 2605.24719, cs.CL.)
- archival: preprint — arXiv Comments: "To be presented at the 17th International Conference on Computational Creativity (ICCC'26)"; no journal-ref or publisher DOI on the record. The bib note is still accurate; optionally add the ICCC'26 statement to the note.
- context: FAIR — abstract: LLMs "predict state changes within rule-based Interactive Storytelling systems, triggering pre-programmed world-state transformations" that "offer a way to maintain world-state consistency", matching "restricts the LLM to selecting authored world-state transformations, gaining consistency by construction"; the abstract describes an 8-participant exploratory evaluation and no gate/audit/repair machinery, so the contrast is consistent.
- verdict: KEEP

## S45_madaan2023selfrefine
- key: S45_madaan2023selfrefine
- opened: https://doi.org/10.52202/075280-2019 (→ https://www.proceedings.com/075280-2019.html); https://proceedings.neurips.cc/paper_files/paper/2023/hash/91edff07232fb1b55a505a9e9f6c0ff3-Abstract-Conference.html
- resolvable: YES (Curran DOI resolves; the official NeurIPS page lists the same DOI)
- metadata: MATCH (title; all 16 authors in bib order; Advances in Neural Information Processing Systems 36, Main Conference Track, Dec 2023; pages 46534–46594.)
- archival: archival as cited
- context: FAIR — abstract: "the same LLM provides feedback for its output and uses it to refine itself, iteratively … a single LLM as the generator, refiner and the feedback provider", exactly "feeds back language generated by the same untrusted model" / "feedback-driven repair".
- verdict: KEEP

## S46_chen2023selfdebug
- key: S46_chen2023selfdebug
- opened: https://arxiv.org/abs/2304.05128; https://openreview.net/forum?id=KuPixIqPiq
- resolvable: YES (arXiv v2, last revised 5 Oct 2023; OpenReview forum opens without login)
- metadata: MATCH for the arXiv record (title; Xinyun Chen, Maxwell Lin, Nathanael Schärli, Denny Zhou; 2023; eprint 2304.05128). The arXiv page carries no journal-ref/comments naming a venue.
- archival: Published at ICLR 2024 (poster) — OpenReview: "Published: 16 Jan 2024", decision "Accept (poster)", Submission 4261, https://openreview.net/forum?id=KuPixIqPiq. ICLR issues no publisher DOI; the OpenReview forum is the archival record. The bib note ("no archival venue … as of 2026-08-21") is now inaccurate.
- context: FAIR — abstract: the model "is able to identify its mistakes by investigating the execution results" and "leveraging feedback messages", i.e. feedback comes from executing the generated program, matching "consumes execution results from a trusted full-program runtime".
- verdict: REPLACE-WITH-ARCHIVAL (suggest @inproceedings, booktitle "The Twelfth International Conference on Learning Representations (ICLR 2024)", year 2024, url https://openreview.net/forum?id=KuPixIqPiq; keep eprint 2304.05128 as a secondary field)

## S47_solarlezama2006sketching
- key: S47_solarlezama2006sketching
- opened: https://doi.org/10.1145/1168857.1168907 (→ https://dl.acm.org/doi/10.1145/1168857.1168907); open-access full text https://dl.acm.org/doi/pdf/10.1145/1168857.1168907
- resolvable: YES
- metadata: MATCH (ACM DL: "Combinatorial sketching for finite programs"; Solar-Lezama, Tancau, Bodik, Seshia, Saraswat; ASPLOS XII: Proc. 12th Int. Conf. on Architectural Support for Programming Languages and Operating Systems; pages 404–415; published 20 Oct 2006; ACM. Cosmetic only: ACM prints "Bodik" without the accent the bib uses.)
- archival: archival as cited
- context: FAIR — the abstract does not say "counterexample", but Section 5.4 "Counterexample-Driven Solver" describes the synthesize–verify loop in which "a counterexample input provided by the verifier is added to the set of inputs considered by the synthesizer and the process repeats" (Fig. 4); "counterexample-guided inductive synthesis" is the standard retrospective name for this algorithm.
- verdict: KEEP

## S48_shinn2023reflexion
- key: S48_shinn2023reflexion
- opened: https://doi.org/10.52202/075280-0377 (→ https://www.proceedings.com/075280-0377.html); https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html
- resolvable: YES (Curran DOI resolves; official NeurIPS page lists the same DOI)
- metadata: MATCH (title, sentence case on the pages vs Title Case in bib, cosmetic; Shinn, Cassano, Gopinath, Narasimhan, Yao; NeurIPS 36, Main Conference Track, 2023; pages 8634–8652.)
- archival: archival as cited
- context: FAIR — abstract: agents "verbally reflect on task feedback signals, then maintain their own reflective text in an episodic memory buffer to induce better decision-making in subsequent trials", precisely "stores verbal self-reflections across trials".
- verdict: KEEP

## S49_haerder1983transaction
- key: S49_haerder1983transaction
- opened: https://doi.org/10.1145/289.291 (→ https://dl.acm.org/doi/10.1145/289.291); open-access PDF https://dl.acm.org/doi/pdf/10.1145/289.291 (landing page shows only a first-page image, so the PDF was opened for the abstract)
- resolvable: YES
- metadata: MATCH (ACM DL: "Principles of transaction-oriented database recovery"; Theo Haerder, Andreas Reuter; ACM Computing Surveys, Volume 15, Issue 4, pages 287–317; published Dec 1983; PDF header "Computing Surveys, Vol. 15, No. 4, December 1983".)
- archival: archival as cited
- context: FAIR — the paper defines atomicity as all-or-nothing and Transaction UNDO: "If a transaction aborts itself or must be aborted by the system … UNDO removes all effects of this transaction from the database", directly supporting "leaves the prior state intact on abort".
- verdict: KEEP

## S50_kambhampati2024llmmodulo
- key: S50_kambhampati2024llmmodulo
- opened: https://proceedings.mlr.press/v235/kambhampati24a.html
- resolvable: YES
- metadata: MATCH (PMLR: "Position: LLMs Can't Plan, But Can Help Planning in LLM-Modulo Frameworks"; Kambhampati, Valmeekam, Guan, Verma, Stechly, Bhambri, Saldyt, Anil B Murthy; Proc. 41st ICML, PMLR 235:22895–22907, 2024. PMLR's BibTeX splits the last author as "B Murthy, Anil"; the bib's "Murthy, Anil B." is an equivalent split, not an error.)
- archival: archival as cited
- context: FAIR — abstract: LLM-Modulo combines LLMs "with external model-based verifiers in a tighter bi-directional interaction regime", i.e. the model proposes and external sound critics accept or reject.
- verdict: KEEP

## S51_ichter2023saycan
- key: S51_ichter2023saycan
- opened: https://proceedings.mlr.press/v205/ichter23a.html
- resolvable: YES
- metadata: MATCH (PMLR: "Do As I Can, Not As I Say: Grounding Language in Robotic Affordances"; first author "brian ichter", then Brohan … Ahn in exactly the bib's order, followed by 20 further authors (45 total) that the bib truncates with "and others"; Proc. 6th Conference on Robot Learning, PMLR 205:287–318, 2023. Only difference: PMLR gives "Alexander T Toshev" (middle initial omitted in bib).)
- archival: archival as cited
- context: FAIR — abstract: pretrained skills "constrain the model to propose natural language actions that are both feasible and contextually appropriate" and "value functions associated with these skills provide the grounding", i.e. a state-dependent affordance check gates the language-proposed skill.
- verdict: KEEP

## S52_wang2025agentspec
- key: S52_wang2025agentspec
- opened: https://arxiv.org/abs/2503.18666; https://dl.acm.org/action/doSearch?AllField=AgentSpec+Customizable+Runtime+Enforcement+for+Safe+and+Reliable+LLM+Agents; https://ieeexplore.ieee.org/search/searchresult.jsp?queryText=AgentSpec%20Customizable%20Runtime%20Enforcement&highlight=true&returnType=SEARCH&matchPubs=true&returnFacets=ALL
- resolvable: YES (arXiv v3, last revised 31 Jul 2025)
- metadata: MATCH (title; Haoyu Wang, Christopher M. Poskitt, Jun Sun; 2025; arXiv Comments: "Accepted by the 48th IEEE/ACM International Conference on Software Engineering (ICSE 2026)"; no journal-ref or publisher DOI on the record.)
- archival: preprint — ICSE 2026 acceptance stated on arXiv, but ACM DL and IEEE Xplore searches returned no AgentSpec record on 2026-09-03; no proceedings DOI found. Bib note remains accurate (bump its date to 2026-09-03).
- context: FAIR — abstract: users "define structured rules that incorporate triggers, predicates, and enforcement mechanisms" for runtime constraints on LLM agents, matching both the "trigger–predicate–enforcement triples" sentence and "runtime enforcement for general agents".
- verdict: KEEP

## S53_li2025settingdc
- key: S53_li2025settingdc
- opened: https://openreview.net/forum?id=3Op7kJOvaD (including its BibTeX modal); https://openreview.net/pdf?id=3Op7kJOvaD
- resolvable: YES (forum and PDF open without login; "NeurIPS 2025 Workshop GenProCC", published 24 Sept 2025, last modified 08 Nov 2025, Track: Regular paper, CC BY 4.0, Submission 31)
- metadata: FIX: author order: "Li, Shengqi and Zeng, Ziyi and Xi, Jiajun and Zhu, Andrew and Ammanabrolu, Prithviraj" -> "Zeng, Ziyi and Li, Shengqi and Xi, Jiajun and Zhu, Andrew and Ammanabrolu, Prithviraj" (OpenReview heading, OpenReview BibTeX key `zeng2025setting`, and the PDF byline all list Ziyi Zeng first; Zeng and Li carry equal-contribution marks). Title, year, url match; OpenReview's booktitle is "Generative and Protective AI for Content Creation" and the PDF header reads "The First Workshop on Generative and Protective AI for Content Creation", consistent with the bib's venue label.
- archival: archival as cited (non-archival workshop paper; OpenReview is the record; no publisher DOI)
- context: FAIR — the paper designs "a structured API of game actions, each with predefined parameters and precondition checks, to ground the agents' decisions", with calls "validated against preconditions (initiative ownership, budgets, spell slots, range, line of sight …)", supporting both "tool calls with precondition checks" and "symbolic state management in generated game worlds".
- verdict: FIX-METADATA (author order; consider renaming the key to zeng2025settingdc)

## S54_zhou2025story2game
- key: S54_zhou2025story2game
- opened: https://arxiv.org/abs/2505.03547
- resolvable: YES (v1, submitted 6 May 2025; only version)
- metadata: MATCH (title "STORY2GAME: Generating (Almost) Everything in an Interactive Fiction Game"; Eric Zhou, Shreyas Basavatia, Moontashir Siam, Zexin Chen, Mark O. Riedl; 2025; eprint 2505.03547, cs.AI.)
- archival: preprint — no journal-ref or comments field on the arXiv record; only the arXiv DOI 10.48550/arXiv.2505.03547. Bib note remains accurate.
- context: FAIR — abstract: "The key to successful action generation is to use LLM-generated preconditions and effects of actions in the stories as guides for what aspects of the game state must be tracked and changed by the game engine", exactly "lets the LLM generate the action preconditions and effects it plays under".
- verdict: KEEP

## S55_huang2026beyond
- key: S55_huang2026beyond
- opened: https://arxiv.org/abs/2604.13824
- resolvable: YES (v1, submitted 15 Apr 2026)
- metadata: MATCH (title "Beyond State Consistency: Behavior Consistency in Text-Based World Models"; all 11 authors in bib order, including "ChenZhuo Zhao" capitalization; 2026; eprint 2604.13824, cs.LG; Comments: "20 pages, 2 figures".)
- archival: preprint — no journal-ref or venue on the record. Bib note remains accurate.
- context: FAIR — abstract: single-step state metrics "such as Exact Match … have been shown to be insufficient for capturing actual agent behavior", which supports "state consistency alone is not behavioral coherence". Note the paper is about world models for WebShop/TextWorld agents and says nothing about narrative; the "or narrative coherence" half of L1 is the manuscript's own extension, not attributable to this work. Consider wording so the citation covers only the behavioral half.
- verdict: KEEP

## S56_feng2025agentrr
- key: S56_feng2025agentrr
- opened: https://arxiv.org/abs/2505.17716
- resolvable: YES (v1, submitted 23 May 2025; only version)
- metadata: MATCH (title "Get Experience from Practice: LLM Agents with Record & Replay"; all 11 authors in bib order; 2025; eprint 2505.17716, cs.LG / cs.MA.)
- archival: preprint — no journal-ref or comments field on the record. Bib note remains accurate.
- context: OVERCLAIM (mild) — the abstract "proposes a new paradigm called AgentRR (Agent Record & Replay), which introduces the classical record-and-replay mechanism into AI agent frameworks" and explicitly targets experience reuse ("Replay these experiences in subsequent similar tasks"), so "record-and-replay for experience reuse" is fair, but calling it "an established agent paradigm" contradicts the paper's own self-description as new; the second context sentence ("agent record-and-replay") is FAIR. Suggest "a proposed agent paradigm" or "has been introduced as an agent paradigm".
- verdict: KEEP (bib entry correct; wording tweak in the manuscript text recommended)

## Summary

Counts per verdict (18 entries):
- KEEP: 16 (S39, S40, S41, S42, S44, S45, S47, S48, S49, S50, S51, S52, S54, S55, S56)
- FIX-METADATA: 1 (S53_li2025settingdc)
- REPLACE-WITH-ARCHIVAL: 1 (S46_chen2023selfdebug)
- DROP: 0

Resolvability: 18/18 YES. Citation contexts: 17 FAIR, 1 mild OVERCLAIM (S56 "established"), 0 UNRELATED.

Keys that need action:
- S53_li2025settingdc: swap author order to Zeng, Li, Xi, Zhu, Ammanabrolu (first author is Ziyi Zeng on OpenReview and the PDF).
- S46_chen2023selfdebug: convert to the ICLR 2024 poster record (OpenReview KuPixIqPiq); the "no archival venue" note is stale.

Optional text/notes tweaks (no bib change required):
- S56: soften "established agent paradigm" to "proposed".
- S55: limit the attribution to behavioral (not narrative) coherence.
- S44: bib note may cite the ICCC'26 presentation stated on arXiv.
- S52: bump the note's "as of" date to 2026-09-03 (still no ICSE 2026 DOI in ACM DL / IEEE Xplore).[0m
