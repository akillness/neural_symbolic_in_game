# Aside deep-research intake — detective feel, guided tutorial, HUD legibility (2026-09-18, D-073)

Status: design basis only ([INFERENCE]); advice, not evidence. Produced by an Aside browser-research session on 2026-09-18 for the D-073 detective/tutorial/HUD work. Sources were opened by the Aside agent; retrieval date 2026-09-18.

# Deepening the Detective Feel — Research Report for *The Sealed Lighthouse*

**All sources retrieved 2026-09-18.** Every URL below was opened during this task. Quotes from the highest-leverage sources were re-fetched and string-matched against the live page to confirm they are verbatim. Items I could not verify are flagged explicitly.

**Project constraints this report respects:** Godot 4, `Control`-based UI, 1280×720 browser and 390×844 mobile, presentation reads **committed snapshots only** and adds **no second game-state model**.

---

## 1 Findings

### 1.1 Confirmation, refusal, and the economics of guessing

**F1 — Obra Dinn's batch-of-3 confirmation exists specifically to price out brute force while keeping feedback immediate.** Lucas Pope: *"I prefer something more immediate just for player satisfaction, but there's a problem that immediate feedback can be cheated. If I tell them their guess was correct right away, it's trivial for them to just try all the combinations and boom, game skipped. The solution I ended up with is to basically make it really hard to try all the combinations. The game now tells you when any set of 3 fates are correct."* And: *"Cheating one fate is easy but cheating three fates requires just enough work, intent, or both that you'd be better off solving it the right way."* Confirmation is both ceremony and lock: *"there's a little fanfare reveal and those pages in the book are locked from editing."*
— https://dukope.com/devlogs/obra-dinn/tig-30 (2026-09-18)

**F2 — Pope explicitly declined to punish wrong guesses.** *"I like the immediate feedback of knowing when you got something right. Brute-forcing is cheating yourself out of the game's puzzles but I can understand the temptation."* Community replies in the same thread proposed punishment (a book that deteriorates with each wrong entry); he adopted a confirmation *threshold* instead.
— https://dukope.com/devlogs/obra-dinn/tig-06 (2026-09-18)

**F3 — Counter-evidence, and it matters for your ledger.** In Pope's own devlog replies, a player reports the batching rule leaked: *"Since the game explicitly tells me that I get to know correct fates in pairs of three, it felt that this brute forcing is the intended method. Due to this, I completely missed out on how to use the hammocks to identify topmen and seamen."* A 2017 commenter predicted it: *"A player who is sure about two fates can get a third one 'for free' by exhaustive attempts."* **Caveat: these are forum commenters, not developer statements; no developer reply appears in the thread.**
— https://dukope.com/devlogs/obra-dinn/tig-37 and https://dukope.com/devlogs/obra-dinn/tig-30 (2026-09-18)

**F4 — Binary whole-puzzle validation works only at tutorial scale.** Golden Idol's Andrejs Klavins: *"When building an early demo, players had to fill in the scroll puzzle for a scenario and it would tell them if it was correct or incorrect. This worked fine for a smaller, tutorial-like scenario, but with more complex scenarios, players would get very frustrated. This was because there were so many places they might be wrong and they had no idea which of their deductions were correct."* **This is a direct licence for a short three-node chain to use simple pass/fail, and a warning about what happens when chains lengthen.**
— https://www.gamedeveloper.com/design/case-of-the-golden-idol (2026-09-18)

**F5 — The fix was partial-progress sub-puzzles plus a bounded "closeness" signal, not hints.** *"we introduced the extra puzzles, such as identifying people in the scene and solving an additional custom puzzle for each scenario, which greatly improved the satisfaction with the game. Now, they had a feeling that they are getting somewhere and were rewarded for figuring things out."* And on the closeness signal, including its honest cost: *"we settled on adding the indicator 'two or fewer slots are incorrect' … However, this reduced the difficulty and length of the game."*
— https://www.gamedeveloper.com/design/case-of-the-golden-idol (2026-09-18)

**F6 — The input-design spectrum: free text frustrates on syntax, multiple choice destroys deduction.** *"In the old text-based adventure games … playing these games could be incredibly frustrating, because you might not know the right syntax or phrasing that the system would accept. On the other side of the spectrum are games that you could call 'pretend detective games' where you are offered, for example, three solutions and you have to choose the right one. It's very easy to input it, but you deny the player the actual act of deduction."* Their resolution: scaffolding lives in **grammar and a bounded vocabulary**, not in hints — *"the scrolling text is not completely blank—it offers a lot of grammatical and semantic context. Or, there would be a limited amount of phrases in each scenario."*
— https://www.gamedeveloper.com/design/case-of-the-golden-idol (2026-09-18)

**F7 — Obra Dinn standardised fate grammar to Subject-Verb-Object and accepts multiple correct answers.** *"At some point I standardized all the fates to use a Subject-Verb-Object format … This makes matching fates easier and is friendlier to localization."* And: *"The fate system allows each death to have multiple correct fates so hopefully players won't get stuck by entering something they thought was correct but wasn't flagged as so."*
— https://dukope.com/devlogs/obra-dinn/tig-30 (2026-09-18)

**F8 — Bounded input systems invite brute force as a predictable consequence.** *"This opened a new can of worms—as the famous quote goes 'Given the opportunity, players will optimize the fun out of a game'. With a limited input system, an option to brute force solutions appears."*
— https://www.gamedeveloper.com/design/case-of-the-golden-idol (2026-09-18)

**F9 — The player, not the game, should assemble the hypothesis.** Paradise Killer's Kaizen Game Works rebuilt the trial late in development to enforce this: *"When we originally implemented the trials … it was more automated and Lady Love Dies … would present all of the evidence against your chosen suspect. We realised that this broke our rules and the player should choose which evidence to present so we had to tear them apart and put them back together near the end of development."* Their standing rule: *"The key is to never force the player to do anything."*
— https://1printgames.com/paradise-killer-special-developer-interview (2026-09-18)

**F10 — Some detective games refuse to adjudicate at all.** Kaizen: *"The player constructs their own truth and accuses whoever they want in an end game trial. The game never tells the player that they got it wrong or they failed to get a true ending."*
— https://the-avocado.org/2021/04/02/indie-developer-interview-kaizen-game-works/ (2026-09-18)
Josh Sawyer on Pentiment: *"On our side there's no canonical true killer, so we won't be telling the player they got it wrong. That's not really the point. It's more like: here's what you found out, this is the choice you made, and here are the consequences."*
— https://www.thegamer.com/interview-obsidian-josh-sawyer-pentiment (2026-09-18)

**F11 — Availability of an option is not endorsement of it.** Sawyer: *"just because a dialogue option appears doesn't mean it's a good idea to pick it … We want players to really think about the options they pick rather than just blindly selecting them."* This is the design justification for a **held/refused proposal that is still offerable** — the option exists, the world declines it, and the player learns why.
— https://www.thegamer.com/interview-obsidian-josh-sawyer-pentiment (2026-09-18)

**F12 — GDC 2022 framed feedback-on-a-wrong-hypothesis as the central unsolved problem of the genre.** Jon Ingold (inkle), *The Burden of Proof: Narrative Deduction Mechanics for Detective Games*: *"Having uncovered a complex crime full of twists and turns, how can the player show the game they've solved it? And what if they haven't?"* — and the talk addresses *"how it tackles the problem of proving specific feedback without removing the need for player creativity."* **Abstract only; the Vault video is gated and was not viewed.**
— https://www.gdcvault.com/play/1027723/The-Burden-of-Proof-Narrative (2026-09-18)

**F13 — Ace Attorney's entire series rests on one verb, chosen for puzzle pleasure over realism.** Shu Takumi: *"One thing I'd written intrigued me though: 'spot the contradictions'… so I decided to choose that idea to build my new game around."* On internal pushback: *"I received a lot of negative comments like, 'This game seems hard and unforgiving.' … But the point of the game wasn't 'the law' or even 'reality'."*
— https://shmuplations.com/aceattorney3 and https://news.capcomusa.com/lets/browse/shu-takumis-reflections-on-ace-attorney (2026-09-18)

---

### 1.2 The ledger / case file as an object

**F14 — The book metaphor was chosen precisely so navigation needs no tutorial.** Pope: *"Because everyone knows how a book works, I could lean into a few metaphors like chapters, bookmark system, glossary, table of contents, and more without detailed instructions."*
— https://www.gamedeveloper.com/business/road-to-the-igf-lucas-pope-s-i-return-of-the-obra-dinn-i- (2026-09-18)

**F15 — The ledger's core job is imposing order on out-of-order discovery.** *"Design-wise the book in Obra Dinn is intended to collect and organize the deluge of information thrown at the player during gameplay. It establishes the chronology of events…"* He explicitly rejected a shorter logbook and a navigable timeline in favour of *"a story-like book as the most implicitly useful metaphor."*
— https://dukope.com/devlogs/obra-dinn/tig-37 (2026-09-18)

**F16 — An empty ledger is itself the motivational engine.** *"My goal for Obra Dinn was to overwhelm the player initially, then give them time to get comfortable with the core loop before relying on their internal compulsions to motivate them into solving all the fates and completing the book."* And: *"just facing that empty book is enough to pressure me into filling it out."*
— https://www.gamedeveloper.com/business/road-to-the-igf-lucas-pope-s-i-return-of-the-obra-dinn-i- (2026-09-18)

