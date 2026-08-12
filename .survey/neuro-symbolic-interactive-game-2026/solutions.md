# Solution Landscape: Neuro-Symbolic Interactive Game Research 2026

## Solution List

| Name | Approach | Strengths | Weaknesses | Notes |
|------|----------|-----------|------------|-------|
| Qwen-AgentWorld-35B-A3B | Language world model | Explicit environment simulation research; Apache-2.0 | New, experimental, not game-specific | 2026 primary candidate |
| Phi-4-mini-instruct | Compact instruction model | MIT, 4B edge/latency baseline | Lower long-horizon ceiling | Small-model baseline |
| Qwen3-14B | Hybrid reasoning instruction model | Multilingual, Apache-2.0 | Long-context extension cost | Practical open baseline |
| DeepSeek-R1-Distill-Qwen-14B | Distilled reasoning model | MIT, formalization/repair candidate | Verbose reasoning may not yield executable actions | Reasoning baseline |
| OLMo-2-13B-Instruct | Open training-artifact model | Reproducibility-oriented, Apache-2.0 | Shorter context and English focus | Audit baseline |
| gpt-oss-20b | Open reasoning model | Structured outputs; documented 16 GB profile | Text-only; usage policy accompanies Apache license | Local reasoning baseline |
| Mistral Small 3.1 24B | Multimodal/function-calling model | Image+text, Apache-2.0 | Higher local VRAM | Strong local comparator |
| Qwen3-VL-8B-Instruct | Compact vision-language model | UI/spatial observation, Apache-2.0 | Visual state is not canonical truth | Visual observer |
| GPT-5.4 | Hosted frontier | Snapshot, 1.05M context, strong tool use | Proprietary, cost and drift risk | Hosted quality ceiling |
| Gemini 3.6 Flash | Hosted multimodal | Video and low-latency agentic control | Proprietary; API lifecycle | Real-time/multimodal ceiling |

## Categories

- World simulation: Qwen-AgentWorld.
- Practical open proposers: Phi-4-mini, Qwen3-14B, OLMo-2, gpt-oss, Mistral Small 3.1.
- Formalizer/repair candidate: DeepSeek-R1-Distill-Qwen-14B.
- Multimodal controls: Qwen3-VL, Mistral Small 3.1, Gemini 3.6 Flash.
- Hosted ceilings: GPT-5.4 and Gemini 3.6 Flash.
- Non-model stack: typed event log, KG/RAG, Z3/PDDL/graph reachability, deterministic replay, MLflow-compatible trace evaluation.

## What People Actually Use

Official model cards consistently expose Transformers, vLLM/SGLang, llama.cpp/Ollama, or API paths. The portable experiment boundary is therefore an OpenAI-compatible structured-output adapter plus a strict trace schema, not a model-specific orchestration framework. `direct page retrieval`

## Frequency Ranking

1. LLM proposer + deterministic validator + repair.
2. Lore RAG/KG + symbolic disclosure/quest policy.
3. Exact-model revision, prompt hash, seed, cost, and latency trace.
4. Two-stage model screening before confirmatory ablation.
5. Multimodal affect as a soft signal with uncertainty fallback.

## Key Gaps

- No public benchmark currently unifies playable world validity, NPC disclosure, long-horizon memory, and affect adaptation.
- Model-card benchmarks do not measure game-state commit safety.
- Human evaluation plans in the source drafts are underpowered for broad claims.
- "NPC Mind" and several 2026 titles in the source archive lack primary-source confirmation and remain excluded.

## Contradictions

- Larger or more constrained models may improve consistency while reducing improvisational believability.
- RAG can improve factual grounding but cannot guarantee hard game rules.
- Video models recognize visible cues yet may not infer latent engagement reliably.
- Open weights are not synonymous with OSI-approved open source; licenses must remain explicit.

## Key Insight

The publishable unit is the controller and its audit trail, not a claim that any single model is an NPC engine. Screen ten models, promote three representative models, and test whether the same hard symbolic commit gate produces model-size-independent safety gains.

## Curated Sources

- [IVIE](https://arxiv.org/abs/2606.13348) — `direct page retrieval`
- [Symbolically Scaffolded Play](https://arxiv.org/abs/2510.25820) — `direct page retrieval`
- [KNUDGE](https://arxiv.org/abs/2212.10618) — `direct page retrieval`
- [GameVibe VLM study](https://arxiv.org/abs/2603.18480) — `direct page retrieval`
- [Qwen-AgentWorld](https://github.com/QwenLM/Qwen-AgentWorld) — `direct page retrieval`
- [gpt-oss](https://openai.com/index/introducing-gpt-oss/) — `direct page retrieval`
- [Mistral 3](https://mistral.ai/news/mistral-3/) — `direct page retrieval`
- [GPT-5.4 API model](https://developers.openai.com/api/docs/models/gpt-5.4) — `direct page retrieval`
- [Gemini 3.6 Flash](https://ai.google.dev/gemini-api/docs/latest-model) — `direct page retrieval`
