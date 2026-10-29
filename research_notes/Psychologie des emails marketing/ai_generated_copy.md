# AI-generated marketing and sales copy: reader response, linguistic tells, persuasion, homogenisation, LLM judges

Method note. Research run on 29 Oct 2026. The web-search budget for this run (shared with the other researchers) ran out partway through, so later checks were direct fetches of known primary URLs only. **[verified]** = read on the cited page this session (or in a search-result summary of that page, where marked). **[not re-fetched]** = from prior knowledge of the paper, given with its canonical URL; spot-check before quoting figures. Grades: **STRONG** = meta-analysis, independent replication, or a large preregistered randomized experiment (taken here as roughly N ≥ 2,000, or many internal replications); **MODERATE** = a single peer-reviewed study or well-designed preprint; **WEAK-FOLKLORE** = vendor surveys, editor compilations, journalism, anecdote. Application tags: **(a)** deterministic code check, **(b)** writer-prompt instruction, **(c)** cold-reader/critic criterion. **[JUDGE-BLIND]** = an LLM judge is likely to miss or mis-score this.

## 1. Consumer and buyer response to (perceived) AI authorship and to disclosure

### Takeaway
The cost of AI authorship is relational, not argumentative. When people *believe* a message was written by AI, trust in the sender, word of mouth and loyalty fall. The fall is largest for emotional messages and smallest for factual ones or when AI only edited, and being caught costs more trust than disclosing. Yet an "AI-generated" label does not make the content itself less persuasive. B2B-specific evidence is vendor-grade only, and its main complaint is irrelevant outreach, not AI authorship.

