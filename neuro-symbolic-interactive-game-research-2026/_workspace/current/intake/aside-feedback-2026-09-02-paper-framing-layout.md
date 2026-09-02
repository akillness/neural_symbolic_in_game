<!-- Filed verbatim (Aside internal citation tags stripped) from an `aside exec --effort high` research session run on 2026-09-02 by the parallel Claude Code session. Evidence level: external web search feedback, [INFERENCE] for this project; nothing here is a measured result. -->

# Aside search-based feedback: TRACE-RPG paper framing and page layout

Retrieval date: **2026-09-02**

Scope: public web research only. No manuscript-title search, login, purchase, submission, or posting was performed.

## 1. IEEE ToG author guidance (with URLs)

### Submission category and page budget

- IEEE ToG lists **short papers as 6–8 pages**, but its detailed paragraph calls them “limited to 6 pages.” References and optional biographies count toward that total; supplementary material does not.
- Pages beyond six incur a **mandatory US$200 per-page charge**. A seven-page paper therefore implies US$200, and an eight-page paper US$400, unless the journal clarifies otherwise.
- The page-limit page contains internally inconsistent wording, including an older statement that papers over 12 pages require justification. Treat six pages as the safe short-paper target and confirm the eight-page ceiling with the editor before relying on it.
- Abstract: **150–200 words**, one paragraph, self-contained, with no references, footnotes, displayed equations, or tables. The journal requests 2–5 keywords.

