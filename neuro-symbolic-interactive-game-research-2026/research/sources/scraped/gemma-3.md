[![Google for Developers](https://storage.googleapis.com/gweb-developer-goog-blog-cms-assets/site/20260731-000318/images/g-dev.svg)](https://developers.google.com/)

[Community/Events](//developers.google.com/community)

[Learn](//developers.google.com/solutions/catalog)

[Blog](//developers.googleblog.com)

[YouTube](https://www.youtube.com/user/GoogleDevelopers)

Search

[![Google for Developers](https://storage.googleapis.com/gweb-developer-goog-blog-cms-assets/site/20260731-000318/images/g-dev.svg)](https://developers.google.com/)

* [Community/Events](//developers.google.com/community)
* [Learn](//developers.google.com/solutions/catalog)
* [Blog](//developers.googleblog.com)
* [YouTube](https://www.youtube.com/user/GoogleDevelopers)

[Gemma](/en/search/?product_categories=Gemma)

Introducing Gemma 3: The Developer Guide
========================================

MARCH 12, 2025

[Omar Sanseviero](/en/search/?author=Omar+Sanseviero)
Member of the Technical Staff

[Philipp Schmid](/en/search/?author=Philipp+Schmid)
Developer Relations Engineer

Share

* [Facebook](https://www.facebook.com/sharer/sharer.php?u={url} "Share on Facebook")
* [Twitter](https://twitter.com/intent/tweet?text={url} "Share on Twitter")
* [LinkedIn](https://www.linkedin.com/shareArticle?url={url}&mini=true "Share on LinkedIn")
* [Mail](mailto:name@example.com?subject=Check%20out%20this%20site&body=Check%20out%20{url} "Send via Email")

![Gemma 3](https://storage.googleapis.com/gweb-developer-goog-blog-assets/images/gemma-3_2.original.png)

Since its first launch, Gemma models have been downloaded over 100 million times, with the community creating over 60,000 variations for all kinds of use cases. We are excited to introduce Gemma 3, our most capable and advanced version of the Gemma open-model family, building upon the success of previous Gemma releases. We listened to community feedback and added the most requested features, such as longer context, multimodality, and more!

What’s new in Gemma?
--------------------

[Link to Youtube Video](https://www.youtube.com/watch?v=UU13FN2Xpyw)
(visible only when JS is disabled)

Gemma 3 introduces multimodality, supporting vision-language input and text outputs. It handles context windows up to 128k tokens, understands over 140 languages, and offers improved math, reasoning, and chat capabilities, including structured outputs and function calling. Gemma 3 is available in four sizes (1B, 4B, 12B, and 27B) as both pre-trained models, which can be fine-tuned for your own use cases and domains, and general-purpose instruction-tuned versions.

![Comparison chart - Gemma models](https://storage.googleapis.com/gweb-developer-goog-blog-assets/images/comparison-chart-gemma-models.original.jpg)

How was Gemma built?
--------------------

Gemma's pre-training and post-training processes were optimized using a combination of distillation, reinforcement learning, and model merging. This approach results in enhanced performance in math, coding, and instruction following. Gemma 3 uses a new tokenizer for better multilingual support for over 140+ languages and was trained on 2T tokens for 1B, 4T for 4B, 12T for 12B, and 14T tokens for 27B, on Google TPUs using the JAX Framework.

For post-training, Gemma 3 uses 4 components:

* Distillation from a larger instruct model into the Gemma 3 pre-trained checkpoints.

* Reinforcement Learning from Human Feedback (RLHF) to align model predictions with human preferences.

* Reinforcement Learning from Machine Feedback (RLMF) to enhance mathematical reasoning.

* Reinforcement Learning from Execution Feedback (RLEF) to improve coding capabilities.

These updates significantly improved the model math, coding, and instruction following capabilities, making it the top open compact model in LMArena, with a score of 1338.

![Graph showing a comparison of Model performance v. Size](https://storage.googleapis.com/gweb-developer-goog-blog-assets/images/model-performance-v-size-gemma-3.original.png)

The instruct versions of Gemma 3 use the same dialog format as Gemma 2, so you don’t need to update your tooling to update to the latest version for text-only input. For image input, Gemma 3 allows specifying images interleaved with text.

### **Multi-turn text example**

```
<bos><start_of_turn>user
knock knock<end_of_turn>
<start_of_turn>model
who is there<end_of_turn>
<start_of_turn>user
Gemma<end_of_turn>
<start_of_turn>model
Gemma who?<end_of_turn>
```

Markdown

Copied

**Interleaved image example**

```
<bos><start_of_turn>user
Image A: <start_of_image>
Image B: <start_of_image>

Label A: water lily
Label B:<end_of_turn>
<start_of_turn>model
Desert rote<end_of_turn>
```

Markdown

Copied

Multimodality
-------------

Gemma 3 has an integrated vision encoder based on [SigLIP](https://arxiv.org/abs/2303.15343). The Gemma 3 vision model, which was kept frozen during training, is the same across its different sizes (4B, 12B and 27B). Thanks to this, Gemma can use images and videos as inputs, allowing it to analyze images, answer questions about an image, compare images, identify objects, and even reply about text within an image. Although the model was originally created to work with images of 896x896 pixels, a new adaptive window algorithm is used to segment input images, allowing Gemma 3 to work with high resolution and non-square images.

![Gemma 3 Multimodality example](https://storage.googleapis.com/gweb-developer-goog-blog-assets/images/gemma-3-multimodality-example.original.png)

Input: I need to get warm. What button turns up the heat?

![Gemma 3 multimodality - output example](https://storage.googleapis.com/gweb-developer-goog-blog-assets/images/gemma-3-multimodality--output-example.original.png)

Based on the image, the button that likely turns up the heat is 暖房 (Danbou).
"暖房" means "heating" in Japanese. It's the button you'd press to activate the heating function on the air conditioner/climate control system.
The button with the plus sign (+) might adjust the temperature after you've selected the heating mode.

ShieldGemma 2
-------------

ShieldGemma 2 is a 4B image safety classifier built on Gemma 3. It outputs labels across key safety categories, enabling safety moderation of synthetic images (from image generation models) and natural images (which could be the input filter of a Vision-Language Model such as Gemma 3). Learn more about [ShieldGemma 2](/en/safer-and-multimodal-responsible-ai-with-gemma/).

What are you building?
----------------------

We're continually astounded by the ingenuity of the Gemma community and the explosive growth of the [Gemmaverse](https://ai.google.dev/gemma/gemmaverse). From research labs pioneering novel fine-tuning techniques – such as the [SimPO method](https://huggingface.co/princeton-nlp/gemma-2-9b-it-SimPO) developed by Princeton NLP, which directly optimizes for human preferences without a reference model; INSAIT training [state-of-the-art LLMs for Bulgarian](https://ai.google.dev/gemma/gemmaverse/insait) – to developers training Gemma on entirely new modalities like [Nexa AI did with OmniAudio](https://ai.google.dev/gemma/gemmaverse/omniaudio). We can't wait to see what breakthroughs you achieve next.

Get started with Gemma 3 today
------------------------------

Ready to explore the potential of Gemma 3 today? Here's how:

* **Experiment directly:** Use [Google AI Studio](https://aistudio.google.com/prompts/new_chat?model=gemma-3-27b-it) to try Gemma 3 in just a couple of clicks.

* **Download the models**: Find the model weights on [Hugging Face](https://huggingface.co/collections/google/gemma-3-release-67c6c6f89c4f76621268bb6d) and [Kaggle](https://www.kaggle.com/models/google/gemma-3).

* **Learn & integrate:** Dive into [our technical report](https://goo.gle/Gemma3Report) and [comprehensive documentation](https://ai.google.dev/gemma/docs) to quickly integrate Gemma into your projects or start with our inference guide or try fine-tuning with a custom dataset.

* **Use your favorite development tools:** Leverage your preferred tools and frameworks, including [Hugging Face Transformers](https://huggingface.co/blog/gemma3), [Ollama](https://ollama.com/library/gemma3), our new [Gemma JAX library](https://gemma-llm.readthedocs.io/en/latest/), [MaxText](https://github.com/AI-Hypercomputer/maxtext), [LiteRT](https://developers.googleblog.com/en/gemma-3-on-mobile-and-web-with-google-ai-edge), [Gemma.cpp](https://github.com/google/gemma.cpp), llama.cpp, and [Unsloth](https://unsloth.ai/blog/gemma3).

* **Deploy your way**: Gemma 3 offers multiple deployment options, including [Google GenAI API](https://github.com/googleapis/python-genai), [Vertex AI](https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/gemma3), [Cloud Run](https://cloud.google.com/run/docs/tutorials/gpu-gemma-with-ollama), [Cloud TPU](https://cloud.google.com/tpu/docs/intro-to-tpu), and [Cloud GPU](https://cloud.google.com/gpu) and integrations across platforms, giving you the flexibility to choose the best fit for your use case.

posted in:

* [Gemma](/en/search/?product_categories=Gemma)
* [AI](/en/search/?technology_categories=AI)
* [Announcements](/en/search/?content_type_categories=Announcements)
* [generative AI models](/en/search/?tag=generative%20AI%20models)
* [Generative AI](/en/search/?tag=Generative%20AI)
* [Explore](/en/search/?tag=Explore)
* [ShieldGemma](/en/search/?tag=ShieldGemma)
* [Gemma 3](/en/search/?tag=Gemma%203)

Previous

Next

Related Posts

[![Why Go is an Ideal Language for AI-Assisted Software Engineering](https://storage.googleapis.com/gweb-developer-goog-blog-assets/images/Go_Logo_-_Blue.2e16d0ba.fill-800x400.png)

AI
Cloud
Community
Business and Leadership

Why Go is an Ideal Language for AI-Assisted Software Engineering

AUG. 11, 2026](/en/why-go-is-an-ideal-language-for-ai-assisted-software-engineering/)
[![Agent Plugins package your skills, tools, and more](https://storage.googleapis.com/gweb-developer-goog-blog-assets/images/agent-plugins-banner-4209x1253.2e16d0ba.fill-800x400.jpg)

AI
Announcements
Learn

Agent Plugins package your skills, tools, and more

AUG. 6, 2026](/en/agent-plugins-package-your-skills-tools-and-more/)
[![Introducing EmbeddingGemma: The Best-in-Class Open Model for On-Device Embeddings](https://storage.googleapis.com/gweb-developer-goog-blog-assets/images/EmbeddingGemma_Metadatal_RD2-V01.2e16d0ba.fill-800x400.jpg)

Gemma
Mobile
AI
Announcements

Introducing EmbeddingGemma: The Best-in-Class Open Model for On-Device Embeddings

SEPT. 4, 2025](/en/introducing-embeddinggemma/)
[![Introducing Gemma 3 270M: The compact model for hyper-efficient AI](https://storage.googleapis.com/gweb-developer-goog-blog-assets/images/Gemma3-270M_Metadata_RD2-V02.2e16d0ba.fill-800x400.jpg)

Gemma
AI
Announcements

Introducing Gemma 3 270M: The compact model for hyper-efficient AI

AUG. 14, 2025](/en/introducing-gemma-3-270m/)
[![Mastering Edge AI on Raspberry Pi with LiteRT and Gemma](https://storage.googleapis.com/gweb-developer-goog-blog-assets/images/Banner.2e16d0ba.fill-800x400.png)

Web
AI
How-To Guides
Announcements

Mastering Edge AI on Raspberry Pi with LiteRT and Gemma

AUG. 11, 2026](/en/mastering-edge-ai-on-raspberry-pi-with-litert-and-gemma/)

* Connect
  + [Blog](//googledevelopers.blogspot.com)
  + [Bluesky](https://goo.gle/3FReQXN)
  + [Instagram](https://goo.gle/googlefordevs)
  + [LinkedIn](https://goo.gle/gdevs-li)
  + [X (Twitter)](https://goo.gle/gdevs-tw)
  + [YouTube](https://goo.gle/developers)
* Programs
  + [Google Developer Program](//developers.google.com/program)
  + [Google Developer Groups](//developers.google.com/community/gdg)
  + [Google Developer Experts](//developers.google.com/community/experts)
  + [Accelerators](//developers.google.com/community/accelerators)
  + [Women Techmakers](//www.womentechmakers.com)
  + [Google Cloud & NVIDIA](//developers.google.com/community/nvidia)
* Developer consoles
  + [Google API Console](//console.developers.google.com)
  + [Google Cloud Platform Console](//console.cloud.google.com)
  + [Google Play Console](//play.google.com/apps/publish)
  + [Firebase Console](//console.firebase.google.com)
  + [Actions on Google Console](//console.actions.google.com)
  + [Cast SDK Developer Console](//cast.google.com/publish)
  + [Chrome Web Store Dashboard](//chrome.google.com/webstore/developer/dashboard)
  + [Google Home Developer Console](//console.home.google.com/)

[![Google for Developers](https://storage.googleapis.com/gweb-developer-goog-blog-cms-assets/site/20260731-000318/images/g-dev.svg)](https://developers.google.com/)

* [Android](//developer.android.com)
* [Chrome](//developer.chrome.com/home)
* [Firebase](//firebase.google.com)
* [Google Cloud Platform](//cloud.google.com)
* [All products](//developers.google.com/products)

* [Terms](//developers.google.com/terms/site-terms)
* [Privacy](//policies.google.com/privacy)