**F17 — Shadows of Doubt's corkboard is deliberately a borrowed cultural trope so it needs no instruction.** Cole Jefferies: *"The corkboard itself is a familiar detective trope that everyone knows from movies and tv shows."* He extends this to borrowed OS affordances: *"Just the presence of a small 'X' in the top corner gives the player feedback this is an interface they are familiar with."* And the thesis: *"A good UI the player will never really notice because ideally, it presents no barrier to interaction and immersion with the game."*
— https://colepowered.com/shadows-of-doubt-devblog-4-case-folders-cork-boards/ (2026-09-18)

**F18 — Connections can carry a quantified, visually-encoded value.** *"Incrimination is passed along from one evidence item to another via connections (represented by the string) … String colours range from white to red the more incriminating a connection is. The strings also vary in width depending on how reliable a connection is."* Animation shows *"which way the incrimination is 'flowing'."*
— https://colepowered.com/shadows-of-doubt-devblog-4-case-folders-cork-boards/ (2026-09-18)

**F19 — Guaranteed solvability and information recovery must be explicit systems.** *"the killer will always leave fingerprints at the murder scene, so you have at least one clue to start with."* Plus an in-fiction recovery channel — a newspaper *"reports on each murder, listing everything found at the scene"* — because *"we always want to make sure the information is available and isn't lost completely."*
— https://www.gamesindustry.biz/making-a-true-detective-game-in-shadows-of-doubt (2026-09-18)

**F20 — Disco Elysium externalises hypotheses as slotted, time-resolving, reversible objects.** *"Each Thought comes into play face down. Only its name and some initial info are known to you. It takes in-game time to reveal its true identity by 'internalizing' it."* … *"Prior to this, you only have a vague idea of what a Thought might do. You have a set-up. A picture on a closed box."* Reversibility has a price: *"If you don't like the conclusion you've reached, you can always 'forget' the thought by spending one 'skill point'."* And crucially, thoughts can emit a next action: *"it tells you to go and ask a specific person in the world a specific question. This creates a rhythm where you talk to someone, mull it over, then return to them with a new (often revelatory) topic."*
— https://steamcommunity.com/games/632470/announcements/detail/1615021499154801682 (2026-09-18)

**F21 — Her Story's constraint is what gives an unstructured database its shape.** Sam Barlow: *"for every query you can only return five clips, and those are returned in chronological order. So the more generic terms you use, the more likely you are to be hitting the early interviews. So there is a challenge there, if you want to dig deeper. It gives it some shape."* On zero-tutorial affordance: *"If you can Google, you can play Her Story."*
— https://www.rockpapershotgun.com/text-lies-and-videotape-her-story-interview and https://www.herstorygame.com/about/ (2026-09-18)

---

### 1.3 Clue chains, "aha" pacing, and dependency graphs

**F22 — "Thought Path": author the chain of realisations, then delete clues that let players skip steps.** Golden Idol: *"we used a sort of 'thought path' scheme that would inform portions of a mystery that players needed to figure out to progress their understanding."* The pruning rule is the reusable part: *"During the testing, if players would suddenly bypass many of these steps with some other clue, we knew that we had to remove that clue because it was making parts of the game superfluous."* They also admit it did not generalise: *"we have to admit we failed to create a reliable framework for mystery building."*
— https://www.gamedeveloper.com/design/case-of-the-golden-idol and https://www.gamedeveloper.com/business/-the-case-of-the-golden-idol-i-used-frequent-testing-to-improve-its-mystery-solving (2026-09-18)

**F23 — Named pacing failure signature, usable as a QA heuristic.** *"if a player understands the main mystery immediately and then is stuck for thirty minutes on some technicality, that's bad."*
— https://www.gamedeveloper.com/business/-the-case-of-the-golden-idol-i-used-frequent-testing-to-improve-its-mystery-solving (2026-09-18)

**F24 — The "Aha!" is the explicit design target, and the pride must be the player's competence.** *"often it would take some time and players would suddenly get an insight with a loud 'Aha!' and everything would become clear to them. Those precious 'Aha!' moments are something that we strived for."* And: *"We hope we make players feel like detectives not because their character is wearing a deerstalker hat, but because they are very smart and solved the mystery."*
— https://www.gamedeveloper.com/design/case-of-the-golden-idol (2026-09-18)

**F25 — Deliberate minimalism: only solution-bearing content or intentional misdirection.** They abandoned the Obra Dinn / Gone Home "lived-in space" approach: *"This quickly proved to create a bad player experience because, on their own, our more complex scenarios contained lots of information to recall. To amend this, we focused on a very minimalistic approach where we would only fill in the contents that were either necessary to the solution or create interesting misdirections."*
— https://www.gamedeveloper.com/design/case-of-the-golden-idol (2026-09-18)

**F26 — Deduction games cannot be balanced by their authors; qualitative playtest interviews are the instrument.** 5–7 test rounds per scenario, starting from Excel tables: *"We did not rely on any hard quantitative data; for us, playtest interviews were much more important."* Relevantly for your context, **Golden Idol was built in Godot**: *"For prototyping we used Construct and for development we used the Godot engine."*
— https://www.gamedeveloper.com/design/case-of-the-golden-idol and https://www.gamedeveloper.com/business/-the-case-of-the-golden-idol-i-used-frequent-testing-to-improve-its-mystery-solving (2026-09-18)

**F27 — Deliver exposition as clue-fragments, not walls.** *"nobody is attacking you with a wall of exposition text… You have to lure in players that care about the narrative. This is something Portal did brilliantly, where you just get scraps of some shadowy mystery."*
— https://www.gamedeveloper.com/business/-the-case-of-the-golden-idol-i-used-frequent-testing-to-improve-its-mystery-solving (2026-09-18)

---

### 1.4 Academic frames

**F28 — The "4E" model of investigation gameplay: Exploration → Elicitation → Experimentation → Evaluation**, nested as an *Observation Cycle* (Explore + Elicit) and a *Deduction Cycle* (Experiment + Evaluate). Built via Grounded Theory across 32 investigation games including Obra Dinn, Golden Idol, Ace Attorney, Her Story and Paradise Killer. The most directly usable line for a case chain: *"Questions act as waypoints, directing players toward particular areas of interest. The game instills a sense of purpose and orientation in the player's experimentation by providing concrete questions to answer."* The paper also treats **Clue Storage** and **Evaluation Feedback** as explicit, tunable design axes, noting that *"in The Case of the Golden Idol and Return of the Obra Dinn, players don't receive feedback from individual experiments, but when they complete correctly many of them."*
Marques, Parreiras, Kritz, Xexéo, *A Conceptual Model for the Analysis of Investigation Elements in Games*, arXiv:2403.10272 (2024).
— https://arxiv.org/html/2403.10272v1 (2026-09-18)

**F29 — CHI PLAY 2024 gives quotable design guidelines for exactly a ledger-style UI.** Kärnä, Väkevä, Rautalahti & Lindqvist, *Questions without Answers: Enjoyment of Irresolution in Mystery Player Experience*, PACM HCI 8, CHI PLAY, Art. 335, CC BY. Verbatim from the guidelines section:
- *"Provide tools for thinking to support interpretations (T2). Since a major part of mystery solving happens inside the player's head, provide them with tools that help to unravel the big picture. DO THIS by providing the player with some form of a information map in the game where players can manage their interpretations… Consider making them apparent to your players to allow them track their progress. Depending on your aspirations for the game, pay careful attention to what extent you execute this: **DO NOT quantify all the unknowns.**"*
- *"Encourage questioning mode to facilitate exploration (T1). Start by setting player expectations by letting them know that they are playing a mystery game. Make sure in the beginning of the game that there are at least a few apparent gaps of information for the player to notice. DO THIS by making the gaps observable through open questions."*
- *"Sustain suspicions to motivate player's curiosity and uncertainty (T2)… DO THIS by offering players ambiguous, contrasting information. **DO NOT go overboard with suspicion – also remember to confirm facts.**"*
The paper also scopes ambiguity: it is *"highly encouraged"* during play but not at the end of a detective mystery, which *"need to provide clear-cut answers."*
— https://aaltodoc.aalto.fi/server/api/core/bitstreams/5516f1a8-c521-4663-bdb0-0dfd69d860fe/content (2026-09-18) · paywalled record: https://dl.acm.org/doi/10.1145/3677100

**F30 — Detective framing is itself a tutorial affordance.** Clara Fernández-Vara (DiGRA 2018) invokes Murray's *"scripting the interactor"*: genre conventions *"create expectations about what players should be doing (or not) in a game, without having to provide explicit instructions or explicitly constraining their actions."* She also flags a pacing hazard: *"the moment the rules of the story become established, the solution to the mystery becomes obvious."*
— https://dl.digra.org/index.php/dl/article/download/1033/1033/1030 (2026-09-18)

