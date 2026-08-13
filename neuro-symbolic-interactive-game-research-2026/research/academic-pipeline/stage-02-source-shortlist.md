# Stage 2 Source Shortlist / 문헌 후보군

Status: **USER APPROVED — 2026-08-12**  
Retrieval date: 2026-08-12  
Scope: 37 Stage-2 sources plus 5 Stage-8 lineage additions, 2011--2026; systems, games, evaluation, statistics, and reproducibility

## Evidence labels / 근거 등급

- **PR**: peer-reviewed final publication verified from an official publisher/proceedings page.
- **PR-OA**: peer-reviewed official proceedings/article without a publisher DOI.
- **ONLINE**: peer-reviewed online record or future issue assignment; metadata must be rechecked at submission.
- **PREPRINT**: not treated as archival peer-reviewed evidence.
- Metadata was cross-checked against official pages and, where available, Crossref and OpenAlex. Semantic
  Scholar returned HTTP 429 for much of the batch, so this packet does **not** claim complete three-index
  triangulation. Full claim-level verification is reserved for Stage 5.

## Shortlist

| ID | Evidence and primary link | 3W role | Intended use in TRACE-RPG | Claim boundary |
| --- | --- | --- | --- | --- |
| S01 | Vaucher et al., “IVIE: A Neuro-symbolic Approach to Incremental and Validated Generation of Interactive Fiction Worlds,” 2026, [arXiv:2606.13348](https://arxiv.org/abs/2606.13348). **PREPRINT / accepted-forthcoming non-archival material** | HOW/WHAT | Direct game-specific comparator for incremental world generation plus symbolic validation. | Not evidence that TRACE-RPG is correct or superior; publication status must not be overstated. |
| S02 | Figueiredo and Elumeze, “Symbolically Scaffolded Play,” 2025, [arXiv:2510.25820](https://arxiv.org/abs/2510.25820). **PREPRINT** | WHY/WHAT | Motivates role-sensitive constraint/creativity trade-offs in NPC dialogue. | Cannot anchor a central factual or SOTA claim alone. |
| S03 | Weir et al., “Ontologically Faithful Generation of Non-Player Character Dialogues,” EMNLP 2024, [doi:10.18653/v1/2024.emnlp-main.520](https://doi.org/10.18653/v1/2024.emnlp-main.520). **PR** | HOW/WHAT | Quest/entity grounding and NPC knowledge-faithfulness benchmark design. | Ontological grounding does not prove executable transition or disclosure safety. |
| S04 | He et al., “G-Retriever,” NeurIPS 2024, [doi:10.52202/079017-4224](https://doi.org/10.52202/079017-4224). **PR** | HOW/WHAT | Bounded relevant-subgraph retrieval comparator. | Retrieval quality is not a hard game-state guarantee. |
| S05 | Gutiérrez et al., “HippoRAG,” NeurIPS 2024, [doi:10.52202/079017-1902](https://doi.org/10.52202/079017-1902). **PR** | HOW/WHAT | Long-term multi-hop memory and latency/cost comparator. | Does not establish reduction of game contradictions. |
| S06 | Chhikara et al., “Mem0,” ECAI 2025, [doi:10.3233/FAIA251160](https://doi.org/10.3233/FAIA251160). **PR** | HOW/WHAT | Extraction--consolidation--retrieval memory baseline and systems metrics. | Conversational memory is not canonical event sourcing. |
| S07 | Park et al., “Generative Agents,” UIST 2023, [doi:10.1145/3586183.3606763](https://doi.org/10.1145/3586183.3606763). **PR** | HOW/WHAT | Memory/reflection/planning baseline and component ablation precedent. | Believability does not imply symbolic validity or authorization. |
| S08 | Shao et al., “Character-LLM,” EMNLP 2023, [doi:10.18653/v1/2023.emnlp-main.814](https://doi.org/10.18653/v1/2023.emnlp-main.814). **PR** | HOW/WHAT | Persona, experience, and affect-conditioned role-playing comparator. | Persona fidelity is distinct from factual and policy correctness. |
| S09 | Geng et al., “Grammar-Constrained Decoding for Structured NLP Tasks,” EMNLP 2023, [doi:10.18653/v1/2023.emnlp-main.674](https://doi.org/10.18653/v1/2023.emnlp-main.674). **PR** | HOW/WHAT | Syntax/schema-valid generation baseline. | Grammar constraints do not validate semantic preconditions or effects. |
| S10 | Beurer-Kellner et al., “Prompting Is Programming: A Query Language for Large Language Models,” PLDI/PACMPL 2023, [doi:10.1145/3591300](https://doi.org/10.1145/3591300). **PR** | HOW/WHAT | Constraint and bounded control-flow design. | Model-independent control flow is not a game-policy oracle. |
| S11 | Côté et al., “TextWorld,” CCIS 1017, 2019, [doi:10.1007/978-3-030-24337-1_3](https://doi.org/10.1007/978-3-030-24337-1_3). **PR** | HOW | Generated text-game environments, explicit state, and held-out evaluation. | Does not establish the proposed commit gate’s benefit. |
| S12 | Wang et al., “ScienceWorld,” EMNLP 2022, [doi:10.18653/v1/2022.emnlp-main.775](https://doi.org/10.18653/v1/2022.emnlp-main.775). **PR** | WHY/WHAT | Grounded interactive execution and held-out task/world evaluation. | Static QA versus environment gaps are motivation, not TRACE-RPG results. |
| S13 | Fan et al., “MineDojo,” NeurIPS 2022, [doi:10.52202/068431-1333](https://doi.org/10.52202/068431-1333). **PR** | WHY/HOW/WHAT | Open-ended knowledge-rich game-agent stress tests. | Does not provide transactional state guarantees. |
| S14 | Pérez-Liébana et al., “General Video Game AI: A Multitrack Framework,” IEEE ToG 2019, [doi:10.1109/TG.2019.2901021](https://doi.org/10.1109/TG.2019.2901021). **PR** | HOW/WHAT | Justifies separated agent/game/content tracks and multitrack reporting. | Does not prescribe TRACE-RPG’s metrics or gate. |
| S15 | Liu et al., “AgentBench,” ICLR 2024, [official proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/e9df36b21ff4ee211a8b71ee8b7e9f57-Abstract-Conference.html). **PR-OA** | WHY/WHAT | Cross-model interactive evaluation and failure taxonomy. | Aggregate benchmark rank cannot substitute for game-specific validity. |
| S16 | Ma et al., “AgentBoard,” NeurIPS 2024, [doi:10.52202/079017-2365](https://doi.org/10.52202/079017-2365). **PR** | WHY/HOW | Supports process/progress metrics in addition to terminal success. | Does not validate the proposed metric definitions. |
| S17 | Zhou et al., “SOTOPIA,” ICLR 2024, [official proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/b3075b88e583a0e98d8b24338a613060-Abstract-Conference.html). **PR-OA** | WHY/HOW/WHAT | Social-goal, cooperation, competition, and open-ended role-play scenarios. | Social benchmark results cannot be generalized to NPC safety. |
| S18 | Paglieri et al., “BALROG,” ICLR 2025, [official proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/hash/f0b1515be276f6ba82b4f2b25e50bef0-Abstract-Conference.html). **PR-OA** | WHY/WHAT | Long-horizon game reasoning and modality/model strata. | Does not establish a current universal game-agent SOTA. |
| S19 | Le Pelletier de Woillemont et al., “Automated Play-Testing through RL Based Human-Like Play-Styles Generation,” AIIDE 2022, [doi:10.1609/aiide.v18i1.21958](https://doi.org/10.1609/aiide.v18i1.21958). **PR** | HOW/WHAT | Adversarial synthetic-player and scenario-generation precedent. | Automated agents are not a replacement for human evaluation. |
| S20 | Ashby et al., “Personalized Quest and Dialogue Generation in Role-Playing Games,” CHI 2023, [doi:10.1145/3544548.3581441](https://doi.org/10.1145/3544548.3581441). **PR** | HOW/WHAT | Knowledge-graph plus language-model quest/dialogue comparator. | Knowledge-graph use alone does not prove symbolic safety. |
| S21 | Akoury et al., “A Framework for Exploring Player Perceptions of LLM-Generated Dialogue in Commercial Video Games,” Findings EMNLP 2023, [doi:10.18653/v1/2023.findings-emnlp.151](https://doi.org/10.18653/v1/2023.findings-emnlp.151). **PR** | WHY/HOW/WHAT | Grounded dialogue, pairwise preference, and qualitative player evaluation. | Player preference is not inferable from automated validity. |
| S22 | Hochreiter et al., “Beyond Pre-Defined Scripts: Player Perceptions on Generative NPC Dialogues,” IUI 2026, [doi:10.1145/3742413.3789221](https://doi.org/10.1145/3742413.3789221). **PR, 2026** | WHY/WHAT | Recent evidence on flexibility/naturalness and predictability/control trade-offs. | Its 62-participant findings do not transfer directly to TRACE-RPG. |
| S23 | Yin et al., “How Contextualized Generative AI Shapes Player Experience in Games,” *Entertainment Computing* 58, 101194, 2026, [doi:10.1016/j.entcom.2026.101194](https://doi.org/10.1016/j.entcom.2026.101194). **ONLINE** | WHY/WHAT | Contextualized generation and player-experience constructs. | September 2026 issue metadata must be rechecked; no symbolic-validity inference. |
| S24 | Yannakakis and Togelius, “Experience-Driven Procedural Content Generation,” IEEE TAFFC 2011, [doi:10.1109/T-AFFC.2011.6](https://doi.org/10.1109/T-AFFC.2011.6). **PR** | WHY/HOW | Theoretical basis for player-model-driven adaptation. | Affect adaptation does not imply affect-estimate accuracy or authority. |
| S25 | Melhart et al., “Moment-to-Moment Engagement Prediction through the Eyes of the Observer,” FDG 2020, [doi:10.1145/3402942.3402958](https://doi.org/10.1145/3402942.3402958). **PR** | HOW/WHAT | Continuous engagement annotation and uncertainty precedent. | Observed engagement is not the player’s latent ground truth. |
| S26 | Wang et al., “Do Vision Language Models Understand Human Engagement in Games?” 2026, [arXiv:2603.18480](https://arxiv.org/abs/2603.18480). **PREPRINT** | WHY/WHAT | Cautionary evidence for keeping affect as non-authoritative soft context. | Must be described as a recent preprint, not a settled SOTA result. |
| S27 | van der Lee et al., “Best Practices for the Human Evaluation of Automatically Generated Text,” INLG 2019, [doi:10.18653/v1/W19-8643](https://doi.org/10.18653/v1/W19-8643). **PR** | HOW | Construct, instruction, scale, sample, rater, reliability, and analysis protocol. | A checklist does not establish adequacy of a particular sample size. |
| S28 | Karpinska et al., “The Perils of Using Mechanical Turk to Evaluate Open-Ended Text Generation,” EMNLP 2021, [doi:10.18653/v1/2021.emnlp-main.97](https://doi.org/10.18653/v1/2021.emnlp-main.97). **PR** | WHY/HOW/WHAT | Supports trained/player-qualified raters, attention checks, and comparisons. | Findings should not be generalized to all crowdsourcing platforms. |
| S29 | Zheng et al., “Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena,” NeurIPS 2023, [doi:10.52202/075280-2020](https://doi.org/10.52202/075280-2020). **PR** | HOW/WHAT | Scalable auxiliary pairwise judge baseline and known bias controls. | LLM judging cannot replace blinded human evaluation for player experience. |
| S30 | Chen et al., “Humans or LLMs as the Judge? A Study on Judgement Bias,” EMNLP 2024, [doi:10.18653/v1/2024.emnlp-main.474](https://doi.org/10.18653/v1/2024.emnlp-main.474). **PR** | WHY/HOW/WHAT | Bias taxonomy and adversarial robustness checks for human/LLM judges. | Bias evidence does not make every LLM evaluation invalid; calibration is required. |
| S31 | Agarwal et al., “Deep Reinforcement Learning at the Edge of the Statistical Precipice,” NeurIPS 2021, [official proceedings](https://proceedings.neurips.cc/paper/2021/hash/f514cec81cb148559cf475e7426eed5e-Abstract.html). **PR-OA** | HOW/WHAT | Interval estimates, robust aggregates, and performance profiles across seeds. | Does not justify a fixed five-seed design. |
| S32 | Lakens et al., “Equivalence Testing for Psychological Research: A Tutorial,” AMPPS 2018, [doi:10.1177/2515245918770963](https://doi.org/10.1177/2515245918770963). **PR** | HOW | Preregistered equivalence/non-inferiority margins and TOST logic. | Does not justify the project’s provisional 2 percentage-point margin. |
| S33 | Pineau et al., “Improving Reproducibility in Machine Learning Research,” JMLR 2021, [official article](https://jmlr.org/papers/v22/20-303.html). **PR-OA** | WHY/HOW | Code/data/environment/seed disclosure and artifact-checklist basis. | Disclosure does not automatically produce byte-identical reproduction. |
| S34 | Henderson et al., “Towards the Systematic Reporting of the Energy and Carbon Footprints of Machine Learning,” JMLR 2020, [official article](https://jmlr.org/papers/v21/20-312.html). **PR-OA** | HOW | Hardware, runtime, measured energy, and carbon reporting boundary. | Hosted-provider energy must remain unobserved unless directly supplied. |
| S35 | Barr et al., “Random Effects Structure for Confirmatory Hypothesis Testing: Keep It Maximal,” *Journal of Memory and Language* 68(3), 2013, [doi:10.1016/j.jml.2012.11.001](https://doi.org/10.1016/j.jml.2012.11.001). **PR** | HOW | Crossed participant/item mixed-effects structure for human preference analysis. | Maximal models may require preregistered convergence simplification. |
| S36 | Scholak et al., “PICARD: Parsing Incrementally for Constrained Auto-Regressive Decoding from Language Models,” EMNLP 2021, [doi:10.18653/v1/2021.emnlp-main.779](https://doi.org/10.18653/v1/2021.emnlp-main.779). **PR** | HOW/WHAT | Incremental constrained-decoding comparator. | Syntactic admissibility is not semantic game-state correctness. |
| S42 | Buongiorno et al., “PANGeA: Procedural Artificial Narrative Using Generative AI for Turn-Based, Role-Playing Video Games,” AIIDE 2024, [doi:10.1609/aiide.v20i1.31876](https://doi.org/10.1609/aiide.v20i1.31876). **PR** | HOW/WHAT | Direct game-specific memory, validation, REST, and Unity-integration comparator. | Its LLM self-reflection validation is not deterministic state-relative authorization; its reported task accuracy is not comparable to TRACE-RPG fixture conformance. |

## Proposed evidence architecture / 제안 근거 구조

| Manuscript section | Primary anchors | Planned role |
| --- | --- | --- |
| Problem and novelty | S01--S03, S11--S18, S20--S23 | Define the gap between expressive generation, interactive execution, and hard validity. |
| Transaction gate | S03, S09, S10, S36 | Separate structural decoding from independent semantic validation and commit. |
| Memory and graph context | S04--S08 | Compare bounded retrieval and memory without granting them state authority. |
| Game benchmark | S11--S19 | Build held-out, adversarial, multitrack scenarios and process metrics. |
| Player/affect evaluation | S21--S30, S24--S28 | Define matched-validity human comparisons and non-authoritative affect signals. |
| Statistics and reproducibility | S31--S35 | Fix estimands, uncertainty, mixed effects, equivalence, artifacts, and reporting. |

## Exclusion and reserve rules / 제외·보류 규칙

- Blog posts, vendor benchmarks without frozen artifacts, and search snippets are discovery aids only.
- Preprints S01, S02, and S26 may motivate novelty or risk but require peer-reviewed corroboration for central claims.
- S23 remains conditional on final bibliographic verification because its issue is assigned after this retrieval date.
- A source is removed if its primary record, methods, or reported population cannot be independently recovered.
- New 2026 sources may be added at Stage 2.5 only when they materially change novelty, methods, or evaluation.

## Decision requested / 사용자 결정

Approve this 36-source pool, identify any source to remove, or name a required paper/author/venue to add.
Approval unlocks Stage 2.5 gap analysis and Stage 3 IMRaD outline construction.

## 2026-08-13 comparator addendum

S42 was added after the user-requested final literature refresh because it materially changes the
novelty boundary: IVIE cannot be ranked as the single “closest” comparator when archival PANGeA
already combines game-engine integration, memory, and validation. The Scrapling research-harvest
gate was run before retrieval; official AAAI/OJS, Crossref, OpenAlex, and Semantic Scholar metadata
agree on DOI, title, authors, date, venue, volume, issue, and pages. The official paper documents an
LLM yes/no self-reflection and iterative-refinement validator, so the comparison is bounded to
architecture and authority placement rather than superiority.
