[Skip to yearly menu bar](#child-menu)
[Skip to main content](#main)

Main Navigation
---------------

[![conference_logo](/static/core/img/icml-navbar-logo.svg)](/)



* [ICML](#)
  + [Help/FAQ](/FAQ)
  + [Contact ICML](/Help/Contact)
  + [Create Profile](/Profile/create)
  + [Code of Conduct](/yearly-document/CodeOfConduct)
  + [Privacy Policy](/public/PrivacyPolicy)
  + [Press](/Conferences/2026/Press)
  + [Journal To Conference Track](/public/JournalToConference)
  + [Careers](/careers)
  + [Downloads](/Downloads)
  + [Inclusion](/public/Inclusion)
  + [Future Meetings](/Conferences/FutureMeetings)
* [My Stuff](/MyStuff)

 [Login](/accounts/login?nextp=/virtual/2026/papers.html%20)

* [Select Year: (2026)](#)
  + [2026](/Conferences/2026)
  + [2025](/Conferences/2025)
  + [2024](/Conferences/2024)
  + [2023](/Conferences/2023)
  + [2022](/Conferences/2022)
  + [2021](/Conferences/2021/index.html)
  + [2020](/Conferences/2020/)
  + [2019](/Conferences/2019/)
  + [2018](/Conferences/2018)
  + [2017](/Conferences/2017)
  + [2016](/Conferences/2016)
  + [2015](/Conferences/2015)
  + [2014](/Conferences/2014)
  + [2013](/Conferences/2013)
  + [2012](/Conferences/2012)
  + [2011](/Conferences/2011)
  + [2010](/Conferences/2010)
  + [2009](/Conferences/2009)
  + [2008](/Conferences/2008)
  + [2007](/Conferences/2008)
  + [2006](/Conferences/2007)
  + [2005](/Conferences/2005)
  + [2004](/Conferences/2005)
  + [2002](/Conferences/2002)
  + [1996](/Conferences/1996)
  + [IMLS Archives](http://www.machinelearning.org/archive.html)
* [Getting Started](/virtual/2026/index.html)
* [Schedule](/virtual/2026/calendar?filter_events=&filter_rooms=)
* [Tutorials](/virtual/2026/events/tutorial)
* [Main Conference](#)
  + [Invited Talks](/virtual/2026/eventlistwithbios/invited%20talk)
  + [Orals](/virtual/2026/events/oral)
  + [Awards](/virtual/2026/awards_detail)
  + [Test of Time Award](/virtual/2026/test-of-time-award)
  + [Papers](/virtual/2026/papers.html)
  + [Spotlight Posters](/virtual/2026/events/2026SpotlightPosters)
  + [Position Paper Posters](/virtual/2026/events/2026-position-papers)
  + [Journal Track Posters](/virtual/2026/events/2026-journal-track)
* [Workshops](/virtual/2026/events/workshop)
* [Socials](/virtual/2026/events/social)
* [Exhibitors](#)
  + [Exhibitors](/virtual/2026/sponsor_list)
  + [Expo Talks, Demos, and Workshops](/virtual/2026/events/2026-Expo)
* [Organizers](/virtual/2026/organizers)
* [HelpDesk](/chat-directory?channel=icml-helpdesk)

  
  

Poster


Wed, Jul 8, 2026 • 10:30 PM – 12:15 AM PDT


HALL A #2108

AutoTool: Dynamic Tool Selection and Integration for Agentic Reasoning
======================================================================

Jiaru Zou ⋅ Ling Yang ⋅ Yunzhe Qi ⋅ Sirui Chen ⋅ Mengting Ai ⋅ Ke Shen ⋅ Jingrui He ⋅ Mengdi Wang

[Project Page](https://github.com/Gen-Verse/Open-AgentRL)

### Abstract

Agentic reinforcement learning has advanced large language models (LLMs) to reason through long chain-of-thought trajectories while interleaving external tool use. Existing approaches assume a fixed inventory of tools, which limits the adaptability of LLM agents to new or evolving toolsets. We present AutoTool, a training framework that equips LLM agents with dynamic tool-selection capabilities throughout their reasoning trajectories. AutoTool employs a dual-phase optimization pipeline: (i) SFT and RL-based trajectory stabilization for coherent reasoning, and (ii) KL-regularized Plackett–Luce Ranking to refine consistent multi-step tool selection. We further build a 200k dataset with explicit tool-selection rationales across 1,000+ tools and 100+ tasks spanning mathematics, science, code generation, and multimodal reasoning. Across ten diverse benchmarks, we train two base models, Qwen3-8B and Qwen2.5-VL-7B, with AutoTool. With fewer parameters, AutoTool consistently outperforms advanced LLM agents and tool-integration methods, yielding average gains of 6.4\% in math &amp; science reasoning, 4.5\% in search-based QA, 7.7\% in code generation, and 6.9\% in multimodal understanding. In addition, AutoTool exhibits stronger generalization by dynamically leveraging unseen tools from evolving toolsets during inference.

Show more

### Lay Summary

Large language models are increasingly used as agents that can reason step by step and call external tools such as search engines, code interpreters, or vision tools. However, most existing agent systems assume a fixed set of tools, which makes them less flexible when new tools are added or when the task requires choosing among many possible tools. We introduce AutoTool, a training framework that teaches language-model agents to dynamically select and use the right tools during reasoning. AutoTool first stabilizes the model’s reasoning trajectory through supervised fine-tuning and reinforcement learning, then further improves tool selection using a ranking-based optimization method that encourages better tool choices over weaker alternatives. Across math, science, search, code, and multimodal tasks, AutoTool improves performance over standard agent-training and tool-use baselines. It also generalizes to previously unseen tools, suggesting a path toward more adaptable AI agents that can operate in evolving tool environments.

Show more

Log in and register to view live content

Successful Page Load

| ICML uses cookies for essential functions only. We do not sell your personal information. [Our Privacy Policy »](/public/PrivacyPolicy) | Accept |

  

###### ICML logo

The ICML Logo above may be used on presentations. Right-click and choose
download. It is a vector graphic and may be used at any scale.

###### Useful links

###### Contact

1269 Law Street, San Diego CA 92109

[Email](/Help/Contact)