**F31 — Only known controlled evaluation of an automated hint system in an exploratory 3D puzzle game.** El Montaser, Lallé & Muratet, *Evaluating the Impact of Automated Hints in a 3D Educational Escape Game*, **IUI '25** (30th Intl. Conf. on Intelligent User Interfaces), pp. 685–694, DOI 10.1145/3708359.3712132. Design principles stated by the authors: hints provide *"gradual support through incremental levels of details"* and remain *"fully optional, so as to minimize intrusiveness and preserve a sense of autonomy"*; hint selection is driven by a Petri-net model of each puzzle's resolution. Key nuance: hints are **not** universally effective — in the harder version *"the increased play time enabled by the hints did not lead to the learners solving more puzzles."* Reported per-condition puzzle counts of 10.1 vs 4.6 (high-skill, with vs. without hints) appear on the page; I confirmed the strings exist but did not re-derive the statistics, so treat exact figures as needing a second read before quoting.
— https://dl.acm.org/doi/full/10.1145/3708359.3712132 (2026-09-18)

**F32 — Formal spec for contradiction-based evidence.** *TurnaboutLLM* (EMNLP 2025) formalises the Ace Attorney loop as: read a story, examine evidence, examine testimonies, *"find a contradiction between an evidence and a testimony."* Deductions are annotated as **reasoning-chain trees** where *"leaf nodes represent observed facts, while internal (non-leaf) nodes correspond to intermediate atomic propositions,"* and the paper reports that **answer-space size and number of reasoning steps** measurably drive difficulty — i.e. those are the calibration knobs.
— https://aclanthology.org/2025.emnlp-main.101.pdf (2026-09-18)

**F33 — Heavy HUD-based guidance has a measurable cost.** A University of Alberta thesis on immersive wayfinding argues many games rely on *"incongruous visual cues and intrusive user-interface elements"* which *"may reduce a player's spatial presence, immersion, and game enjoyment,"* and proposes environmentally-appropriate in-level cues instead. **Abstract page only; full PDF not retrieved.**
— https://ualberta.scholaris.ca/items/2888abe8-6f52-4aba-85fc-8d6616809798 (2026-09-18)

**F34 — Framing of the genre shift your game sits inside.** *Making the Player the Detective* (FDG 2020): historically *"most detective games have followed a more traditional adventure game structure, with little emphasis on actual investigation in the player's actions, but where the player more acts as a proxy for the plot to follow its course."* **Abstract only; full text paywalled; author block did not render — do not attribute without re-checking.**
— https://dl.acm.org/doi/10.1145/3402942.3402969 (2026-09-18)

---

### 1.5 Tutorial and onboarding

**F35 — The three-page-folio-at-the-start pattern is the documented failure case.** NN/g on onboarding tutorials names three structural reasons: *"Users want to start using the product right away… This is known as the **paradox of the active user**"*; *"The tutorial shows information **out of context**, and users would have to memorize it to use it when applicable."* The proposed replacement is **pull revelations** — *"help content triggered by some signal that the user would benefit from that information at that moment."* Their guidelines include making help easy to dismiss **and recall**, *"No memorization!"*, and *"Skip the obvious stuff."*
— https://www.nngroup.com/articles/onboarding-tutorials/ (2026-09-18)

**F36 — Obra Dinn tested graduated text hints in public and they failed outright.** *"If you played the game at PAX Aus you would've been treated to numerous popup messages with graduated hints and clues about how you're supposed to advance since this concept is not introduced well. **Nobody read the hints** and so most people got stuck."* The diagnosis of the alpha was blunt: *"the game not only doesn't hold your hand, it breaks both arms at the wrist and zip-ties your pinkies together… it's natural to A) get totally lost and B) not care."*
— https://dukope.com/devlogs/obra-dinn/tig-30 (2026-09-18)

**F37 — The fix was not more text. It was a mode change plus a diegetic pointer to the next valid action.** *"there's now an explicit 'corpse hunt' mode shoehorned in there… the environment is reduced to wobbly outlines and any outstanding corpses are highlighted clearly"*; *"a ghostlike effect emanates from the watch and leads you directly to where the freshly-pulled corpses will appear."* Result: *"Now it's possible to hintlessly progress through the game while piecing together its internal logic and story flow at a much more natural pace."* He accepts the modality cost: *"This whole process feels a bit uncomfortable with its modality but it so neatly draws the player along that I like it."*
— https://dukope.com/devlogs/obra-dinn/tig-30 (2026-09-18)

**F38 — Reducing the *types* of interactable object was itself a guidance fix.** *"The game goes out of its way to teach you that you shouldn't bother trying to interact with small things so having to hunt around for a small lantern switch is just bad business… Classic game design BS."* He removed item pickup entirely: *"That solves a major 'item-importance' design problem that plagued the game since the beginning."* **Directly relevant: your lens pickup is the one pickup in the game, so it must be unmissable and its interactable class must be consistent.**
— https://dukope.com/devlogs/obra-dinn/tig-30 (2026-09-18)

**F39 — Progressive disclosure, defined.** *"Initially, show users **only a few** of the most important options. Offer a **larger set** of specialized options upon request."* It *"improves 3 of usability's 5 components: learnability, efficiency of use, and error rate."* NN/g also distinguishes **staged** disclosure (linear wizard, benefit = simplicity) from **progressive** (hierarchical, benefit = learnability), and warns staged disclosure is *"problematic when the steps are interdependent and users must alternate between them"* — a direct comment on a 3-page folio.
— https://www.nngroup.com/articles/progressive-disclosure/ (2026-09-18)

**F40 — Working memory caps onboarding at about 3 new items.** Celia Hodent: *"The Working Memory span is about 5 'items' more or less 2… I suggest you to remember that 3 items to process at the same time is THE MAXIMUM when in learning mode."* Also: *"you should never punish the players WHILE THEY ARE JUST LEARNING ABOUT SOMETHING."* And teach the **why**: *"don't explain more than 3 things and focus on the *why* (main goals) rather than the *how*… or the *what*."* Her comprehension test is worth copying: ask players to *restate* the objective rather than asking whether it was clear.
— https://celiahodent.com/gamers-brain-ux-onboarding/ (2026-09-18)

**F41 — False affordances are the top onboarding killer.** *"A false affordance is when the perceived affordance is not the one intended… False cognitive affordances misinform and mislead the players, and then it makes it much harder to teach them the right thing… Make sure to track down and ruthlessly destroy all false affordances in your game."* Same source: **"show the locks before giving the keys"** — teasing a mechanic before granting it makes the reveal intrinsically motivating, and empty labelled HUD slots tease progression.
— https://celiahodent.com/gamers-brain-ux-onboarding/ (2026-09-18)

**F42 — Coach marks: one interaction at a time, and do not make them look like the UI.** *"it is more effective to **focus on a single interaction** rather than attempting to explain every possible area of the user interface."* … *"Bombarding users with frequent hint screens causes them to **dismiss hints more quickly**, regardless of how helpful each may be."* Plus: use a different font for coach marks than the main UI so users don't try to click the tutorial.
— https://www.nngroup.com/articles/mobile-instructional-overlay/ (2026-09-18)

**F43 — Recognition beats recall, and NN/g names game-style tutorials as the failure case.** *"Recognition is easier than recall because it involves more cues."* Their remedy: *"Instead of showing general tutorials, use contextual tips tailored to the page that the user is visiting."*
— https://www.nngroup.com/articles/recognition-and-recall/ (2026-09-18)

**F44 — Interactive tutorials beat instruction screens; in-gameplay teaching beats both.** *"guided interactive tuition is still far more useful for all players than a simple instructions screen… practising the interaction in the context of gameplay is less demanding on short term memory than having to recall the instruction at the point in the future where the interaction takes place."*
— https://www.gameaccessibilityguidelines.com/include-interactive-tutorials/ (2026-09-18)
And the higher tier: *"More effective again than separate tutorials… Gradually introducing concepts to the player during gameplay not only gives greater context, but also avoids overburdening gamers who are unable to process complex systems/concepts with too much information at once, and is more useful than upfront instruction/tutorial screens for people with short term memory issues."*
— https://gameaccessibilityguidelines.com/include-contextual-in-game-helpguidancetips/ (2026-09-18)

**F45 — Golden Idol names deduction-game onboarding as an open, unsolved problem.** *"We identified three main issues; gameplay flow, disjointed narrative, and the **communication of insights when the player is solving mysteries**."*
— https://www.gamedeveloper.com/business/-the-case-of-the-golden-idol-i-used-frequent-testing-to-improve-its-mystery-solving (2026-09-18)

**F46 — Shadows of Doubt carried nearly all onboarding on tooltips before a tutorial existed.** *"In absence of a tutorial, I'm relying on tooltips to communicate to players almost everything right now."*
— https://colepowered.com/shadows-of-doubt-devblog-4-case-folders-cork-boards/ (2026-09-18)

---

### 1.6 Refusal as pedagogy, objectives, and hints

**F47 — When an action is rejected, state the error *and* the correction, and visually mark where it happened.** Xbox Accessibility Guideline 115: *"the error and the method to correct the error is described to the player in multiple ways (like through text or voice narration)."* Plus *"Make error and warning messages easy to visually distinguish from other text on the screen"* and *"Visually emphasize errors and warnings where they've occurred."* **This is the specification for your held-proposal row.**
— https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/115 (2026-09-18)

**F48 — Blame the design, not the player; a refusal reveals a *mistake*, not a slip.** NN/g: *"The term 'user error' implies that the user is at fault… Not so. The designer is at fault."* Mistakes *"arise when a user has incomplete or incorrect information about the task, and develops a mental model that doesn't match how the interface actually works"* — which is exactly what a refused proposal exposes. Named prevention tools: **helpful constraints, suggestions, and good defaults** (*"Good defaults also help reduce mistakes, because they teach users about reasonable values"*).
— https://www.nngroup.com/articles/slips/ (2026-09-18)

