<!-- Filed verbatim (Aside internal citation tags stripped) from an `aside exec --effort high` research session run on 2026-09-02 by the parallel Claude Code session. Evidence level: external web search feedback, [INFERENCE] for this project; nothing here is a measured result. -->

# Aside search-based feedback: Sealed Lighthouse UI, fun, and contribution

Research scope: public web only. No login, purchase, posting, or search for the unpublished game. All cited pages were opened on 2026-09-02.

## 1. Legible progress and contribution (patterns + citations)

### Pattern 1: Organize discoveries as relationships, not a checklist

*Return of the Obra Dinn* uses a familiar book metaphor to organize chronology, deaths, identities, chapters, bookmarks, and references. Lucas Pope described it as the answer to a story that had become too complex for simpler log pages. “The book ended up being the perfect tool for setting down both the sequence of events when they're experienced out of order, and a logical rationale for inputting everyone's fate.”

*Outer Wilds* makes knowledge the upgrade and presents its metagame as a narrative web. This preserves relationships between discoveries instead of turning exploration into “icon janitor” work. “The things you do matter in relation to other things you do.”

**Apply it:** Keep the ledger, but add a compact four-node case chain:

`HARBOR OBSERVED -> LENS SECURED -> MIRA CORROBORATED -> MOUNT ACTIVATED`

Show links, not merely `CASE 2/3`. A filled link explains what the action contributed.

### Pattern 2: Verify intermediate deductions

*Golden Idol* initially marked only the whole solution correct or incorrect. Players could not identify whether any of their reasoning was productive. The team added person-identification and scenario-specific sub-puzzles, which made players feel they were “getting somewhere.” “Now, they had a feeling that they are getting somewhere and were rewarded for figuring things out.”

**Apply it:** Give every commit a causal delta:

```text
ENTRY #3 | COMMITTED
CONTRIBUTION: Lens provenance confirmed
CASE IMPACT: 2/4 links established
UNLOCKED: Ask Mira about the harbor mount
```

Count causal links established, not arbitrary experience points.

### Pattern 3: Let the player state the theory

*Golden Idol* uses constrained fill-in-the-blank conclusions. The supplied grammar lowers syntax friction while leaving the inference to the player. The scroll provides “grammatical and semantic context,” balancing steady progress with moments where “an insight strikes.”

*Her Story* goes further: the player’s chosen search term becomes the investigative action. Its clips were deliberately interconnected so different query paths remained satisfying. Barlow balanced the script by measuring clip connectivity, word use, and which clips were easiest to discover.

**Apply it:** Before the final tide-marks commit, ask the player to complete one conclusion:

```text
THE LENS REVEALS [TIDE MARKS] WHEN INSTALLED AT [HARBOR MOUNT].
```

Do not let the ledger infer this automatically from inventory state.

### Pattern 4: Use coarse partial correctness

*Golden Idol* found that binary whole-puzzle feedback was frustrating, but validating each slot enabled brute force. Its compromise was a coarse “two or fewer slots are incorrect” indicator. The team could not validate every phrase slot, while evaluating the whole puzzle as simply wrong or right frustrated players.

**Apply it:** For the final conclusion, report:

```text
LEDGER STATUS: The theory is close, but one relationship conflicts with the evidence.
```

Do not reveal which slot is wrong on the first attempt. Reveal it only after repeated attempts.

### Pattern 5: Batch major confirmations

*Obra Dinn* confirms complete identity-and-fate solutions in groups of three. This produces a larger musical and visual release while making individual-option brute force harder. GMTK identifies this “tester” design as central to protecting the player’s deduction. Obra Dinn avoids leading questions and requires three correct fates before confirming the player’s thinking.

**Apply it:** Keep immediate feedback for ordinary actions, but batch the final two related facts into a single `LEDGER RECONCILED` event. The micro-feedback says the input was heard; the batch confirms the insight.

### Pattern 6: Give every important fact at least two contexts

*Chants of Sennaar* presents every word at least twice in different situations, allowing players to form and revise hypotheses. Difficulty is tuned by adding another occurrence or context rather than by displaying the answer. “Every word you encounter in the game must be seen at least twice in two different situations.”

**Apply it:** Establish the lens rule twice:

1. The lamp-store display or keeper explains that signal lenses reveal salt residue.
2. Mira or the harbor mount provides a second, independent context.

This makes the tide-marks inference earned rather than dependent on one mandatory line.

