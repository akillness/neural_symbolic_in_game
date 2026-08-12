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

[Qwen](/Qwen)  /  [Qwen3-VL-8B-Instruct](/Qwen/Qwen3-VL-8B-Instruct)  like  1.04k    Follow Qwen 95.9k
======================================================================================================

[Image-Text-to-Text](/models?pipeline_tag=image-text-to-text)[Transformers](/models?library=transformers)[Safetensors](/models?library=safetensors)[qwen3\_vl](/models?other=qwen3_vl)[conversational](/models?other=conversational)[Eval Results](/models?other=eval-results)

arxiv: 4 papers

License: apache-2.0

[Model card](/Qwen/Qwen3-VL-8B-Instruct) [Files Files and versions 

xet](/Qwen/Qwen3-VL-8B-Instruct/tree/main) [Community

32](/Qwen/Qwen3-VL-8B-Instruct/discussions)

Deploy

 Copy to bucket new 

Use this model  

### Instructions to use Qwen/Qwen3-VL-8B-Instruct with libraries, inference providers, notebooks, and local apps. Follow these links to get started.

* Libraries
* [Transformers](/Qwen/Qwen3-VL-8B-Instruct?library=transformers)

  How to use Qwen/Qwen3-VL-8B-Instruct with Transformers:

  ```
  # Use a pipeline as a high-level helper
  from transformers import pipeline

  pipe = pipeline("image-text-to-text", model="Qwen/Qwen3-VL-8B-Instruct")
  messages = [
      {
          "role": "user",
          "content": [
              {"type": "image", "url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/p-blog/candy.JPG"},
              {"type": "text", "text": "What animal is on the candy?"}
          ]
      },
  ]
  pipe(text=messages)
  ```

  ```
  # Load model directly
  from transformers import AutoProcessor, AutoModelForMultimodalLM

  processor = AutoProcessor.from_pretrained("Qwen/Qwen3-VL-8B-Instruct")
  model = AutoModelForMultimodalLM.from_pretrained("Qwen/Qwen3-VL-8B-Instruct", device_map="auto")
  messages = [
      {
          "role": "user",
          "content": [
              {"type": "image", "url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/p-blog/candy.JPG"},
              {"type": "text", "text": "What animal is on the candy?"}
          ]
      },
  ]
  inputs = processor.apply_chat_template(
  	messages,
  	add_generation_prompt=True,
  	tokenize=True,
  	return_dict=True,
  	return_tensors="pt",
  ).to(model.device)

  outputs = model.generate(**inputs, max_new_tokens=40)
  print(processor.decode(outputs[0][inputs["input_ids"].shape[-1]:]))
  ```
* Inference
* Inference Providers
* Notebooks
* [Google Colab](/Qwen/Qwen3-VL-8B-Instruct/colab)
* [Kaggle](/Qwen/Qwen3-VL-8B-Instruct/kaggle)
* [AMD Developer Cloud](/Qwen/Qwen3-VL-8B-Instruct/amd)
* Local Apps [Settings](/settings/local-apps "Set up your favorite local applications")
* [vLLM](/Qwen/Qwen3-VL-8B-Instruct?local-app=vllm) 

  How to use Qwen/Qwen3-VL-8B-Instruct with vLLM:

  ##### Install from pip and serve model

  ```
  # Install vLLM from pip:
  pip install vllm
  # Start the vLLM server:
  vllm serve "Qwen/Qwen3-VL-8B-Instruct"
  # Call the server using curl (OpenAI-compatible API):
  curl -X POST "http://localhost:8000/v1/chat/completions" \
  	-H "Content-Type: application/json" \
  	--data '{
  		"model": "Qwen/Qwen3-VL-8B-Instruct",
  		"messages": [
  			{
  				"role": "user",
  				"content": [
  					{
  						"type": "text",
  						"text": "Describe this image in one sentence."
  					},
  					{
  						"type": "image_url",
  						"image_url": {
  							"url": "https://cdn.britannica.com/61/93061-050-99147DCE/Statue-of-Liberty-Island-New-York-Bay.jpg"
  						}
  					}
  				]
  			}
  		]
  	}'
  ```

  ##### Use Docker

  ```
  docker model run hf.co/Qwen/Qwen3-VL-8B-Instruct
  ```
