# Deep Research Report: 2026 Model Panel

> Evidence snapshot: 2026-08-12. Exact revisions and service availability must be rechecked at experiment time.

## Table of contents

1. [DeepSeek-R1-Distill-Qwen-14B](#deepseek-r1-distill-qwen-14b) — Access: open-weight | Context: 131072 | License: MIT
2. [Gemini-3.6-Flash](#gemini-3-6-flash) — Access: hosted API | Context: 1000000 | License: Proprietary service terms
3. [GPT-5.4-2026-03-05](#gpt-5-4-2026-03-05) — Access: hosted API | Context: 1050000 | License: Proprietary service terms
4. [gpt-oss-20b](#gpt-oss-20b) — Access: open-weight | Context: 131072 | License: Apache-2.0 plus OpenAI usage policy
5. [Mistral-Small-3.1-24B-Instruct-2503](#mistral-small-3-1-24b-instruct-2503) — Access: open-weight | Context: 131072 | License: Apache-2.0
6. [OLMo-2-1124-13B-Instruct](#olmo-2-1124-13b-instruct) — Access: open-weight with open training artifacts | Context: 4096 | License: Apache-2.0
7. [Phi-4-mini-instruct](#phi-4-mini-instruct) — Access: open-weight | Context: 131072 | License: MIT
8. [Qwen-AgentWorld-35B-A3B](#qwen-agentworld-35b-a3b) — Access: open-weight | Context: 262144 | License: Apache-2.0
9. [Qwen3-14B](#qwen3-14b) — Access: open-weight | Context: 32768 | License: Apache-2.0
10. [Qwen3-VL-8B-Instruct](#qwen3-vl-8b-instruct) — Access: open-weight | Context: 262144 | License: Apache-2.0

## DeepSeek-R1-Distill-Qwen-14B

### Basic Info

| Field | Value |
|---|---|
| name | DeepSeek-R1-Distill-Qwen-14B |
| exact_model | deepseek-ai/DeepSeek-R1-Distill-Qwen-14B |
| release | 2025-01 |
| access | open-weight |
| license | MIT |

### Technical Features

| Field | Value |
|---|---|
| modalities | text |
| context_tokens | 131072 |
| serving_path | Transformers or compatible local inference server with exact revision and reasoning-output policy recorded. |

### Experimental Fit

| Field | Value |
|---|---|
| game_research_use | Formalization, structured repair, and reasoning-control comparator. |
| key_risk | Verbose reasoning can inflate latency and does not guarantee executable predicates or truthful rationales. |
| source_urls | https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B, https://github.com/deepseek-ai/DeepSeek-R1 |
| evidence_status | Verified from official DeepSeek model and repository pages as of 2026-08-12. |

### Uncertainty

| Field | Value |
|---|---|
| uncertain |  |


## Gemini-3.6-Flash

### Basic Info

| Field | Value |
|---|---|
| name | Gemini-3.6-Flash |
| exact_model | gemini-3.6-flash |
| release | 2026-07-21 |
| access | hosted API |
| license | Proprietary service terms |

### Technical Features

| Field | Value |
|---|---|
| modalities | image, text, video |
| context_tokens | 1000000 |
| serving_path | Gemini API using the exact documented model ID and retained request/configuration metadata. |

### Experimental Fit

| Field | Value |
|---|---|
| game_research_use | Low-latency hosted multimodal control and gameplay-video observer. |
| key_risk | Very recent API behavior and lifecycle can change; video-derived affect remains a non-authoritative soft signal. |
| source_urls | https://ai.google.dev/gemini-api/docs/latest-model, https://ai.google.dev/gemini-api/docs/models |
| evidence_status | Verified from official Google documentation as of 2026-08-12. |

### Uncertainty

| Field | Value |
|---|---|
| uncertain |  |


## GPT-5.4-2026-03-05

### Basic Info

| Field | Value |
|---|---|
| name | GPT-5.4-2026-03-05 |
| exact_model | gpt-5.4-2026-03-05 |
| release | 2026-03-05 |
| access | hosted API |
| license | Proprietary service terms |

### Technical Features

| Field | Value |
|---|---|
| modalities | image, text |
| context_tokens | 1050000 |
| serving_path | OpenAI API using the dated snapshot, with request IDs and API configuration retained. |

### Experimental Fit

| Field | Value |
|---|---|
| game_research_use | Hosted frontier quality and tool-use control for proposal and repair. |
| key_risk | Cost, service dependence, policy changes, and backend drift require snapshot and request-level audit trails. |
| source_urls | https://developers.openai.com/api/docs/models/gpt-5.4, https://openai.com/index/introducing-gpt-5-4/ |
| evidence_status | Verified from official OpenAI documentation as of 2026-08-12. |

### Uncertainty

| Field | Value |
|---|---|
| uncertain |  |


## gpt-oss-20b

### Basic Info

| Field | Value |
|---|---|
| name | gpt-oss-20b |
| exact_model | openai/gpt-oss-20b |
| release | 2025-08-05 |
| access | open-weight |
| license | Apache-2.0 plus OpenAI usage policy |

### Technical Features

| Field | Value |
|---|---|
| modalities | text |
| context_tokens | 131072 |
| serving_path | Local runtimes including Transformers and compatible servers; preserve Harmony formatting and exact revision. |

### Experimental Fit

| Field | Value |
|---|---|
| game_research_use | Local reasoning, structured proposal, and repair baseline with a documented 16 GB reference profile. |
| key_risk | Text-only observation and model-specific message formatting can confound adapter comparisons. |
| source_urls | https://openai.com/index/introducing-gpt-oss/, https://huggingface.co/openai/gpt-oss-20b |
| evidence_status | Verified from official OpenAI sources as of 2026-08-12. |

### Uncertainty

| Field | Value |
|---|---|
| uncertain |  |


## Mistral-Small-3.1-24B-Instruct-2503

### Basic Info

| Field | Value |
|---|---|
| name | Mistral-Small-3.1-24B-Instruct-2503 |
| exact_model | mistralai/Mistral-Small-3.1-24B-Instruct-2503 |
| release | 2025-03-17 |
| access | open-weight |
| license | Apache-2.0 |

### Technical Features

| Field | Value |
|---|---|
| modalities | image, text |
| context_tokens | 131072 |
| serving_path | Mistral inference, Transformers, vLLM, or compatible local server with an exact weight revision. |

### Experimental Fit

| Field | Value |
|---|---|
| game_research_use | High-capability local proposer, dialogue model, and optional screenshot-audit comparator. |
| key_risk | Memory demand and multimodal preprocessing complicate matched-hardware latency comparisons. |
| source_urls | https://huggingface.co/mistralai/Mistral-Small-3.1-24B-Instruct-2503, https://mistral.ai/news/mistral-small-3-1 |
| evidence_status | Verified from official Mistral sources as of 2026-08-12. |

### Uncertainty

| Field | Value |
|---|---|
| uncertain |  |


## OLMo-2-1124-13B-Instruct

### Basic Info

| Field | Value |
|---|---|
| name | OLMo-2-1124-13B-Instruct |
| exact_model | allenai/OLMo-2-1124-13B-Instruct |
| release | 2024-11 |
| access | open-weight with open training artifacts |
| license | Apache-2.0 |

### Technical Features

| Field | Value |
|---|---|
| modalities | text |
| context_tokens | 4096 |
| serving_path | Transformers-compatible local inference with exact revision and prompt template recorded. |

### Experimental Fit

| Field | Value |
|---|---|
| game_research_use | Reproducibility-oriented proposal baseline for separating controller effects from closed training data. |
| key_risk | Short context and language coverage can disadvantage long-horizon or multilingual scenarios. |
| source_urls | https://huggingface.co/allenai/OLMo-2-1124-13B-Instruct, https://github.com/allenai/OLMo |
| evidence_status | Verified from official AI2 sources as of 2026-08-12. |

### Uncertainty

| Field | Value |
|---|---|
| uncertain |  |


## Phi-4-mini-instruct

### Basic Info

| Field | Value |
|---|---|
| name | Phi-4-mini-instruct |
| exact_model | microsoft/Phi-4-mini-instruct |
| release | 2025-03 |
| access | open-weight |
| license | MIT |

### Technical Features

| Field | Value |
|---|---|
| modalities | text |
| context_tokens | 131072 |
| serving_path | Transformers, ONNX, or compatible local runtimes using an exact model revision. |

### Experimental Fit

| Field | Value |
|---|---|
| game_research_use | Compact edge and latency baseline for proposal and NPC dialogue. |
| key_risk | A small model may underperform on long-horizon formalization; context capacity does not imply reasoning reliability. |
| source_urls | https://huggingface.co/microsoft/Phi-4-mini-instruct |
| evidence_status | Verified from the official Microsoft model card as of 2026-08-12. |

### Uncertainty

| Field | Value |
|---|---|
| uncertain |  |


## Qwen-AgentWorld-35B-A3B

### Basic Info

| Field | Value |
|---|---|
| name | Qwen-AgentWorld-35B-A3B |
| exact_model | Qwen/Qwen-AgentWorld-35B-A3B |
| release | 2026-06-24 |
| access | open-weight |
| license | Apache-2.0 |

### Technical Features

| Field | Value |
|---|---|
| modalities | image, text |
| context_tokens | 262144 |
| serving_path | Transformers-compatible repository path; freeze the exact weight revision in each run. |

### Experimental Fit

| Field | Value |
|---|---|
| game_research_use | Experimental visual-language world-dynamics proposer and synthetic player simulator; never canonical state. |
| key_risk | Very recent and not designed as a transactional game-state engine; capability findings may not transfer to symbolic validity. |
| source_urls | https://github.com/QwenLM/Qwen-AgentWorld |
| evidence_status | Verified from the official repository as of 2026-08-12. |

### Uncertainty

| Field | Value |
|---|---|
| uncertain |  |


## Qwen3-14B

### Basic Info

| Field | Value |
|---|---|
| name | Qwen3-14B |
| exact_model | Qwen/Qwen3-14B |
| release | 2025-04-29 |
| access | open-weight |
| license | Apache-2.0 |

### Technical Features

| Field | Value |
|---|---|
| modalities | text |
| context_tokens | 32768 |
| serving_path | Transformers, vLLM, SGLang, llama.cpp, or compatible local serving with a frozen revision. |

### Experimental Fit

| Field | Value |
|---|---|
| game_research_use | Practical multilingual proposal and dialogue baseline with explicit thinking-mode control. |
| key_risk | Extended context may require YaRN configuration and thinking modes can alter latency and token accounting. |
| source_urls | https://github.com/QwenLM/Qwen3, https://huggingface.co/Qwen/Qwen3-14B |
| evidence_status | Verified from official Qwen sources as of 2026-08-12. |

### Uncertainty

| Field | Value |
|---|---|
| uncertain |  |


## Qwen3-VL-8B-Instruct

### Basic Info

| Field | Value |
|---|---|
| name | Qwen3-VL-8B-Instruct |
| exact_model | Qwen/Qwen3-VL-8B-Instruct |
| access | open-weight |
| license | Apache-2.0 |

### Technical Features

| Field | Value |
|---|---|
| modalities | image, text |
| context_tokens | 262144 |
| serving_path | Transformers, vLLM, SGLang, or compatible multimodal local inference using a frozen revision. |

### Experimental Fit

| Field | Value |
|---|---|
| game_research_use | Compact screenshot and UI observer; visual evidence is reconciled against engine state before use. |
| key_risk | Visual hallucination and game-affect perception gaps make the output unsafe as authoritative state. |
| source_urls | https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct, https://github.com/QwenLM/Qwen3-VL |
| evidence_status | Verified from official Qwen sources as of 2026-08-12. |

### Uncertainty

| Field | Value |
|---|---|
| uncertain | release |

### Uncertain fields

- release