### Pattern 7: Make contribution consequential, not merely correct

*Paradise Killer* supports player-chosen investigative order and lets players decide when they possess enough evidence to accuse someone. Its case files group evidence without choosing the player’s theory. The developers broke crimes into case files so players could choose which evidence to discuss, preserving agency.

*Pentiment* makes the eventual accusation a value-laden responsibility rather than confirming a canonical answer. Josh Sawyer described the uncertainty as foundational because certainty would remove the player’s responsibility for the outcome.

**Apply it:** The final reveal should change how the player understands Brinewake or Mira, not simply award the hint. Even in a linear episode, let the player decide which evidence to enter first or which interpretation to present.

### Pattern 8: Make a text-heavy feed scannable

*Disco Elysium* borrowed the fast, vertically flowing form of a social-media feed so players could extract the gist from dense text. Its dialogue text “tumbles up” in a column designed for fast, snappy reading.

**Apply it:** Split each ledger entry into visually stable fields:

```text
OUTCOME       COMMITTED
PROPOSAL      Install signal lens
WHY           Lens and mount now correspond
CONTRIBUTION  Harbor surface became readable
NEXT          Inspect revealed tide marks
```

Avoid paragraph-shaped validator output.

## 2. Legible refusals (patterns + citations)

### A. Treat HOLD as a game-state result, not an error

A HOLD is an acknowledged proposal that made no state change. It should not use system-error language, alarms, or a failure modal.

NN/g recommends immediate, local feedback; otherwise users assume an input was missed and repeat it. “Whenever users interact with a system, they need to know whether the interaction was successful.”

Recommended structure:

```text
ENTRY #4 | HELD
GATE: PRECONDITION
WORLD FACT: The harbor mount has no lens.
RULE LEARNED: Installation requires a carried signal lens.
NEXT VALID ENTRY: Visit the lamp store.
```

### B. Name the unmet condition without blame

Avoid `INVALID`, `ILLEGAL`, `WRONG`, and `ACCESS DENIED`. Describe the world-state threshold instead.

NN/g recommends precise, human-readable language, constructive remedies, and a nonjudgmental tone. “Merely stating the problem is also not enough; offer some potential remedies.”

Good:

```text
HELD - QUEST STAGE: Mira has not identified the harbor mount.
```

Poor:

```text
INVALID ACTION - You have not completed the quest.
```

### C. Make the next affordance executable

`NEXT VALID ENTRY` should identify an action currently available, not merely a goal:

- Good: `Talk to Mira beside the west pier.`
- Weak: `Progress the quest.`
- Misleading: `Find more evidence.`

Where controls allow it, focus or highlight that affordance without executing it. This reduces correction effort, consistent with NN/g’s recommendation to present a small set of viable fixes. Error recovery should preserve effort and reduce the work needed to correct the action.

### D. Signpost gates before the player hits them

The 3D scene should already suggest the condition: an empty circular mount, a missing-lens silhouette, or Mira looking toward the mount. The ledger then confirms a world rule instead of inventing one after rejection.

This matches *Chants of Sennaar’s* insistence that rules remain coherent and consistently observable. Once a rule is made clear, the designers argue it must be followed consistently so players can trust and learn the system.

### E. Convert failure into information

Juul’s study argues that failure can add perceived content by causing players to reconsider their strategy. The FDG study distinguishes productive temporary struggle from perpetual failure associated with frustration and disengagement. Temporary failure can be integral to the later experience of overcoming the struggle; perpetual failure is the harmful case.

Therefore:

- First unique HOLD: reveal one rule fragment.
- Second HOLD on the same gate: highlight the relevant object or person.
- Third: state the exact next action.
- Never print identical HOLD text repeatedly and call it progress.
- Never remove inventory, entries, or case progress for a HOLD.

### F. Do not reject harmless exploration

Observation should normally succeed even when mutation is gated. Prematurely grading exploratory interaction is a hostile pattern in ordinary UX. “Don't assume that exploratory interactions ... are errors.”

For this episode, `observe`, `inspect`, and `review ledger` should remain valid at every stage. Gate only actions that would mutate canonical state.

## 3. Fun in constraint loops (theory + 5 changes)

### Theory

**Primary lens: learning and mastery.** Koster describes game fun as progress in predicting and mastering problems. His interaction loop is almost identical to this game’s proposal model: form a hypothesis, act, see a result, and update the hypothesis. “Fun is basically about making progress on prediction,” and feedback should show what the player can do, that they did it, what changed, and whether it helped.