**F49 — Objectives must be re-checkable at any time, including auto-triggered after inactivity.** *"A reminder can help greatly. Either permanently displayed, on player request, or triggered automatically, by for example spending a long time without making any progress towards an objective."*
— https://gameaccessibilityguidelines.com/indicate-allow-reminder-of-current-objectives-during-gameplay/ (2026-09-18)

**F50 — A worked, non-spoiling, configurable hint model.** *Silence*, cited by GAG as best practice for three guidelines at once: *"Configurable hints system, with options for a reminder of the current objective, highlighting interactive elements by both a name and a visual cue, and visual hints showing which inventory objects can be used with which environmental objects."*
— https://www.gameaccessibilityguidelines.com/silence-hints/ (2026-09-18)

**F51 — Signal interactivity explicitly; do not rely on shared conventions.** *"Players with cognitive or vision impairments can have difficulty distinguishing which UI elements or in-game items are intended to be interactive, and are sometimes not familiar with the same metaphors and conventions as other players. This can be achieved by clear and consistent differences in style, contrast, or **additional signifiers** such as a mouseover effect, glow, icon etc."*
— https://www.gameaccessibilityguidelines.com/give-a-clear-indication-that-interactive-elements-are-interactive/ (2026-09-18)

**F52 — Never time-gate instruction text.** *"As reading speeds and ability are so varied even within very specific age brackets, it is not possible to set a speed for text to be displayed which will be appropriate for all readers. **Instead of a timer, dismiss information on a player action**, allowing it to be stepped through."*
— https://www.gameaccessibilityguidelines.com/allow-players-to-progress-through-text-prompts-at-their-own-pace/ (2026-09-18)

**F53 — Plain language, with a stated reason.** *"Aim for as straightforward language as your copy style allows"*; *"large blocks of text can be extremely intimidating."*
— https://gameaccessibilityguidelines.com/use-simple-clear-language/ (2026-09-18)

---

### 1.7 HUD composition, legibility, accessibility

**F54 — WCAG 2.2 SC 1.4.3 Contrast (Minimum), AA:** body text needs **4.5:1**; large-scale text (**18pt / 24px**, or **14pt / 18.5px bold**) needs **3:1**. Thresholds are not rounded — *"4.499:1 would not meet the 4.5:1 threshold."* There is also a specific warning that thin fonts can nominally pass but render fainter due to anti-aliasing, so *"best practice would be for authors to choose a font with stronger/thicker lines, or to aim for a foreground/background color combination that exceeds the normative requirements."* <citation refs="LxFQOaft870bgbIhIXcIl">18 point text or 14 point bold text is judged to be large enough to require a lower contrast ratio</citation>
— https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html (2026-09-18)

**F55 — WCAG 2.2 SC 1.4.11 Non-text Contrast, AA: 3:1** for *"visual information required to identify user interface components and states"* and for *"parts of graphics required to understand the content."* <citation refs="aRopFJ52fSnzFwPsJcXgg">Ensure meaningful visual cues achieve 3:1 against the background</citation> **This governs your case-chain node borders, chain connector lines, and committed/held state pips — not just your text.**
— https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html (2026-09-18)

**F56 — WCAG 2.2 SC 2.5.8 Target Size (Minimum), AA: 24×24 CSS px**, or undersized targets spaced so that 24px-diameter circles centred on each do not intersect. The Understanding doc adds: *"As a best practice it is recommended to at least meet the minimum size requirement of the Success Criterion, regardless of spacing."* <citation refs="qL0cAMx5Soizjwj-nmnN4">The size of the target for pointer inputs is at least 24 by 24 CSS pixels</citation>
— https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html (2026-09-18)

**F57 — WCAG 2.2 SC 2.3.3 Animation from Interactions (AAA):** *"Motion animation triggered by interaction can be disabled, unless the animation is essential."* Sufficient techniques explicitly include using the reduced-motion media query, in CSS (C39) or via JavaScript (SCR40). <citation refs="IY2OYvDgbC2MzM8umVO6a">Support user preferences for motion, and eliminate unnecessary motion effects</citation>
— https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html (2026-09-18)

**F58 — `prefers-reduced-motion` is Baseline "widely available" since January 2020**, and detects *"if a user has enabled a setting on their device to minimize the amount of non-essential motion."* Relevant because your game ships in a browser, where this query is directly readable. <citation refs="QbnyHd4kFJnJKW2zqsBz6">This feature is well established and works across many devices and browser versions. It's been available across browsers since January 2020.</citation>
— https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion (2026-09-18)

**F59 — A concrete font-size floor: 28px at 1080p, treated as a minimum rather than a target.** GAG: *"Amazon TV have 10-foot-UI guidelines that include text size recommendations, of 28px minimum when viewed on a 1080p screen… because it does not take any degree of vision impairment into account, use 28px as a minimum rather than a target, aim to exceed it wherever possible."* <citation refs="br9y5NADivEs3iTVu8m9T">use 28px as a minimum rather than a target, aim to exceed it wherever possible</citation> **Note this floor is derived from 10-foot TV UI, so it is conservative for a 390px-wide handheld held at arm's length; it is a strong target for the 1280×720 desktop case.**
— https://gameaccessibilityguidelines.com/use-an-easily-readable-default-font-size/ (2026-09-18)

**F60 — Related GAG basics** that apply directly: *"Provide high contrast between text/UI and background"*, *"Use simple clear text formatting"*, *"Ensure no essential information is conveyed by a fixed colour alone"*, *"Ensure interactive elements / virtual controls are large and well spaced, particularly on small or touch screens"*, plus intermediate items *"Allow interfaces to be resized"*, *"Provide an option to adjust contrast"*, *"Provide an option to turn off / hide background movement"*, and *"Avoid placing essential temporary information outside the player's eye-line."*
— https://gameaccessibilityguidelines.com/full-list/ (2026-09-18)

**F61 — Obra Dinn's art direction is legibility-first, with an explicit refusal to hide information.** *"So geometric shapes are going to be outlined. If it's against white it'll have a black outline, if it's against black it'll have a white outline. So it's always an inverse, so the shapes and geometry are always clear to see."* And: *"it removes any mystery about where you are or the environment. Everything is perfectly defined… I wasn't making a horror game, so I didn't want to hide things from the player."*
— https://www.gamedeveloper.com/design/for-lucas-pope-i-return-of-the-obra-dinn-i-was-a-bunch-of-appealing-design-problems (2026-09-18)

**F62 — Visual comfort was treated as a multi-year, first-class problem.** *"dithering is not a technology that you want to use in a moving picture, basically because it gives you a headache… There's too many high contrast, flashing pixels."* … *"The real magic for me in making this work was solving that dithering problem and figuring out how to make it so people could play a four-hour game without getting massively uncomfortable."* Ambient motion was also restrained: *"The ship's rocking motion from the waves is intentionally subtle. Anything more and I get sick."*
— https://www.gamedeveloper.com/design/for-lucas-pope-i-return-of-the-obra-dinn-i-was-a-bunch-of-appealing-design-problems and https://dukope.com/devlogs/obra-dinn/tig-06 (2026-09-18)

**F63 — HUD zoning: compress persistent chrome into the fewest regions to maximise workspace.** Shadows of Doubt: *"I'm trying to keep the UI as minimalist as possible. In this initial design, I've managed to fit in all essential display elements into 2 compact but not overcrowded spaces. The more room the player has to browse those case files the better!"* Also, a hard scaling constraint: *"since I'm working with bitmap pixel art fonts on this project, I can't scale them properly without them looking awful. Therefore I've had to stick to 1x, 2x or more their designed size."*
— https://colepowered.com/shadows-of-doubt-devblog-4-case-folders-cork-boards/ (2026-09-18)

**F64 — Pixel-exact UI layouts do not survive a resolution change.** Pope's book was built on a fixed grid (*"the screen is 800px wide, each page is 310px wide"*), but *"the layouts were so precise, just scaling it up created too many artifacts"* when moving from 640×360 to 800×450. He also notes a framing win: *"My solution was to add visible front and back inside covers and to center the book against a black screen. I think this unintentionally improved the presentation by adding visual context and giving the dense pages some room to breath."*
— https://dukope.com/devlogs/obra-dinn/tig-37 (2026-09-18)

**F65 — Typography can carry state without an explanatory aside — but it needs a legibility escape hatch.** Pentiment's text rendering was *"not an exaggeration to say that no feature set took as much time from all departments."* Authenticity was subordinated to readability: *"We essentially just Romanised them to make them work for a modern eye… we make compromises to just make it readable, because that's obviously very important."* Sawyer at GDC 2025: *"if they looked authentic, they were often quite difficult to read. Yes, we wanted them to look authentic, but the difficult-to-read part is not good for a game full of text."* The shipped answer was a player-facing toggle offered up front: *"The Easy-read font option improves legibility by disabling some fonts and writing effects."*
— https://www.rockpapershotgun.com/how-obsidian-entertainment-resurrected-dead-fonts-for-pentiment · https://www.gamedeveloper.com/design/pentiment-director-explains-how-going-all-in-on-fonts-helped-elevate-the-medieval-detective-rpg- · https://pentiment.obsidian.net/ · https://www.polygon.com/23447253/pentiment-xbox-obsidian-font-design-text-medieval-manuscript/ (2026-09-18)