Source: [IEEE ToG submission guidelines](https://transactions.games/submit/submission-guidelines). The page lists short papers as 6–8 pages, states that short papers are limited to six pages in the detailed guidance, and imposes US$200 per page over six.

**Implication for the current draft:** fifty references plus seven pages of body content are unlikely to fit a safe six-page submission. Decide immediately between:

1. a six-page short paper with approximately 30–35 essential references and most implementation detail in supplementary material;
2. a paid seven- or eight-page short paper, after editorial confirmation; or
3. a full or Immersive Article if the playable experience is itself a primary contribution.

ToG describes an **Immersive Article** as a 6–14-page paper with an interactive ZIP. It may fit “The Sealed Lighthouse,” but changing category would change the paper’s framing and should not be done only to gain space: [Immersive Article Explained](https://transactions.games/submit/immersive-article-explained).

### Double-anonymous review

A date-specific notice says submissions from **2025-01-01 onward must be fully anonymized**, including names, affiliations, biographies, funding acknowledgments, and other identifying information. A later paragraph on the same page still says single-blind and asks authors to list their names. The newer dated notice should control, but the contradiction should be confirmed in ScholarOne or with the editor.

Sources:

- [IEEE ToG submission guidelines](https://transactions.games/submit/submission-guidelines)
- [IEEE CIS Information for Authors](https://cis.ieee.org/publications/t-games/tciaig-information-for-authors)
- [ScholarOne submission portal](https://mc.manuscriptcentral.com/tg-ieee)

### AI-generated-content disclosure

IEEE-wide policy requires disclosure of AI-generated **text, figures, images, or code** in the acknowledgments, identifying the system, affected sections, and level of use. Editing and grammar assistance are generally exempt, although disclosure is recommended. IEEE explicitly includes text, figures, images, and code in its disclosure rule and places the disclosure in acknowledgments.

There is a procedural conflict: ToG requires acknowledgments to be removed for double-anonymous review, while IEEE’s AI policy places disclosure there. Recommended handling:

- Do not expose identifying acknowledgment information in the blinded manuscript.
- Prepare the full AI-use disclosure for the de-anonymized version.
- If generative AI created manuscript content, figures, or submitted code, ask the editor whether a non-identifying disclosure should appear in the blinded paper or only in ScholarOne/cover materials.
- Merely studying an LLM as the system component does not itself mean the manuscript contains AI-generated content.

Source: [IEEE Submission and Peer Review Policies](https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/).

### Reproducibility and playable artifacts

IEEE **encourages**, rather than universally mandates, sharing methods, data, code, and other research outputs. It points authors toward repositories such as Zenodo, figshare, Dryad, and Code Ocean. IEEE describes data and code sharing as encouraged and provides repository and Code Ocean options.

For TRACE-RPG, the checksums and semantic-replay claim will be stronger if the supplement contains:

- frozen E1 fixtures;
- parser and predicate versions;
- policy and ontology snapshots;
- accepted, rejected, and repaired trace records;
- expected replay outcomes;
- a manifest connecting every result-table row to the corresponding fixture or trace;
- the Godot build or source, subject to anonymous-review rules.

Source: [IEEE Research Reproducibility](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/research-reproducibility/).

### Graphics

IEEE’s current graphics guidance specifies:

- one-column width: **3.5 in / 88.9 mm**;
- two-column width: **7.16 in / 182 mm**;
- color and grayscale raster graphics: over 300 dpi;
- line art: over 600 dpi;
- vector graphics preferred;
- effective figure type around 9–10 pt;
- color should not be the sole encoding.

Source: [IEEE Resolution and Size](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/resolution-and-size/). IEEE specifies 3.5-inch and 7.16-inch target widths and greater-than-300/600-dpi raster requirements.

### Other audit findings

- No current ToG or IEEE Author Center page inspected imposed a separate CRediT contribution-statement requirement.
- The ToG page’s print-era illustration instructions conflict with newer IEEE Author Center guidance. Follow the current Author Center for file preparation and the current IEEEtran template for layout.
- ToG says extended prior work must explain the relationship and new contribution **inside the manuscript**, not only in the cover letter.

## 2. Contribution legibility moves (5 concrete moves, cited)

### 1. Replace the page-1 C1–C5 table with three refutable contribution bullets

Five rows make the reader decode an internal taxonomy before understanding the central result. Use three claims that a reviewer can prove or disprove, each ending with section and evidence pointers.

A possible structure:

- **Commit gate.** We define a runtime boundary that admits an LLM-proposed event only after type-strict parsing, external action-policy evaluation, and six deterministic predicates over the current game state (Sec. III; E1).
- **Bounded repair.** We define a repair operator that exposes only validator error payloads and report a small live screening result of 5/5 repaired cases versus 0/5 blind retries; this is pilot evidence, not a population estimate (Sec. IV-B; E2).
- **Trace-linked realization.** We connect every decision to checksummed, semantically replayable records and demonstrate the boundary in a Godot 4 slice plus a closed-world ontology-link simulation (Secs. IV-C and V; E3 and artifact).

Widom recommends a bulleted “Summary of Contributions” with section pointers, while Peyton Jones recommends refutable claims instead of descriptions such as “we present a system.”

Sources:

- [Jennifer Widom, Tips for Writing Technical Papers](https://cs.stanford.edu/people/widom/paper-writing.html) Widom recommends contribution bullets with section pointers and says an important technical contribution should be articulated by page three.
- [Simon Peyton Jones, How to Write a Great Research Paper](https://www.cis.upenn.edu/~sweirich/icfp-plmw15/slides/peyton-jones.pdf)

### 2. Make the first page answer problem, failure, boundary, and evidence

By the end of page one, readers should know:

1. what can go wrong when generated events mutate authoritative game state;
2. why prompt-only constraints or model self-checking do not establish admission correctness;
3. where the trusted boundary is;
4. exactly what is evaluated.

Do not spend page one enumerating all six predicates or all evidence lanes. State the invariant first: **untrusted generation may propose, but cannot directly commit state**.

Widom’s introduction structure asks what the problem is, why it matters, why it is hard, why prior approaches are insufficient, and what the approach and result are. Peyton Jones treats the introduction as a one-page problem-and-contribution contract.

Sources:

- [Widom writing guide](https://cs.stanford.edu/people/widom/paper-writing.html)
- [Peyton Jones writing guide](https://simon.peytonjones.org/great-research-paper)

### 3. Use one bold, declarative positioning sentence

Near the end of the opening paragraph, use a single bold sentence such as:

**TRACE-RPG treats generated game events as untrusted transaction proposals and permits state mutation only through an external, deterministic commit gate.**

This should be the paper’s position, not a marketing slogan. ICML’s position-paper guidance explicitly recommends stating the position in bold text, and its review guidance treats presentation and contribution legibility as independently reviewable qualities.

Source: [ICML 2026 Reviewer Instructions](https://icml.cc/Conferences/2026/ReviewerInstructions).

### 4. Introduce one running Lighthouse trace before the formal architecture

Use one compact event throughout the paper:

`proposal → parse → policy check → failed predicate → error payload → ρ repair → accepted commit → replay`

Show the concrete state fields changed and the trace identifiers retained. Then reuse the same example in the predicate table, repair description, and replay discussion.

This removes repeated toy examples and gives readers a stable map between formal notation and the playable system. Widom explicitly recommends a running example and a top-down description.

Source: [Widom writing guide](https://cs.stanford.edu/people/widom/paper-writing.html).

### 5. Make every page-1 claim resolve to a result and limitation

Audit the abstract, bold position, contribution bullets, results headings, discussion, and conclusion as one claim chain. In particular:

- E1 can support deterministic conformance claims on frozen fixtures.
- E2 supports only a small screening observation, not general repair efficacy.
- E3 supports behavior within the declared closed world, not open-world ontology correctness.
- The Godot slice supports integration and playability, not external validity by itself.

The NeurIPS checklist asks whether abstract and introduction claims match the actual contributions, assumptions, and limitations.

Sources:

- [NeurIPS Paper Checklist](https://neurips.cc/public/guides/PaperChecklist)
- [NeurIPS 2025 Reviewer Guidelines](https://neurips.cc/Conferences/2025/ReviewerGuidelines)

## 3. Teaser/overview figure norms and float-placement pitfalls (cited)

### Do not treat an ACM-style teaser as an IEEEtran norm

Base IEEEtran has no generic teaser mechanism. Its class documentation says IEEE journals never place floats in the first column of page one and rarely place them in the second column. A page-1 hero figure is therefore risky unless ToG explicitly approves it.

The teaser mechanisms in ACM’s `acmart` class and IEEE VGTC/TVCG journal-track templates are venue-specific. They should not be copied into an ordinary ToG IEEEtran manuscript.

Sources:

- [How to Use the IEEEtran LaTeX Class](https://attend.ieee.org/argencon-2026/wp-content/uploads/sites/814/How-to-Use-the-IEEEtran-LATEX-Class.pdf) 
- [IEEEtran CTAN record](https://ctan.org/pkg/ieeetran)
- [ACM class guide](https://mirrors.ctan.org/macros/latex/contrib/acmart/acmguide.pdf)
- [TVCG journal-track formatting](https://tc.computer.org/vgtc/publications/journal)

### Recommended TRACE-RPG overview placement

Use the trust-boundary/pipeline overview as a **top-of-page, two-column `figure*` on page two**, not as a page-one teaser.

The figure should show one left-to-right transaction:

1. LLM proposal, outside trust boundary
2. strict parser
3. external action policy
4. six state-relative predicates
5. reject or bounded repair
6. commit
7. checksummed trace and semantic replay

Attach E1, E2, and E3 labels only at the stage each lane actually measures. This prevents the evidence-lane table and architecture figure from competing for the same explanatory role.

### `figure*` pitfalls

- `figure*` cannot appear on the same page where it is defined. Declare it earlier in the source than the intended page.
- IEEEtran strongly favors top floats.
- Bottom placement normally does not work without float patches.
- Wide and narrow floats can appear out of numerical order.
- If a patch is required, IEEEtran documentation recommends `dblfloatfix`; do not combine incompatible float patches.
- Do not use `cuted.sty`, `midfloat.sty`, or equivalent tricks to force a full-width object across the middle of two columns. IEEEtran explicitly warns against these packages.
- A first textual reference should precede the float, with the float on that page or the next when possible.

Sources:

- [IEEEtran HOWTO](https://attend.ieee.org/argencon-2026/wp-content/uploads/sites/814/How-to-Use-the-IEEEtran-LATEX-Class.pdf)
- [IEEE PES formatted-paper guidance](https://ieee-pes.org/publications/authors-kit/preparation-of-a-formatted-technical-work/)
- [IEEE TAP submission preparation](https://ieeeaps.org/ieee-tap/for-authors/how-to-prepare-your-submission)

### Figure readability and captions

- Size diagrams to exactly `\columnwidth` or `\textwidth`.
- Test the final PDF at 100% and in grayscale.
- Keep labels at approximately body-text size.
- Use shape, border, or pattern in addition to color for accepted, rejected, repaired, and replayed states.
- In Transactions style, cite **“Fig. 1”**, not “Figure 1.”
- Figure captions go below figures; table titles go above tables.
- Captions should explain how to read the figure, not merely restate its title.

Sources:

- [IEEE Create Graphics](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/)
- [IEEE Resolution and Size](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/resolution-and-size/)
- [IEEE Editorial Style Manual for Authors](https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/sites/7/IEEE-Editorial-Style-Manual-for-Authors.pdf)
- [Ten Simple Rules for Better Figures](https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1003833)

## 4. 2025-2026 related-work candidates (table: title | authors | venue/year | URL | relevance verdict)

Search coverage included arXiv, Google Scholar, OpenAlex, and Semantic Scholar. Semantic Scholar was heavily rate-limited, and OpenAlex omitted several confirmed arXiv papers. Absence from either index was therefore not treated as evidence of absence.

| title | authors | venue/year | URL | relevance verdict |
|---|---|---|---|---|
| AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents | Haoyu Wang; Christopher M. Poskitt; Jun Sun | ICSE 2026 accepted; arXiv 2025 | https://arxiv.org/abs/2503.18666 | **Must cite.** Closest general precedent for trigger/predicate/enforcement runtime constraints over LLM-agent actions. TRACE-RPG must distinguish its game-state semantics, parsing boundary, repair contract, and replay records. AgentSpec defines structured runtime rules containing triggers, predicates, and enforcement mechanisms. |
| Setting the DC: Tool-Grounded D&D Simulations to Test LLM Agents | Ziyi Zeng; Shengqi Li; Jiajun Xi; Andrew Zhu; Prithviraj Ammanabrolu | NeurIPS GenProCC Workshop, 2025 | https://openreview.net/forum?id=3Op7kJOvaD | **Must cite.** Closest game-side analogue: structured action APIs and precondition checks separate narration from mechanically valid state changes. Distinguish tool calling from TRACE-RPG’s free-text parse-and-admit boundary. |
| Game Knowledge Management System: Schema-Governed LLM Pipeline for Executable Narrative Generation in RPGs | Aynigar Rahman; Aihe Yu; Kyungeun Cho | Systems 14(2), 2026 | https://doi.org/10.3390/systems14020175 | **Must cite.** Schema-governed generation, repair, and engine-aligned knowledge admission in an RPG. Distinguish authored knowledge admission from runtime event commitment. |
| STORY2GAME: Generating (Almost) Everything in an Interactive Fiction Game | Eric Zhou; Shreyas Basavatia; Moontashir Siam; Zexin Chen; Mark O. Riedl | arXiv, 2025 | https://arxiv.org/abs/2505.03547 | **Must cite.** Generates action preconditions and effects and grounds play in tracked game state. Key contrast: its constraints are LLM-generated rather than independently fixed external policy. STORY2GAME uses LLM-generated preconditions and effects to guide what the engine tracks and changes. |
| IVIE: A Neuro-symbolic Approach to Incremental and Validated Generation of Interactive Fiction Worlds | Micaela Vaucher; Santiago Silveira; Santiago Góngora; Luis Chiruzzo | ICCC 2026; arXiv 2026 | https://arxiv.org/abs/2606.13348 | **Must cite.** Direct neuro-symbolic validated world-generation neighbor. Its reported puzzle-constraint leaks motivate TRACE-RPG’s strict admission boundary without proving TRACE-RPG solves every coherence problem. IVIE reports that some inconsistencies bypass puzzle constraints and some structurally impossible goals pass validation. |
| World-State Transformations for Neuro-symbolic Interactive Storytelling | Santiago Góngora; Luis Chiruzzo; Gonzalo Méndez; Pablo Gervás | arXiv, 2026 | https://arxiv.org/abs/2605.24719 | **Must cite.** LLM predictions trigger pre-programmed world-state transformations. Distinguish prediction-triggered transformations from explicit event admission, rejection, and repair. The work uses LLM predictions to trigger pre-programmed transformations intended to preserve world-state consistency. |
| Fly, Fail, Fix: Iterative Game Repair with Reinforcement Learning and Large Multimodal Models | Alex Zook; Josef Spjut; Jonathan Tremblay | RL and Video Games Workshop at RLC, 2025 | https://arxiv.org/html/2507.12666v1 | **Must cite for repair.** Game-specific iterative repair driven by play traces. Contrast behavioral, stochastic feedback with TRACE-RPG’s deterministic validator-error payload. The paper iteratively modifies Flappy Bird configurations using RL play traces supplied to a multimodal model. |
| Agent-R: Training Language Model Agents to Reflect via Iterative Self-Training | Siyu Yuan; Zehui Chen; Zhiheng Xi; Junjie Ye; Zhengyin Du; Jiecao Chen | arXiv, 2025 | https://arxiv.org/abs/2501.11425 | **Strong contrast.** Representative model-internal trajectory repair. Use it to separate reflection/self-training from bounded repair grounded only in an external validator’s error payload. |
| Get Experience from Practice: LLM Agents with Record & Replay (AgentRR) | Erhu Feng; Wenbo Zhou; Zibin Liu; Le Chen; Yunpeng Dong; Cheng Zhang; Yisheng Zhao; Dong Du; Zhichao Hua; Yubin Xia; Haibo Chen | arXiv, 2025 | https://arxiv.org/abs/2505.17716 | **Must cite for replay.** Establishes record-and-replay as an agent paradigm. Clarify that TRACE-RPG claims semantic replay of admitted game-state transitions, not general experience reuse. |
| PROV-AGENT: Unified Provenance for Tracking AI Agent Interactions in Agentic Workflows | Renan Souza; Amal Gueroudji; Stephen DeWitt; Daniel Rosendo; Tirthankar Ghosal; Robert Ross; Prasanna Balaprakash; Rafael Ferreira da Silva | IEEE e-Science, 2025 | https://arxiv.org/abs/2508.02866 | **Must cite for provenance.** W3C-PROV-aligned tracking of prompts, responses, and decisions. Distinguish provenance representation from checksum integrity and deterministic state replay. |
| From Agent Traces to Trust: A Survey of Evidence Tracing and Execution Provenance in LLM Agents | Yiqi Wang et al. | arXiv, 2026 | https://arxiv.org/abs/2606.04990 | **Must cite as taxonomy.** Use its trace-source, provenance-relation, timing, and trust-function vocabulary rather than presenting “trace-linked” as an unoccupied area. |
| GameGen-Verifier: Parallel Keypoint-Based Verification for LLM-Generated Games via Runtime State Injection | Chaobo Jia; Ruipeng Wan; Ting Sun; Weihao Tan; Borui Wan; Yuxuan Tong; Guangming Sheng; Hong Xu | arXiv, 2026 | https://arxiv.org/abs/2605.07442 | **Strong adjacent citation.** Verifies generated games by injecting runtime states and testing keypoint assertions. Its unit is a generated game artifact, not an individual proposed event. |
| Beyond State Consistency: Behavior Consistency in Text-Based World Models | Youling Huang; Guanqiao Chen; Junchi Yao; Lu Wang; Fangkai Yang; Chao Du; ChenZhuo Zhao; Pu Zhao; Qingwei Lin; Saravan Rajmohan; Dongmei Zhang | arXiv, 2026 | https://arxiv.org/abs/2604.13824 | **Required limitation citation.** Challenges the sufficiency of state consistency alone. Use it to bound the six predicates: they establish declared invariants, not complete behavioral or narrative coherence. |

### Recommended novelty sentence

> Prior work separately demonstrates runtime specification enforcement for general LLM agents, symbolic or schema-governed state management in generated game worlds, verifier-guided game repair, and agent provenance or replay. TRACE-RPG studies their intersection at an interactive game-state commit boundary: free-form proposals are parsed, checked against an independently defined policy and deterministic state predicates, optionally repaired from bounded validator feedback, and recorded for semantic replay.

This is defensible only as an **intersection claim**, not as “the first verified LLM game system.” No search can prove universal absence, and several 2025–2026 neighbors are very close.

## 5. Playable-artifact presentation examples (3, cited)

### 1. Live Game Design: Prototyping at the Speed of Play

- **Venue:** FDG 2025
- **Author:** Riemer van Rozen
- **URL:** https://dl.acm.org/doi/10.1145/3723498.3723726
- **Presentation pattern:** Section 2 is a six-step playable tutorial with successive rule-state figures. Later figures separate architecture, data representation, editor views, and the running simulator. The implementation section gives an explicit versioned and licensed artifact statement for Vie v0.0.7, and the appendix supplies a one-page notation cheat sheet.
- **TRACE-RPG lesson:** Make the Lighthouse sequence a paper-readable interaction walkthrough, separate conceptual architecture from actual Godot screenshots, and state artifact version/platform/license in one visible place.

The full paper describes the prototype as simultaneously playable and editable, and its sections separately present the conceptual and implemented views. Vie is presented as a game-making game for simultaneous prototyping and playtesting.

### 2. SoulGarden: A Gamified Meditation Application

- **Venue:** CHI PLAY 2025, PACMHCI
- **Authors:** Oliver Braese; Jeanine Kirchner-Krath; Marc Schubhan; Donald Degraen; Maximilian Altmeyer
- **URL:** https://dl.acm.org/doi/pdf/10.1145/3748597
- **Presentation pattern:** a full-width page-one end-state screenshot; a master interface screenshot with twelve numbered callouts; smaller screenshots for individual mechanics; a hypotheses-to-measures table; and a study-flow diagram.
- **TRACE-RPG lesson:** A single annotated Godot overview is more informative than an unstructured capture strip. Number only the UI features needed to understand proposal, rejection, repair, commit, and replay.
- **Caution:** SoulGarden uses the PACMHCI/ACM format, so its page-one teaser is visual precedent, not evidence that ToG permits the same placement.

### 3. Baba is Y’all 2.0: Design and Investigation of a Collaborative Mixed-Initiative System

- **Venue:** IEEE Transactions on Games, vol. 16, no. 1, 2024
- **Authors:** Megan Charity; Isha Dave; Ahmed Khalifa; Julian Togelius
- **URL:** https://arxiv.org/html/2203.02035v2
- **IEEE record:** https://ieeexplore.ieee.org/document/9956016
- **Presentation pattern:** the system-description section uses one subsection and screenshot per interactive module. Other figures compare v1 and v2, show serialized level data beside its rendering, and display generated levels grouped by authorship.
- **TRACE-RPG lesson:** Present the Godot artifact by research function rather than as a gallery. Pair a serialized trace/event with its rendered consequence and show rejected, repaired, and committed outcomes in parallel columns.

The author version identifies Baba is Y’all as a playable mixed-initiative level-design prototype and reports a user evaluation. The paper presents an updated mixed-initiative prototype and connects the website, user-created levels, and evaluation.

## 6. Top 10 prioritized layout/framing recommendations (what, why, evidence URL, effort S/M/L)

| Priority | What | Why | Evidence URL | Effort |
|---:|---|---|---|:---:|
| 1 | **Freeze the submission category and six-, seven-, or eight-page budget before editing.** Treat six pages as the safe short-paper baseline; obtain clarification before relying on eight. | The official page simultaneously says “6–8” and “limited to 6,” while charging US$200 for every page over six. References count. Layout work will otherwise optimize against an uncertain target. | https://transactions.games/submit/submission-guidelines | S |
| 2 | **Replace the C1–C5 page-one table with three refutable, section-anchored bullets.** | Five labels fragment one contribution into implementation inventory. Three claims map cleanly to gate, repair, and trace-linked realization. | https://cs.stanford.edu/people/widom/paper-writing.html; https://www.cis.upenn.edu/~sweirich/icfp-plmw15/slides/peyton-jones.pdf | M |
| 3 | **Put the trust-boundary thesis in the first paragraph and bold it once.** | Reviewers should not have to infer whether the paper contributes generation, game design, validation, or runtime enforcement. | https://icml.cc/Conferences/2026/ReviewerInstructions; https://neurips.cc/public/guides/PaperChecklist | S |
| 4 | **Move the architecture overview to a top-of-page `figure*` on page two and declare it early in the source.** | Base IEEEtran discourages page-one floats, and double-column floats cannot appear on the page where they are defined. | https://attend.ieee.org/argencon-2026/wp-content/uploads/sites/814/How-to-Use-the-IEEEtran-LATEX-Class.pdf | M |
| 5 | **Use one running Lighthouse event across introduction, architecture, validation, repair, and replay.** | A repeated concrete trace reduces notation cost and makes the trusted boundary inspectable before the reader encounters every predicate. | https://cs.stanford.edu/people/widom/paper-writing.html | M |
| 6 | **Reorganize related work into four contrasts: runtime enforcement, symbolic game-state systems, verifier-guided repair, and provenance/replay. End with an intersection claim.** | This is more defensible than claiming general novelty and directly accommodates AgentSpec, STORY2GAME/IVIE, Fly Fail Fix, AgentRR, and PROV-AGENT. | https://arxiv.org/abs/2503.18666; https://arxiv.org/abs/2505.03547; https://arxiv.org/abs/2606.13348; https://arxiv.org/html/2507.12666v1; https://arxiv.org/abs/2505.17716 | M |
| 7 | **Collapse the crowded page 3–4 material. Keep one overview figure, one predicate table, and one pseudocode block; move the repair-operator table and low-level state machine detail to the supplement unless each encodes a distinct claim.** | Multiple representations of the same pipeline consume scarce short-paper space and split attention. IEEE recommends selective graphics, while figure guidance prioritizes one legible message. | https://proceedingsoftheieee.ieee.org/resources/guidelines-for-figures-and-tables/; https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1003833 | M |
| 8 | **Replace the generic Godot capture strip with a numbered causal sequence: proposed, rejected, repaired, committed, replayed. Include the trace ID and one changed state field.** | This turns “playable” from decoration into evidence of the claimed boundary and follows strong FDG/ToG artifact-presentation precedents. | https://dl.acm.org/doi/10.1145/3723498.3723726; https://arxiv.org/html/2203.02035v2 | M |
| 9 | **Turn the evidence-boundary figure into a compact claim-to-evidence table. Explicitly mark E2 as pilot-only and E3 as closed-world.** | The key review risk is not missing data but overgeneralization across heterogeneous evidence lanes. The checklist requires claims, assumptions, and limitations to match. | https://neurips.cc/public/guides/PaperChecklist; https://arxiv.org/abs/2604.13824 | S |
| 10 | **Add an anonymized artifact/replay availability box and run a final compliance pass for anonymity, AI disclosure, figure size, grayscale readability, and caption form.** | Reproducibility is central to the trace claim, while anonymization and AI-disclosure instructions currently conflict. Resolving them before submission avoids a preventable administrative return. | https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/research-reproducibility/; https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/; https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/resolution-and-size/ | M |

### Suggested six-page allocation

| Page | Recommended dominant content |
|---|---|
| 1 | Abstract; problem and trust-boundary thesis; running event; three contribution bullets |
| 2 | Related-work positioning; top-spanning architecture/trace overview |
| 3 | formal admission model; six-predicate table; compact pseudocode |
| 4 | E1 deterministic conformance results; bounded-repair definition and E2 pilot |
| 5 | E3 closed-world simulation; causal Godot artifact sequence; replay manifest |
| 6 | evidence-boundary table; limitations, ethics/AI disclosure note, conclusion, compressed references |

If seven or eight pages are approved and budgeted, spend the extra space on clearer results and threats, not additional architecture diagrams.

## Sources (numbered list of every URL opened with title and retrieval date)

The ledger below includes every stable content page individually inspected or fetched and the four requested search surfaces. Repeated arXiv versions are grouped under the same numbered entry but every opened version URL is shown. Transient generated API-query URLs were used for discovery but are not suitable citation targets; the stable records selected from them appear below. All were retrieved **2026-09-02**.

1. [Submission guidelines, IEEE Transactions on Games](https://transactions.games/submit/submission-guidelines), retrieved 2026-09-02.
2. [Information for Authors, IEEE Computational Intelligence Society](https://cis.ieee.org/publications/t-games/tciaig-information-for-authors), retrieved 2026-09-02.
3. [Immersive Article Explained, IEEE Transactions on Games](https://transactions.games/submit/immersive-article-explained), retrieved 2026-09-02.
4. [IEEE ToG ScholarOne portal](https://mc.manuscriptcentral.com/tg-ieee), retrieved 2026-09-02.
5. [Submission and Peer Review Policies, IEEE Author Center](https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/), retrieved 2026-09-02.
6. [Research Reproducibility, IEEE Author Center](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/research-reproducibility/), retrieved 2026-09-02.
7. [Create Graphics for Your Article, IEEE Author Center](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/), retrieved 2026-09-02.
8. [Resolution and Size, IEEE Author Center](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/resolution-and-size/), retrieved 2026-09-02.
9. [File Formatting, IEEE Author Center](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/file-formatting/), retrieved 2026-09-02.
10. [Structure Your Article, IEEE Author Center](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-the-text-of-your-article/structure-your-article/), retrieved 2026-09-02.
11. [Author Responsibilities, IEEE Author Center](https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/author-responsibilities/), retrieved 2026-09-02.
12. [IEEE Editorial Style Manual for Authors](https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/sites/7/IEEE-Editorial-Style-Manual-for-Authors.pdf), retrieved 2026-09-02.
13. [How to Use the IEEEtran LaTeX Class](https://attend.ieee.org/argencon-2026/wp-content/uploads/sites/814/How-to-Use-the-IEEEtran-LATEX-Class.pdf), retrieved 2026-09-02.
14. [IEEEtran package record, CTAN](https://ctan.org/pkg/ieeetran), retrieved 2026-09-02.
15. [How to Use the IEEEtran LaTeX Templates, IEEE Publication Technology Department, version 1](https://arxiv.org/html/2109.09506v3), retrieved 2026-09-02.
16. [How to Use the IEEEtran LaTeX Templates, IEEE Publication Technology Department, version 2](https://arxiv.org/html/2312.17663v2), retrieved 2026-09-02.
17. [IEEE journal-template example mirrored on arXiv](https://arxiv.org/html/2404.04907v1), retrieved 2026-09-02.
18. [Preparation of a Formatted Transactions/Journal Paper, IEEE PES](https://ieee-pes.org/publications/authors-kit/preparation-of-a-formatted-technical-work/), retrieved 2026-09-02.
19. [How to Prepare Your Submission, IEEE Transactions on Antennas and Propagation](https://ieeeaps.org/ieee-tap/for-authors/how-to-prepare-your-submission), retrieved 2026-09-02.
20. [Guidelines for Figures and Tables, Proceedings of the IEEE](https://proceedingsoftheieee.ieee.org/resources/guidelines-for-figures-and-tables/), retrieved 2026-09-02.
21. [TVCG Journal Track Formatting Guidelines](https://tc.computer.org/vgtc/publications/journal), retrieved 2026-09-02.
22. [VGTC Conference Formatting Guidelines](https://tc.computer.org/vgtc/publications/conference/), retrieved 2026-09-02.
23. [TVCG journal-track LaTeX template](https://raw.githubusercontent.com/ieeevgtc/tvcg-journal-latex/main/template.tex), retrieved 2026-09-02.
24. [Force double-column figure location in IEEEtran, TeX Stack Exchange](https://tex.stackexchange.com/questions/358210/force-double-column-figure-location-in-ieeetran), retrieved 2026-09-02.
25. [Tips for Writing Technical Papers, Jennifer Widom](https://cs.stanford.edu/people/widom/paper-writing.html), retrieved 2026-09-02.
26. [How to Write a Great Research Paper, Simon Peyton Jones, UPenn-hosted deck](https://www.cis.upenn.edu/~sweirich/icfp-plmw15/slides/peyton-jones.pdf), retrieved 2026-09-02.
27. [How to Write a Great Research Paper, Simon Peyton Jones](https://simon.peytonjones.org/great-research-paper), retrieved 2026-09-02.
28. [Microsoft Research program: Write a Great Research Paper](https://www.microsoft.com/en-us/research/academic-program/write-great-research-paper), retrieved 2026-09-02.
29. [ICML 2026 Reviewer Instructions](https://icml.cc/Conferences/2026/ReviewerInstructions), retrieved 2026-09-02.
30. [NeurIPS 2025 Reviewer Guidelines](https://neurips.cc/Conferences/2025/ReviewerGuidelines), retrieved 2026-09-02.
31. [NeurIPS Paper Checklist](https://neurips.cc/public/guides/PaperChecklist), retrieved 2026-09-02.
32. [Ten Simple Rules for Better Figures](https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1003833), retrieved 2026-09-02.
33. [ACM LaTeX Class Guide](https://mirrors.ctan.org/macros/latex/contrib/acmart/acmguide.pdf), retrieved 2026-09-02.
34. [How to Construct a Nature Summary Paragraph](https://www.nature.com/documents/nature-summary-paragraph.pdf), retrieved 2026-09-02.
35. [CVPR 2026 Author Guidelines](https://cvpr.thecvf.com/Conferences/2026/AuthorGuidelines), retrieved 2026-09-02.
36. [AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents](https://arxiv.org/abs/2503.18666), retrieved 2026-09-02.
37. [Setting the DC: Tool-Grounded D&D Simulations to Test LLM Agents](https://openreview.net/forum?id=3Op7kJOvaD), retrieved 2026-09-02.
38. [Setting the DC PDF](https://openreview.net/pdf?id=3Op7kJOvaD), retrieved 2026-09-02.
39. [Setting the DC, NeurIPS virtual page](https://neurips.cc/virtual/2025/128312), retrieved 2026-09-02.
40. [Game Knowledge Management System](https://doi.org/10.3390/systems14020175), retrieved 2026-09-02.
41. [Game Knowledge Management System, OpenAlex record](https://api.openalex.org/works/https://doi.org/10.3390/systems14020175), retrieved 2026-09-02.
42. [Game Knowledge Management System PDF](https://www.mdpi.com/2079-8954/14/2/175/pdf?version=1770288509), retrieved 2026-09-02.
43. [STORY2GAME: Generating (Almost) Everything in an Interactive Fiction Game](https://arxiv.org/abs/2505.03547), retrieved 2026-09-02.
44. [IVIE: A Neuro-symbolic Approach to Incremental and Validated Generation of Interactive Fiction Worlds](https://arxiv.org/abs/2606.13348), retrieved 2026-09-02.
45. [World-State Transformations for Neuro-symbolic Interactive Storytelling](https://arxiv.org/abs/2605.24719), retrieved 2026-09-02.
46. [GameGen-Verifier](https://arxiv.org/abs/2605.07442), retrieved 2026-09-02.
47. [PDDL-Mind](https://arxiv.org/abs/2604.17819), retrieved 2026-09-02.
48. [Agent-R](https://arxiv.org/abs/2501.11425), retrieved 2026-09-02.
49. [Fly, Fail, Fix, arXiv HTML](https://arxiv.org/html/2507.12666v1), retrieved 2026-09-02.
50. [Fly, Fail, Fix, NVIDIA Research](https://research.nvidia.com/publication/2025-08_fly-fail-fix-iterative-game-repair-reinforcement-learning-and-large-multimodal), retrieved 2026-09-02.
51. [AgentRR abstract](https://arxiv.org/abs/2505.17716), retrieved 2026-09-02.
52. [AgentRR full HTML](https://arxiv.org/html/2505.17716v1), retrieved 2026-09-02.
53. [PROV-AGENT](https://arxiv.org/abs/2508.02866), retrieved 2026-09-02.
54. [PROV-AGENT, ORNL publication record](https://impact.ornl.gov/en/publications/prov-agent-unified-provenance-for-tracking-ai-agent-interactions-/), retrieved 2026-09-02.
55. [From Agent Traces to Trust, current abstract](https://arxiv.org/abs/2606.04990), retrieved 2026-09-02.
56. [From Agent Traces to Trust, v1](https://arxiv.org/abs/2606.04990v1), retrieved 2026-09-02.
57. [From Agent Traces to Trust, v3](https://arxiv.org/abs/2606.04990v3), retrieved 2026-09-02.
58. [From Agent Traces to Trust, v4 HTML](https://arxiv.org/html/2606.04990v4), retrieved 2026-09-02.
59. [Beyond State Consistency](https://arxiv.org/abs/2604.13824), retrieved 2026-09-02.
60. [Tracking World States with Language Models](https://arxiv.org/abs/2508.19851), retrieved 2026-09-02.
61. [GameWorld](https://arxiv.org/abs/2604.07429), retrieved 2026-09-02.
62. [Formal Policy Enforcement for Real-World Agentic Systems](https://arxiv.org/abs/2602.16708), retrieved 2026-09-02.
63. [Don’t Make Models Guess Security and Safety](https://arxiv.org/abs/2604.15579), retrieved 2026-09-02.
64. [Towards Verifiably Safe Tool Use for LLM Agents](https://arxiv.org/abs/2601.08012), retrieved 2026-09-02.
65. [Towards Verifiably Safe Tool Use, publisher DOI](https://doi.org/10.1145/3786582.3786839), retrieved 2026-09-02.
66. [VIGIL](https://arxiv.org/abs/2606.26524), retrieved 2026-09-02.
67. [PL-Guard](https://arxiv.org/abs/2608.15673), retrieved 2026-09-02.
68. [Toward Safe LLM Agents](https://arxiv.org/abs/2608.14590), retrieved 2026-09-02.
69. [Bridging LLM Planning Agents and Formal Methods](https://arxiv.org/abs/2510.03469), retrieved 2026-09-02.
70. [Bridging LLM Planning Agents and Formal Methods, ASEW DOI](https://doi.org/10.1109/asew67777.2025.00018), retrieved 2026-09-02.
71. [Plan Verification for LLM-Based Embodied Task Completion Agents](https://arxiv.org/abs/2509.02761), retrieved 2026-09-02.
72. [Verify, Repair, Repeat, or Stop?](https://arxiv.org/abs/2607.17641), retrieved 2026-09-02.
73. [Counterexample Guided Learning in the Large](https://arxiv.org/abs/2606.11521), retrieved 2026-09-02.
74. [AutoCedar](https://arxiv.org/abs/2607.03656), retrieved 2026-09-02.
75. [AutoCedar, Semantic Scholar](https://www.semanticscholar.org/paper/3803d0d0eb0ef070ab2af6b84406b0ce87708bbd), retrieved 2026-09-02.
76. [From Faulty Memories to Corrected Actions](https://arxiv.org/abs/2608.10502), retrieved 2026-09-02.
77. [DelAct](https://doi.org/10.1109/iwqos70441.2026.11661202), retrieved 2026-09-02.
78. [DelAct, IEEE Xplore record](https://ieeexplore.ieee.org/abstract/document/11661202/), retrieved 2026-09-02.
79. [Proof of Execution](https://arxiv.org/abs/2607.05397), retrieved 2026-09-02.
80. [SkillTrace](https://arxiv.org/abs/2608.05204), retrieved 2026-09-02.
81. [Towards Security-Auditable LLM Agents](https://arxiv.org/abs/2605.06812), retrieved 2026-09-02.
82. [AgentLTL](https://arxiv.org/abs/2607.02599), retrieved 2026-09-02.
83. [AgentLTL, HAL record](https://hal.science/hal-05675960), retrieved 2026-09-02.
84. [TraceGrant](https://arxiv.org/abs/2608.21126), retrieved 2026-09-02.
85. [Trace Integrity for LLM Data Agents](https://arxiv.org/abs/2608.26036), retrieved 2026-09-02.
86. [TraceAegis](https://arxiv.org/abs/2510.11203), retrieved 2026-09-02.
87. [VERGE](https://arxiv.org/html/2601.20055v1), retrieved 2026-09-02.
88. [The Self-Correction Illusion](https://arxiv.org/html/2606.05976v1), retrieved 2026-09-02.
89. [LLM-Modulo, arXiv](https://arxiv.org/abs/2402.01817), retrieved 2026-09-02.
90. [LLM-Modulo, PMLR](https://proceedings.mlr.press/v235/kambhampati24a.html), retrieved 2026-09-02.
91. [Robust Planning with Compound LLM Architectures](https://arxiv.org/abs/2411.14484), retrieved 2026-09-02.
92. [Robot Planning via LLM Proposals and Symbolic Verification, Semantic Scholar](https://www.semanticscholar.org/paper/3a4903b03ab0ad54be582fe5d293501ed7046cfd), retrieved 2026-09-02.
93. [Awesome Auditable AI](https://github.com/yzhao062/awesome-auditable-ai), retrieved 2026-09-02.
94. [Dapr 1.18 Verifiable Execution, TFiR](https://tfir.io/dapr-1-18-verifiable-execution-ai-agents-yaron-schneider/), retrieved 2026-09-02.
95. [Attestation, provenance, and tamper-evident execution history, TechRevolt](https://techrevolt.news/articles/exclusive-bringing-attestation-provenance-and-tamper-evident-execution-history-to-workflows-and-ai-agents), retrieved 2026-09-02.
96. [Live Game Design: Prototyping at the Speed of Play](https://dl.acm.org/doi/10.1145/3723498.3723726), retrieved 2026-09-02.
97. [Vie artifact site](https://vrozen.github.io/Vie), retrieved 2026-09-02.
98. [SoulGarden PDF](https://dl.acm.org/doi/pdf/10.1145/3748597), retrieved 2026-09-02.
99. [Baba is Y’all 2.0, author version](https://arxiv.org/html/2203.02035v2), retrieved 2026-09-02.
100. [Baba is Y’all 2.0, IEEE Xplore record](https://ieeexplore.ieee.org/document/9956016), retrieved 2026-09-02.
101. [Google Scholar search: neuro-symbolic narrative generation and game-state consistency](https://scholar.google.com/scholar?as_ylo=2025&q=neuro-symbolic+narrative+generation+LLM+game+state+consistency+validation), retrieved 2026-09-02.
102. [Google Scholar search: game-state validators, rejected actions, and preconditions](https://scholar.google.com/scholar?as_ylo=2025&q=LLM+%22game+state%22+validator+reject+actions+parser+preconditions), retrieved 2026-09-02.
103. [arXiv recent computer-science AI submissions](https://arxiv.org/list/cs.AI/recent), retrieved 2026-09-02.
104. [OpenAlex search: game narrative, symbolic verification, and state consistency](https://api.openalex.org/works?search=LLM%20game%20narrative%20symbolic%20verification%20state%20consistency&filter=from_publication_date:2025-01-01), retrieved 2026-09-02.
105. [OpenAlex search: LLM-Modulo](https://api.openalex.org/works?search=%22LLM-Modulo%22&filter=from_publication_date:2025-01-01), retrieved 2026-09-02.
106. [Semantic Scholar Graph search: symbolic validation of LLM game actions](https://api.semanticscholar.org/graph/v1/paper/search?query=LLM%20game%20agent%20symbolic%20validation%20verifier%20actions&year=2025-2026), retrieved 2026-09-02.[0m
