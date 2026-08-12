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

[allenai](/allenai)  /  [OLMo-2-1124-13B-Instruct](/allenai/OLMo-2-1124-13B-Instruct)  like  48    Follow Ai2 6.42k
===================================================================================================================

[Text Generation](/models?pipeline_tag=text-generation)[Transformers](/models?library=transformers)[Safetensors](/models?library=safetensors)

allenai/RLVR-MATH

[English](/models?language=en)[olmo2](/models?other=olmo2)[conversational](/models?other=conversational)

arxiv: 2501.00656

arxiv: 2411.15124

License: apache-2.0

[Model card](/allenai/OLMo-2-1124-13B-Instruct) [Files Files and versions 

xet](/allenai/OLMo-2-1124-13B-Instruct/tree/main) [Community

1](/allenai/OLMo-2-1124-13B-Instruct/discussions)

Deploy

 Copy to bucket new 

Use this model  

### Instructions to use allenai/OLMo-2-1124-13B-Instruct with libraries, inference providers, notebooks, and local apps. Follow these links to get started.

* Libraries
* [Transformers](/allenai/OLMo-2-1124-13B-Instruct?library=transformers)

  How to use allenai/OLMo-2-1124-13B-Instruct with Transformers:

  ```
  # Use a pipeline as a high-level helper
  from transformers import pipeline

  pipe = pipeline("text-generation", model="allenai/OLMo-2-1124-13B-Instruct")
  messages = [
      {"role": "user", "content": "Who are you?"},
  ]
  pipe(messages)
  ```

  ```
  # Load model directly
  from transformers import AutoTokenizer, AutoModelForCausalLM

  tokenizer = AutoTokenizer.from_pretrained("allenai/OLMo-2-1124-13B-Instruct")
  model = AutoModelForCausalLM.from_pretrained("allenai/OLMo-2-1124-13B-Instruct", device_map="auto")
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
* Notebooks
* [Google Colab](/allenai/OLMo-2-1124-13B-Instruct/colab)
* [Kaggle](/allenai/OLMo-2-1124-13B-Instruct/kaggle)
* Local Apps [Settings](/settings/local-apps "Set up your favorite local applications")
* [vLLM](/allenai/OLMo-2-1124-13B-Instruct?local-app=vllm) 

  How to use allenai/OLMo-2-1124-13B-Instruct with vLLM:

  ##### Install from pip and serve model

  ```
  # Install vLLM from pip:
  pip install vllm
  # Start the vLLM server:
  vllm serve "allenai/OLMo-2-1124-13B-Instruct"
  # Call the server using curl (OpenAI-compatible API):
  curl -X POST "http://localhost:8000/v1/chat/completions" \
  	-H "Content-Type: application/json" \
  	--data '{
  		"model": "allenai/OLMo-2-1124-13B-Instruct",
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
  docker model run hf.co/allenai/OLMo-2-1124-13B-Instruct
  ```
* [SGLang](/allenai/OLMo-2-1124-13B-Instruct?local-app=sglang) 

  How to use allenai/OLMo-2-1124-13B-Instruct with SGLang:

  ##### Install from pip and serve model

  ```
  # Install SGLang from pip:
  pip install sglang
  # Start the SGLang server:
  python3 -m sglang.launch_server \
      --model-path "allenai/OLMo-2-1124-13B-Instruct" \
      --host 0.0.0.0 \
      --port 30000
  # Call the server using curl (OpenAI-compatible API):
  curl -X POST "http://localhost:30000/v1/chat/completions" \
  	-H "Content-Type: application/json" \
  	--data '{
  		"model": "allenai/OLMo-2-1124-13B-Instruct",
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
          --model-path "allenai/OLMo-2-1124-13B-Instruct" \
          --host 0.0.0.0 \
          --port 30000
  # Call the server using curl (OpenAI-compatible API):
  curl -X POST "http://localhost:30000/v1/chat/completions" \
  	-H "Content-Type: application/json" \
  	--data '{
  		"model": "allenai/OLMo-2-1124-13B-Instruct",
  		"messages": [
  			{
  				"role": "user",
  				"content": "What is the capital of France?"
  			}
  		]
  	}'
  ```
* [Docker Model Runner](/allenai/OLMo-2-1124-13B-Instruct?local-app=docker-model-runner) 

  How to use allenai/OLMo-2-1124-13B-Instruct with Docker Model Runner:

  ```
  docker model run hf.co/allenai/OLMo-2-1124-13B-Instruct
  ```
* [Browse
  Quantizations](/models?other=base_model:quantized:allenai/OLMo-2-1124-13B-Instruct) to use this model in  llama.cpp,  Ollama,  LM Studio, or any compatible app.

* [OLMo-2-1124-13B-Instruct](#olmo-2-1124-13b-instruct "OLMo-2-1124-13B-Instruct")
  + [NOTE: 1/3/2025 UPDATE:](#note-132025-update "NOTE: 1/3/2025 UPDATE:")
  + [Release Documentation](#release-documentation "Release Documentation")
  + [Model description](#model-description "Model description")
    - [Model Sources](#model-sources "Model Sources")
  + [Installation](#installation "Installation")
  + [Using the model](#using-the-model "Using the model")
    - [Loading with HuggingFace](#loading-with-huggingface "Loading with HuggingFace")
    - [Chat template](#chat-template "Chat template")
    - [System prompt](#system-prompt "System prompt")
    - [Bias, Risks, and Limitations](#bias-risks-and-limitations "Bias, Risks, and Limitations")
  + [Performance](#performance "Performance")
  + [License and use](#license-and-use "License and use")
  + [Citation](#citation "Citation")

![OLMo Logo](https://huggingface.co/datasets/allenai/blog-images/resolve/main/olmo2/olmo.png)

OLMo-2-1124-13B-Instruct
========================

NOTE: 1/3/2025 UPDATE:
----------------------

Upon the initial release of OLMo-2 models, we realized the post-trained models did not share the pre-tokenization logic that the base models use. As a result, we have trained new post-trained models. The new models are available under the same names as the original models, but we have made the old models available with a postfix "-preview". See [OLMo 2 Preview Post-trained Models](https://huggingface.co/collections/allenai/olmo-2-preview-post-trained-models-6762f662c660962e52de7c96) for the colleciton of the legacy models.

Release Documentation
---------------------

OLMo 2 13B Instruct November 2024 is post-trained variant of the [OLMo-2 13B November 2024](https://huggingface.co/allenai/OLMo2-13B-1124) model, which has undergone supervised finetuning on an OLMo-specific variant of the [Tülu 3 dataset](<https://huggingface.co/datasets/allenai/tulu-3-sft-olmo-2-mixture> and further DPO training on [this dataset](https://huggingface.co/datasets/allenai/olmo-2-1124-13b-preference-mix), and finally RLVR training using [this data](https://huggingface.co/datasets/allenai/RLVR-GSM).
Tülu 3 is designed for state-of-the-art performance on a diversity of tasks in addition to chat, such as MATH, GSM8K, and IFEval.
Check out the [OLMo 2 paper](https://arxiv.org/abs/2501.00656) or [Tülu 3 paper](https://arxiv.org/abs/2411.15124) for more details!

OLMo is a series of **O**pen **L**anguage **Mo**dels designed to enable the science of language models.
These models are trained on the Dolma dataset. We are releasing all code, checkpoints, logs (coming soon), and associated training details.
The core models released in this batch include the following:

| **Stage** | **OLMo 2 7B** | **OLMo 2 13B** |
| --- | --- | --- |
| **Base Model** | [allenai/OLMo2-7B-1124](https://huggingface.co/allenai/OLMo2-7B-1124) | [allenai/OLMo-2-13B-1124](https://huggingface.co/allenai/OLMo-2-13B-1124) |
| **SFT** | [allenai/OLMo-2-1124-7B-SFT](https://huggingface.co/allenai/OLMo-2-1124-7B-SFT) | [allenai/OLMo-2-1124-13B-SFT](https://huggingface.co/allenai/OLMo-2-1124-13B-SFT) |
| **DPO** | [allenai/OLMo-2-1124-7B-DPO](https://huggingface.co/allenai/OLMo-2-1124-7B-DPO) | [allenai/OLMo-2-1124-13B-DPO](https://huggingface.co/allenai/OLMo-2-1124-13B-DPO) |
| **Final Models (RLVR)** | [allenai/OLMo-2-1124-7B-Instruct](https://huggingface.co/allenai/OLMo-2-1124-7B-Instruct) | [allenai/OLMo-2-1124-13B-Instruct](https://huggingface.co/allenai/OLMo-2-1124-13B-Instruct) |
| **Reward Model (RM)** | [allenai/OLMo-2-1124-7B-RM](https://huggingface.co/allenai/OLMo-2-1124-7B-RM) | [allenai/OLMo-2-1124-13B-RM](https://huggingface.co/allenai/OLMo-2-1124-13B-RM) |

Model description
-----------------

* **Model type:** A model trained on a mix of publicly available, synthetic and human-created datasets.
* **Language(s) (NLP):** Primarily English
* **License:** Apache 2.0
* **Finetuned from model:** allenai/OLMo-2-13B-1124-RLVR2

### Model Sources

* **Project Page:** <https://allenai.org/olmo>
* **Repositories:**
  + Core repo (training, inference, fine-tuning etc.): <https://github.com/allenai/OLMo>
  + Evaluation code: <https://github.com/allenai/olmes>
  + Further fine-tuning code: <https://github.com/allenai/open-instruct>
* **Paper:** <https://arxiv.org/abs/2501.00656>
* **Demo:** <https://playground.allenai.org/>

Installation
------------

OLMo 2 will be supported in the next version of Transformers, and you need to install it from the main branch using:

```
pip install --upgrade git+https://github.com/huggingface/transformers.git
```

Using the model
---------------

### Loading with HuggingFace

To load the model with HuggingFace, use the following snippet:

```
from transformers import AutoModelForCausalLM