**F66 — Audio can act as an orientation landmark, not just mood.** *"the themes are subtle landmarks to help the player orient themselves in the story."*
— https://www.gamedeveloper.com/business/road-to-the-igf-lucas-pope-s-i-return-of-the-obra-dinn-i- (2026-09-18)

---

### 1.8 Godot 4 specifics

**F67 — Godot's own recommendation for your exact dual-target problem.** For a landscape mobile/desktop game: base window **1280×720**, **Stretch Mode = `canvas_items`**, **Stretch Aspect = `expand`**, and *"Configure Control nodes' anchors to snap to the correct corners using the Layout menu."* Crucially, for supporting both orientations the docs say: *"To support both portrait and landscape mode with a similar automatically determined scale factor, set your project's base resolution to be a square (1:1 aspect ratio) instead of a rectangle. For instance, if you wish to design for 1280×720 as the base resolution but wish to support both portrait and landscape mode, use 720×720 as the project's base window size."* <citation refs="JMHd32lo1FFaNxbS4jzO_">use 720×720 as the project's base window size in the Project Settings</citation> The docs also flag `GUI > Theme > Default Theme Scale` for keeping UI readable, and note it *"cannot be changed at runtime, as its value is only read once when the project starts"* — so a runtime font-scale option must go through theme font sizes or `content_scale_factor`, not that setting.
— https://docs.godotengine.org/en/stable/tutorials/rendering/multiple_resolutions.html (2026-09-18)

**F68 — Godot exposes a safe-area API.** `DisplayServer.get_display_safe_area()` returns *"the unobscured area of the display where interactive controls should be rendered,"* and `DisplayServer.get_display_cutouts()` returns notch/cutout rects — with the caveat that cutouts are *"Currently only implemented on Android. Other platforms will return an empty array even if they do have display cutouts or notches."* <citation refs="8WzdHtgFq-CfYrSVbE-LG">Returns the unobscured area of the display where interactive controls should be rendered.</citation> **Because a 390×844 web build will not get reliable cutout data, your safe-area margins must have a sane hardcoded fallback.**
— https://docs.godotengine.org/en/stable/classes/class_displayserver.html (2026-09-18)

**F69 — Anchors and offsets are the mechanism for edge-pinned HUD regions.** *"the vertical (top, bottom) anchors adjust from 0.0 (top of parent) to 1.0 (bottom of parent) with 0.5 being the center."* <citation refs="eJPEeu8Dwv62EVbQlkemx">This is done by editing the anchor offsets of controls, which behave similar to a margin.</citation>
— https://docs.godotengine.org/en/stable/tutorials/ui/size_and_anchors.html (2026-09-18)

**F70 — Precedent: The Case of the Golden Idol shipped its deduction UI in Godot** (see F26), which makes its validation-indicator and slot-grammar decisions directly transferable rather than aspirational.

---

## 2 Prioritized recommendations

Priorities: **P1** = do before anything else, high impact / small scope. **P2** = clear win, slightly more work. **P3** = polish or depends on P1/P2 landing.

Every suggestion below assumes one read-only contract:

```gdscript
# presentation/ledger_view.gd
extends Control
# Pure render. Never mutates, never caches derived game state.
func render(snapshot: Dictionary) -> void: ...
```

Anything a view needs that is not in the snapshot is either (a) **static authored content** keyed by an ID from the snapshot, or (b) **ephemeral view-local state** that dies with the view (scroll position, which hint rung is expanded, whether the folio is open). Neither is a second game-state model, and I flag which is which below.

---

### A. Case file / evidence board

**A-P1. Make the held (refused) row the most detective-feeling object in the game: `PROPOSAL → RULE → WHAT THAT TELLS YOU`.**
Right now a held row records the rule that held it. The research says that is only two thirds of a correction. XAG 115 requires both the error *and* the method to correct it (F47), and NN/g classes a refusal as a *mistake* revealing a wrong mental model (F48). Add a third static line per rule: the inference the refusal licenses. Refusing to mount the lens before the signal is inspected should not just print `RULE: SIGNAL_UNINSPECTED` — it should print *"The mount is keyed. You'd need to know the keying before you could match it."* That line is authored content keyed by `rule_id`, not new state.

```gdscript
# HeldEntryRow.tscn: PanelContainer > VBoxContainer
#   ProposalLabel   (theme_type_variation "LedgerProposal")
#   RuleLabel       (theme_type_variation "LedgerRule")   <- rule_id + rule_text from snapshot
#   InferenceLabel  (theme_type_variation "LedgerLearn")  <- RuleCopy.INFERENCE[rule_id], static
func render_held(entry: Dictionary) -> void:
    proposal_label.text = entry.proposal_text
    rule_label.text = "HELD — %s" % entry.rule_text
    inference_label.text = RuleCopy.INFERENCE.get(entry.rule_id, "")
    inference_label.visible = not inference_label.text.is_empty()
```

**A-P1. Encode committed vs held with three redundant channels: glyph, label word, and colour — never colour alone.** GAG basic (F60) and XAG 103 both prohibit colour-only encoding. Use a leading glyph (`✓` / `✗` or a filled/hollow seal), the literal words `ENTERED` / `HELD`, and colour. Then the state survives greyscale, colour-vision deficiency, and a dim phone screen.

**A-P2. Give held rows the same visual weight as committed rows, and keep them permanently.** Two independent sources support this: Shadows of Doubt's *"we always want to make sure the information is available and isn't lost completely"* (F19), and CHI PLAY's *"provide them with tools that help to unravel the big picture … allow them track their progress"* (F29). A refusal is evidence about the world's rules; it is not an error log. Do not fade, collapse, or auto-dismiss held rows.

**A-P2. Make the empty ledger visible at the start and treat it as the motivator.** Pope: *"just facing that empty book is enough to pressure me into filling it out"* (F16). Render the ledger with its slot structure present and unfilled from the first frame rather than starting blank-and-growing. Hodent's *"show the locks before giving the keys"* (F41) is the same principle from the other direction.

**A-P2. Add a section header that states the question, not the category.** The 4E model's most actionable line: *"Questions act as waypoints, directing players toward particular areas of interest"* (F28). Rename ledger sections from nouns to open questions — `WHY IS THE LIGHT SEALED?` rather than `Lighthouse`. CHI PLAY's T1 guideline is the same instruction: *"making the gaps observable through open questions"* (F29).

**A-P3. If you ever add a fourth chain node, add a closeness indicator before you add hints.** Golden Idol's exact sequence: binary validation was fine at tutorial scale and broke at real scale (F4), and the fix was partial-progress sub-puzzles plus a bounded `two or fewer slots are incorrect` signal (F5) — with the honest admission that it *"reduced the difficulty and length of the game."* At three nodes you do not need this yet. Note the threshold where you will.

**A-P3. Do not quantify everything.** CHI PLAY is explicit: *"DO NOT quantify all the unknowns"* (F29). A `3/3` chain counter is fine because the chain is the tutorial spine. A global `12/40 clues found` counter would convert deduction into collection. Keep exactly one progress number on screen.

---

### B. Guided tutorial

**B-P1. Keep the three-page folio, but demote it from "the tutorial" to "the reference card," and make it reopenable.** Every source converges here. NN/g: upfront tutorials fail on the paradox of the active user and out-of-context information, and help must be easy to dismiss *and recall* (F35). Pope tested exactly your pattern at PAX and *"Nobody read the hints"* (F36). GAG ranks contextual in-gameplay teaching above interactive tutorials above instruction screens (F44). Smallest change with the largest return: add a persistent **`FOLIO`** button in the HUD that reopens the same three pages at any time, and make page 1 the only page shown at boot.

```gdscript
# TutorialFolio is a CanvasLayer > Control. `open_page` is view-local ephemeral state.
func _on_folio_button_pressed() -> void:
    folio.open_at(0)   # never blocks input permanently; ESC / tap-outside closes
```

**B-P1. Move folio pages 2 and 3 to just-in-time trigger points, driven by committed state.** Page 2 (how the ledger works) should surface the first time a committed entry exists; page 3 (what a hold means) should surface the first time a held entry exists. This is teaching a rule *after* a refusal, which is precisely the F47/F48 pattern, and it is a pure function of the snapshot — no new state:

```gdscript
func render(snapshot: Dictionary) -> void:
    var has_commit := snapshot.ledger.any(func(e): return e.state == "committed")
    var has_held   := snapshot.ledger.any(func(e): return e.state == "held")
    _maybe_show_card("ledger_intro", has_commit)
    _maybe_show_card("hold_intro", has_held)
    # _shown_cards is a view-local Dictionary; it is presentation memory, not game state.
```

**B-P1. Never auto-advance folio pages on a timer.** GAG: *"Instead of a timer, dismiss information on a player action, allowing it to be stepped through"* (F52).

**B-P2. Cap each folio page and each just-in-time card at three new ideas, and lead with *why*.** Hodent: *"3 items to process at the same time is THE MAXIMUM when in learning mode"* and *"focus on the why (main goals) rather than the how… or the what"* (F40). Page 1 should say *why* Mira needs the signal lit and *what the ledger is for*, not enumerate controls.