* [SGLang](/Qwen/Qwen3-VL-8B-Instruct?local-app=sglang) 

  How to use Qwen/Qwen3-VL-8B-Instruct with SGLang:

  ##### Install from pip and serve model

  ```
  # Install SGLang from pip:
  pip install sglang
  # Start the SGLang server:
  python3 -m sglang.launch_server \
      --model-path "Qwen/Qwen3-VL-8B-Instruct" \
      --host 0.0.0.0 \
      --port 30000
  # Call the server using curl (OpenAI-compatible API):
  curl -X POST "http://localhost:30000/v1/chat/completions" \
  	-H "Content-Type: application/json" \
  	--data '{
  		"model": "Qwen/Qwen3-VL-8B-Instruct",
  		"messages": [
  			{
  				"role": "user",
  				"content": [
  					{
  						"type": "text",
  						"text": "Describe this image in one sentence."
  					},
  					{
  						"type": "image_url",
  						"image_url": {
  							"url": "https://cdn.britannica.com/61/93061-050-99147DCE/Statue-of-Liberty-Island-New-York-Bay.jpg"
  						}
  					}
  				]
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
          --model-path "Qwen/Qwen3-VL-8B-Instruct" \
          --host 0.0.0.0 \
          --port 30000
  # Call the server using curl (OpenAI-compatible API):
  curl -X POST "http://localhost:30000/v1/chat/completions" \
  	-H "Content-Type: application/json" \
  	--data '{
  		"model": "Qwen/Qwen3-VL-8B-Instruct",
  		"messages": [
  			{
  				"role": "user",
  				"content": [
  					{
  						"type": "text",
  						"text": "Describe this image in one sentence."
  					},
  					{
  						"type": "image_url",
  						"image_url": {
  							"url": "https://cdn.britannica.com/61/93061-050-99147DCE/Statue-of-Liberty-Island-New-York-Bay.jpg"
  						}
  					}
  				]
  			}
  		]
  	}'
  ```
* [Docker Model Runner](/Qwen/Qwen3-VL-8B-Instruct?local-app=docker-model-runner) 

  How to use Qwen/Qwen3-VL-8B-Instruct with Docker Model Runner:

  ```
  docker model run hf.co/Qwen/Qwen3-VL-8B-Instruct
  ```
* [Browse
  Quantizations](/models?other=base_model:quantized:Qwen/Qwen3-VL-8B-Instruct) to use this model in  llama.cpp,  Ollama,  LM Studio, or any compatible app.