**MDA translation:**

`Typed proposal -> symbolic validation -> COMMIT/HOLD feedback -> revised mental model -> Discovery + Challenge + earned competence`

MDA cautions that mechanics do not directly guarantee an aesthetic experience; they produce runtime dynamics that must be tuned toward the intended experience. MDA separates mechanics, dynamics, and aesthetics to support explicit, iterative design reasoning.

**Self-determination theory:** perceived autonomy and competence predict game enjoyment and continued play. The cited studies found perceived in-game autonomy and competence associated with enjoyment, preference, and changes in well-being.

The main risk is therefore not “too many refusals” by itself. It is a combination of:

- outcomes that are arbitrary or completely predictable;
- repeated clerical proposals with no new inference;
- one mandatory route;
- feedback that says no without improving the player’s model;
- progress measured independently of the evidence relationships;
- a tester that exposes the answer or allows exhaustive guessing.

GMTK describes the desired balance as clear questions, multiple solution paths, small confirmations, useful investigative tools, and a tester that neither prompts nor permits brute force. The recommended detective-game tester should not lead the player or permit guessing, while assistance comes from complexity ramps, multiple avenues, small victories, tools, and hints.

### Five changes for a 10-minute episode

1. **Guarantee a meaningful COMMIT in the first 30 to 45 seconds.**  
   Let the opening harbor observation establish the ledger grammar and fill the first evidence link. Then increase complexity toward a final two-precondition deduction. This supports a challenge ramp rather than beginning with procedural friction.  
   Evidence: [Koster on variation, escalation, and feedback](https://www.raphkoster.com/2025/11/03/game-design-is-simple-actually/).

2. **Make each unique HOLD teach exactly one testable rule.**  
   The player should be able to predict the result of a related future proposal after reading it. Repeated identical HOLDs get progressively stronger guidance.  
   Evidence: [The Struggle is Spiel](https://dl.acm.org/doi/fullHtml/10.1145/3472538.3472565).

3. **Use instant micro-feedback but batch the main reconciliation.**  
   Immediately show that every proposal was heard; reserve a stronger page turn, seal, sound, or ledger reconciliation for the final connected deduction.  
   Evidence: [GMTK on detective-game testers](https://gmtk.substack.com/p/what-makes-a-great-detective-game).

4. **Provide two paths to one important fact.**  
   The player might learn the mount requirement from Mira or infer it from the mount’s shape and the lamp-store diagram. Either path unlocks the same typed fact.  
   Evidence: [Chants of Sennaar developer interview](https://www.gamedeveloper.com/design/immersing-players-in-the-culture-of-a-people-with-language-puzzler-chants-of-sennaar).

5. **End with recombination, not another fetch action.**  
   The final action should require combining two previously learned rules: lens provenance plus correct installation location. This tests the player’s model rather than repeating the inventory sequence.  
   Evidence: [Golden Idol’s thought-path and fill-in-the-blank design](https://www.gamedeveloper.com/design/case-of-the-golden-idol).

**Falsifier to test:** If players mostly follow `NEXT VALID ENTRY` literally but cannot explain why the final action became valid, the interface is functioning as a quest checklist, not a rule-discovery game.

## 4. HUD/ledger conventions and accessibility (citations)

### Progress

- Retain `CASE 2/3`, but accompany it with named steps or evidence links. A bare percentage or fill bar cannot explain contribution.
- Distinguish:
  - `case phase`;
  - `evidence links confirmed`;
  - `current valid opportunities`.
- Keep current objectives recallable from the ledger. Game Accessibility Guidelines explicitly recommend objective reminders and progress summaries. [Full guideline list](https://gameaccessibilityguidelines.com/full-list/).

### Per-action feedback

Show the result adjacent to the proposal immediately. Include:

1. outcome;
2. state change or unchanged state;
3. why it mattered;
4. next available action.

Immediate state visibility helps users identify whether their input was registered and how the system changed. Appropriate feedback reduces uncertainty and enables users to steer the interaction without wasting effort.

Do not use color alone:

- COMMITTED: filled seal/check shape + word + optional short bell.
- HELD: outlined pause/bar shape + word + optional dull knock.
- Gate types: distinct text labels and icons, not red/yellow/green alone.

Xbox guidance requires critical visual content to use an additional channel and explicitly states that color alone must not represent information. Text, symbols, shapes, color, audio, and haptics should be combined so key information is not dependent on one channel.

### Why-it-mattered summaries

Use one sentence tied to a concrete dependency:

```text
WHY IT MATTERED: Mira can now identify the mount.
```

Avoid praise such as `Great job!` without state information. The valuable reward is the newly intelligible relationship.

### End receipt

Keep the reproducibility data, but separate player meaning from research diagnostics:

```text
CASE RECEIPT
4 facts established
3 case links completed
1 validator rule discovered through a hold
Tide marks revealed

INVESTIGATOR'S CONTRIBUTION
- Recognized the damaged signal
- Secured the matching lens
- Corroborated the mount with Mira
- Reconstructed the tide-mark method

TECHNICAL RECEIPT
Entries: 7 | Holds: 2 | State hash: 8F31...
```

Narrative progress recaps assist players with memory difficulties and players returning after interruption. Game Accessibility Guidelines identifies progress summaries as an intermediate cognitive-accessibility practice.

### Text and contrast

For the Web export:

- Default body text at least 18 px at a 1080p reference viewport.
- Support up to 200% text scaling without lost content or meaning.
- Keep text lines at 80 characters or fewer.
- Use at least 1.5 line spacing for multi-line blocks.
- Keep reasons in sentence case. Reserve all caps for short stamps such as `HELD`.
- Offer a plain sans-serif mode if the ledger typeface is stylized.
- Make the ledger scroll in one direction when enlarged.

These values come directly from XAG 101. XAG 101 recommends 18 px PC text at 1080p, scaling to 200%, an 80-character line limit, 1.5 line spacing, and a sans-serif option.

Use a solid or opacity-adjustable ledger backing over the harbor. Target:

- normal text: 4.5:1;
- large text and meaningful non-text elements: 3:1;
- high-contrast mode: 7:1.

XAG 102 specifies these contrast ratios and recommends solid or adjustable-opacity backgrounds behind text over changing scenes.

### Motion and timing

Provide a reduced-motion option that:

- changes animated stamps to immediate state changes;
- removes ledger shake and large page sweeps;
- suppresses nonessential harbor movement behind open ledger pages;
- preserves all feedback in persistent text.

The Web wrapper should honor `prefers-reduced-motion` where practical. WCAG 2.2 recommends disabling nonessential interaction-triggered motion and recognizes the `prefers-reduced-motion` query as a sufficient technique.

## 5. Research-game presentation examples (citations)

### 1. A validator can be a diegetic role

The closest retrieved example is the CHI EA 2025 prototype *1001 Nights*. A persona-driven King accepts, redirects, or asks the player to rephrase story input according to context and bounded preferences. The AI mechanism appears as character behavior rather than a generic system dialog. The King evaluates each turn, requests correction when it contradicts context, and otherwise continues the narrative.

For *Sealed Lighthouse*, the Harbor Ledger itself can occupy this role. Do not give it a chatty personality, but let its vocabulary remain administrative and in-world: `entry`, `corroboration`, `precondition`, `held`, `reconciled`.

### 2. Materialize the player’s accepted contribution

In *1001 Nights*, accepted story content becomes weapon cards and changes the generated scene. Its end-of-session storybook records the player’s dialogue, artifacts, and final outcome. The paper explicitly frames these artifacts as making players’ contributions part of progression and giving them a lasting record for reflection.

Equivalent treatment here:

- a committed observation adds a physical sketch or stamp;
- Mira’s corroboration adds her signature;
- lens installation changes both the harbor and the ledger diagram;
- the end receipt retells what the investigator established.

### 3. Let players probe the mechanism through play

The CHI PLAY study of the adversarial AI in *iNNk* found players built mental models systematically or reactively and processed discrepancies by comparing the AI with other systems, previous gameplay, and themselves. The study identifies focus, style, and comparison as dimensions of player mental-model development.

Players will intentionally test the symbolic validator. Support that behavior. Record the proposal, show stable gate names, and make repeated rules consistent. Do not treat probing as misuse.

### 4. Use play as the explanation, with explicit support for hard questions

DiGRA’s simulation-game analysis found that game mechanics can support many XAI questions, especially by letting players manipulate inputs and observe outputs, while some questions remain difficult to communicate implicitly. The paper presents games as explainable interfaces but warns that not every explanation type is equally easy to convey.

Use three explanation layers:

- **Layer 0, always visible:** `COMMITTED` or `HELD`.
- **Layer 1, concise:** gate, relevant world fact, state delta, next valid action.
- **Layer 2, optional Research Notes:** typed proposal, checked predicates, resulting state hash.

Do not expose model chain-of-thought. Show verifiable rule checks.

### 5. Do not over-gamify the research explanation

A 2025 CHI probe using NPC-like conversations to explain AI improved nontechnical participants’ AI knowledge, but participants disagreed on whether the gamification was engaging or disruptive. The study found the tool beneficial, but the effect of gamification alone was inconclusive and engagement opinions were mixed.

Therefore, keep technical detail optional. The primary play surface should explain the harbor mystery; the research layer should explain why that outcome was safe and reproducible.

### 6. Evaluate the player’s understanding, not just system accuracy

The FDG 2023 paper on AI-based game design argues that player perspectives are often missing and should inform how the intended AI experience is designed. It recommends incorporating players’ perspectives so designers can anticipate how the AI will actually be experienced.

Add two post-episode questions:

1. “Why was installing the lens held the first time?”
2. “What made the final installation valid?”

If players answer correctly, the mechanism was visible. If they only recall `go to shop, talk to Mira`, the quest was visible but the research mechanism was not.

## 6. Top 10 prioritized recommendations for this game

1. **Replace the abstract phase bar with a causal case chain.**  
   **What:** Show four named evidence links beneath `CASE 2/3`.  
   **Why:** It reveals how each action moves the investigation instead of displaying unrelated completion.  
   **Evidence URL:** [Outer Wilds critical analysis](https://www.gamedeveloper.com/design/outer-wilds-critical-analysis)  
   **Effort:** S

2. **Add `CONTRIBUTION`, `CASE IMPACT`, and `UNLOCKED` to every commit.**  
   **What:** Report the fact established, links completed, and newly available affordance.  
   **Why:** This answers “what changed because of me?” immediately.  
   **Evidence URL:** [The Case of the Golden Idol developer interview](https://www.gamedeveloper.com/design/case-of-the-golden-idol)  
   **Effort:** S

3. **Turn each unique HOLD into one learned rule.**  
   **What:** Print gate, unmet world fact, rule fragment, and one valid next action.  
   **Why:** A rejected action can become temporary productive struggle rather than dead time.  
   **Evidence URL:** [The Struggle is Spiel](https://dl.acm.org/doi/fullHtml/10.1145/3472538.3472565)  
   **Effort:** S

4. **Escalate guidance after repeated holds on the same gate.**  
   **What:** Rule fragment first, visual highlight second, exact next action third.  
   **Why:** This prevents temporary struggle from becoming perpetual frustration.  
   **Evidence URL:** [Error-Message Guidelines](https://www.nngroup.com/articles/error-message-guidelines/)  
   **Effort:** M

5. **Keep observation verbs universally valid.**  
   **What:** Apply symbolic HOLDs only to canonical state mutations.  
   **Why:** Players need safe space to probe the world and validator without being graded for exploration.  
   **Evidence URL:** [Error-Message Guidelines](https://www.nngroup.com/articles/error-message-guidelines/)  
   **Effort:** S

6. **Require one player-authored final deduction.**  
   **What:** Use a constrained sentence or two-slot relationship before revealing tide marks.  
   **Why:** The player demonstrates the insight instead of merely completing an inventory sequence.  
   **Evidence URL:** [GMTK: What Makes a Great Detective Game?](https://gmtk.substack.com/p/what-makes-a-great-detective-game)  
   **Effort:** M

7. **Give the lens and mount rules two independent evidence contexts.**  
   **What:** Pair an environmental clue with Mira’s corroboration.  
   **Why:** Redundancy supports hypothesis testing without directly exposing the answer.  
   **Evidence URL:** [Chants of Sennaar developer interview](https://www.gamedeveloper.com/design/immersing-players-in-the-culture-of-a-people-with-language-puzzler-chants-of-sennaar)  
   **Effort:** M

8. **Present the symbolic gate in three layers.**  
   **What:** Outcome, concise predicate explanation, optional technical trace.  
   **Why:** It makes the research mechanism inspectable without forcing technical prose into the fiction.  
   **Evidence URL:** [Can Games Be AI Explanations?](https://dl.digra.org/index.php/dl/article/view/2234)  
   **Effort:** M

9. **Replace the statistical end card with a two-part contribution receipt.**  
   **What:** Lead with the investigator’s causal contributions; put entry counts and state hash below as technical evidence.  
   **Why:** Counts prove execution, but the contribution narrative supplies meaning and reflection.  
   **Evidence URL:** [1001 Nights CHI EA 2025 paper](https://arxiv.org/html/2503.09102v1)  
   **Effort:** S

10. **Ship a ledger accessibility pass with the UI revision.**  
    **What:** 18 px minimum PC text, 200% scaling, sentence-case reasons, 4.5:1 contrast, text-plus-shape outcomes, and reduced motion.  
    **Why:** The ledger is the main gameplay surface; unreadable or motion-dependent feedback blocks both the mystery and the research contribution.  
    **Evidence URL:** [XAG 101](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/101), [XAG 102](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/102), [XAG 103](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/103)  
    **Effort:** M

## Sources

All retrieved 2026-09-02.

1. “The Case of the Golden Idol used frequent testing to sharpen its mystery-solving” - https://www.gamedeveloper.com/business/-the-case-of-the-golden-idol-i-used-frequent-testing-to-improve-its-mystery-solving
2. “Pursuing the ‘Aha!’ Moment with The Case of the Golden Idol” - https://www.gamedeveloper.com/design/case-of-the-golden-idol
3. “Confirmation in The Return of Obra Dinn” - https://intermittentmechanism.blog/2024/05/21/confirmation-in-the-return-of-obra-dinn/
4. “Road to the IGF: Lucas Pope’s Return of the Obra Dinn” - https://www.gamedeveloper.com/business/road-to-the-igf-lucas-pope-s-i-return-of-the-obra-dinn-i-
5. Lucas Pope, “Animating the Book” development log - https://dukope.com/devlogs/obra-dinn/tig-37/
6. “Road to the IGF: Sam Barlow’s Her Story” - https://www.gamedeveloper.com/audio/road-to-the-igf-sam-barlow-s-i-her-story-i-
7. “Her Story Game Interview With Sam Barlow” - https://taylorholmes.com/2015/01/24/her-story-game-interview-with-sam-barlow
8. GDC, “The Burden of Proof: Narrative Deduction Mechanics for Detective Games” - https://www.youtube.com/watch?v=--3meejDM-U
9. GDC Vault, “Sparking Curiosity-Driven Exploration Through Narrative in Outer Wilds” - https://www.gdcvault.com/play/1027368/Independent-Games-Summit-Sparking-Curiosity
10. “Outer Wilds Critical Analysis” - https://www.gamedeveloper.com/design/outer-wilds-critical-analysis
11. “Making Pentiment’s Most Macabre Murder Mysteries” - https://www.gamedeveloper.com/design/making-pentiment-s-most-macabre-murder-mysteries
12. “Inside the Fantastic Murder-Mystery Design of Paradise Killer” - https://www.gamedeveloper.com/design/inside-the-fantastic-murder-mystery-design-of-i-paradise-killer-i-
13. “Immersing Players in the Culture of a People with Chants of Sennaar” - https://www.gamedeveloper.com/design/immersing-players-in-the-culture-of-a-people-with-language-puzzler-chants-of-sennaar
14. “Disco Elysium: Working on UI Design” - https://80.lv/articles/disco-elysium-working-on-ui-design
15. “Error-Message Guidelines” - https://www.nngroup.com/articles/error-message-guidelines/
16. Celia Hodent, “Developing UX Practices at Epic Games” - https://celiahodent.com/ux-practices-epic-games/
17. “Signposting Tips and Tricks” - http://gamedevfocus.blogspot.com/2014/12/signposting-tips-and-tricks.html
18. Steve Bromley, “Get Lost! Improving Player Experience Through Signposting and Map Design” - https://www.stevebromley.com/blog/2010/03/29/get-lost-improving-player-experience-through-signposting-and-map-design-in-games/
19. Jesper Juul, “Fear of Failing?” - https://www.jesperjuul.net/text/fearoffailing/
20. Frommel, Klarkowski, Mandryk, “The Struggle is Spiel” - https://dl.acm.org/doi/fullHtml/10.1145/3472538.3472565
21. Hunicke, LeBlanc, Zubek, “MDA: A Formal Approach to Game Design and Game Research” - https://users.cs.northwestern.edu/~hunicke/MDA.pdf
22. AAAI record for the MDA paper - https://aaai.org/papers/ws04-04-001-mda-a-formal-approach-to-game-design-and-game-research
23. GMTK, “What Makes a Great Detective Game?” - https://gmtk.substack.com/p/what-makes-a-great-detective-game
24. Raph Koster, “A Theory of Fun” presentation index - https://www.raphkoster.com/games/a-theory-of-fun/
25. Raph Koster, “A Theory of Fun 10 Years Later” - https://www.raphkoster.com/wp-content/uploads/2026/07/Theory-of-Fun-10-Years-Later.pdf
26. Raph Koster, “Game Design Is Simple, Actually” - https://www.raphkoster.com/2025/11/03/game-design-is-simple-actually/
27. Jürgen Schmidhuber, “Formal Theory of Creativity, Fun, and Intrinsic Motivation” - https://people.idsia.ch/~juergen/creativity.html
28. Ryan, Rigby, Przybylski, “The Motivational Pull of Video Games” - https://selfdeterminationtheory.org/wp-content/uploads/2020/10/2006_RyanRigbyPrzybylski_MandE.pdf
29. Jenova Chen, “Flow in Games” - https://www.jenovachen.com/flowingames/Flow_in_games_final.pdf
30. Xbox Accessibility Guideline 101: Text display - https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/101
31. Xbox Accessibility Guideline 102: Contrast - https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/102
32. Xbox Accessibility Guideline 103: Additional channels - https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/103
33. Game Accessibility Guidelines: Full list - https://gameaccessibilityguidelines.com/full-list/
34. Game Accessibility Guidelines: Narrative progress summaries - https://gameaccessibilityguidelines.com/if-using-a-long-overarching-narrative-provide-summaries-of-progress/
35. Game Accessibility Guidelines: Destiny 2 memories - https://gameaccessibilityguidelines.com/destiny-2-memories/
36. Game Accessibility Guidelines: Hide background movement - https://gameaccessibilityguidelines.com/provide-an-option-to-turn-off-hide-background-movement/
37. WCAG 2.2: Animation from interactions - https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html
38. NN/g, “Visibility of System Status” - https://www.nngroup.com/articles/visibility-system-status/
39. NN/g, “Progress Indicators Make a Slow System Less Insufferable” - https://www.nngroup.com/articles/progress-indicators/
40. Accessible Player Experiences: Clear Text - https://accessible.games/accessible-player-experiences/access-patterns/clear-text/
41. “1001 Nights: A Co-Creative Story-Crafting Game” - https://arxiv.org/html/2503.09102v1
42. “Understanding Mental Models of AI through Player-AI Interaction” - https://arxiv.org/abs/2103.16168
43. “‘I Want To See How Smart This AI Really Is’” - https://dl.acm.org/doi/10.1145/3549482
44. “Getting Playful with Explainable AI” - https://dl.acm.org/doi/10.1145/3334480.3382831
45. CMU publication page for “Getting Playful with Explainable AI” - https://dig.cmu.edu/publications/2020-aigwap.html
46. “Can Games Be AI Explanations?” - https://dl.digra.org/index.php/dl/article/view/2234
47. “Integrating Players’ Perspectives in AI-Based Games” - https://dl.acm.org/doi/10.1145/3582437.3582451
48. “Enhancing AI Explainability for Non-technical Users with LLM-Driven Narrative Gamification” - https://dl.acm.org/doi/10.1145/3706599.3719795
49. “The Role of Explainable AI and Dynamic Difficulty Adjustment” - https://dl.acm.org/doi/10.1145/3841631
50. “Explainable AI for Designers” - https://antoniosliapis.com/articles/explainable.php

Unusable retrieval attempts, opened but not used as evidence:

51. DiGRA direct PDF endpoint, returned an iframe/stub - https://dl.digra.org/index.php/dl/article/view/2234/2231
52. iNNk institutional PDF, no extractable content returned - https://pure.itu.dk/files/92621777/iNNk_mentalModels_CHIPlay22_2_.pdf
53. ACM alternate full-HTML endpoint, no additional usable content - https://dl.acm.org/doi/fullHtml/10.1145/3334480.3382831
54. “‘Ah! I See’: Facilitating Process Reflection in Gameplay,” retrieval timed out and was not cited - https://dl.acm.org/doi/10.1145/3613904.3642484[0m