olmo_model = AutoModelForCausalLM.from_pretrained("allenai/OLMo-2-1124-13B-Instruct")
```

### Chat template

The chat template for our models is formatted as:

```
<|endoftext|><|user|>\nHow are you doing?\n<|assistant|>\nI'm just a computer program, so I don't have feelings, but I'm functioning as expected. How can I assist you today?<|endoftext|>
```

Or with new lines expanded:

```
<|endoftext|><|user|>
How are you doing?
<|assistant|>
I'm just a computer program, so I don't have feelings, but I'm functioning as expected. How can I assist you today?<|endoftext|>
```

It is embedded within the tokenizer as well, for `tokenizer.apply_chat_template`.

### System prompt

In Ai2 demos, we use this system prompt by default:

```
You are OLMo 2, a helpful and harmless AI Assistant built by the Allen Institute for AI.
```

The model has not been trained with a specific system prompt in mind.

### Bias, Risks, and Limitations

The OLMo-2 models have limited safety training, but are not deployed automatically with in-the-loop filtering of responses like ChatGPT, so the model can produce problematic outputs (especially when prompted to do so).
See the Falcon 180B model card for an example of this.

Performance
-----------

| Model | Average | AlpacaEval | BBH | DROP | GSM8k | IFEval | MATH | MMLU | Safety | PopQA | TruthQA |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Open weights models** |  |  |  |  |  |  |  |  |  |  |  |
| Gemma-2-9B-it | 51.9 | 43.7 | 2.5 | 58.8 | 79.7 | 69.9 | 29.8 | 69.1 | 75.5 | 28.3 | 61.4 |
| Ministral-8B-Instruct | 52.1 | 31.4 | 56.2 | 56.2 | 80.0 | 56.4 | 40.0 | 68.5 | 56.2 | 20.2 | 55.5 |
| Mistral-Nemo-Instruct-2407 | 50.9 | 45.8 | 54.6 | 23.6 | 81.4 | 64.5 | 31.9 | 70.0 | 52.7 | 26.9 | 57.7 |
| Qwen-2.5-7B-Instruct | 57.1 | 29.7 | 25.3 | 54.4 | 83.8 | 74.7 | 69.9 | 76.6 | 75.0 | 18.1 | 63.1 |
| Llama-3.1-8B-Instruct | 58.9 | 25.8 | 69.7 | 61.7 | 83.4 | 80.6 | 42.5 | 71.3 | 70.2 | 28.4 | 55.1 |
| Tülu 3 8B | 60.4 | 34.0 | 66.0 | 62.6 | 87.6 | 82.4 | 43.7 | 68.2 | 75.4 | 29.1 | 55.0 |
| Qwen-2.5-14B-Instruct | 60.8 | 34.6 | 34.0 | 50.5 | 83.9 | 82.4 | 70.6 | 81.1 | 79.3 | 21.1 | 70.8 |
| **Fully open models** |  |  |  |  |  |  |  |  |  |  |  |
| OLMo-7B-Instruct | 28.2 | 5.2 | 35.3 | 30.7 | 14.3 | 32.2 | 2.1 | 46.3 | 54.0 | 17.1 | 44.5 |
| OLMo-7B-0424-Instruct | 33.1 | 8.5 | 34.4 | 47.9 | 23.2 | 39.2 | 5.2 | 48.9 | 49.3 | 18.9 | 55.2 |
| OLMoE-1B-7B-0924-Instruct | 35.5 | 8.5 | 37.2 | 34.3 | 47.2 | 46.2 | 8.4 | 51.6 | 51.6 | 20.6 | 49.1 |
| MAP-Neo-7B-Instruct | 42.9 | 17.6 | 26.4 | 48.2 | 69.4 | 35.9 | 31.5 | 56.5 | 73.7 | 18.4 | 51.6 |
| *OLMo-2-7B-SFT* | 50.2 | 10.2 | 49.7 | 59.6 | 74.6 | 66.9 | 25.3 | 61.1 | 82.1 | 23.6 | 48.6 |
| *OLMo-2-7B-DPO* | 54.2 | 27.9 | 46.7 | 60.2 | 82.6 | 73.0 | 30.3 | 60.8 | 81.0 | 23.5 | 56.0 |
| *OLMo-2-13B-SFT* | 55.3 | 11.5 | 59.6 | 71.3 | 76.3 | 68.6 | 29.5 | 68.0 | 82.3 | 29.4 | 57.1 |
| *OLMo-2-13B-DPO* | 60.6 | 38.3 | 57.9 | 71.5 | 82.3 | 80.2 | 35.2 | 67.9 | 79.7 | 29.0 | 63.9 |
| **OLMo-2-7B-1124–Instruct** | 54.8 | 29.1 | 46.6 | 60.5 | 85.1 | 72.3 | 32.5 | 61.3 | 80.6 | 23.2 | 56.5 |
| **OLMo-2-13B-1124-Instruct** | 62.0 | 39.5 | 58.8 | 71.5 | 87.4 | 82.6 | 39.2 | 68.5 | 79.1 | 28.8 | 64.3 |

License and use
---------------

OLMo 2 is licensed under the Apache 2.0 license.
OLMo 2 is intended for research and educational use.
For more information, please see our [Responsible Use Guidelines](https://allenai.org/responsible-use).
This model has been fine-tuned using a dataset mix with outputs generated from third party models and are subject to additional terms: [Gemma Terms of Use](https://ai.google.dev/gemma/terms).

Citation
--------

```
@article{olmo20242olmo2furious,
      title={2 OLMo 2 Furious}, 
      author={Team OLMo and Pete Walsh and Luca Soldaini and Dirk Groeneveld and Kyle Lo and Shane Arora and Akshita Bhagia and Yuling Gu and Shengyi Huang and Matt Jordan and Nathan Lambert and Dustin Schwenk and Oyvind Tafjord and Taira Anderson and David Atkinson and Faeze Brahman and Christopher Clark and Pradeep Dasigi and Nouha Dziri and Michal Guerquin and Hamish Ivison and Pang Wei Koh and Jiacheng Liu and Saumya Malik and William Merrill and Lester James V. Miranda and Jacob Morrison and Tyler Murray and Crystal Nam and Valentina Pyatkin and Aman Rangapur and Michael Schmitz and Sam Skjonsberg and David Wadden and Christopher Wilhelm and Michael Wilson and Luke Zettlemoyer and Ali Farhadi and Noah A. Smith and Hannaneh Hajishirzi},
      year={2024},
      eprint={2501.00656},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2501.00656}, 
}
```

Downloads last month
:   13,585

Safetensors

Model size

14B params

Tensor type

BF16

·

Chat template

Files info

Inference Providers [NEW](https://huggingface.co/docs/inference-providers)

[Text Generation](/tasks/text-generation "Learn more about text-generation")

This model isn't deployed by any Inference Provider. [🙋  Ask for provider support](/spaces/huggingface/InferenceSupport/discussions/new?title=allenai/OLMo-2-1124-13B-Instruct&description=React%20to%20this%20comment%20with%20an%20emoji%20to%20vote%20for%20%5Ballenai%2FOLMo-2-1124-13B-Instruct%5D(%2Fallenai%2FOLMo-2-1124-13B-Instruct)%20to%20be%20supported%20by%20Inference%20Providers.%0A%0A(optional)%20Which%20providers%20are%20you%20interested%20in%3F%20(Novita%2C%20Hyperbolic%2C%20Together%E2%80%A6)%0A)

Model tree for allenai/OLMo-2-1124-13B-Instruct
-----------------------------------------------

Base model

[allenai/OLMo-2-1124-7B](/allenai/OLMo-2-1124-7B)

Finetuned

[allenai/OLMo-2-1124-7B-SFT](/allenai/OLMo-2-1124-7B-SFT)

Finetuned

[allenai/OLMo-2-1124-7B-DPO](/allenai/OLMo-2-1124-7B-DPO)

Finetuned

[allenai/OLMo-2-1124-13B-Instruct-RLVR1](/allenai/OLMo-2-1124-13B-Instruct-RLVR1)

Finetuned

[allenai/OLMo-2-1124-13B-Instruct-RLVR2](/allenai/OLMo-2-1124-13B-Instruct-RLVR2)

Finetuned

([1](/models?other=base_model:finetune:allenai/OLMo-2-1124-13B-Instruct-RLVR2))

this model

Adapters

[5 models](/models?other=base_model:adapter:allenai/OLMo-2-1124-13B-Instruct)

Finetunes

[37 models](/models?other=base_model:finetune:allenai/OLMo-2-1124-13B-Instruct)

Quantizations

[30 models](/models?other=base_model:quantized:allenai/OLMo-2-1124-13B-Instruct)

Dataset used to train allenai/OLMo-2-1124-13B-Instruct
------------------------------------------------------

[#### allenai/RLVR-MATH

Viewer • Updated Nov 20, 2024 • 7.5k • 136 • 19](/datasets/allenai/RLVR-MATH)

Spaces using allenai/OLMo-2-1124-13B-Instruct 19
------------------------------------------------

[💻

FallnAI/Quantize-HF-Models](/spaces/FallnAI/Quantize-HF-Models)[🏃

openfree/LLM\_Quantization](/spaces/openfree/LLM_Quantization)[📊

EuroEval/euroeval\_leaderboard](/spaces/EuroEval/euroeval_leaderboard)[🏃

seawolf2357/LLM\_Quantization](/spaces/seawolf2357/LLM_Quantization)[💻

Oss11/Quantize-HF-Models](/spaces/Oss11/Quantize-HF-Models)[🏃

GTO83/LLM\_Quantization](/spaces/GTO83/LLM_Quantization)[🎭

hplisiecki/pinocchio-inventory-explorer](/spaces/hplisiecki/pinocchio-inventory-explorer)[💻

KBaba7/Quant](/spaces/KBaba7/Quant) + 14 Spaces + 11 Spaces

Collection including allenai/OLMo-2-1124-13B-Instruct
-----------------------------------------------------

[#### OLMo 2

Collection

Artifacts for the OLMo 2 release. • 35 items • Updated Mar 3 • 157](/collections/allenai/olmo-2)

Papers for allenai/OLMo-2-1124-13B-Instruct
-------------------------------------------

[#### 2 OLMo 2 Furious

Paper • 2501.00656 • Published Dec 31, 2024 • 22](/papers/2501.00656)

[#### TÜLU 3: Pushing Frontiers in Open Language Model Post-Training

Paper • 2411.15124 • Published Nov 22, 2024 • 68](/papers/2411.15124)

System theme

Company

[TOS](/terms-of-service) [Privacy](/privacy) [About](/huggingface) [Careers](https://apply.workable.com/huggingface/) 

Website

[Models](/models) [Datasets](/datasets) [Spaces](/spaces) [Pricing](/pricing) [Docs](/docs)