### Cited Findings
**AI-authorship effect in marketing communications**
- [MODERATE: 7 preregistered experiments, one team] Kirk (lead author; the brief names Givi as co-author, which the fetched pages did not confirm), *Journal of Business Research* 2025, "The AI-authorship effect: Understanding authenticity, moral disgust, and consumer responses to AI-generated marketing communications". Main result: when consumers believe an **emotional** marketing communication was written by AI rather than a human, positive word of mouth and customer loyalty fall. The effect is serially mediated: lower perceived authenticity, then moral disgust.
  - The effect is attenuated for factual (vs emotional) messages (Study 2), when AI only *edits* the message (Study 3), when the message is signed directly by an AI (Study 4), and when consumers think most marketing is AI-written (Study WA1).
  - It is *reversed* when consumers believe the message is reused, i.e. not originally written by the sender (Study 6).
  - It held across personalised and mass communications, across different emotions, across businesses and employees, and on behavioural measures. The abstract page reports no effect sizes.
  - Source: [Newswise research alert](https://www.newswise.com/articles/the-ai-authorship-effect-understanding-authenticity-moral-disgust-and-consumer-responses-to-ai-generated-marketing-communications) [verified]. ScienceDirect PII S0148296324004880.
  - Use: (b) do not claim feelings, effort or personal attention the sender has not stated; let facts carry the warmth. (c) flag emotional claims that are not anchored in a specific fact the sender owns. The trigger is *belief* in AI authorship, so the tells in Section 3 are what set the penalty off.
- [STRONG: 13 preregistered experiments, single team; sample given as ">3,000" in secondary write-ups and ">5,000" in the university release] Schilke & Reimann, *Organizational Behavior and Human Decision Processes* 2025, "The transparency dilemma: How AI disclosure erodes trust" (DOI 10.1016/j.obhdp.2025.104405).
  - People who disclose AI use are trusted less than people who do not. The mechanism is reduced perceived legitimacy.
  - The penalty holds whether disclosure is voluntary or mandatory and across framings, and goes beyond plain algorithm aversion. It is attenuated, but not eliminated, among evaluators who are positive about technology or believe AI is accurate, and it persists among frequent AI users.
  - Being *exposed* by someone else (for example through an AI detector) produces the steepest trust drop.
  - Sources: [University of Arizona news](https://news.arizona.edu/employee-news/being-honest-about-using-ai-work-makes-people-trust-you-less-research-finds); [IDEAS/RePEc record](https://ideas.repec.org/a/eee/jobhdp/v188y2025ics0749597825000172.html) [verified via search summaries]
  - Use: being "found out" through tells is the worst case, so removing tells in code (a) matters more than the wording of any disclosure.
- [MODERATE: N = 1,601, preregistered survey experiment] Gallegos et al., *PNAS Nexus* (Feb 2026), "Labeling messages as AI-generated does not reduce their persuasive effects". Participants read an AI-generated policy message randomly labelled as AI-written, human-written, or unlabelled.
  - 92.0% believed the label they saw.
  - Labels had no significant effect on attitude change, perceived accuracy or intentions. The messages themselves shifted policy views by 9.74 percentage points on average.
  - The issues were deliberately low-salience and not highly polarised.
  - Sources: [PMC full text](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12887897/); [arXiv 2504.09865](https://arxiv.org/abs/2504.09865v2); [Stanford HAI brief](https://hai.stanford.edu/policy/labeling-ai-generated-content-may-not-change-its-persuasiveness) [verified via search summary]
- [MODERATE] Longoni & Cian, *Journal of Marketing* 2022, the "word-of-machine" effect. People judge AI recommenders more competent than humans on utilitarian attributes and less competent on hedonic or experiential ones. Preference for AI advice weakens when hedonic goals are salient, and the effect shrinks when AI is framed as *assisting* a human ("augmented intelligence"). — [Journal of Marketing](https://journals.sagepub.com/doi/10.1177/0022242920957347) [not re-fetched]
- [MODERATE each] Two older results frame the debate.
  - Algorithm aversion: people abandon an algorithm after seeing it err (Dietvorst, Simmons & Massey 2015). — [JEP: General](https://doi.org/10.1037/xge0000033) [not re-fetched]
  - Algorithm appreciation: people often weight algorithmic advice above human advice for estimates (Logg, Minson & Moore 2019). — [OBHDP](https://doi.org/10.1016/j.obhdp.2018.12.005) [not re-fetched]

**AI-mediated interpersonal communication (messages, profiles, emails)**
- [MODERATE] Jakesch et al., CHI 2019, the "Replicant effect". When readers were told that *some* host profiles were AI-written, they rated the ones they suspected as AI-written less trustworthy. When told that *all* profiles were AI-written, there was no penalty. — [ACM DL](https://doi.org/10.1145/3290605.3300469) [not re-fetched]
- [MODERATE] Hohenstein et al., *Scientific Reports* 2023. AI smart replies made conversations more efficient and more positive, and partners rated users more favourably. But people *perceived* as using smart replies were rated more negatively (less cooperative, less affiliative). — [Scientific Reports](https://www.nature.com/articles/s41598-023-30938-9) [not re-fetched]
- [MODERATE study, seen only through a vendor page] University of Florida study of about 1,100 professionals (Coman & Cardon, 2025). 40–52% judged a supervisor sincere when an email was heavily AI-assisted, against 83% when it was lightly assisted. — cited on [Sales.co](https://sales.co/research/ai-in-sales-statistics) [secondary; primary not fetched]
- [MODERATE] Altay & Gilardi, *PNAS Nexus* 2024. Headlines labelled "AI-generated" were believed and shared less, whether they were true or false and even when a human wrote them, because readers assume full automation. — [PNAS Nexus](https://doi.org/10.1093/pnasnexus/pgae403) [not re-fetched]

**B2B and email-specific data (all WEAK-FOLKLORE)**
- [WEAK-FOLKLORE] Gartner, survey of 645 B2B buyers (fielded Aug–Sep 2025, released May 2026). The survey is about buyers' own use of AI, not about email copy.
  - 69% want a sales rep to validate AI-generated information.
  - 67% would prefer a rep-free buying process.
  - 51% expect misleading information more from GenAI, 49% more from sales reps.
  - Source: [Gartner press release](https://www.gartner.com/en/newsroom/press-releases/2026-05-20-gartner-survey-finds-sixty-nine-percent-of-b-two-b-buyers-turn-to-sales-reps-to-validate-ai-generated-insights) [via search summary]
- [WEAK-FOLKLORE] Gartner 2025, as cited by a vendor: 73% of B2B buyers actively avoid suppliers who send irrelevant outreach. — [Sales.co](https://sales.co/research/ai-in-sales-statistics)
- [WEAK-FOLKLORE] Sales.co's own sending data (a cold-email agency).
  - 0.70% of 1,288,605 emails (Oct 2025–Aug 2026) got a reply from a real person.
  - 18 of 2,391 human replies (0.75%) said the email looked AI-written or automated ("AI slop", "your automation"). These were found by keyword search; the vendor calls 18 a floor.
  - There is no human-written control group, and the page's own reply figures do not reconcile.
  - Source: [Sales.co](https://sales.co/research/ai-in-sales-statistics) [verified]
- [WEAK-FOLKLORE] Hunter cold-email survey (via Sales.co): 67% of decision-makers say they don't mind receiving AI-generated emails; most people shown nine emails identified fewer than four of the AI-written ones. — [Sales.co](https://sales.co/research/ai-in-sales-statistics)
- [WEAK-FOLKLORE] Validity 2026 (via Sales.co): 40% of consumers say they are less likely to trust marketing emails they know were written by AI. — [Sales.co](https://sales.co/research/ai-in-sales-statistics)
- [WEAK-FOLKLORE] HG Insights 2026: only 2% of buyers say they "always" trust AI outputs; 94% fact-check AI-generated information. — [HG Insights](https://hginsights.com/blog/trust-more-verify-everything-what-the-2026-b2b-buying-disconnect-report-says-about-where-buying-is-actually-heading/) [via search summary]

**Disclosure law, where it bears on these findings**
- EU AI Act, Article 50. My legal reading needs confirming by whoever covers law. — [Article 50 text](https://artificialintelligenceact.eu/article/50/) [not re-fetched]
  - Art. 50(2): providers of AI systems that generate synthetic text must mark outputs as artificially generated, in a machine-readable, detectable way. There is an exception for assistive standard editing.
  - Art. 50(4): deployers must disclose AI-generated text *published to inform the public on matters of public interest*, unless it underwent human review or editorial control.
  - These obligations apply from 2 August 2026. Ordinary marketing emails are not the "public interest" category; the 50(2) marking duty is the part that could reach a copy-generation product.

### Inferences
- **The likely causal chain.** Detectable tells lead the reader to believe AI wrote the email. For emotional or hedonic copy, that belief costs authenticity and triggers moral disgust, which lowers loyalty and word of mouth (Kirk). Separately, it lowers trust in the sender (Schilke & Reimann).
- **Why tells matter more than labels.** Labels leave content persuasion intact (Gallegos), while belief in AI authorship damages the relationship. So MarketingOS's main lever is *not reading as AI*, not its disclosure wording.
- **Where readers care least:** factual or utilitarian content, AI as editor rather than author, and settings where AI is assumed to be everywhere (Kirk WA1, Jakesch 2019).
- **Where they care most:** emotional, personal and hedonic copy, such as thanks, founder stories, or "we care" messages. That is where tell-removal effort pays most. B2B utilitarian copy carries less of the authenticity penalty, but its readers are the best detectors (Section 2).
- **Applications for MarketingOS:**
  - (b) "Never assert feelings, effort or personal attention that the sender's material does not state."
  - (c) "Does any sentence claim sincerity, excitement or personal care without a concrete fact the sender owns?"
  - (a) a list of manufactured-sincerity phrases would have to be mined from MarketingOS's own drafts; no research list exists.
- [JUDGE-BLIND] An LLM cold reader cannot feel moral disgust at AI authorship, and it tends to prefer LLM-written text (Section 6). It will not reproduce the authenticity penalty, so code and the writer prompt must handle it.
- Kirk's reversal for "reused" messages suggests readers expect a sender to write their own words. Template-feel is already penalised; AI-feel violates the same expectation.

### Gaps
- No peer-reviewed study found on B2B buyers' response to AI-written sales emails specifically (reply rates, perceived competence). All B2B numbers are vendor surveys. Gong, LinkedIn and Forrester data could not be searched once the budget ran out.
- No effect sizes found for Kirk et al.; only the lead author was confirmed.
- Schilke & Reimann's sample size is inconsistent across sources (3,000 vs 5,000).
- Liu, Mittal, Yang & Bruckman (CHI 2022), "Will AI console me when I lose my pet? Understanding perceptions of AI-mediated email writing" ([ACM DL](https://doi.org/10.1145/3491102.3517731)), is likely the most email-specific study. Its findings were not verified this session.
- No study found on AI disclosure specifically in marketing *emails* (only ads, headlines, policy messages, profiles). No French-language study on consumer response to AI authorship found.
- Whether the penalty decays as AI becomes assumed everywhere (Kirk WA1 hints yes) has not been tested over time.
- The EU "Digital Omnibus" proposals may change Article 50 timing; not checked.

## 2. Can people tell? Human and machine detection of AI text

### Takeaway
Ordinary readers spot AI text at about chance, using flawed cues: contractions, first person or family topics read as "human"; perfect grammar reads as human; fancy words read as AI. People who use LLMs heavily for writing, however, are near-perfect detectors. What they key on is countable: the specific AI vocabulary, predictable structures, "safe" unoriginal content, over-uniform quotes and formatting, generic openings and optimistic closings. Prompted LLMs are mediocre detectors.

### Cited Findings
- [STRONG: 6 experiments, N ≈ 4,600] Jakesch, Hancock & Naaman, *PNAS* 2023, "Human heuristics for AI-generated language are flawed". People could not tell AI-generated self-presentations (professional, hospitality and dating profiles) from human ones; accuracy was near chance. They leaned on intuitive but flawed heuristics: first-person pronouns, contractions and family topics read as human. AI can exploit these heuristics to produce text judged "more human than human". — [PNAS](https://www.pnas.org/doi/10.1073/pnas.2208839120) [not re-fetched]
- [MODERATE] Clark et al., ACL 2021, "All That's 'Human' Is Not Gold". Untrained evaluators told GPT-3 text from human text at chance, and training raised accuracy only modestly. — [ACL Anthology](https://aclanthology.org/2021.acl-long.565/) [not re-fetched]
- [MODERATE: 5 expert annotators, 300 non-fiction articles; GPT-4o, Claude and o1-Pro outputs] Russell, Karpinska & Iyyer, ACL 2025, "People who frequently use ChatGPT for writing tasks are accurate and robust detectors of AI-generated text". — [arXiv HTML](https://arxiv.org/html/2501.15654v1); [ACL Anthology](https://aclanthology.org/2025.acl-long.267) [verified]

  Accuracy (TPR = AI text correctly flagged; FPR = human text wrongly flagged):

  | Detector | TPR | FPR |
  |---|---|---|
  | Majority vote of five frequent-LLM-user annotators | 99.3% (1 article of 300 misclassified) | 0% |
  | Individual experts (average) | 92.7% | 4.0% |
  | Non-experts (average) | 56.7% | 51.7% (≈ chance) |
  | Pangram | 98.0% | 2% |
  | GPTZero | 85.3% | 0.7% |
  | Fast-DetectGPT | 80.0% | 7.2% |
  | Binoculars | 66.7% | 1.3% |
  | RADAR | 15.3% | 2% |
  | GPT-4o prompted with chain-of-thought and a detection guide | 78.0% | 10.7% |

  - The experts' majority vote stayed at 100% TPR / 0% FPR on paraphrased text and on o1-Pro "humanized" text. Individual experts varied; one fell to 0% TPR on humanized text.
  - Under humanization, GPTZero fell to 46.7% TPR and Binoculars to 6.67%. Pangram's humanizer-aware model held 96.7%.
- **What the experts used** [same source, verified], as a share of their explanations:
  - AI vocabulary, 53.1% ("testament", "crucial", "vibrant", "significantly", "delve").
  - Sentence structure, 35.9% ("not only … but also", lists of three).
  - Grammar and punctuation, 24.8% (AI is grammatically perfect; humans make minor errors).
  - Originality, 23.7% (AI is "safe" and lacks surprises).
  - Quotes, 22.3% (quotes sound overly formal, mirror the article's style, and always come in the same format).
  - Clarity, 19.5% (over-explains, adds irrelevant detail).
  - Formatting, 15.0% (overly consistent).
  - Conclusions, 13.1% (repetitive and optimistic).
  - Formality, 12.3% (rarely uses contractions, slang or filler).
  - Names and titles, 11.7% (reuses names such as "Emily Carter" and "Sarah Thompson"; gives many people the same title, e.g. "Dr.").
  - Tone, 9.3% (consistently neutral or positive).
  - Introductions, 7.3% (generic).
  - Factuality, 7.2%; topics, 3.1% (avoids darker topics).
  - With o1-Pro, experts also noticed that humans repeat "says" where AI writes "notes" or "explains".
- **Non-expert errors** [same source]: treating any fancy or rare word as AI (experts know the specific overused ones); believing correct grammar means human and run-on sentences mean AI (the reverse is closer to true); labelling any neutral tone as AI, which produces many false positives.
- [MODERATE] Liang et al., *Patterns* 2023. GPT detectors misclassified more than half of TOEFL essays by non-native English writers as AI-generated: perplexity-based detection punishes plain, low-variance prose. — [arXiv 2304.02819](https://arxiv.org/abs/2304.02819) [not re-fetched]
- [WEAK-FOLKLORE] Wikipedia's AI Cleanup editors.
  - Humans are poor at spotting AI text, and human writing is itself becoming more LLM-like.
  - Fixing surface signs only "make[s] detection harder".
  - A sudden shift in style, such as flawless grammar from someone whose other writing is not, is a strong contextual sign.
  - Source: [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) [verified]
- [WEAK-FOLKLORE] French detectors. A Next.ink test found several detectors failed on French text written by OpenAI models while others succeeded. Detection depends heavily on how much the text was rewritten. — [Next.ink](https://next.ink/article/71730/comment-tenter-didentifier-textes-emanant-dintelligences-artificielles-generatives); [Pasquale Pillitteri (FR)](https://pasqualepillitteri.it/fr/news/404/reconnaitre-texte-ecrit-ia-detector-checker) [via search summary]

### Inferences
- The B2B recipients MarketingOS writes for (marketing, sales, tech, agencies) are increasingly the "frequent LLM user" population that Russell et al. found to be near-perfect detectors. Consumers at large cannot tell, but they react to *belief*, and Section 1 shows being found out is the worst case.
- The expert detection channel is mostly countable: vocabulary, structural templates, quote formatting, uniform formatting, contraction rate, generic openings, optimistic closings, default names. Deterministic checks (a) match how detection actually happens.
- Jakesch's heuristics cut both ways. Adding contractions and first person makes text *read* human to lay readers, but not to experts, who key on vocabulary and structure. Do not optimise only for the lay heuristics.
- [JUDGE-BLIND] An LLM prompted to detect "AI-ness" missed about 1 in 5 AI texts and wrongly flagged about 1 in 10 human ones (GPT-4o with a guide). That is too noisy to block on, which fits MarketingOS's rule that judgment never blocks. Commercial detectors (Pangram) are stronger but are paid APIs.
- A burstiness or perplexity "gate" would punish exactly the plain, clear copy MarketingOS wants (Liang 2023). Use it as a soft signal at most.

### Gaps
- No study found on human detection of AI-written *marketing emails* specifically. Hunter's nine-email test is vendor-grade.
- No French-language human-detection study found. Antoun, Mouilleron, Sagot & Seddah 2023 (INRIA; [arXiv 2306.05871](https://arxiv.org/abs/2306.05871), not re-fetched) built French ChatGPT-detection datasets, but it tests detectors, not people.
- The Wikipedia page cites "a 2025 study" finding human detection no better than chance; I could not identify it.

## 3. The stylistic fingerprint of LLM writing (EN and FR): material for a deterministic style check

### Takeaway
The fingerprint is real and measurable, and it drifts with each model generation. It has six parts:
- excess "style" vocabulary, mostly verbs and adjectives;
- grammatical habits, such as present-participle clauses and nominalisations;
- structural templates: negative parallelism, triads, trailing "-ing" commentary, copula avoidance;
- formatting leaking in from markdown: em dashes, bold, Title Case, colon-before-list;
- collaborative and hedging boilerplate;
- generic-optimistic conclusions.

The em dash, the best-known tell of 2023–25, became model-specific in 2026: Claude kept it, GPT-5.x suppressed it, and the newest models reportedly drop it. Any list has to be versioned per model and measured, not frozen. French evidence is practitioner-grade only.

### Cited Findings
**Corpus studies of excess vocabulary**
- [STRONG for biomedical abstracts: observational, >15 M PubMed abstracts 2010–2024] Kobak et al., *Science Advances*, 2 July 2025, "Delving into LLM-assisted writing in biomedical publications through excess vocabulary". — [arXiv HTML v5](https://arxiv.org/html/2406.07016v5); [Science Advances, DOI 10.1126/sciadv.adt3813](https://www.science.org/doi/10.1126/sciadv.adt3813) [verified]
  - At least **13.5%** of 2024 abstracts were LLM-processed. This is a lower bound, revised up from "≥10%" in an earlier preprint. It exceeds 40% in some subcorpora: computation papers from China 0.41, against 0.07 for *Nature*, *Science* and *Cell*.
  - Top 2024 excess words by frequency ratio: "delves" (r = 28.0), "underscores" (13.8), "showcasing" (10.7). By frequency gap: "potential", "findings", "crucial".
  - Common marker set: "across", "additionally", "comprehensive", "crucial", "enhancing", "exhibited", "insights", "notably", "particularly", "within".
  - Of the 379 excess *style* words in 2024, 66% were verbs and 14% adjectives. Pre-LLM excess words were mostly nouns (79.2%), i.e. driven by content.
  - The code and monthly updates are in the GitHub repo berenslab/llm-excess-vocab.
  - Use: (a) Kobak's method, an excess-frequency ratio against a human baseline, is the template for a MarketingOS-specific list (see Inferences).
- [MODERATE] Liang et al., ICML 2024. 6.5–16.9% of peer-review text at major AI conferences was substantially LLM-modified, with surging adjectives such as "commendable", "meticulous" and "intricate". — [arXiv 2403.07183](https://arxiv.org/abs/2403.07183) [not re-fetched]
- [MODERATE: large observational preprint] Liang et al. 2025, "The Widespread Adoption of Large Language Model-Assisted Writing Across Society". Growth in adoption stabilised during 2024; the authors cannot say whether that is saturation or newer models being harder to detect. — [arXiv 2502.09747](https://arxiv.org/abs/2502.09747) [verified]

  Estimated LLM-assisted share of text by late 2024:

  | Text type | Share |
  |---|---|
  | US financial consumer complaints | ≈18% |
  | Corporate press releases | up to 24% |
  | Job postings at small firms | just under 10% (higher at younger firms) |
  | UN press releases | ≈14% |

- [MODERATE: peer-reviewed; parallel human/LLM corpora; Llama 3 variants, GPT-4o, GPT-4o mini] Reinhart et al., *PNAS* 2025, "Do LLMs write like humans? Variation in grammatical and rhetorical styles", using Biber's feature set. — [arXiv HTML](https://arxiv.org/html/2410.16107v2); [arXiv abstract](https://arxiv.org/abs/2410.16107) [verified]

  Rates in instruction-tuned models relative to human text:

  | Feature | Rate vs human |
  |---|---|
  | Present-participle clauses | 2–5× (GPT-4o 5.3×) |
  | "That"-clauses as subjects | 2.6× |
  | Nominalisations | 1.5–2× (GPT-4o 2.1×) |
  | Phrasal coordination | 1.9× |
  | Agentless passives | ≈0.5× |

  - GPT-4o overuses downtoners; Llama avoids them.
  - Some words appear at more than 100× the human rate in GPT-4o and 4o-mini: "camaraderie" (162/171), "tapestry" (155), "palpable" (145 in 4o-mini), "intricate" (119/129).
  - The differences are larger for instruction-tuned models than for base models and persist in bigger models: "LLMs struggle to match human stylistic variation."
  - Use: (a) participle-clause and nominalisation rates can be computed with a part-of-speech tagger (spaCy has English and French models), with no model call.
- [MODERATE] Juzek & Ward, COLING 2025, "Why Does ChatGPT 'Delve' So Much?". They studied 21 focal words ("delve", "intricate", "underscore", …) and found no evidence that architecture, algorithm choices or training data cause the overuse. The results are consistent with RLHF (learning from human feedback) playing a role. — [arXiv 2412.11385](https://arxiv.org/abs/2412.11385) [verified]
- [MODERATE] Sun et al., ICML 2025, "Idiosyncrasies in Large Language Models". A fine-tuned embedding classifier tells ChatGPT, Claude, Grok, Gemini and DeepSeek apart with **97.1%** accuracy. The signal lives in word-level distributions and semantic content, and persists when another LLM rewrites, translates or summarises the text. — [arXiv 2502.12150](https://arxiv.org/abs/2502.12150) [verified]
- [MODERATE: preprint] Paech et al. 2025, "Antislop". Some "slop" patterns occur more than **1,000×** more often in LLM output than in human text.
  - A backtracking sampler suppressed more than 8,000 patterns without quality loss; simple token banning breaks down around 2,000.
  - FTPO fine-tuning cut slop by about 90% and kept benchmark scores.
  - DPO suppressed less and degraded writing quality and lexical diversity.
  - Source: [arXiv 2510.15061](https://arxiv.org/abs/2510.15061) [verified]
- [MODERATE] Shaib et al., EMNLP 2024. Models produce part-of-speech "syntactic templates" more often than humans; about 76% of templates in model text occur in pretraining data, against about 35% for human text. — [arXiv 2407.00211](https://arxiv.org/abs/2407.00211) [not re-fetched]
- [MODERATE] Chakrabarty, Laban & Wu, CHI 2025, "Can AI writing be salvaged?". — [arXiv 2409.14509](https://arxiv.org/abs/2409.14509) [partly verified]
  - Professional writers edited 1,057 LLM-written paragraphs (the LAMP corpus) using a 7-category taxonomy of AI idiosyncrasies.
  - Two categories were confirmed this session: clichés and unnecessary exposition. Per my reading of the paper, the other five are purple prose, poor sentence structure, lack of specificity and detail, awkward word choice or phrasing, and tense inconsistency; these were not re-verified.
  - GPT-4o, Claude 3.5 Sonnet and Llama 3.1 70B showed common limitations, and none wrote better than the others.
  - Experts preferred expert edits over automatic ones.

**Editor compilation: the most operational list**
- [WEAK-FOLKLORE: editor compilation drawn from thousands of AI drafts; descriptive, not proof] Wikipedia, "Signs of AI writing" (WikiProject AI Cleanup), as of October 2026. — [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) [verified]
  - **Vocabulary**
    - Core list: "Additionally" (especially sentence-initial), "align with", "boasts" (meaning "has"), "bolstered", "crucial", "deep dive", "delve", "emphasizing", "enduring", "enhance", "fostering", "garner", "highlight" (as a verb), "interplay", "intricate/intricacies", "landscape" (abstract), "meticulous/meticulously", "pivotal", "robust", "showcase", "tapestry" (abstract), "testament", "underscore" (as a verb), "valuable", "vibrant".
    - By era: "key" (GPT-4, 2023 to mid-2024); "highlighting", "showcasing" (GPT-4o, mid-2024 to mid-2025); and, from mid-2026 (the "GPT-6" era), "challenge", "clearer", "dependable", "echoed", "foster", "leverage", "matters", "multifaceted", "practical", "prioritize", "quietly", "steady", "universally".
    - Caveats: synonyms of an overused word are not themselves tells. The strongest tell is many of these words arriving together.
  - **Significance inflation:** "stands/serves as", "is a testament/reminder", "a crucial/pivotal/vital/significant/key role/moment", "underscores/highlights its importance/significance", "reflects broader", "setting the stage for", "marking/shaping the", "key turning point", "evolving landscape", "focal point", "indelible mark", "deeply rooted".
  - **Superficial analysis:** trailing present-participle phrases at the end of a sentence, such as "…, highlighting/underscoring/emphasizing …", "ensuring", "reflecting/symbolizing", "contributing to", "cultivating/fostering", "encompassing", "enhancing", "valuable insights", "align/resonate with".
  - **Promotional register:** "boasts a", "vibrant", "rich", "profound", "enhancing", "showcasing", "exemplifies", "commitment to", "natural beauty", "nestled", "in the heart of", "groundbreaking", "renowned", "featuring", "diverse array"; a travel-guide or press-release tone. Older models were blatantly positive; newer ones are subtler and avoid superlatives like "the best".
  - **Vague attribution:** "Industry reports", "Observers have cited", "Experts argue", "Some critics argue", "several sources/publications".
  - **Copula avoidance:** "serves as", "stands as", "marks", "functions as", "operates as", "represents", "boasts/features/maintains/offers" where "is" or "has" would do.
  - **Negative parallelism:** "Not just X, but also Y", "Not only … but …", "It is not just …, it's …", "Not X, but Y", "It's not …, it's …", "no …, no …, just …". Recent output increasingly reverses the form ("Y rather than X"), including mid-2026 "corrective framing" disclaimers.
  - **Rule of three:** "adjective, adjective, adjective" or "short phrase, short phrase, and short phrase", used to make superficial analysis look comprehensive. It is a stronger sign where nobody would normally bother with such a flourish.
  - **Outline-style conclusions:** "Despite its … faces several challenges", "Despite these challenges", "Future Outlook".
  - **Style:**
    - Title Case headings; mechanical bold, often in "key takeaways" fashion.
    - Inline-header lists (bullet, bold header, colon); emoji before headings or bullets, now rarer.
    - Curly quotes: ChatGPT and DeepSeek typically use them; Gemini and Claude typically do not. Word, macOS and iOS also insert them, so they prove nothing on their own.
  - **Phrases addressed to the user:** "I hope this helps", "Certainly!", "let me know"; "While specific details are limited/scarce", "based on available information"; "it's important to note" (typical of about 2023); placeholders such as "[Describe …]" or "2025-XX-XX"; "utm_source=chatgpt.com".
  - **Historical indicators (era-bound):** knowledge-cutoff statements (2022–23); "In summary", "In conclusion", "Overall" (2023); "as an AI language model" (2024 and earlier); "elegant variation", i.e. excessive synonym switching (the repetition-penalty era); em-dash overuse (2022 to September 2026).
  - **Indicators the page says do not work:** perfect grammar; mixed registers; "bland" or "robotic" prose; "fancy" or formal prose in general; isolated transition words ("Additionally", "Consequently", "Notably"); unsourced content.
  - **Signs of *human* writing:** simple "is/has"; plain words ("wrote", not "authored"); superlatives and definitive statements ("one of the best", "was the first"); qualifiers and intensifiers ("very", "perhaps", "tends to"); wordy constructions ("as a result of", "in order to", "the fact that").

**Em dashes: a finding revised in 2026**
- [MODERATE: single-author preprint; small samples of 10 topics per model and 8 human essays] Freeburg, "The Last Fingerprint: How Markdown Training Shapes LLM Prose" (arXiv, March 2026). — [arXiv 2603.27006](https://arxiv.org/html/2603.27006v1) [verified]

  Em dashes per 1,000 words, unconstrained vs. told to write "flowing prose paragraphs only":

  | Model | Unconstrained | Prose-only instruction |
  |---|---|---|
  | GPT-4.1 | 10.62 | 9.10 |
  | Claude Opus 4.6 | 9.09 | 0.19 |
  | Claude Sonnet 4 | 8.29 | 1.31 |
  | Claude Haiku 3.5 | 7.51 | 0.18 |
  | DeepSeek V3 | 6.95 | 5.41 |
  | GPT-4o | 4.12 | 2.68 |
  | Gemini 2.5 Pro | 3.53 | 0.00 |
  | GPT-5.4 | 1.43 | 0.29 |
  | Llama 3.x | 0.00 | 0.00 |
  | Human baseline (8 published essays) | mean 3.23; median 3.83; range 0.33–17.12 | — |

  - An explicit "Do not use em dashes" took GPT-4.1 from 11.51 to 3.86, DeepSeek V3 from 8.66 to 1.57, and Claude Opus 4.6 to 0.00.
  - The author reads this as markdown structure leaking into prose. "Colon-before-list" patterns and formulaic transitions are named as related tics.
- [WEAK-FOLKLORE: journalism] *The Economist* (July 2026) had four models rewrite archived articles. Only Claude used em dashes more than the human writers; ChatGPT used them less than anyone, humans included. Wikipedia adds three points:
  - GPT-5.1 was reportedly tuned to suppress em dashes.
  - Since September 2026 some of the latest models avoid them entirely, and the resulting overuse of commas and full stops "has become its own sign".
  - AI em dashes tend to be surrounded by spaces.
  - Sources: [Fast Company on the Economist report](https://www.fastcompany.com/91584243/how-to-identify-ai-generated-writing-viral-report-has-surprising-new-clues-economist) (page returned 403; content via search summary); [Wikipedia](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) [verified]
- [WEAK-FOLKLORE: secondary reports of Graphite/Arena measurements, not verified] Claude Opus 5.5 reportedly uses about 99% fewer em dashes than Opus 5 (0.8 vs 15.2 per 1,000 words) while still showing many other AI patterns. — reported in secondary coverage; search results included [Inc.](https://www.inc.com/chris-morris/wondering-if-ai-wrote-that-document-these-are-the-surprising-new-clues/91413963) and [Medium](https://medium.com/illumination/are-em-dashes-a-sign-of-ai-writing-what-the-2026-evidence-says-6bc3fae77c11) [search summary only]

**French**
- [WEAK-FOLKLORE] French practitioner and teaching sources.
  - Long ChatGPT texts repeat adjectives such as « crucial », « essentiel », « fondamental » and connectors such as « par ailleurs », « de plus », « néanmoins » (Digitad).
  - Stock openers such as « Dans un monde où… » (Université de Nantes teaching sheet, quoted in a search snippet; the PDF now returns 404).
  - A vendor list sorts French "AI words" into five families, including empty transitions (« en outre », « néanmoins ») and vague quantifiers (« divers », « nombreux »). It also claims a 2024 Académie française warning, which I did not verify.
  - Sources: [Digitad](https://digitad.ca/comment-savoir-texte-genere-par-chatgpt/); [Blog du Modérateur](https://www.blogdumoderateur.com/detecter-texte-ia-chatgpt-outils-methodes/); [gpt-watermark-remover (vendor)](https://gpt-watermark-remover.com/fr/blog/mots-typiques-ia-eviter) [via search summary]

### Inferences
**Proposed deterministic style check**, ordered by strength of evidence. Every item is a regex or part-of-speech count; none spends quota.
1. **Excess-vocabulary density (EN).** Count the sourced words per 100 words and flag on *density or co-occurrence*, not on single hits. Wikipedia: an isolated transition word is not a tell; many of these words together is the strongest one. Sourced starter list, by provenance (K = Kobak, W = Wikipedia, R = Russell, Re = Reinhart, J = Juzek & Ward, L = Liang 2024):
   - Verbs: delve (K, W, R, J), underscore (K, W, J), showcase (K, W), highlight as a verb (W), foster (W), enhance (K, W), bolster (W), garner (W), align/resonate with (W), exemplify (W), boast (W), leverage, prioritize, echo (W, mid-2026 era).
   - Adjectives: crucial (K, W, R), pivotal (W), intricate (Re, J, W, L), meticulous (W, L), commendable (L), robust (W), vibrant (W, R), comprehensive (K), valuable (W), enduring (W), multifaceted (W), palpable (Re), groundbreaking, renowned, profound, rich (W, promotional).
   - Nouns: testament (W, R), tapestry (W, Re), landscape used abstractly (W), interplay (W), camaraderie (Re), insights (K), deep dive (W).
   - Adverbs and connectors: additionally sentence-initially (K, W), notably, particularly (K), significantly (R), quietly, universally (W, mid-2026 era).
   - Phrases: "is a testament to", "plays a crucial/pivotal role", "setting the stage for", "in the heart of", "nestled", "diverse array", "commitment to" (W).
2. **Structural regexes:**
   - negative parallelism and corrective framing ("not just/not only … but", "it's not … it's", "isn't … it's", "not X, but Y", "rather than");
   - triads per paragraph ("A, B, and C");
   - a sentence-final participle clause (", ensuring/highlighting/underscoring/reflecting/fostering …");
   - copula avoidance ("serves as", "stands as", "boasts", "features a", "offers a");
   - vague attribution ("experts say/argue", "studies show", "industry reports");
   - outline-style conclusions ("despite these challenges");
   - phrases addressed to the user ("I hope this helps", "let me know if", "it's important to note", "based on available information").
3. **Formatting leaking into an email body:** bold, headers, bullets with bold inline headers, emoji bullets, Title Case subject lines or headings, colon-before-list.
4. **Em-dash rate per 1,000 words, versioned by model.** Claude up to Opus 4.6 / Sonnet 4 produced about 8–9 per 1,000 against about 3 in human essays. One explicit instruction removes them in Claude, and the newest models may already be near zero. The count is cheap insurance, but over-correcting into chains of commas and full stops is the next tell. Use a writer instruction (b) plus a soft count (a), not a block. French has legitimate dash uses (dialogue, incises), so the count needs French-specific rules.
5. **Grammar rates with a POS tagger:** participle clauses (2–5×), nominalisations (1.5–2×), phrasal coordination (1.9×), few agentless passives. Thresholds must be calibrated on MarketingOS's human anchors (`golden.py`); no published thresholds exist for email.
6. **Default-name check:** names such as "Emily Carter" and "Sarah Thompson" in examples or testimonials (Russell). The quote-licensing gate already blocks unlicensed testimonials; a name check catches placeholder personas.
7. **MarketingOS's own excess-vocabulary list.** Compare word and phrase frequencies in its eval drafts, per model and per model version, against its human anchors and the user's own material, using Kobak's excess ratio. This is free, because the drafts already exist under `eval/`. It is also *necessary*: the tell set changes every model generation (Wikipedia's era lists, the 2026 em-dash shift), and fingerprints are model-specific (Sun et al.).

**Other applications**
- (b) Writer prompt: say "is" and "has"; no "not X but Y" reframes; no sentence-final "-ing" commentary; no list of three unless there are exactly three things; no em dashes; use contractions; name concrete things.
  - A prompt alone does not remove tells reliably. Freeburg's "no markdown" instruction left GPT-4.1's em dashes intact, and Antislop needed enforcement to suppress patterns. Keep the code check as the backstop.
- (c) Critic: "Could this sentence appear unchanged in a competitor's email?" (originality was 23.7% of expert cues). "Does it over-explain?" (clarity, 19.5%). "Is the close generic and optimistic?" (13.1%).
- [JUDGE-BLIND] LLM judges prefer low-perplexity, LLM-like text (Section 6). MarketingOS's own `judge_bench` found `stock_phrase_open` caught only 2 of 6, which matches the literature: tells belong in code.
- **Rewriting does not remove the fingerprint.** It survives rewriting by a different LLM (Sun et al.), so "launder Claude through GPT" is not a remedy.

**French hypotheses** (unsourced; validate on French drafts before use)
- English tells probably have French calques:
  - « plonger dans » or « explorer » (delve); « témoigne de » or « un témoignage de » (testament); an abstract « paysage » (landscape); « dynamique » or « vibrant » (vibrant);
  - « crucial », « essentiel », « incontournable », « véritable »;
  - « au cœur de » (in the heart of); « niché » (nestled); « souligner » or « mettre en lumière » (underscore/highlight); « favoriser » (foster); « renforcer » (bolster); « robuste »; « méticuleux »;
  - « Il ne s'agit pas seulement de X, mais de Y » or « Ce n'est pas X, c'est Y » (negative parallelism); « Non seulement… mais aussi »;
  - « Que vous soyez X ou Y »; « En somme », « En résumé »; « Il est important de noter que »; « N'hésitez pas à… ».
- French-specific typographic tells, also a hypothesis: English typography leaking into French output. Examples: Title Case headings or subject lines (« Les Avantages Du Programme »); "…" instead of « … »; missing non-breaking spaces before « : ; ! ? »; an English-style spaced em dash used for asides.
- These can be checked deterministically against French typographic norms, which is cheaper and safer than any French lexicon. Agarwal et al. 2025 (Section 5: AI suggestions pull writing toward Western styles) supports the expectation that French output inherits anglophone rhetoric.

### Gaps
- No peer-reviewed corpus study of excess vocabulary in *French* LLM output found; the search budget ran out before a targeted search. The French list above is practitioner-grade or hypothesis. I could not establish whether French Wikipedia keeps a counterpart to "Signs of AI writing".
- No study measured tells in marketing emails specifically; the corpora are abstracts, peer reviews, Wikipedia, essays and press releases.
- No published per-1,000-word thresholds exist for email copy, and the 3.23 em-dash human baseline comes from just 8 essays.
- Evidence that uniform sentence length (low "burstiness") is a tell readers notice was not found beyond Reinhart's general finding on stylistic variation. Wikipedia lists "bland/robotic" prose as an ineffective indicator.
- Marketing-buzzword lists ("I hope this email finds you well", "In today's fast-paced world", "game-changer", "unlock", "elevate", "seamless", "streamline") had no research source in this session. Treat them as folklore until measured on MarketingOS's own drafts.
- Whether "delve" and similar words declined after public attention in 2024–26 (Kobak's July 2025 update may show it) was not checked.
- Claude's current fingerprint (Opus 5.5 / fable5 era), beyond em dashes, is not documented in any source found.

## 4. Persuasiveness of LLM-written and LLM-personalised messages

### Takeaway
Single LLM-written messages persuade about as well as human-written ones, and conversational LLMs can exceed humans. The strongest, best-measured lever is **information density**: many specific, checkable claims. Personalisation and model size matter much less, and the methods that raise persuasion tend to lower accuracy. Personalisation effects are small and inconsistent outside live dialogue with personal data, and AI labels do not blunt the persuasion of the content.

### Cited Findings
- [STRONG: 3 experiments, N = 76,977, 19 LLMs, 707 issues, 466,769 claims fact-checked] Hackenburg et al., "The levers of political persuasion with conversational artificial intelligence", *Science* (Dec 2025).
  - Post-training and prompting raised persuasiveness by "as much as 51% and 27%" respectively. Persuasive power is "likely to stem more from" these methods than from personalisation or model scale.
  - The most persuasive systems packed in many fact-checkable claims. Roughly half of the explainable variation in persuasion across models traced to this information density.
  - Where methods raised persuasiveness, they "systematically decreased factual accuracy".
  - Sources: [arXiv 2507.13919](https://arxiv.org/abs/2507.13919) [verified abstract]; [Oxford news](https://www.ox.ac.uk/news/2025-12-11-study-reveals-how-conversational-ai-can-exert-influence-over-political-beliefs); [LSE record](https://researchonline.lse.ac.uk/id/eprint/130605) [via search summary]
  - Use: (b) make claims specific and checkable from the Evidence Ledger. (a) count licensed claims per email (`substantiation.py` already measures this spend). The accuracy trade-off is exactly why the gates must license every claim.
- [STRONG: N = 25,982, 24 LLMs] Hackenburg et al., *PNAS* 2025, "Scaling language model size yields diminishing returns for persuasion". Persuasiveness follows a log scaling law with sharply diminishing returns: frontier models were barely more persuasive than models an order of magnitude smaller, and task completion (coherence, staying on topic) explained the gap. — [PNAS](https://www.pnas.org/doi/10.1073/pnas.2413443122) [not re-fetched]
- [STRONG: N = 8,587] Hackenburg & Margetts, *PNAS* 2024. GPT-4 political messages were persuasive, but microtargeted versions tailored to individual attributes were not significantly more persuasive than generic ones. — [PNAS](https://www.pnas.org/doi/10.1073/pnas.2403116121) [not re-fetched]
- [MODERATE: preregistered; N = 820 in the preprint] Salvi, Horta Ribeiro, Gallotti & West, *Nature Human Behaviour* 2025, "On the conversational persuasiveness of GPT-4". In short multi-round debates, GPT-4 given the opponent's basic sociodemographic data had **81.7% higher odds** of increasing agreement than human opponents (p < 0.01). Without that data, GPT-4's edge was smaller and not significant (p = 0.31). — [arXiv 2403.14380](https://arxiv.org/abs/2403.14380) [verified preprint figures]; [Nature Human Behaviour](https://www.nature.com/articles/s41562-025-02194-6) (published version; paywall redirect, final figures not checked)
- [MODERATE: 4 studies, N ≈ 1,788] Matz et al., *Scientific Reports* 2024, "The potential of generative AI for personalized persuasion at scale". ChatGPT messages tailored to recipients' psychological profiles (e.g. personality) beat non-tailored ones across domains including consumer products and political appeals. The effects were small. — [Scientific Reports](https://www.nature.com/articles/s41598-024-53755-0) [not re-fetched]
- [MODERATE: N = 3,832, 28 topics, 56 claims; lab publication, not peer-reviewed] Anthropic 2024, "Measuring the persuasiveness of language models". — [Anthropic](https://www.anthropic.com/research/measuring-model-persuasiveness) [verified]
  - Claude 3 Opus's single-turn arguments of about 250 words were not statistically different from human-written ones.
  - Each new model generation was rated more persuasive than the last.
  - The "Deceptive" prompt, free to invent facts, sources and statistics, was the most persuasive. Logical reasoning with evidence beat rhetorical or emotional appeals.
  - Stated limits: single-turn, less-polarised issues, short-term measurement. Also: "automated persuasiveness scoring did not correlate well with human judgments".
- [STRONG: preregistered RCT, N ≈ 2,190] Costello, Pennycook & Rand, *Science* 2024. Personalised GPT-4 dialogues that presented tailored counter-evidence cut conspiracy belief by about 20%, with the effect lasting at least two months. — [Science](https://doi.org/10.1126/science.adq1814) [not re-fetched]
- [MODERATE] Bai, Voelkel, Eichstaedt & Willer (preprint 2023, later published). GPT-3 messages persuaded on policy issues about as much as human-written ones. Readers rated the AI messages more logical and informed, less angry, *less unique*, and less likely to use storytelling. — [OSF preprint](https://osf.io/stakv/) [not re-fetched; publication venue not verified]
- [MODERATE] Karinshak, Liu, Park & Hancock, CSCW 2023. GPT-3 pro-vaccination messages were rated more effective, with stronger arguments, than messages written by the CDC. — [ACM DL](https://doi.org/10.1145/3579592) [not re-fetched]
- [MODERATE: N = 101] Heiding et al. 2024, the closest email-format evidence. Fully AI-automated spear-phishing emails reached a 54% click-through rate, the same as emails written by human experts (54%), against 12% for a generic control. AI with a human in the loop reached about 56%. — [arXiv 2412.00586](https://arxiv.org/abs/2412.00586) [not re-fetched]
- [MODERATE: preprint] Schoenegger et al. 2025. Claude 3.5 Sonnet out-persuaded incentivised human persuaders in an interactive quiz, both toward right and toward wrong answers. — [arXiv 2505.09662](https://arxiv.org/abs/2505.09662) [not re-fetched]
- [MODERATE] Gallegos et al. 2026 (Section 1): AI labels do not reduce persuasion. — [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12887897/)

### Inferences
- For a one-to-many email with no recipient data, the best-supported lever is the one MarketingOS is already built around: dense, specific, verifiable claims. The personalisation research gives little reason to spend quota on per-persona variants without real recipient data (Hackenburg & Margetts; Levers; Matz's small effects). That fits the "audience intelligence" experiments' framing.
- Two results point the same way: the Levers persuasion–accuracy trade-off, and Anthropic's "Deceptive" prompt being the most persuasive. An optimiser that rewards a judge's persuasion score will drift toward invented specifics. MarketingOS's licensing gates are the right counterweight and should never be relaxed for a higher judged "pull".
- Model size gives diminishing returns, so the writer's tier is not where persuasion comes from; prompting and evidence are. This argues for spending quota on evidence rather than on a bigger writer model.
- Bai's finding that AI messages read as "less unique, less narrative" links persuasion to homogenisation (Section 5): AI copy can persuade and still be indistinguishable from a competitor's.
- (c) Critic criterion: "How many distinct, checkable facts does this email give the reader, and does each one serve the ask?"
- [JUDGE-BLIND] Anthropic found automated persuasiveness scores did not track human judgments. A judge's persuasion score is not a measurement.

### Gaps
- No peer-reviewed field experiment found comparing LLM-written and human-written *marketing emails* on real opens, clicks or replies; the search budget ran out before a targeted search. Vendor subject-line tool claims were not assessed.
- OpenAI's and Google DeepMind's persuasion work was not re-verified this session: OpenAI system-card ChangeMyView evaluations, OpenAI's April 2025 Preparedness Framework change that dropped persuasion as a tracked category, and DeepMind's "Evaluating Frontier Models for Dangerous Capabilities" ([arXiv 2403.13793](https://arxiv.org/abs/2403.13793)).
- Lin et al. (*Nature*, Dec 2025), on AI dialogues shifting voter preferences, was not verified.
- The final published Salvi et al. figures (reported elsewhere as N = 900) were not checked.
- All of these studies are political, health or security persuasion. Transfer to commercial email (low involvement, skimming, an existing sender relationship) is untested.
- Only Costello et al. measured durability over weeks.

## 5. Homogenisation and differentiation

### Takeaway
AI assistance raises the average quality of each output and makes outputs more alike. Different LLMs converge on the same answers, so mixing Claude and GPT does not buy diversity, and up to a quarter of corporate press releases were already AI-assisted by late 2024. Default model output is therefore category-typical by construction. Distinctiveness has to come from inputs only the sender has: their own facts, their customers' words, unusual but true details. It cannot come from the model.

### Cited Findings
- [MODERATE: N = 293 writers, 600 evaluators] Doshi & Hauser, *Science Advances* 2024, "Generative AI enhances individual creativity but reduces the collective diversity of novel content". — [PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC11244532/) [verified]

  Gains from access to GPT-4 story ideas, against writers with no AI:

  | Condition | Novelty | Usefulness |
  |---|---|---|
  | 1 AI idea | +5.4% | +3.7% |
  | 5 AI ideas | +8.1% | +9.0% |
  | Least creative writers, 5 AI ideas | +10.7% | +11.5% |

  - The stories became more similar to each other. The increase equals 10.7% (1 idea) and 8.9% (5 ideas) of the similarity range among human-only stories.
  - The stories were also about 5% more similar to the AI ideas themselves.
- [MODERATE] Padmakumar & He, ICLR 2024, "Does Writing with Language Models Reduce Content Diversity?". Writing with InstructGPT (but not with base GPT-3) made essays by different authors more alike, mainly through the text the model contributed. — [arXiv 2309.05196](https://arxiv.org/abs/2309.05196) [not re-fetched]
- [MODERATE] Anderson, Shah & Kreminski, C&C 2024. ChatGPT-assisted ideation produced ideas that were less semantically distinct across users, and users felt less responsible for their ideas. — [arXiv 2402.01536](https://arxiv.org/abs/2402.01536) [not re-fetched]
- [MODERATE: preprint] Wenger & Kenett 2025, "We're Different, We're the Same: Creative Homogeneity Across LLMs". LLM responses to standardised creativity tests are "much more similar to other LLM responses than human responses are to each other", even after controlling for response structure. — [arXiv 2501.19361](https://arxiv.org/abs/2501.19361) [verified]
- [MODERATE: NeurIPS 2025 Datasets & Benchmarks oral] Jiang et al., "Artificial Hivemind: The Open-Ended Homogeneity of Language Models (and Beyond)". On 26K real open-ended queries (31,250 human annotations, 25 per example), models showed both intra-model repetition and inter-model homogeneity ("different models produce strikingly similar outputs"). LMs, reward models and LM judges are "less well calibrated" to humans where annotators' preferences are idiosyncratic. — [arXiv 2510.22954](https://arxiv.org/abs/2510.22954) [verified]
- [MODERATE] Kirk et al., ICLR 2024. RLHF reduces output diversity compared with supervised fine-tuning. — [arXiv 2310.06452](https://arxiv.org/abs/2310.06452) [not re-fetched]
- [MODERATE] Agarwal, Naaman & Vashistha, CHI 2025, "AI Suggestions Homogenize Writing Toward Western Styles and Diminish Cultural Nuances". AI suggestions pushed Indian participants' writing toward Western styles. — [arXiv 2409.11360](https://arxiv.org/abs/2409.11360) [not re-fetched]
- [MODERATE: preprint] Zhang et al. 2025, "Verbalized Sampling". The authors trace mode collapse to a bias toward typical answers in human preference data. Asking the model for several responses with their probabilities raised creative-writing diversity by about 1.6–2.1×, without retraining. — [arXiv 2510.01171](https://arxiv.org/abs/2510.01171) [not re-fetched]
- [MODERATE] Liang et al. 2025: up to 24% of corporate press releases were LLM-assisted by late 2024 (Section 3). — [arXiv 2502.09747](https://arxiv.org/abs/2502.09747) [verified]
- [MODERATE] Russell et al. 2025: "originality" (AI is safe and holds no surprises) made up 23.7% of expert detection reasoning, and generic introductions 7.3%. — [arXiv](https://arxiv.org/html/2501.15654v1) [verified]
- [MODERATE] Bai et al.: AI messages were perceived as less unique and less narrative (Section 4). — [OSF](https://osf.io/stakv/) [not re-fetched]

### Inferences
- **Ensembles do not diversify.** A Claude writer with a GPT critic, or a mix of model families, does not create diversity (Wenger & Kenett; Hivemind), and the fingerprint survives cross-model rewriting (Sun et al.). Distinctiveness must be injected through the inputs.
- **The model's first idea is the category's first idea.** That makes MarketingOS's closed list of competitor argument frames in `sameness.py` the right shape.
  - (a) A cheap extension: measure the n-gram overlap between a draft and a stored set of the model's own "unbranded" defaults for the same brief type. High overlap means any competitor could send this email. N-gram overlap needs no model call.
- (b) Writer requirements:
  - at least N facts from the ledger that a competitor could not truthfully write (proper nouns, figures, named customers, places, processes);
  - lift customers' own phrasing from the user's material (voice-of-customer) instead of paraphrasing it into model vocabulary.
- (b) Escaping the default without fine-tuning: a verbalized-sampling-style prompt ("give five openings with probabilities; pick a low-probability one that is still true"). It costs tokens, not extra calls.
- (c) Critic swap test: "Could a competitor send this with only the brand name changed?"
- [JUDGE-BLIND] Hivemind shows judges are worst calibrated exactly where human preferences are idiosyncratic. An LLM judge will tend to reward the typical answer, which is the homogenised one.
- **Marketing-theory link** (not sourced this session): the Ehrenberg-Bass "distinctive brand assets" view (Romaniuk) separates *distinctiveness*, being recognisable as this brand, from *differentiation*. Homogenised AI copy wears away the verbal side of brand assets.
- **French.** Agarwal's Western-style homogenisation suggests French drafts may read as translated American copy. A French typography and rhetoric check therefore doubles as a distinctiveness check.

### Gaps
- No study found on homogenisation of marketing emails or ad copy specifically, or on whether AI-induced sameness lowers response. Wiles & Horton's field experiments on AI-written job posts may bear on this; not verified.
- Ehrenberg-Bass / Romaniuk distinctive-asset research was not fetched. Practitioner methods (voice-of-customer mining, review mining) are unsourced: WEAK-FOLKLORE at best.
- Meincke, Nave & Terwiesch ("ChatGPT decreases idea diversity in brainstorming"; prompt strategies partly restore diversity) was not verified.
- Whether homogenisation is stronger in French than in English is untested.

## 6. LLM-as-judge for copy: biases and predictive validity

### Takeaway
LLM judges have well-documented biases: position, length and verbosity, and preference for their own outputs. They prefer low-perplexity (familiar) text, and LLM-written over human-written text. Frontier LLMs barely beat random at judging writing quality, and an LLM's persuasiveness scores did not track human judgments. No evidence was found that LLM ratings of emails or ads predict real A/B outcomes. LLM judges are defensible for comprehension and for rewrite suggestions; they are not a measurement of quality or of response.

### Cited Findings
- [STRONG for the existence of these biases; widely replicated] Zheng et al., NeurIPS 2023 (MT-Bench / Chatbot Arena). LLM judges show position bias, verbosity bias and self-enhancement bias. On chat-assistant tasks, GPT-4's agreement with human preferences was above 80%, about the level of agreement between humans. — [arXiv 2306.05685](https://arxiv.org/abs/2306.05685) [not re-fetched]
- [MODERATE] Wang et al. 2023, "Large Language Models are not Fair Evaluators". Swapping the order of the candidates changes verdicts. — [arXiv 2305.17926](https://arxiv.org/abs/2305.17926) [not re-fetched]
- [MODERATE] Dubois et al. 2024, "Length-Controlled AlpacaEval". Automatic evaluators favour longer outputs; controlling for length improved agreement with human rankings. — [arXiv 2404.04475](https://arxiv.org/abs/2404.04475) [not re-fetched]
- [MODERATE] Panickssery, Bowman & Feng, NeurIPS 2024. LLM evaluators recognise their own generations and favour them, and self-recognition correlates linearly with self-preference. — [arXiv 2404.13076](https://arxiv.org/abs/2404.13076) [not re-fetched]
- [MODERATE] Wataoka et al. 2024. LLM judges (notably GPT-4) rate lower-perplexity outputs higher than human evaluators do, whether or not they wrote them. "Self-preference" is therefore largely a preference for the familiar. — [arXiv 2410.21819](https://arxiv.org/abs/2410.21819) [not re-fetched]
- [MODERATE] Laurito et al., *PNAS* 2025 (vol. 122, no. 31, e2415697122), "AI–AI bias: large language models favor communications generated by large language models". In binary choices designed like employment-discrimination studies, GPT-3.5, GPT-4 and open-weight models consistently preferred items (consumer products, academic papers, films) described by an LLM over the same items described by a human. — [arXiv 2407.12856](https://arxiv.org/abs/2407.12856) [verified abstract]
- [MODERATE] Feuer et al., ICLR 2025, "Style Outweighs Substance". LLM-judge preferences did not correlate with concrete measures of safety, world knowledge or instruction following; judges implicitly put style above factuality. — [arXiv 2409.15268](https://arxiv.org/abs/2409.15268) [not re-fetched]
- [MODERATE] Chakrabarty, Laban & Wu 2025, "AI-Slop to AI-Polish?". — [arXiv 2504.07532](https://arxiv.org/abs/2504.07532) [verified]
  - The Writing Quality benchmark holds 4,729 judgments consolidated from five preference datasets. On it, most strong baselines, "including state-of-the-art LLMs that excel at reasoning tasks, barely outperform random baselines".
  - A reward model trained on expert edits (WQRM) reached 74%.
  - Nine experienced writers preferred WQRM-selected texts 66% of the time overall, and 72.2% when the reward gap exceeded one point.
- [MODERATE] Chakrabarty et al., CHI 2024, "Art or Artifice?". LLM-written stories passed 3–10× fewer of the Torrance-derived creativity tests than professional stories, and LLMs used as assessors did not correlate positively with expert assessments. — [arXiv 2309.14556](https://arxiv.org/abs/2309.14556) [not re-fetched]
- [MODERATE] Anthropic 2024: "automated persuasiveness scoring did not correlate well with human judgments". — [Anthropic](https://www.anthropic.com/research/measuring-model-persuasiveness) [verified]
- [MODERATE] Jiang et al. 2025 (Hivemind): LM judges and reward models are less well calibrated to humans where preferences are idiosyncratic. — [arXiv 2510.22954](https://arxiv.org/abs/2510.22954) [verified]
- [MODERATE] Russell et al. 2025: GPT-4o as a prompted AI-text detector reached 78.0% TPR with a 10.7% false-positive rate. — [arXiv](https://arxiv.org/html/2501.15654v1) [verified]
- **Synthetic respondents** [MODERATE each]
  - Argyle et al., *Political Analysis* 2023: GPT-3 "silicon samples", conditioned on demographics, reproduced subgroup-level attitude distributions. — [Political Analysis](https://doi.org/10.1017/pan.2023.2) [not re-fetched]
  - Bisbee et al., *Political Analysis* 2024: ChatGPT synthetic survey answers had too little variance, were sensitive to prompt wording, and changed over time. — [Political Analysis](https://doi.org/10.1017/pan.2024.5) [not re-fetched]

### Inferences
- **MarketingOS's own bench matches the literature.** `judge_bench` found the judge "a content instrument and measurably poor on form": `stock_phrase_open` caught 2 of 6, and the judge twice preferred the wall of text. Verbosity bias, familiarity (low-perplexity) preference and AI–AI bias predict exactly that. Running the gates before the duel and never letting the judge overrule them is the posture this literature supports.
- **[JUDGE-BLIND] What the cold reader and critic are likely to miss or mis-score:**
  1. AI vocabulary and templates — it prefers them (Wataoka, Laurito).
  2. Length and walls of text (verbosity bias).
  3. Generic polish against specific roughness (style over substance, Feuer).
  4. Writing quality in general (near random on the Writing Quality benchmark).
  5. Persuasiveness (no correlation with humans, Anthropic).
  6. Idiosyncratic human taste (Hivemind).
  7. The disgust readers feel at AI authorship (Section 1); the judge has no mechanism to feel it.
  8. Self-preference when the judge model is the writer model (Panickssery). Prefer a different model family for the cold read, while remembering that cross-family judges still share the hivemind (Wenger & Kenett; Jiang).
- **Where LLM judgment is more defensible.** Comprehension ("could you say what is being sold?") is closer to reading comprehension than to taste, which fits `BlindRead.understood` being the one judgment that vetoes. No study was found validating an LLM reader's comprehension as a proxy for human comprehension of marketing copy.
- **Pairwise duels.** Randomise and swap candidate order, and length-match where possible, against position and length bias. Report swap-consistency as a reliability statistic. Swapping doubles the calls, so do it in benches, not in production runs.
- **Trained judge vs. prompted judge.** A trained writing-quality model (WQRM) beats prompted LLMs, but MarketingOS has no fine-tuning budget. The nearest free analogue is deterministic proxies for the expert-edit categories: clichés, unnecessary exposition, lack of specificity.

### Gaps
- No study found testing whether LLM ratings of emails, ads or subject lines predict human A/B outcomes (for example, studies on the Upworthy headline archive); the search budget was exhausted. This is the key open question for MarketingOS's duel against a human-written email.
- No study found on LLM judges of *French* copy.
- Synthetic-respondent studies on marketing research (Brand, Israeli & Ngwe, "Using GPT for Market Research"; the PyMC Labs / Colgate purchase-intent work) were not verified.