**B-P2. Style tutorial cards so they cannot be mistaken for the HUD.** NN/g's coach-mark rule: *"use a different font for coach marks than the one used for the main UI"* (F42). Give the folio a distinct `theme_type_variation` (paper stock, different face, offset baseline) so the player never tries to click through a tutorial card as if it were a ledger row.

**B-P2. One interaction per card.** *"it is more effective to focus on a single interaction rather than attempting to explain every possible area of the user interface"* (F42), and stacking hints makes players dismiss them faster regardless of quality.

**B-P3. Test comprehension by asking players to restate the objective, not whether it was clear.** Hodent's method (F40); Golden Idol ran 5–7 qualitative rounds per scenario with no quantitative data (F26). For a micro-RPG, five testers who can each state the current chain node in their own words is a sufficient bar.

---

### C. Objective and hint system

**C-P1. Derive the objective line from the case chain; do not store it.** The next objective is exactly "the first chain node that is not committed." That is one pure function over the snapshot, and it structurally cannot desync:

```gdscript
const CHAIN := ["LENS", "MOUNT", "LEAD"]
func current_objective(snapshot: Dictionary) -> String:
    for id in CHAIN:
        if not snapshot.case_chain[id].committed:
            return ObjectiveCopy.TEXT[id]
    return ObjectiveCopy.TEXT["DONE"]
```

**C-P1. Make the objective re-checkable at all times.** GAG: *"Either permanently displayed, on player request, or triggered automatically, by for example spending a long time without making any progress"* (F49). Given a micro-RPG, permanently displayed at top-left is the cheapest correct answer.

**C-P2. Build a three-rung, opt-in, non-spoiling hint ladder keyed by chain node.** IUI '25 supports exactly this shape: *"gradual support through incremental levels of details"* and *"fully optional, so as to minimize intrusiveness and preserve a sense of autonomy"* (F31); *Silence* is the worked game example (F50). Rungs: **(1)** restate the open question; **(2)** name the place or person to attend to; **(3)** name the next valid action. Store the expanded rung as view-local ephemeral state — a player who reloads should start at rung 0.

```gdscript
# HintPanel.gd — _rung is view-local, resets on scene enter. Text is static, keyed by node id.
func _on_more_pressed() -> void:
    _rung = mini(_rung + 1, 2)
    _refresh(current_chain_node)   # chain node comes from the committed snapshot
```

Read F31's nuance honestly: hints raised retention but not progression in the harder condition. Hints buy patience, not insight. Your insight must come from the refusal copy (A-P1), not from the ladder.

**C-P3. Prefer a diegetic pointer over a HUD marker for the "next valid action" rung.** Pope's replacement for failed text hints was a mode change plus an in-world glow that *"leads you directly to"* the target (F37); the Alberta wayfinding thesis argues intrusive UI markers *"may reduce a player's spatial presence, immersion, and game enjoyment"* (F33). In your harbor: a faint reflected glint from the signal lens, or Mira glancing toward the signal mast, at rung 3 only.

**C-P3. Audit the harbor for false affordances and for inconsistent interactable classes.** Hodent: *"track down and ruthlessly destroy all false affordances"* (F41). Pope's version is more specific and more relevant to you: he removed item pickup entirely because one collectable in a world that teaches you not to touch small things is *"Classic game design BS"* (F38). **Your signal lens is the only pickup in the game.** It must either be visually unmistakable as an interactable class of one, or you need a second, useless-but-pickable object so the class is learnable. Pair this with GAG's *"additional signifiers such as a mouseover effect, glow, icon"* (F51).

---

### D. HUD composition

**D-P1. Four fixed zones, no overlap, in this reading order.** Shadows of Doubt compressed all persistent chrome into two regions to maximise workspace (F63). Yours needs four, so pin each to an anchor and never let them float:

| Zone | Anchor | Content | Rationale |
|---|---|---|---|
| Objective | top-left | one line, current chain node | GAG: keep essential info in eye-line (F60) |
| Case chain | top-centre | LENS → MOUNT → LEAD | the spine; the question waypoints (F28) |
| Ledger handle | top-right / bottom-right on mobile | button + unread pip | the map of interpretations (F29) |
| Prompt / dialogue | bottom-centre | interaction prompt, Mira's lines | nearest the action, thumb-reachable |

Use `MarginContainer` → `VBoxContainer` / `HBoxContainer` with anchor presets rather than hand-placed offsets. Pope's lesson is unambiguous: pixel-exact layouts *"were so precise, just scaling it up created too many artifacts"* (F64), and you have two target resolutions.

**D-P1. Wrap the whole HUD in a safe-area margin with a hardcoded fallback.** `DisplayServer.get_display_safe_area()` is the right API (F68), but cutouts are Android-only, so a 390×844 browser build will report nothing useful.

```gdscript
# SafeAreaMargin.gd  (extends MarginContainer, top of the HUD CanvasLayer)
const FALLBACK := {"top": 24, "bottom": 20, "left": 12, "right": 12}
func _apply() -> void:
    var vp := get_viewport_rect().size
    var safe := DisplayServer.get_display_safe_area()
    var scale := vp.y / float(max(safe.size.y, 1))
    var top := int(max(safe.position.y * scale, FALLBACK.top)) if safe.size.y > 0 else FALLBACK.top
    add_theme_constant_override("margin_top", top)
    # ... left / right / bottom likewise; call on ready and on get_viewport().size_changed
```

**D-P1. Set the type scale from the 28px-at-1080p floor, then work backwards to each target.** GAG's floor is 28px at 1080p, explicitly a minimum not a target (F59). At a 1280×720 design space upscaled to 1080p the factor is 1.5, so **body text must be ≥ 19px in design space (20px is the clean number), and ≥ 24px for anything the player must read under time pressure.** Set this once in a `Theme` resource with `theme_type_variation` roles rather than per-node font-size overrides:

| Role | 720p design px | Notes |
|---|---|---|
| `HudObjective` | 24 | crosses WCAG "large text" at 24px, so 3:1 suffices (F54) |
| `LedgerEntry` | 20 | body, needs 4.5:1 |
| `LedgerRule` | 20 bold | bold ≥ 18.5px also qualifies as large text (F54) |
| `DialogueBody` | 22 | |
| `ChainNodeLabel` | 18 + icon | never the sole carrier of state |
| `HashMono` | 18 | monospace, selectable, see E-P2 |

On 390×844, if you go with `canvas_items` + `expand`, verify the *rendered* size on device rather than trusting the design number — F67 is the mechanism, not a guarantee.

**D-P2. Set the project stretch config deliberately, and consider a square base.** Godot's own guidance for a project targeting both orientations: base **720×720**, `canvas_items`, `expand`, Control anchors snapped via the Layout menu (F67). If you keep 1280×720 as the base, then on 390×844 the `expand` aspect will grow the viewport vertically and your top and bottom zones must be genuinely anchor-pinned, not offset-positioned, or they will drift into the middle of the screen.

**D-P2. Meet 3:1 non-text contrast on chain nodes and connectors, not just on text.** SC 1.4.11 covers *"visual information required to identify user interface components and states"* and *"parts of graphics required to understand the content"* (F55). Your `LENS → MOUNT → LEAD` connectors and the committed/pending node rings are exactly that. Nautical UI tends toward low-contrast brass-on-navy; check the ring stroke against its backing, not just against the page.

**D-P2. Meet 24×24 CSS px targets, and go to 44px on touch.** SC 2.5.8's floor is 24×24 or equivalent spacing (F56); GAG asks for large, well-spaced controls *"particularly on small or touch screens"* (F60). Set `custom_minimum_size = Vector2(44, 44)` on the folio button, ledger handle, hint rung button, and dialogue advance on the mobile layout.

**D-P2. Outline-based legibility over atmospheric murk.** Pope forced inverse outlines so *"the shapes and geometry are always clear to see"* and refused to hide the environment because *"I wasn't making a horror game"* (F61). A sealed dark lighthouse invites exactly the wrong instinct — keep the *lighthouse* dark and the *harbor readable*. Interactables get a rim or outline that inverts against their backing.

**D-P3. Wire one reduced-motion flag and gate every tween through it.** SC 2.3.3 asks that interaction-triggered motion be disablable (F57), the media query is Baseline-widely-available (F58), and Pope spent years on exactly this class of comfort problem (F62). In a web build you can read the OS preference directly:

```gdscript
# Settings.gd (autoload). One bool, consulted by every animating view.
var reduced_motion := false
func _ready() -> void:
    if OS.has_feature("web"):
        var win = JavaScriptBridge.get_interface("window")
        if win:
            reduced_motion = bool(win.matchMedia("(prefers-reduced-motion: reduce)").matches)
    # plus an in-game toggle that overrides, per GAG "Provide an option to turn off background movement"
```

Then in each view: if `reduced_motion`, set the final property value directly instead of creating the `Tween`. Apply this to ledger row entry, chain-node fill, end-card page transitions, and any harbor water/ambient drift. Also give the same flag authority over background motion per GAG (F60).

**D-P3. Offer a high-contrast / larger-text option.** GAG intermediate: *"Provide an option to adjust contrast"*, *"Allow interfaces to be resized"* (F60). Pentiment's precedent is stronger: the legibility toggle is offered **at the start of the game**, not buried (F65). A second `Theme` resource plus a `content_scale_factor` multiplier gets you both cheaply. Do not use `GUI > Theme > Default Theme Scale` for this — Godot notes it *"cannot be changed at runtime"* (F67).