* [Qwen3-VL-8B-Instruct](#qwen3-vl-8b-instruct "Qwen3-VL-8B-Instruct")
  + [Model Performance](#model-performance "Model Performance")
  + [Quickstart](#quickstart "Quickstart")
    - [Using 🤗 Transformers to Chat](#using-%F0%9F%A4%97-transformers-to-chat "Using 🤗 Transformers to Chat")
    - [Generation Hyperparameters](#generation-hyperparameters "Generation Hyperparameters")
  + [Citation](#citation "Citation")

[![Chat](https://img.shields.io/badge/%F0%9F%92%9C%EF%B8%8F%20Qwen%20Chat%20-536af5)](https://chat.qwenlm.ai/)

Qwen3-VL-8B-Instruct
====================

Meet Qwen3-VL — the most powerful vision-language model in the Qwen series to date.

This generation delivers comprehensive upgrades across the board: superior text understanding & generation, deeper visual perception & reasoning, extended context length, enhanced spatial and video dynamics comprehension, and stronger agent interaction capabilities.

Available in Dense and MoE architectures that scale from edge to cloud, with Instruct and reasoning‑enhanced Thinking editions for flexible, on‑demand deployment.

#### Key Enhancements:

* **Visual Agent**: Operates PC/mobile GUIs—recognizes elements, understands functions, invokes tools, completes tasks.
* **Visual Coding Boost**: Generates Draw.io/HTML/CSS/JS from images/videos.
* **Advanced Spatial Perception**: Judges object positions, viewpoints, and occlusions; provides stronger 2D grounding and enables 3D grounding for spatial reasoning and embodied AI.
* **Long Context & Video Understanding**: Native 256K context, expandable to 1M; handles books and hours-long video with full recall and second-level indexing.
* **Enhanced Multimodal Reasoning**: Excels in STEM/Math—causal analysis and logical, evidence-based answers.
* **Upgraded Visual Recognition**: Broader, higher-quality pretraining is able to “recognize everything”—celebrities, anime, products, landmarks, flora/fauna, etc.
* **Expanded OCR**: Supports 32 languages (up from 19); robust in low light, blur, and tilt; better with rare/ancient characters and jargon; improved long-document structure parsing.
* **Text Understanding on par with pure LLMs**: Seamless text–vision fusion for lossless, unified comprehension.

#### Model Architecture Updates:

![](https://qianwen-res.oss-accelerate.aliyuncs.com/Qwen3-VL/qwen3vl_arc.jpg)

1. **Interleaved-MRoPE**: Full‑frequency allocation over time, width, and height via robust positional embeddings, enhancing long‑horizon video reasoning.
2. **DeepStack**: Fuses multi‑level ViT features to capture fine‑grained details and sharpen image–text alignment.
3. **Text–Timestamp Alignment:** Moves beyond T‑RoPE to precise, timestamp‑grounded event localization for stronger video temporal modeling.

This is the weight repository for Qwen3-VL-8B-Instruct.

---

Model Performance
-----------------

**Multimodal performance**

[![](https://qianwen-res.oss-accelerate.aliyuncs.com/Qwen3-VL/qwen3vl_4b_8b_vl_instruct.jpg)](https://qianwen-res.oss-accelerate.aliyuncs.com/Qwen3-VL/qwen3vl_4b_8b_vl_instruct.jpg)

**Pure text performance**
[![](https://qianwen-res.oss-accelerate.aliyuncs.com/Qwen3-VL/qwen3vl_4b_8b_text_instruct.jpg)](https://qianwen-res.oss-accelerate.aliyuncs.com/Qwen3-VL/qwen3vl_4b_8b_text_instruct.jpg)

Quickstart
----------

Below, we provide simple examples to show how to use Qwen3-VL with 🤖 ModelScope and 🤗 Transformers.

The code of Qwen3-VL has been in the latest Hugging Face transformers and we advise you to build from source with command:

```
pip install git+https://github.com/huggingface/transformers
# pip install transformers==4.57.0 # currently, V4.57.0 is not released
```

### Using 🤗 Transformers to Chat

Here we show a code snippet to show how to use the chat model with `transformers`:

```
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor

# default: Load the model on the available device(s)
model = Qwen3VLForConditionalGeneration.from_pretrained(
    "Qwen/Qwen3-VL-8B-Instruct", dtype="auto", device_map="auto"
)

# We recommend enabling flash_attention_2 for better acceleration and memory saving, especially in multi-image and video scenarios.
# model = Qwen3VLForConditionalGeneration.from_pretrained(
#     "Qwen/Qwen3-VL-8B-Instruct",
#     dtype=torch.bfloat16,
#     attn_implementation="flash_attention_2",
#     device_map="auto",
# )

processor = AutoProcessor.from_pretrained("Qwen/Qwen3-VL-8B-Instruct")

messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "image",
                "image": "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen-VL/assets/demo.jpeg",
            },
            {"type": "text", "text": "Describe this image."},
        ],
    }
]

# Preparation for inference
inputs = processor.apply_chat_template(
    messages,
    tokenize=True,
    add_generation_prompt=True,
    return_dict=True,
    return_tensors="pt"
)
inputs = inputs.to(model.device)

# Inference: Generation of the output
generated_ids = model.generate(**inputs, max_new_tokens=128)
generated_ids_trimmed = [
    out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
]
output_text = processor.batch_decode(
    generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
)
print(output_text)
```

### Generation Hyperparameters

#### VL

```
export greedy='false'
export top_p=0.8
export top_k=20
export temperature=0.7
export repetition_penalty=1.0
export presence_penalty=1.5
export out_seq_length=16384
```

#### Text

```
export greedy='false'
export top_p=1.0
export top_k=40
export repetition_penalty=1.0
export presence_penalty=2.0
export temperature=1.0
export out_seq_length=32768
```

Citation
--------

If you find our work helpful, feel free to give us a cite.

```
@misc{qwen3technicalreport,
      title={Qwen3 Technical Report}, 
      author={Qwen Team},
      year={2025},
      eprint={2505.09388},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2505.09388}, 
}

@article{Qwen2.5-VL,
  title={Qwen2.5-VL Technical Report},
  author={Bai, Shuai and Chen, Keqin and Liu, Xuejing and Wang, Jialin and Ge, Wenbin and Song, Sibo and Dang, Kai and Wang, Peng and Wang, Shijie and Tang, Jun and Zhong, Humen and Zhu, Yuanzhi and Yang, Mingkun and Li, Zhaohai and Wan, Jianqiang and Wang, Pengfei and Ding, Wei and Fu, Zheren and Xu, Yiheng and Ye, Jiabo and Zhang, Xi and Xie, Tianbao and Cheng, Zesen and Zhang, Hang and Yang, Zhibo and Xu, Haiyang and Lin, Junyang},
  journal={arXiv preprint arXiv:2502.13923},
  year={2025}
}

@article{Qwen2VL,
  title={Qwen2-VL: Enhancing Vision-Language Model's Perception of the World at Any Resolution},
  author={Wang, Peng and Bai, Shuai and Tan, Sinan and Wang, Shijie and Fan, Zhihao and Bai, Jinze and Chen, Keqin and Liu, Xuejing and Wang, Jialin and Ge, Wenbin and Fan, Yang and Dang, Kai and Du, Mengfei and Ren, Xuancheng and Men, Rui and Liu, Dayiheng and Zhou, Chang and Zhou, Jingren and Lin, Junyang},
  journal={arXiv preprint arXiv:2409.12191},
  year={2024}
}

@article{Qwen-VL,
  title={Qwen-VL: A Versatile Vision-Language Model for Understanding, Localization, Text Reading, and Beyond},
  author={Bai, Jinze and Bai, Shuai and Yang, Shusheng and Wang, Shijie and Tan, Sinan and Wang, Peng and Lin, Junyang and Zhou, Chang and Zhou, Jingren},
  journal={arXiv preprint arXiv:2308.12966},
  year={2023}
}
```

Downloads last month
:   4,538,226

Safetensors

Model size

9B params

Tensor type

BF16

·

Chat template

Files info

Inference Providers [NEW](https://huggingface.co/docs/inference-providers)

Featherless AI

[Image-Text-to-Text](/tasks/image-text-to-text "Learn more about image-text-to-text")

Examples

Input a message to start chatting with **Qwen/Qwen3-VL-8B-Instruct**.

Send

View Code Snippets

[Compare providers](/inference/models?model=Qwen%2FQwen3-VL-8B-Instruct)

Model tree for Qwen/Qwen3-VL-8B-Instruct
----------------------------------------

Adapters

[153 models](/models?other=base_model:adapter:Qwen/Qwen3-VL-8B-Instruct)

Finetunes

[528 models](/models?other=base_model:finetune:Qwen/Qwen3-VL-8B-Instruct)

Merges

[1 model](/models?other=base_model:merge:Qwen/Qwen3-VL-8B-Instruct)

Quantizations

[100 models](/models?other=base_model:quantized:Qwen/Qwen3-VL-8B-Instruct)

Spaces using Qwen/Qwen3-VL-8B-Instruct 100
------------------------------------------

[👀💨

LPX55/Qwen-Image-Edit-2511-Turbo-Lightning](/spaces/LPX55/Qwen-Image-Edit-2511-Turbo-Lightning)[🎨

mage-flow-community/mage-flow](/spaces/mage-flow-community/mage-flow)[🏥

Alibaba-DAMO-Academy/clinfusion-medical-vlm](/spaces/Alibaba-DAMO-Academy/clinfusion-medical-vlm)[📊

nvidia/Cosmos3-Action-Viewer-Prerelease](/spaces/nvidia/Cosmos3-Action-Viewer-Prerelease)[🔥

prithivMLmods/Qwen3-VL-Outpost](/spaces/prithivMLmods/Qwen3-VL-Outpost)[🤖

smolagents/computer-use-agent](/spaces/smolagents/computer-use-agent)[⚡

artificialguybr/qwen-vl](/spaces/artificialguybr/qwen-vl)[🚀

modelscope/modelscope-studio](/spaces/modelscope/modelscope-studio) + 95 Spaces + 92 Spaces

Collection including Qwen/Qwen3-VL-8B-Instruct
----------------------------------------------

[#### Qwen3-VL

Collection

37 items • Updated Dec 31, 2025 • 767](/collections/Qwen/qwen3-vl)

Papers for Qwen/Qwen3-VL-8B-Instruct
------------------------------------

[#### Qwen3 Technical Report

Paper • 2505.09388 • Published May 14, 2025 • 343](/papers/2505.09388)

[#### Qwen2.5-VL Technical Report

Paper • 2502.13923 • Published Feb 19, 2025 • 218](/papers/2502.13923)

[#### Qwen2-VL: Enhancing Vision-Language Model's Perception of the World at Any Resolution

Paper • 2409.12191 • Published Sep 18, 2024 • 80](/papers/2409.12191)

[#### Qwen-VL: A Frontier Large Vision-Language Model with Versatile Abilities

Paper • 2308.12966 • Published Aug 24, 2023 • 12](/papers/2308.12966)

Evaluation results
------------------

* [tiiuae/PBench](/datasets/tiiuae/PBench) · Average [View evaluation results](/Qwen/Qwen3-VL-8B-Instruct/discussions/28)  [leaderboard](/datasets/tiiuae/PBench?eval_result=Qwen/Qwen3-VL-8B-Instruct&leaderboard_task_id=average) 

  49 \*
* [llamaindex/ParseBench](/datasets/llamaindex/ParseBench)  [leaderboard](/datasets/llamaindex/ParseBench?eval_result=Qwen/Qwen3-VL-8B-Instruct)
* Mean [View evaluation results](/Qwen/Qwen3-VL-8B-Instruct/discussions/27)  [![](https://cdn-avatars.huggingface.co/v1/production/uploads/6980fe7cc9e5d7013d527b3a/F5Z_0zjcdl0cIKIq-MvTR.jpeg)

  source](https://huggingface.co/datasets/llamaindex/ParseBench)

  Pipeline name: qwen3vl\_layout

  46.8 \*
* Text Content [View evaluation results](/Qwen/Qwen3-VL-8B-Instruct/discussions/27)  [![](https://cdn-avatars.huggingface.co/v1/production/uploads/6980fe7cc9e5d7013d527b3a/F5Z_0zjcdl0cIKIq-MvTR.jpeg)

  source](https://huggingface.co/datasets/llamaindex/ParseBench)

  Pipeline name: qwen3vl\_layout

   89.5 \*
* Text Formatting [View evaluation results](/Qwen/Qwen3-VL-8B-Instruct/discussions/27)  [![](https://cdn-avatars.huggingface.co/v1/production/uploads/6980fe7cc9e5d7013d527b3a/F5Z_0zjcdl0cIKIq-MvTR.jpeg)

  source](https://huggingface.co/datasets/llamaindex/ParseBench)

  Pipeline name: qwen3vl\_layout

   66.8 \*
* +3 more
* [Delores-Lin/MDPBench](/datasets/Delores-Lin/MDPBench)  [leaderboard](/datasets/Delores-Lin/MDPBench?eval_result=Qwen/Qwen3-VL-8B-Instruct)
* +22 more

System theme

Company

[TOS](/terms-of-service) [Privacy](/privacy) [About](/huggingface) [Careers](https://apply.workable.com/huggingface/) 

Website

[Models](/models) [Datasets](/datasets) [Spaces](/spaces) [Pricing](/pricing) [Docs](/docs)