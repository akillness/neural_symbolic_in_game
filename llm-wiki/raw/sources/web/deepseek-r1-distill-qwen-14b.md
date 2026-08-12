[![Hugging Face's logo](/front/assets/huggingface_logo-noborder.svg)Hugging Face](/)

* [Models](/models)
* [Datasets](/datasets)
* [Spaces](/spaces)
* [Buckets new](/storage)
* [Docs](/docs)
* [Enterprise](/enterprise)
* [Pricing](/pricing)
* + Website

    - [Tasks](/tasks)
    - [HuggingChat](/chat)
    - [Collections](/collections)
    - [Languages](/languages)
    - [Organizations](/organizations)
  + Community

    - [Blog](/blog)
    - [Posts](/posts)
    - [Daily Papers](/papers)
    - [Hardware](/hardware)
    - [Learn](/learn)
    - [Discord](/join/discord)
    - [Forum](https://discuss.huggingface.co/)
    - [GitHub](https://github.com/huggingface)
  + Solutions

    - [Team & Enterprise](/enterprise)
    - [Hugging Face PRO](/pro)
    - [Enterprise Support](/support)
    - [Inference Providers](/inference/models)
    - [Inference Endpoints](/inference-endpoints)
    - [Storage Buckets](/storage)
* ---
* [Log In](/login)
* [Sign Up](/join)

[deepseek-ai](/deepseek-ai)  /  [DeepSeek-R1-Distill-Qwen-14B](/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B)  like  668    Follow DeepSeek 141k
============================================================================================================================================

[Text Generation](/models?pipeline_tag=text-generation)[Transformers](/models?library=transformers)[Safetensors](/models?library=safetensors)[qwen2](/models?other=qwen2)[conversational](/models?other=conversational)[text-generation-inference](/models?other=text-generation-inference)

arxiv: 2501.12948

License: mit

[Model card](/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B) [Files Files and versions 

xet](/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B/tree/main) [Community

28](/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B/discussions)

Deploy

 Copy to bucket new 

Use this model  

### Instructions to use deepseek-ai/DeepSeek-R1-Distill-Qwen-14B with libraries, inference providers, notebooks, and local apps. Follow these links to get started.

* Libraries
* [Transformers](/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B?library=transformers)

  How to use deepseek-ai/DeepSeek-R1-Distill-Qwen-14B with Transformers:

  ```
  # Use a pipeline as a high-level helper
  from transformers import pipeline

  pipe = pipeline("text-generation", model="deepseek-ai/DeepSeek-R1-Distill-Qwen-14B")
  messages = [
      {"role": "user", "content": "Who are you?"},
  ]
  pipe(messages)
  ```

  ```
  # Load model directly
  from transformers import AutoTokenizer, AutoModelForCausalLM

  tokenizer = AutoTokenizer.from_pretrained("deepseek-ai/DeepSeek-R1-Distill-Qwen-14B")
  model = AutoModelForCausalLM.from_pretrained("deepseek-ai/DeepSeek-R1-Distill-Qwen-14B", device_map="auto")
  messages = [
      {"role": "user", "content": "Who are you?"},
  ]
  inputs = tokenizer.apply_chat_template(
  	messages,
  	add_generation_prompt=True,
  	tokenize=True,
  	return_dict=True,
  	return_tensors="pt",
  ).to(model.device)

  outputs = model.generate(**inputs, max_new_tokens=40)
  print(tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:]))
  ```
* Inference
* Inference Providers
* [HuggingChat](/chat/models/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B)
* Notebooks
* [Google Colab](/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B/colab)
* [Kaggle](/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B/kaggle)
* Local Apps [Settings](/settings/local-apps "Set up your favorite local applications")
* [vLLM](/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B?local-app=vllm) 

  How to use deepseek-ai/DeepSeek-R1-Distill-Qwen-14B with vLLM:

  ##### Install from pip and serve model

  ```
  # Install vLLM from pip:
  pip install vllm
  # Start the vLLM server:
  vllm serve "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B"
  # Call the server using curl (OpenAI-compatible API):
  curl -X POST "http://localhost:8000/v1/chat/completions" \
  	-H "Content-Type: application/json" \
  	--data '{
  		"model": "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
  		"messages": [
  			{
  				"role": "user",
  				"content": "What is the capital of France?"
  			}
  		]
  	}'
  ```

  ##### Use Docker

  ```
  docker model run hf.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B
  ```
* [SGLang](/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B?local-app=sglang) 

  How to use deepseek-ai/DeepSeek-R1-Distill-Qwen-14B with SGLang:

  ##### Install from pip and serve model

  ```
  # Install SGLang from pip:
  pip install sglang
  # Start the SGLang server:
  python3 -m sglang.launch_server \
      --model-path "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B" \
      --host 0.0.0.0 \
      --port 30000
  # Call the server using curl (OpenAI-compatible API):
  curl -X POST "http://localhost:30000/v1/chat/completions" \
  	-H "Content-Type: application/json" \
  	--data '{
  		"model": "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
  		"messages": [
  			{
  				"role": "user",
  				"content": "What is the capital of France?"
  			}
  		]
  	}'
  ```

  ##### Use Docker images

  ```
  docker run --gpus all \
      --shm-size 32g \
      -p 30000:30000 \
      -v ~/.cache/huggingface:/root/.cache/huggingface \
      --env "HF_TOKEN=<secret>" \
      --ipc=host \
      lmsysorg/sglang:latest \
      python3 -m sglang.launch_server \
          --model-path "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B" \
          --host 0.0.0.0 \
          --port 30000
  # Call the server using curl (OpenAI-compatible API):
  curl -X POST "http://localhost:30000/v1/chat/completions" \
  	-H "Content-Type: application/json" \
  	--data '{
  		"model": "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
  		"messages": [
  			{
  				"role": "user",
  				"content": "What is the capital of France?"
  			}
  		]
  	}'
  ```
* [Docker Model Runner](/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B?local-app=docker-model-runner) 

  How to use deepseek-ai/DeepSeek-R1-Distill-Qwen-14B with Docker Model Runner:

  ```
  docker model run hf.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B
  ```
* [Browse
  Quantizations](/models?other=base_model:quantized:deepseek-ai/DeepSeek-R1-Distill-Qwen-14B) to use this model in  llama.cpp,  Ollama,  LM Studio, or any compatible app.

* [DeepSeek-R1](#deepseek-r1 "DeepSeek-R1")
  + [1. Introduction](#1-introduction "1. Introduction")
  + [2. Model Summary](#2-model-summary "2. Model Summary")
  + [3. Model Downloads](#3-model-downloads "3. Model Downloads")
    - [DeepSeek-R1 Models](#deepseek-r1-models "DeepSeek-R1 Models")
    - [DeepSeek-R1-Distill Models](#deepseek-r1-distill-models "DeepSeek-R1-Distill Models")
  + [4. Evaluation Results](#4-evaluation-results "4. Evaluation Results")
    - [DeepSeek-R1-Evaluation](#deepseek-r1-evaluation "DeepSeek-R1-Evaluation")
    - [Distilled Model Evaluation](#distilled-model-evaluation "Distilled Model Evaluation")
  + [5. Chat Website & API Platform](#5-chat-website--api-platform "5. Chat Website &amp; API Platform")
  + [6. How to Run Locally](#6-how-to-run-locally "6. How to Run Locally")
    - [DeepSeek-R1 Models](#deepseek-r1-models-1 "DeepSeek-R1 Models")
    - [DeepSeek-R1-Distill Models](#deepseek-r1-distill-models-1 "DeepSeek-R1-Distill Models")
    - [Usage Recommendations](#usage-recommendations "Usage Recommendations")
  + [7. License](#7-license "7. License")
  + [8. Citation](#8-citation "8. Citation")
  + [9. Contact](#9-contact "9. Contact")

DeepSeek-R1
===========

![DeepSeek-V3](https://github.com/deepseek-ai/DeepSeek-V2/blob/main/figures/logo.svg?raw=true)

---

[![Homepage](https://github.com/deepseek-ai/DeepSeek-V2/blob/main/figures/badge.svg?raw=true)](https://www.deepseek.com/)
[![Chat](https://img.shields.io/badge/%F0%9F%A4%96%20Chat-DeepSeek%20R1-536af5?color=536af5&logoColor=white)](https://chat.deepseek.com/)
[![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-DeepSeek%20AI-ffc107?color=ffc107&logoColor=white)](https://huggingface.co/deepseek-ai)

[![Discord](https://img.shields.io/badge/Discord-DeepSeek%20AI-7289da?logo=discord&logoColor=white&color=7289da)](https://discord.gg/Tc7c45Zzu5)
[![Wechat](https://img.shields.io/badge/WeChat-DeepSeek%20AI-brightgreen?logo=wechat&logoColor=white)](https://github.com/deepseek-ai/DeepSeek-V2/blob/main/figures/qr.jpeg?raw=true)
[![Twitter Follow](https://img.shields.io/badge/Twitter-deepseek_ai-white?logo=x&logoColor=white)](https://twitter.com/deepseek_ai)

[![License](https://img.shields.io/badge/License-MIT-f5de53?&color=f5de53)](https://github.com/deepseek-ai/DeepSeek-R1/blob/main/LICENSE)

[**Paper Link**👁️](https://github.com/deepseek-ai/DeepSeek-R1/blob/main/DeepSeek_R1.pdf)

1. Introduction
---------------

We introduce our first-generation reasoning models, DeepSeek-R1-Zero and DeepSeek-R1.
DeepSeek-R1-Zero, a model trained via large-scale reinforcement learning (RL) without supervised fine-tuning (SFT) as a preliminary step, demonstrated remarkable performance on reasoning.
With RL, DeepSeek-R1-Zero naturally emerged with numerous powerful and interesting reasoning behaviors.
However, DeepSeek-R1-Zero encounters challenges such as endless repetition, poor readability, and language mixing. To address these issues and further enhance reasoning performance,
we introduce DeepSeek-R1, which incorporates cold-start data before RL.
DeepSeek-R1 achieves performance comparable to OpenAI-o1 across math, code, and reasoning tasks.
To support the research community, we have open-sourced DeepSeek-R1-Zero, DeepSeek-R1, and six dense models distilled from DeepSeek-R1 based on Llama and Qwen. DeepSeek-R1-Distill-Qwen-32B outperforms OpenAI-o1-mini across various benchmarks, achieving new state-of-the-art results for dense models.

**NOTE: Before running DeepSeek-R1 series models locally, we kindly recommend reviewing the [Usage Recommendation](#usage-recommendations) section.**

![](/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B/resolve/main/figures/benchmark.jpg)

2. Model Summary
----------------

---

**Post-Training: Large-Scale Reinforcement Learning on the Base Model**

* We directly apply reinforcement learning (RL) to the base model without relying on supervised fine-tuning (SFT) as a preliminary step. This approach allows the model to explore chain-of-thought (CoT) for solving complex problems, resulting in the development of DeepSeek-R1-Zero. DeepSeek-R1-Zero demonstrates capabilities such as self-verification, reflection, and generating long CoTs, marking a significant milestone for the research community. Notably, it is the first open research to validate that reasoning capabilities of LLMs can be incentivized purely through RL, without the need for SFT. This breakthrough paves the way for future advancements in this area.
* We introduce our pipeline to develop DeepSeek-R1. The pipeline incorporates two RL stages aimed at discovering improved reasoning patterns and aligning with human preferences, as well as two SFT stages that serve as the seed for the model's reasoning and non-reasoning capabilities.
  We believe the pipeline will benefit the industry by creating better models.

---

**Distillation: Smaller Models Can Be Powerful Too**

* We demonstrate that the reasoning patterns of larger models can be distilled into smaller models, resulting in better performance compared to the reasoning patterns discovered through RL on small models. The open source DeepSeek-R1, as well as its API, will benefit the research community to distill better smaller models in the future.
* Using the reasoning data generated by DeepSeek-R1, we fine-tuned several dense models that are widely used in the research community. The evaluation results demonstrate that the distilled smaller dense models perform exceptionally well on benchmarks. We open-source distilled 1.5B, 7B, 8B, 14B, 32B, and 70B checkpoints based on Qwen2.5 and Llama3 series to the community.

3. Model Downloads
------------------

### DeepSeek-R1 Models

| **Model** | **#Total Params** | **#Activated Params** | **Context Length** | **Download** |
| --- | --- | --- | --- | --- |
| DeepSeek-R1-Zero | 671B | 37B | 128K | [🤗 HuggingFace](https://huggingface.co/deepseek-ai/DeepSeek-R1-Zero) |
| DeepSeek-R1 | 671B | 37B | 128K | [🤗 HuggingFace](https://huggingface.co/deepseek-ai/DeepSeek-R1) |

DeepSeek-R1-Zero & DeepSeek-R1 are trained based on DeepSeek-V3-Base.
For more details regarding the model architecture, please refer to [DeepSeek-V3](https://github.com/deepseek-ai/DeepSeek-V3) repository.

### DeepSeek-R1-Distill Models

| **Model** | **Base Model** | **Download** |
| --- | --- | --- |
| DeepSeek-R1-Distill-Qwen-1.5B | [Qwen2.5-Math-1.5B](https://huggingface.co/Qwen/Qwen2.5-Math-1.5B) | [🤗 HuggingFace](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B) |
| DeepSeek-R1-Distill-Qwen-7B | [Qwen2.5-Math-7B](https://huggingface.co/Qwen/Qwen2.5-Math-7B) | [🤗 HuggingFace](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B) |
| DeepSeek-R1-Distill-Llama-8B | [Llama-3.1-8B](https://huggingface.co/meta-llama/Llama-3.1-8B) | [🤗 HuggingFace](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Llama-8B) |
| DeepSeek-R1-Distill-Qwen-14B | [Qwen2.5-14B](https://huggingface.co/Qwen/Qwen2.5-14B) | [🤗 HuggingFace](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B) |
| DeepSeek-R1-Distill-Qwen-32B | [Qwen2.5-32B](https://huggingface.co/Qwen/Qwen2.5-32B) | [🤗 HuggingFace](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B) |
| DeepSeek-R1-Distill-Llama-70B | [Llama-3.3-70B-Instruct](https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct) | [🤗 HuggingFace](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Llama-70B) |

DeepSeek-R1-Distill models are fine-tuned based on open-source models, using samples generated by DeepSeek-R1.
We slightly change their configs and tokenizers. Please use our setting to run these models.

4. Evaluation Results
---------------------

### DeepSeek-R1-Evaluation

For all our models, the maximum generation length is set to 32,768 tokens. For benchmarks requiring sampling, we use a temperature of $0.6$, a top-p value of $0.95$, and generate 64 responses per query to estimate pass@1.

| Category | Benchmark (Metric) | Claude-3.5-Sonnet-1022 | GPT-4o 0513 | DeepSeek V3 | OpenAI o1-mini | OpenAI o1-1217 | DeepSeek R1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
|  | Architecture | - | - | MoE | - | - | MoE |
|  | # Activated Params | - | - | 37B | - | - | 37B |
|  | # Total Params | - | - | 671B | - | - | 671B |
| English | MMLU (Pass@1) | 88.3 | 87.2 | 88.5 | 85.2 | **91.8** | 90.8 |
|  | MMLU-Redux (EM) | 88.9 | 88.0 | 89.1 | 86.7 | - | **92.9** |
|  | MMLU-Pro (EM) | 78.0 | 72.6 | 75.9 | 80.3 | - | **84.0** |
|  | DROP (3-shot F1) | 88.3 | 83.7 | 91.6 | 83.9 | 90.2 | **92.2** |
|  | IF-Eval (Prompt Strict) | **86.5** | 84.3 | 86.1 | 84.8 | - | 83.3 |
|  | GPQA-Diamond (Pass@1) | 65.0 | 49.9 | 59.1 | 60.0 | **75.7** | 71.5 |
|  | SimpleQA (Correct) | 28.4 | 38.2 | 24.9 | 7.0 | **47.0** | 30.1 |
|  | FRAMES (Acc.) | 72.5 | 80.5 | 73.3 | 76.9 | - | **82.5** |
|  | AlpacaEval2.0 (LC-winrate) | 52.0 | 51.1 | 70.0 | 57.8 | - | **87.6** |
|  | ArenaHard (GPT-4-1106) | 85.2 | 80.4 | 85.5 | 92.0 | - | **92.3** |
| Code | LiveCodeBench (Pass@1-COT) | 33.8 | 34.2 | - | 53.8 | 63.4 | **65.9** |
|  | Codeforces (Percentile) | 20.3 | 23.6 | 58.7 | 93.4 | **96.6** | 96.3 |
|  | Codeforces (Rating) | 717 | 759 | 1134 | 1820 | **2061** | 2029 |
|  | SWE Verified (Resolved) | **50.8** | 38.8 | 42.0 | 41.6 | 48.9 | 49.2 |
|  | Aider-Polyglot (Acc.) | 45.3 | 16.0 | 49.6 | 32.9 | **61.7** | 53.3 |
| Math | AIME 2024 (Pass@1) | 16.0 | 9.3 | 39.2 | 63.6 | 79.2 | **79.8** |
|  | MATH-500 (Pass@1) | 78.3 | 74.6 | 90.2 | 90.0 | 96.4 | **97.3** |
|  | CNMO 2024 (Pass@1) | 13.1 | 10.8 | 43.2 | 67.6 | - | **78.8** |
| Chinese | CLUEWSC (EM) | 85.4 | 87.9 | 90.9 | 89.9 | - | **92.8** |
|  | C-Eval (EM) | 76.7 | 76.0 | 86.5 | 68.9 | - | **91.8** |
|  | C-SimpleQA (Correct) | 55.4 | 58.7 | **68.0** | 40.3 | - | 63.7 |

### Distilled Model Evaluation

| Model | AIME 2024 pass@1 | AIME 2024 cons@64 | MATH-500 pass@1 | GPQA Diamond pass@1 | LiveCodeBench pass@1 | CodeForces rating |
| --- | --- | --- | --- | --- | --- | --- |
| GPT-4o-0513 | 9.3 | 13.4 | 74.6 | 49.9 | 32.9 | 759 |
| Claude-3.5-Sonnet-1022 | 16.0 | 26.7 | 78.3 | 65.0 | 38.9 | 717 |
| o1-mini | 63.6 | 80.0 | 90.0 | 60.0 | 53.8 | **1820** |
| QwQ-32B-Preview | 44.0 | 60.0 | 90.6 | 54.5 | 41.9 | 1316 |
| DeepSeek-R1-Distill-Qwen-1.5B | 28.9 | 52.7 | 83.9 | 33.8 | 16.9 | 954 |
| DeepSeek-R1-Distill-Qwen-7B | 55.5 | 83.3 | 92.8 | 49.1 | 37.6 | 1189 |
| DeepSeek-R1-Distill-Qwen-14B | 69.7 | 80.0 | 93.9 | 59.1 | 53.1 | 1481 |
| DeepSeek-R1-Distill-Qwen-32B | **72.6** | 83.3 | 94.3 | 62.1 | 57.2 | 1691 |
| DeepSeek-R1-Distill-Llama-8B | 50.4 | 80.0 | 89.1 | 49.0 | 39.6 | 1205 |
| DeepSeek-R1-Distill-Llama-70B | 70.0 | **86.7** | **94.5** | **65.2** | **57.5** | 1633 |

5. Chat Website & API Platform
------------------------------

You can chat with DeepSeek-R1 on DeepSeek's official website: [chat.deepseek.com](https://chat.deepseek.com), and switch on the button "DeepThink"

We also provide OpenAI-Compatible API at DeepSeek Platform: [platform.deepseek.com](https://platform.deepseek.com/)

6. How to Run Locally
---------------------

### DeepSeek-R1 Models

Please visit [DeepSeek-V3](https://github.com/deepseek-ai/DeepSeek-V3) repo for more information about running DeepSeek-R1 locally.

**NOTE: Hugging Face's Transformers has not been directly supported yet.**

### DeepSeek-R1-Distill Models

DeepSeek-R1-Distill models can be utilized in the same manner as Qwen or Llama models.

For instance, you can easily start a service using [vLLM](https://github.com/vllm-project/vllm):

```
vllm serve deepseek-ai/DeepSeek-R1-Distill-Qwen-32B --tensor-parallel-size 2 --max-model-len 32768 --enforce-eager
```

You can also easily start a service using [SGLang](https://github.com/sgl-project/sglang)

```
python3 -m sglang.launch_server --model deepseek-ai/DeepSeek-R1-Distill-Qwen-32B --trust-remote-code --tp 2
```

### Usage Recommendations

**We recommend adhering to the following configurations when utilizing the DeepSeek-R1 series models, including benchmarking, to achieve the expected performance:**

1. Set the temperature within the range of 0.5-0.7 (0.6 is recommended) to prevent endless repetitions or incoherent outputs.
2. **Avoid adding a system prompt; all instructions should be contained within the user prompt.**
3. For mathematical problems, it is advisable to include a directive in your prompt such as: "Please reason step by step, and put your final answer within \boxed{}."
4. When evaluating model performance, it is recommended to conduct multiple tests and average the results.

Additionally, we have observed that the DeepSeek-R1 series models tend to bypass thinking pattern (i.e., outputting "<think>\n\n</think>") when responding to certain queries, which can adversely affect the model's performance.
**To ensure that the model engages in thorough reasoning, we recommend enforcing the model to initiate its response with "<think>\n" at the beginning of every output.**

7. License
----------

This code repository and the model weights are licensed under the [MIT License](https://github.com/deepseek-ai/DeepSeek-R1/blob/main/LICENSE).
DeepSeek-R1 series support commercial use, allow for any modifications and derivative works, including, but not limited to, distillation for training other LLMs. Please note that:

* DeepSeek-R1-Distill-Qwen-1.5B, DeepSeek-R1-Distill-Qwen-7B, DeepSeek-R1-Distill-Qwen-14B and DeepSeek-R1-Distill-Qwen-32B are derived from [Qwen-2.5 series](https://github.com/QwenLM/Qwen2.5), which are originally licensed under [Apache 2.0 License](https://huggingface.co/Qwen/Qwen2.5-1.5B/blob/main/LICENSE), and now finetuned with 800k samples curated with DeepSeek-R1.
* DeepSeek-R1-Distill-Llama-8B is derived from Llama3.1-8B-Base and is originally licensed under [llama3.1 license](https://huggingface.co/meta-llama/Llama-3.1-8B/blob/main/LICENSE).
* DeepSeek-R1-Distill-Llama-70B is derived from Llama3.3-70B-Instruct and is originally licensed under [llama3.3 license](https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct/blob/main/LICENSE).

8. Citation
-----------

```
@misc{deepseekai2025deepseekr1incentivizingreasoningcapability,
      title={DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning}, 
      author={DeepSeek-AI},
      year={2025},
      eprint={2501.12948},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2501.12948}, 
}
```

9. Contact
----------

If you have any questions, please raise an issue or contact us at [service@deepseek.com](/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B/blob/main/service@deepseek.com).

Downloads last month
:   807,517

Safetensors

Model size

15B params

Tensor type

BF16

·

Chat template

Files info

Inference Providers [NEW](https://huggingface.co/docs/inference-providers)

Nscale

[Text Generation](/tasks/text-generation "Learn more about text-generation")

Examples

Input a message to start chatting with **deepseek-ai/DeepSeek-R1-Distill-Qwen-14B**.

Send

View Code Snippets

[Compare providers](/inference/models?model=deepseek-ai%2FDeepSeek-R1-Distill-Qwen-14B)

Model tree for deepseek-ai/DeepSeek-R1-Distill-Qwen-14B
-------------------------------------------------------

Adapters

[114 models](/models?other=base_model:adapter:deepseek-ai/DeepSeek-R1-Distill-Qwen-14B)

Finetunes

[86 models](/models?other=base_model:finetune:deepseek-ai/DeepSeek-R1-Distill-Qwen-14B)

Merges

[56 models](/models?other=base_model:merge:deepseek-ai/DeepSeek-R1-Distill-Qwen-14B)

Quantizations

[141 models](/models?other=base_model:quantized:deepseek-ai/DeepSeek-R1-Distill-Qwen-14B)

Spaces using deepseek-ai/DeepSeek-R1-Distill-Qwen-14B 100
---------------------------------------------------------

[💥

pliny-the-prompter/obliteratus](/spaces/pliny-the-prompter/obliteratus)[🐢

HPAI-BSC/TuRTLe-Leaderboard](/spaces/HPAI-BSC/TuRTLe-Leaderboard)[💥

dumbordumber/obliteratus](/spaces/dumbordumber/obliteratus)[💥

RavichandranJ/obliteratus](/spaces/RavichandranJ/obliteratus)[💥

marchkamal51/obliteratus](/spaces/marchkamal51/obliteratus)[🏆

eduagarcia/open\_pt\_llm\_leaderboard](/spaces/eduagarcia/open_pt_llm_leaderboard)[🥇

logikon/open\_cot\_leaderboard](/spaces/logikon/open_cot_leaderboard)[📈

ginigen-ai/smol-worldcup](/spaces/ginigen-ai/smol-worldcup) + 95 Spaces + 92 Spaces

Collection including deepseek-ai/DeepSeek-R1-Distill-Qwen-14B
-------------------------------------------------------------

[#### DeepSeek-R1

Collection

10 items • Updated Nov 27, 2025 • 862](/collections/deepseek-ai/deepseek-r1)

Paper for deepseek-ai/DeepSeek-R1-Distill-Qwen-14B
--------------------------------------------------

[#### DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning

Paper • 2501.12948 • Published Jan 22, 2025 • 462](/papers/2501.12948)

System theme

Company

[TOS](/terms-of-service) [Privacy](/privacy) [About](/huggingface) [Careers](https://apply.workable.com/huggingface/) 

Website

[Models](/models) [Datasets](/datasets) [Spaces](/spaces) [Pricing](/pricing) [Docs](/docs)