**D-P3. Consider an audio landmark per chain node.** *"the themes are subtle landmarks to help the player orient themselves in the story"* (F66). Three short distinct stings for LENS / MOUNT / LEAD give a non-visual progress channel, which also satisfies GAG's "reinforce with more than one channel."

---

### E. End card

**E-P1. Present the receipt as a paged document with a visible page number, not one scroll.** Obra Dinn's *"final insurance tally"* is *"a multipage report that summarize the results of your investigation,"* and Pope specifically notes *"The page number is functionally important to make it clear you're flipping through the report"* (F15/F64 source). Three pages maps naturally onto your three sections: **Contributions**, **Rules learned**, **Validator hash**.

**E-P1. Make "Rules learned" the emotional payload, sourced from the held entries.** This is where your architecture is already better than most. Every held proposal carries the rule that held it; the end card can render the distinct set of rules encountered as *things the player figured out*, which is Golden Idol's stated aim — *"we make players feel like detectives … because they are very smart and solved the mystery"* (F24). Pure derivation, no new state:

```gdscript
func rules_learned(snapshot: Dictionary) -> Array:
    var seen := {}
    for e in snapshot.ledger:
        if e.state == "held":
            seen[e.rule_id] = e.rule_text
    return seen.values()
```

**E-P2. Make the validator hash selectable, copyable, and monospaced, with a 24px+ copy target.** A hash the player cannot copy is decoration. Use a `LineEdit` in read-only mode (selectable, keyboard-accessible) or a `Label` plus a `Button` calling `DisplayServer.clipboard_set()`. Meets SC 2.5.8 (F56) and keeps the artifact functional.

**E-P3. Close the loop the game opened, and close it cleanly.** CHI PLAY's scoping note is precise: ambiguity during play is *"highly encouraged,"* but detective mysteries *"need to provide clear-cut answers"* at the end (F29). The lighthouse stays dark and sealed by design — so the end card must be unambiguous about *what was settled* (the tide-route lead was earned, on this evidence, under these rules) while leaving the lighthouse explicitly open as the next question. Fernández-Vara's warning applies: once the rules of the story are fully established, the remaining mystery stops being mysterious (F30). State the settled part plainly; name the unsettled part as a question, not as a tease.

---

## 3 Anti-patterns to avoid

1. **Treating the three-page folio as "the tutorial."** Upfront, out-of-context instruction fails on the paradox of the active user (F35), and Pope's public test found *"Nobody read the hints"* (F36). It is a reference card; the teaching has to happen at the moment of use.
2. **Answering a failed hint with more hint text.** Pope's fix was a mode change plus a diegetic pointer, not better copy (F37). If players miss something, change what they see, not what they read.
3. **Stacking tutorial cards.** *"Bombarding users with frequent hint screens causes them to dismiss hints more quickly, regardless of how helpful each may be"* (F42).
4. **Tutorial cards styled like the HUD.** Players will try to click them as if they were live controls (F42).
5. **Timed auto-advance on instruction text.** Explicitly prohibited: dismiss on player action instead (F52).
6. **Punishing a refused proposal.** Pope declined punishment even though his community proposed it (F2); Hodent: *"never punish the players WHILE THEY ARE JUST LEARNING"* (F40). A hold is a lesson, not a penalty.
7. **Binary all-or-nothing validation once the chain grows past tutorial length.** It *"worked fine for a smaller, tutorial-like scenario"* and frustrated players at real scale (F4).
8. **A confirmation rule that reads as an instruction to brute-force.** Obra Dinn's batch-of-3 leaked in practice — a player reports *"it felt that this brute forcing is the intended method"* and consequently missed a whole deduction route (F3, player comment, unrebutted). If you ever publish your validation threshold, assume it becomes a strategy.
9. **Multiple-choice conclusions.** *"you deny the player the actual act of deduction"* (F6).
10. **Free-text conclusions.** Punishes syntax, not reasoning (F6). Your slot/proposal model is already on the correct part of this spectrum — do not drift off it in either direction.
11. **Auto-assembling the player's case for them.** Kaizen tore down and rebuilt their trial late in development specifically to stop this (F9).
12. **Colour as the sole carrier of committed/held state.** GAG basic, and XAG 103 (F60, F47-adjacent).
13. **Quantifying every unknown.** *"DO NOT quantify all the unknowns"* (F29). One progress number, which is the chain.
14. **Intrusive HUD wayfinding markers as the default guidance layer.** They *"may reduce a player's spatial presence, immersion, and game enjoyment"* (F33).
15. **One special interactable in a world that teaches you not to touch things.** Pope calls this *"Classic game design BS"* and deleted item pickup rather than live with it (F38). Your signal lens is this exact risk.
16. **Pixel-exact HUD layouts tuned to 1280×720.** *"the layouts were so precise, just scaling it up created too many artifacts"* (F64). Use anchors and containers; verify on 390×844.
17. **Atmospheric low-contrast UI because the game is about a dark lighthouse.** Obra Dinn deliberately refused to hide the environment (F61); low-contrast brass-on-navy will fail SC 1.4.3 and 1.4.11 (F54, F55).
18. **Style-driven typefaces with no legibility escape hatch.** Pentiment shipped an easy-read toggle offered at the start precisely because authentic letterforms *"were often quite difficult to read"* (F65).
19. **Unconditional motion on ledger, chain, and end-card transitions.** SC 2.3.3 plus `prefers-reduced-motion` (F57, F58); Pope treated visual comfort as a years-long problem, not polish (F62).
20. **Discarding or fading held entries after they stop being "current."** Information must not be lost (F19); held rows are the record of what the player learned.
21. **A ledger progress model that lives in the view.** Your own constraint, and it is the right one — the moment `LedgerView` caches "which entries are committed" you own two truths that will diverge. Every derived value in the suggestions above is recomputed from the snapshot on `render()`.
22. **Confusing view-local ephemera with game state in the other direction.** Hint rung, open folio page, and scroll offset are *presentation* and belong in the view. Do not promote them into the committed model just to satisfy the single-model rule.

---

## 4 Sources

All retrieved **2026-09-18**. Grouped by type. Items with caveats are marked.

### Developer primary sources — devlogs, first-party pages
1. Lucas Pope, Obra Dinn devlog (fate validation, alpha guidance failure, PAX hint failure, corpse-hunt mode, the Book, SVO fates) — https://dukope.com/devlogs/obra-dinn/tig-30
2. Lucas Pope, Obra Dinn devlog (brute force, wave motion comfort) — https://dukope.com/devlogs/obra-dinn/tig-06
3. Lucas Pope, Obra Dinn devlog (book implementation, UI grid, insurance tally; also contains the player brute-force complaint in replies) — https://dukope.com/devlogs/obra-dinn/tig-37
4. Cole Jefferies, Shadows of Doubt DevBlog 4 (corkboard, incrimination strings, skeuomorphism, bitmap fonts, HUD zoning, tooltips) — https://colepowered.com/shadows-of-doubt-devblog-4-case-folders-cork-boards/
5. Robert Kurvitz, Disco Elysium Steam announcement — Thought Cabinet — https://steamcommunity.com/games/632470/announcements/detail/1615021499154801682
6. Kaizen Game Works, Paradise Killer product page — https://kaizengameworks.com/portfolio-items/paradise-killer
7. Sam Barlow, Her Story official about page — https://www.herstorygame.com/about/
8. Obsidian, Pentiment accessibility page (Easy-read font option) — https://pentiment.obsidian.net/

### Developer interviews and postmortems
9. Road to the IGF: Lucas Pope, *Return of the Obra Dinn* (book metaphor, pacing intent, music landmarks) — https://www.gamedeveloper.com/business/road-to-the-igf-lucas-pope-s-i-return-of-the-obra-dinn-i-
10. Game Developer: *For Lucas Pope, Return of the Obra Dinn was a bunch of appealing design problems* (outlining/legibility, dither comfort, matrix core mechanic) — https://www.gamedeveloper.com/design/for-lucas-pope-i-return-of-the-obra-dinn-i-was-a-bunch-of-appealing-design-problems
11. Andrejs Klavins, *The Case of the Golden Idol* design interview (validation indicator, input spectrum, thought path, minimalism, "Aha!") — https://www.gamedeveloper.com/design/case-of-the-golden-idol
12. Road to the IGF 2023: Golden Idol used frequent testing (testing cadence, Thought Path worked example, Godot, three genre problems) — https://www.gamedeveloper.com/business/-the-case-of-the-golden-idol-i-used-frequent-testing-to-improve-its-mystery-solving
13. Playstack interview with Color Gray Games, archived — https://web.archive.org/web/20221220161119/https://playstack.com/blog-color-gray-interview/
14. Kaizen Game Works interview, The Avocado — https://the-avocado.org/2021/04/02/indie-developer-interview-kaizen-game-works/
15. Kaizen Game Works, 1Print Games developer interview (trial rebuild, never force the player) — https://1printgames.com/paradise-killer-special-developer-interview
16. Sam Barlow, Rock Paper Shotgun Her Story interview — https://www.rockpapershotgun.com/text-lies-and-videotape-her-story-interview
17. Game Developer, *Making Her Story and using the player's imagination as a narrative tool* (write-up of the GDC 2016 talk) — https://www.gamedeveloper.com/design/video-making-i-her-story-i-and-using-the-player-s-imagination-as-a-narrative-tool
18. Josh Sawyer, TheGamer Pentiment interview (no canonical killer; dialogue options) — https://www.thegamer.com/interview-obsidian-josh-sawyer-pentiment
19. Rock Paper Shotgun, *How Obsidian resurrected dead fonts for Pentiment* — https://www.rockpapershotgun.com/how-obsidian-entertainment-resurrected-dead-fonts-for-pentiment
20. Game Developer, Pentiment director on fonts (GDC 2025) — https://www.gamedeveloper.com/design/pentiment-director-explains-how-going-all-in-on-fonts-helped-elevate-the-medieval-detective-rpg-
21. Polygon, Pentiment font design — https://www.polygon.com/23447253/pentiment-xbox-obsidian-font-design-text-medieval-manuscript/
22. GamesIndustry.biz, *Making a true detective game in Shadows of Doubt* — https://www.gamesindustry.biz/making-a-true-detective-game-in-shadows-of-doubt
23. Shu Takumi reflections, Capcom — https://news.capcomusa.com/lets/browse/shu-takumis-reflections-on-ace-attorney
24. Shmuplations, Ace Attorney 3 / Takumi material — https://shmuplations.com/aceattorney3 — *caveat: the pacing note is shmuplations' editorial caption on Takumi's tweeted planning notes, not a direct quote*

### Conference talk pages — abstracts only, videos gated and not viewed
25. Jon Ingold (inkle), *The Burden of Proof: Narrative Deduction Mechanics for Detective Games*, GDC 2022 — https://www.gdcvault.com/play/1027723/The-Burden-of-Proof-Narrative
26. Nicolae Berbece, *This is a Talk About Tutorials, Press 'A' to Skip*, GDC Europe 2016 — https://www.gdcvault.com/play/1023845/This-is-a-Talk-About
27. Game Developer write-up of #26 — https://www.gamedeveloper.com/design/video-a-game-dev-s-guide-to-designing-great-tutorials

### Academic
28. Marques, Parreiras, Kritz & Xexéo, *A Conceptual Model for the Analysis of Investigation Elements in Games*, arXiv:2403.10272 (2024) — https://arxiv.org/html/2403.10272v1
29. Kärnä, Väkevä, Rautalahti & Lindqvist, *Questions without Answers: Enjoyment of Irresolution in Mystery Player Experience*, PACM HCI 8, CHI PLAY, Art. 335 (Oct 2024), CC BY — https://aaltodoc.aalto.fi/server/api/core/bitstreams/5516f1a8-c521-4663-bdb0-0dfd69d860fe/content (record: https://dl.acm.org/doi/10.1145/3677100)
30. Fernández-Vara, *Game Narrative Through the Detective Lens*, DiGRA 2018 extended abstract — https://dl.digra.org/index.php/dl/article/download/1033/1033/1030
31. El Montaser, Lallé & Muratet, *Evaluating the Impact of Automated Hints in a 3D Educational Escape Game*, **IUI '25**, pp. 685–694, DOI 10.1145/3708359.3712132 — https://dl.acm.org/doi/full/10.1145/3708359.3712132 — *venue verified in-browser; exact effect sizes not independently re-derived*
32. Yuan, He, Shahid, Huang, Li & Zhang, *TurnaboutLLM: A Deductive Reasoning Benchmark from Detective Games*, EMNLP 2025 Main — https://aclanthology.org/2025.emnlp-main.101.pdf
33. *Making the Player the Detective*, FDG 2020, DOI 10.1145/3402942.3402969 — https://dl.acm.org/doi/10.1145/3402942.3402969 — *abstract only; author block did not render, do not attribute without re-checking*
34. *Generating Clue-Driven Investigative Game Narratives with Large Language Models*, DOI 10.1145/3815598.3815649 — https://dl.acm.org/doi/10.1145/3815598.3815649 — *author block not captured*
35. *Immersive Wayfinding Cues for 3D Video Games*, University of Alberta thesis — https://ualberta.scholaris.ca/items/2888abe8-6f52-4aba-85fc-8d6616809798 — *abstract page only; full PDF not retrieved*

### UX / onboarding practitioner literature
36. NN/g, *Progressive Disclosure* — https://www.nngroup.com/articles/progressive-disclosure/
37. NN/g, *Onboarding Tutorials* (push vs pull, paradox of the active user) — https://www.nngroup.com/articles/onboarding-tutorials/
38. NN/g, *Mobile Instructional Overlays / coach marks* — https://www.nngroup.com/articles/mobile-instructional-overlay/
39. NN/g, *Recognition vs Recall* — https://www.nngroup.com/articles/recognition-and-recall/
40. NN/g, *Slips vs Mistakes* — https://www.nngroup.com/articles/slips/
41. Celia Hodent, *The Gamer's Brain — UX of Onboarding* — https://celiahodent.com/gamers-brain-ux-onboarding/
42. Celia Hodent, *UX Practices at Epic Games* (7 usability heuristics, curse of knowledge) — https://celiahodent.com/ux-practices-epic-games

### Accessibility standards and guidelines
43. W3C, Understanding SC 1.4.3 Contrast (Minimum) — https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
44. W3C, Understanding SC 1.4.11 Non-text Contrast — https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html
45. W3C, Understanding SC 2.5.8 Target Size (Minimum) — https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html
46. W3C, Understanding SC 2.3.3 Animation from Interactions — https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html
47. MDN, `prefers-reduced-motion` — https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion
48. Game Accessibility Guidelines, full list — https://gameaccessibilityguidelines.com/full-list/
49. GAG, *Use an easily readable default font size* (28px @ 1080p floor) — https://gameaccessibilityguidelines.com/use-an-easily-readable-default-font-size/
50. GAG, *Indicate / allow reminder of current objectives during gameplay* — https://gameaccessibilityguidelines.com/indicate-allow-reminder-of-current-objectives-during-gameplay/
51. GAG, *Include contextual in-game help / guidance / tips* — https://gameaccessibilityguidelines.com/include-contextual-in-game-helpguidancetips/
52. GAG, *Include interactive tutorials* — https://www.gameaccessibilityguidelines.com/include-interactive-tutorials/
53. GAG, *Allow players to progress through text prompts at their own pace* — https://www.gameaccessibilityguidelines.com/allow-players-to-progress-through-text-prompts-at-their-own-pace/
54. GAG, *Give a clear indication that interactive elements are interactive* — https://www.gameaccessibilityguidelines.com/give-a-clear-indication-that-interactive-elements-are-interactive/
55. GAG, *Silence* hints (best-practice example) — https://www.gameaccessibilityguidelines.com/silence-hints/
56. GAG, *Use simple clear language* — https://gameaccessibilityguidelines.com/use-simple-clear-language/
57. Xbox Accessibility Guideline 115 — Errors — https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/115
58. Xbox Accessibility Guideline 103 — Text and captions — https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/103

### Godot documentation
59. Godot, *Multiple resolutions* (stretch mode/aspect, square base for dual orientation, theme scale) — https://docs.godotengine.org/en/stable/tutorials/rendering/multiple_resolutions.html
60. Godot, *Size and anchors* — https://docs.godotengine.org/en/stable/tutorials/ui/size_and_anchors.html
61. Godot, `DisplayServer` class reference (`get_display_safe_area`, `get_display_cutouts`) — https://docs.godotengine.org/en/stable/classes/class_displayserver.html

### Opened but unusable — not cited as evidence
- `https://developer.apple.com/design/human-interface-guidelines/layout` — returned an empty body on two attempts (JS-rendered).
- `https://news.xbox.com/en-us/2022/10/13/xbox-accessibility-showcase-2022/easy-read-fonts-in-pentiment/` — 200 but body was site navigation chrome only.
- `https://link.springer.com/chapter/10.1007/978-3-031-78453-8_9` (Shadows of Doubt agency paper, ICIDS 2024) — page refused to load content.
- `https://www.mdpi.com/2227-9709/10/1/6` (tutorial impact in video games) — HTTP 403.
- `http://www.diva-portal.org/smash/record.jsf?pid=diva2:1875098` (adaptive hint system thesis) — blocked by anti-scraping gate.
- `https://ieeexplore.ieee.org/document/10017301` (Adaptive Hint System for Puzzle Games, IEEE GEM 2022) — not opened; listed only so you know it exists.
- `https://www.bbc.co.uk/gel/features/how-to-design-onboarding-for-games` — empty body on two attempts.
- GDC Vault video players — members-only; only public abstracts were read.

### Known gaps
- **No standalone peer-reviewed case study of Obra Dinn or Her Story** was found that I could open; both appear only as case studies inside sources 28 and 29.
- **Escalating non-spoiling hint ladders** are thinly sourced: source 31 (IUI '25) and source 55 (*Silence*) are the only credible ones. Searches for "puzzle hint system design" returned mostly AI-generated content farms, which I excluded deliberately.
- **No developer statement on Ace Attorney's penalty / press-vs-present rationale** was found; sources 23–24 are the closest primary material.
- **"Teach the rule after a violation" as an explicitly named pedagogy** is not stated as such in any source I found. I assembled it from the mechanism (source 57), the framing (source 40), and the open problem statement (source 25). Treat it as a synthesis, not a citation.