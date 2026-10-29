# Audience differences in how marketing messages work: what works differently for whom (evidence-graded)

How to read these notes. Each finding has a grade. **[STRONG]** means a meta-analysis, a replication or a large field experiment or RCT. **[MODERATE]** means a single peer-reviewed study, or a consistent dataset whose method is disclosed. **[WEAK-FOLKLORE]** means practitioner opinion, a stereotype, or a result nobody has replicated. Each finding is also tagged with two fields:
- *Segment*: can the system act on this difference using only an audience-segment description, with no individual data?
- *Apply*: how MarketingOS could use it.
  - (a) a deterministic code check
  - (b) an instruction in the strategist or writer prompt
  - (c) a criterion for a cold reader reading as a member of the audience
  - (d) only measurable with real send data

**†** means the source is cited from the researcher's prior knowledge, with a DOI link, and was **not re-fetched in this session**. The shared web-search budget ran out partway through the research. Use the DOI as a pointer, and check numbers before quoting them. Every finding without † was read in this session, in the source itself or its abstract or an official summary.

## 1. Personality-tailored persuasion (Matz 2017, Hirsh 2012, critiques, Matz 2024 LLM). How large are the effects, and can tailoring be inferred from an audience description?

### Takeaway
Matching a message to a personality trait does raise persuasion. Across 702 experiments on motivational matching the average effect is about r = .20. LLM-written ads aimed at one trait won in 61% of tests, with small effects. In the field, though, the gains are tiny in absolute terms and the evidence is contested. And in large RCTs, giving an LLM individual demographic data added essentially nothing: +0.43 percentage points, against a strong effect of information density.

Tailoring can work from a segment description, but only when that description carries real trait signal, such as interests or occupation. Matz 2017 itself targeted interest segments, not individuals. Nationality, gender and age stereotypes do not map onto actual traits, and a wrong match costs more than a right match gains. So the default should be trait-neutral, information-dense copy that is matched to the product and the decision context.

### Cited Findings
**Field evidence (Matz et al. 2017) and its critics**
- **[MODERATE]** Matz, Kosinski, Nave and Stillwell ran three Facebook campaigns, reaching more than 3.5 million people. Ads matched to extraversion or openness produced "up to 40% more clicks and up to 50% more purchases" than mismatched or unpersonalized ads. — [PNAS via PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5715760) · *Segment:* yes (see next point) · *Apply:* b, d
- **[MODERATE]** Facebook did not allow targeting by trait, so the authors targeted **single interest "Likes" that correlate with a trait**. For introverts they used Likes such as "Stargate" and "Computers". For extraverts they used "Making People Laugh". Study 3 used a predefined audience of players of similar games, estimated to be introverted. **In other words, the targeting was at segment level, through interests, not through individual data.** — [PMC5715760](https://pmc.ncbi.nlm.nih.gov/articles/PMC5715760) · *Segment:* yes · *Apply:* b
- **[MODERATE]** The absolute effects are tiny.
  - Study 1 (beauty retailer) reached 3.13 million people at a 0.33% click-through rate, with purchases equal to 0.012% of reach.
  - Matched and mismatched ads had **identical CTR (0.33% vs 0.33%)**. Matched ads produced 238 purchases against 152 (odds ratio 1.54).
  - Study 2 (crossword app) had odds ratios of 1.38 for clicks and 1.31 for installs.
  - Study 3 compared a tailored ad with a **standard (neutral) ad** rather than a mismatched one. Its odds ratios were smaller: 1.30 for clicks and 1.15 for installs.
  - The paper does not show how the "40%/50%" maxima were derived from its own table.
  - Source: [PMC5715760](https://pmc.ncbi.nlm.nih.gov/articles/PMC5715760) · *Apply:* d
- **[MODERATE]** Eckles, Gordon and Johnson (2018) argued that field studies of psychologically targeted ads face threats to internal validity: Facebook's delivery optimization decides who within a targeted audience actually sees each ad. — [Kellogg listing](https://www.kellogg.northwestern.edu/academics-research/research/detail/2018/field-studies-of-psychologically-targeted-ads-face-threats-to)
- **[MODERATE]** Sharp, Danenberg and Bellman (Ehrenberg-Bass, 2018) argued three things. The paper's own tests "refute" the claim that psychological targeting beats normal advertising. Targeting was effective in only two of the comparisons. Creative differences explain most of the performance gap between ads. Matz et al. replied that conversions, not clicks, are the relevant metric, and that creative main effects had been controlled. — [Sharp et al., PNAS](https://pmc.ncbi.nlm.nih.gov/articles/PMC6112709); [Matz et al. reply](https://pmc.ncbi.nlm.nih.gov/articles/PMC6112715)

**Lab and LLM evidence**
- **[MODERATE]†** Hirsh, Kang and Bodenhausen (2012) wrote one product ad in five versions, each framed around the motives of one Big Five trait. Participants rated the version matching their own dominant traits as more effective. The study used self-reported ratings in a single lab. — [Psychological Science, DOI](https://doi.org/10.1177/0956797611436349) · *Segment:* partly · *Apply:* b, c
- **[MODERATE]** Matz et al. (2024, *Scientific Reports*) ran 4 studies with 7 sub-studies (N = 1,788). They found:
  - ChatGPT wrote trait-tailored messages that beat generic ones in **20 of 33 tested effects (61%)**.
  - The prompts were as short as "Write a short ad for a person who scores high on Extraversion."
  - For iPhone ads, the matching effects for openness, conscientiousness and extraversion were β ≈ 0.16–0.40. Agreeableness was not significant.
  - **Regulatory-focus tailoring was small and not significant (β = 0.12).**
  - In Study 4 (within-subjects), the effect on perceived effectiveness was d = 0.16 and on willingness to pay d = 0.19. The sneaker ads showed no significant effect.
  - Willingness-to-pay effects were weaker than attitude effects.
  - Telling participants that the ads were AI-made or trait-targeted did not remove the effect (Study 1b).
  - **In Studies 1–3, the messages were tailored to a trait described in text, not to anyone's personal data.**
  - The authors' stated limits: outcomes were self-reported, and the design could not separate the benefit of a match from the penalty of a mismatch.
  - Sources: [PMC10897294](https://pmc.ncbi.nlm.nih.gov/articles/PMC10897294); [Stanford listing](https://maplab.stanford.edu/publications/potential-generative-ai-personalized-persuasion-scale) · *Segment:* yes, when the trait is known · *Apply:* b, c
- **[STRONG]** Hackenburg and Margetts (2024, *PNAS*) ran a preregistered RCT with n = 8,587. GPT-4 messages microtargeted with self-reported demographic and political data were **not more persuasive** than generic ones: 4.83 vs 6.20 percentage points, P = 0.226. The authors conclude that the persuasive power comes from generic message quality. — [Oxford news release](https://www.ox.ac.uk/news/2024-06-26-effectiveness-large-language-models-political-microtargeting-assessed-new-study); [OII summary](https://www.oii.ox.ac.uk/does-political-microtargeting-with-large-language-models-offer-persuasive-returns-ask-kobi-hackenburg-and-professor-helen-margetts/) · *Apply:* b
- **[STRONG]** Hackenburg et al. (2025, *Science*) tested 19 LLMs on 707 political issues across three experiments (N = 76,977). They found:
  - The pooled effect of personalization was **+0.43 percentage points**.
  - **Information density** (the number of fact-checkable claims) explained 44% of the variation in persuasive effect, and 75% among post-trained models.
  - Post-training and prompting raised persuasiveness by up to 51% and 27% respectively.
  - The levers that made models more persuasive also made them less accurate.
  - Sources: [arXiv 2507.13919](https://arxiv.org/pdf/2507.13919); [Oxford news, Dec 2025](https://www.ox.ac.uk/news/2025-12-11-study-reveals-how-conversational-ai-can-exert-influence-over-political-beliefs) · *Apply:* b (and it supports the evidence-ledger design)
- **[MODERATE]** Salvi et al. (2024; journal version in *Nature Human Behaviour*, 2025) found something different in **interactive debates**. When GPT-4 had the opponent's sociodemographic data, participants had 81.7% higher odds of increased agreement than when debating humans (N = 820). Without that data, the advantage was not significant (p = 0.31). The setting is conversational, not a static email. — [arXiv 2403.14380](https://arxiv.org/abs/2403.14380)
- **[STRONG]** Joyal-Desmarais et al. (2022, *Psychological Bulletin*) meta-analysed 702 experiments (5,251 effect sizes, N = 206,482). Motivational matching raises persuasion by **r = .20 [.18, .22]**, with large heterogeneity. The effects are **larger when the message is matched to contextual factors than to individual differences**, larger when the comparison is a conflicting (mismatched) message, and larger when the target characteristic was manipulated rather than measured. — [White Rose eprint](https://eprints.whiterose.ac.uk/id/eprint/204130/); [NYU IFP summary](https://ifp.nyu.edu/?p=1657975) · *Segment:* yes, for contextual matching · *Apply:* b
- **[MODERATE]** Joyal-Desmarais, Rothman and Snyder (2025) ran two experiments (N = 689 and N = 1,101). In the political study, **mismatched messages cut persuasion by more than matched messages raised it**. The authors note that generic or neutral messages "may outperform" matching. — [White Rose eprint 237991](https://eprints.whiterose.ac.uk/id/eprint/237991) · *Apply:* b
- **[MODERATE]†** Petty and Wegener (1998) found that matching a message to the function an attitude serves increases how closely the message is scrutinized. A matched message with strong arguments persuades more; a matched message with weak arguments persuades *less*. — [PSPB, DOI](https://doi.org/10.1177/0146167298243001); see also the review by [Teeny et al. 2021, JCP](https://doi.org/10.1002/jcpy.1198)† · *Apply:* a (substantiation gates matter more for tailored copy), b

**Does tailoring survive without individual data?**
- **[STRONG]†** Terracciano et al. (2005, *Science*) found that national-character stereotypes do **not** match the measured mean personality-trait levels in 49 cultures. — [DOI](https://doi.org/10.1126/science.1117199) · *Segment:* this is a warning against nationality-based trait guesses · *Apply:* b, c
- **[STRONG]** Taras, Steel and Kirkman (2016) covered 558 studies in 32 countries. About **80% of the variance in work values lies within countries, not between them**; for individualism, only 16.6% lies between countries. Occupation and socioeconomic status outperform country for individualism. — [NCSU news](https://news.ncsu.edu/2016/05/nationality-as-work-value-indicator); [IDEAS](https://ideas.repec.org/a/spr/manint/v56y2016i4d10.1007_s11575-016-0283-x.html) · *Segment:* occupation and status are better segment signals than nationality · *Apply:* b
- **[MODERATE]†** Kern et al. (2019, *PNAS*) found that occupations have distinct average personality and value profiles when inferred from social media. Some segment-level trait inference from the job title in an audience description is therefore defensible, though the within-group spread remains large. — [DOI](https://doi.org/10.1073/pnas.1917942116) · *Segment:* partly · *Apply:* b

**Can an LLM persona stand in for the segment? (This bears on the cold reader reading "as" the audience.)**
- **[MODERATE]** Hu and Collier (ACL 2024) found that demographic, social and behavioural persona variables explain **less than 10% of the variance** in human annotations across subjective NLP datasets. Persona prompting gives "modest but statistically significant" gains. — [arXiv 2402.10811](https://arxiv.org/abs/2402.10811) · *Apply:* c
- **[MODERATE]** Wang, Morgenstern and Dickerson found that LLMs standing in for identity groups **misportray** them, **flatten** the variation within them, and essentialize them. Inference-time mitigations reduce these harms but do not remove them. — [arXiv 2402.01908](https://arxiv.org/abs/2402.01908) · *Apply:* c
- **[MODERATE]†** Argyle et al. (2023) showed "algorithmic fidelity": GPT-3 conditioned on backstories reproduced some US subgroup attitude patterns. Bisbee et al. (2024) found that synthetic responses vary less than real ones, are sensitive to prompt wording, and are unstable over time. — [Argyle, Political Analysis](https://doi.org/10.1017/pan.2023.2)†; [Bisbee, Political Analysis](https://doi.org/10.1017/pan.2024.5)† · *Apply:* c

### Inferences
- **Inferring tailoring from an audience description is possible, but narrow.** The evidence supports three things:
  1. Writing to a trait *stated* in text works: Matz 2024 used a one-sentence trait prompt.
  2. Interest and occupation descriptors carry trait signal: Matz 2017 targeted through Likes, and Kern 2019 found occupation profiles.
  3. Individual demographics add almost nothing to LLM copy (Hackenburg, 2024 and 2025).

  The evidence does **not** support inferring traits from nationality, gender or generation (Terracciano; Hyde, in Section 4; Pew and NASEM, in Section 3).
- The famous "+40% clicks / +50% purchases" is measured against *mismatched* ads, which is the comparison that inflates matching effects (Joyal-Desmarais 2022). Against a neutral ad (Matz 2017, Study 3), the odds ratios were 1.15–1.30, on conversion bases of 0.3–0.6%. For a system with no individual data, the realistic upside of a trait guess is small. The downside of guessing wrong is larger than the upside of guessing right (Joyal-Desmarais 2025).
- The highest-value form of "matching" for MarketingOS is to match the **product, the decision context and the stage**. The system knows these from the business's material and the brief. Matching to an imagined reader's personality is worth much less. This follows Joyal-Desmarais' finding that contextual matches beat individual-difference matches.
- Hackenburg 2025 says that **information density beats personalization** for LLM persuasion. That is an argument for spending quota on proof and specifics (the ledger) rather than on persona variants.
- Application:
  - (b) Let the strategist record a "trait hypothesis" only when the brief, the material or the market research supplies a diagnostic descriptor, and name that descriptor. Otherwise, write trait-neutral copy.
  - (a) A provenance check: every audience assumption in a brief must cite a source id (brief, material, research). This mirrors the Evidence Ledger, but for claims about the audience.
  - (c) Use personas for **mismatch detection**: register, assumed relationship, jargon, missing reassurance. Do not use them to predict liking. When a persona is used, give it diagnostic within-segment variation (in-market vs not, high vs low involvement), not a demographic stereotype.
  - (d) The size of any trait lift.

### Gaps
- I found no study of personality tailoring in **email**, in **French**, or in **B2B**.
- I found no independent field replication of Matz 2017. Search was cut short when the shared web-search budget was exhausted.
- I could not verify whether Wang et al. appeared in *Nature Machine Intelligence* (2025), as I believe it did.
- Matz 2024 measured self-reported intentions only. Behavioural effects from LLM trait-tailoring in commerce remain unmeasured in the sources I found.

## 2. Cognitive style and motivation: need for cognition, regulatory focus and fit, construal level, maximizers, tightwads, need for closure, involvement

### Takeaway
The robust moderators are **involvement** and **need for cognition**. When people are motivated, argument quality governs persuasion; when they are not, cues do. Both are backed by meta-analyses and decades of replication. Regulatory fit and construal-level effects are real on average, but they show up most clearly when the frame is matched to the **situation**: the product's goal (gaining vs protecting) or the decision's distance (in-market now vs someday). Guessing the reader's chronic disposition is the weak version. Maximizer, tightwad and need-for-closure research is thinner and rarely inferable from a segment description.

### Cited Findings
- **[STRONG]†** Cacioppo, Petty, Feinstein and Jarvis (1996, *Psychological Bulletin*), reviewing the literature: people high in need for cognition are more influenced by argument quality, and people low in it by peripheral cues such as source attractiveness or the sheer number of arguments. — [DOI](https://doi.org/10.1037/0033-2909.119.2.197) · *Segment:* weak, because a description rarely reveals need for cognition · *Apply:* b, c
- **[MODERATE]†** Haugtvedt, Petty and Cacioppo (1992, *JCP*) showed the same split in advertising: argument quality drove high-NFC consumers, and peripheral ad cues drove low-NFC consumers. — [DOI](https://doi.org/10.1016/S1057-7408(08)80038-1)
- **[STRONG]†** Petty, Cacioppo and Schumann (1983, *JCR*): under high involvement, argument quality drove attitudes; under low involvement, a celebrity endorser did. — [DOI](https://doi.org/10.1086/208954) · *Segment:* **yes**, because involvement follows from price, risk, switching cost and stage · *Apply:* b, c
- **[STRONG]†** Johnson and Eagly (1989, meta-analysis): *outcome-relevant* involvement amplifies the effect of argument quality, so strong arguments persuade more and weak ones less. *Value-relevant* involvement, where the topic touches identity or values, reduces persuasion overall. — [DOI](https://doi.org/10.1037/0033-2909.106.2.290) · *Segment:* yes · *Apply:* b
- **[MODERATE]†** Lee and Aaker (2004, *JPSP*): gain frames persuade more with promotion-focused content, and loss frames with prevention-focused content. The fit raises processing fluency. — [DOI](https://doi.org/10.1037/0022-3514.86.2.205); see also Cesario, Grant and Higgins (2004) on the "feeling right" transfer: [DOI](https://doi.org/10.1037/0022-3514.86.3.388)† · *Segment:* yes, when focus is set by the product · *Apply:* b
- **[STRONG for existence; magnitude not verified]** Motyka et al. (2014, *JCP*) meta-analysed regulatory fit across evaluation, intention and behaviour, with moderators: the source of focus (chronic vs primed), its orientation, matching vs sustaining fit, and incidental vs integral fit. A university release claims fit made consumers "1.86 more likely to purchase". The wording is loose; check the paper before quoting it. — [Lancaster eprint](https://eprints.lancs.ac.uk/id/eprint/67664); [YU release](https://www.yu.edu/node/19377)
- **[MODERATE]** In Matz 2024, regulatory-focus tailoring written by ChatGPT (exercise messages) was small and not significant (β = 0.12). — [PMC10897294](https://pmc.ncbi.nlm.nih.gov/articles/PMC10897294)
- **[MODERATE]†** Culture and regulatory focus:
  - An independent self-view goes with promotion focus, and an interdependent one with prevention focus ([Lee, Aaker & Gardner 2000, JPSP](https://doi.org/10.1037/0022-3514.78.6.1122)†; [Aaker & Lee 2001, JCR](https://doi.org/10.1086/321946)†).
  - East Asian participants were more persuaded by loss-framed health messages, and British participants by gain-framed ones ([Uskul, Sherman & Fitzgibbon 2009, JESP](https://doi.org/10.1016/j.jesp.2008.12.005)†).
  - *Segment:* weak (see Section 5 on within-country variance) · *Apply:* b
- **[STRONG]†** Psychological distance increases abstract construal. Soderberg et al. (2015) found a medium average effect across two meta-analyses ([Soderberg et al. 2015](https://doi.org/10.1037/bul0000005)†; [Trope & Liberman 2010 review](https://doi.org/10.1037/a0018963)†). Distant decisions weigh desirability ("why"); near decisions weigh feasibility ("how"). — *Segment:* **yes**, through stage (out-of-market = distant, in-market = near) · *Apply:* b, c
- **[MODERATE]†** White, MacDonnell and Dahl (2011, *JMR*): loss frames paired with concrete (how) construal, and gain frames with abstract (why) construal, increased recycling intentions and behaviour. — [DOI](https://doi.org/10.1509/jmkr.48.3.472) · *Apply:* b
- **[MODERATE]†** Maximizers (Schwartz et al. 2002, *JPSP*) search and compare more, and report more regret and less satisfaction, than satisficers. Validity of the scale is debated, and I found no message-level studies. — [DOI](https://doi.org/10.1037/0022-3514.83.5.1178) · *Segment:* no · *Apply:* d
- **[MODERATE]†** Tightwads vs spendthrifts (Rick, Cryder & Loewenstein 2008, *JCR*): a scale of how painful paying feels. Tightwads responded more to cost reframing, such as "a small $5 fee". This overlaps with pricing psychology, which is out of scope. — [DOI](https://doi.org/10.1086/523285) · *Segment:* no · *Apply:* d
- **[MODERATE]†** Need for closure: people high in it "seize and freeze" on early, clear information ([Kruglanski & Webster 1996](https://doi.org/10.1037/0033-295X.103.2.263)†). The disrupt-then-reframe technique works through the need for closure ([Kardes et al. 2007, JCR](https://doi.org/10.1086/518541)†). — *Segment:* partly, since the need for closure rises *situationally* under time pressure and fatigue · *Apply:* a, b

### Inferences
- **Dispositions are rarely inferable; situations usually are.** For MarketingOS, the actionable versions are these:
  1. **Involvement**, from what the purchase costs and risks, and whether the reader is in-market. High involvement calls for stronger and more specific arguments; weak claims hurt more (Johnson & Eagly). Low involvement calls for one clear cue and one easy ask.
  2. **The product's own regulatory goal.** Security, compliance, insurance and continuity products are prevention by nature: frame losses avoided, use concrete "how" detail, stress reliability. Growth and opportunity tools are promotion: frame gains.
  3. **Distance.** Cold or out-of-market readers get "why this matters". Readers in-market, or already evaluating, get "how it works, what it takes, what happens next".

  These are (b) strategist and writer instructions keyed to fields the brief already has: audience, awareness, objective.
- (a) A situational need for closure (a busy reader on mobile) supports a structural, deterministic check: the email's point or ask should appear early, which can be measured by its position in words or sentences. This is a form check, which CLAUDE.md notes the judge is poor at.
- (c) A cold-reader criterion follows from the ELM: "As someone who [is / is not] about to buy, did you get a reason that would survive scrutiny?" Strong arguments matter more for high-involvement personas.
- Maximizers and tightwads should **not** be inferred or encoded. Treat them as (d).

### Gaps
- I could not verify the replication status of construal-level effects in persuasion. Many classic CLT studies predate registered reports, and the search budget ran out.
- I could not retrieve Motyka et al.'s pooled effect size.
- I found no evidence on any of these moderators in email specifically.

## 3. Age and generation: socioemotional selectivity, the positivity effect, scarcity, novelty, emotional appeals, and generational claims

### Takeaway
**Age** differences have reasonable evidence behind them. On average, older adults attend more to positive information (a meta-analysed positivity effect). They like and remember emotionally meaningful ads, and ads about *avoiding negative emotion*, better. They prefer fewer options. They seek less novelty and are more loyal to long-established brands. The driver is a shorter perceived time horizon, not age as such.

**Generational** claims ("Gen Z wants X, millennials want Y") are mostly folklore. Meta-analyses and a National Academies panel find generational differences small or not meaningful once age and period are separated. Pew now uses generation labels "sparingly".

### Cited Findings
- **[STRONG]†** Reed, Chan and Mikels (2014, meta-analysis): older adults show a relative preference for positive over negative information. The effect is reliable when information processing is unconstrained (they choose what to attend to) and weaker when tasks constrain it. — [Psychology and Aging, DOI](https://doi.org/10.1037/a0035194) · *Segment:* **yes** (age band in the description) · *Apply:* b, c
- **[MODERATE–STRONG]†** Fung and Carstensen (2003, *JPSP*): older adults preferred, and better remembered, ads with emotionally meaningful appeals. The preference **disappeared when their time horizon was experimentally expanded**, so the mechanism is the time horizon, not age. — [DOI](https://doi.org/10.1037/0022-3514.85.1.163) · *Segment:* yes · *Apply:* b
- **[MODERATE]** Williams and Drolet (2005, *JCR*): older consumers liked and recalled emotional ads more. Ads focused on **avoiding negative emotions** were liked and recalled more by older consumers, and also by young consumers primed with a limited time horizon. — [IDEAS](https://ideas.repec.org/a/oup/jconrs/v32y2005i3p343-354.html) · *Segment:* yes · *Apply:* b, c
- **[MODERATE]†** Drolet, Williams and Lau-Gesk (2007): older adults preferred affective ads for both hedonic and utilitarian products. Younger adults preferred affective ads for hedonic products and rational ads for utilitarian ones. — [Marketing Letters, DOI](https://doi.org/10.1007/s11002-007-9016-z) · *Segment:* yes · *Apply:* b
- **[MODERATE]†** Reed, Mikels and Simon (2008): older adults prefer fewer choices than younger adults across several decision domains. — [Psychology and Aging, DOI](https://doi.org/10.1037/0882-7974.23.3.671) · *Segment:* yes · *Apply:* a (count offers and options), b
- **[MODERATE–STRONG]†** Lambert-Pandraud and Laurent (2010, *JM*; ESCP and HEC, French perfume data): older consumers buy long-established brands, explained by **attachment and declining innovativeness**, not cognitive decline. Earlier work by Lambert-Pandraud, Laurent and Lapersonne (2005, *JM*) found that older new-car buyers consider fewer brands, dealers and models, and repurchase the same brand more often. — [2010 DOI](https://doi.org/10.1509/jmkg.74.5.104)†; [2005 DOI](https://doi.org/10.1509/jmkg.69.2.97.60747)† · *Segment:* yes · *Apply:* b ("new" is a weaker hook for older segments; continuity and reliability are stronger)
- **[STRONG]†** Costanza et al. (2012, meta-analysis of generational differences in work attitudes): the differences were small to moderate and inconsistent, and often attributable to age or period rather than cohort. — [Journal of Business and Psychology, DOI](https://doi.org/10.1007/s10869-012-9259-4) · *Apply:* b ("do not encode generational stereotypes")
- **[STRONG]†** A National Academies (NASEM) consensus report (2020) asked "Are generational categories meaningful distinctions for workforce management?" and concluded that generational categories are not supported as meaningful distinctions. — [NAP 25796](https://nap.nationalacademies.org/catalog/25796/are-generational-categories-meaningful-distinctions-for-workforce-management)
- **[STRONG, methodological]** Pew Research Center (2023) set out the problems with generational analysis:
  - Age, period and cohort effects are hard to separate.
  - Generation boundaries are arbitrary, spanning 15–18 years.
  - The labels "reinforce harmful stereotypes".
  - Within-generation diversity is large.

  Pew will "only talk about generations when it adds value". — [Pew](https://www.pewresearch.org/short-reads/2023/05/22/how-pew-research-center-will-report-on-generations-moving-forward/)
- **[WEAK-FOLKLORE]†** The "8-second attention span, shorter than a goldfish" claim, often attached to Gen Z or millennials, has no traceable research base. — [BBC, "Busting the attention span myth"](https://www.bbc.com/news/health-38896790)†

### Inferences
- **Actionable at segment level, (b) and (c), when the description gives an age band such as 60+ or 65+:**
  - Lead with emotionally meaningful, positively framed benefits.
  - Prefer avoiding a negative feeling (worry, hassle) over fear or loss.
  - Present fewer options and one ask.
  - Use continuity, reliability and track record rather than "new and novel".
  - These are averages with wide overlap, so they belong in guidance, not gates.
- (a) The number of distinct offers, options or CTAs is a deterministic count. It is useful in general and especially for older segments.
- **Stereotype flags.** "Gen Z distrusts ads, wants authenticity, has no attention span" and "millennials want purpose" are not supported by cohort-isolating evidence that I could find. The strategist should not derive an angle from a generation label. If an audience description says "Gen Z", the useful content is the **life stage and age** it implies (student, first job, budget), which can be acted on.
- For the cold reader reading as an older persona: check whether the email opens with a threat or loss, makes the reader juggle options, or leans on novelty.

### Gaps
- **Age and response to scarcity or urgency:** I found no peer-reviewed study in this session.
- I could not verify Shamaskin, Mikels and Reed (2010), the classic test of positive vs negative framing of health messages by age.
- I found no study of age effects in email.
- Evidence on French or European older consumers is limited to the Lambert-Pandraud papers.

## 4. Gender: what is robust, what is stereotype

### Takeaway
Most psychological gender differences are small and the distributions overlap heavily. There is reasonable but dated evidence of a modest **processing-style** difference (the "selectivity" hypothesis): women process more comprehensively, men more heuristically, when motivation is low. The difference shrinks when stakes are high.

Gender differences in emotional-ad responses partly reflect **social display**. Men's private responses did not differ from women's, and email is read privately. "Women want emotion and stories, men want facts and specs" is a stereotype without direct support.

### Cited Findings
- **[STRONG]†** Hyde (2005, *American Psychologist*) reviewed 46 meta-analyses: about 78% of gender differences are small (d ≤ .35) or close to zero. — [DOI](https://doi.org/10.1037/0003-066X.60.6.581) · *Apply:* b ("don't tailor by gender without research")
- **[MODERATE]†** Meyers-Levy and Loken (2015, *JCP*) reviewed the evidence on the selectivity hypothesis. Women tend to process more comprehensively, including subtle cues; men process more selectively and heuristically. The differences depend on context and shrink under high motivation or task demands. Most of the studies are older lab studies with student samples. — [DOI](https://doi.org/10.1016/j.jcps.2014.06.003) · *Segment:* weak · *Apply:* b
- **[STRONG, dated]†** Eagly and Carli (1981, meta-analysis): women were slightly more persuadable and conforming. The effect was small, and larger in studies written by male authors, which suggests sex-typed materials. — [Psychological Bulletin, DOI](https://doi.org/10.1037/0033-2909.90.1.1)
- **[MODERATE]** Fisher and Dubé (2005, *JCR*): men's **private** responses to emotional ads did not differ significantly from women's. Men rated a low-agency, stereotype-incongruent emotional ad less favourably **only when another man was present**. Women's responses did not vary with social context. — [IDEAS](https://ideas.repec.org/a/oup/jconrs/v31y2005i4p850-858.html) · *Apply:* b
- **[STRONG]†** Byrnes, Miller and Schafer (1999, meta-analysis): men take more risks on average, but the effect is small and varies with context and age. — [Psychological Bulletin, DOI](https://doi.org/10.1037/0033-2909.125.3.367)
- **[STRONG]†** Costa, Terracciano and McCrae (2001): across cultures, women score higher on neuroticism, agreeableness and warmth, and men on assertiveness. The differences are small to moderate, and *larger* in Western, egalitarian cultures. — [JPSP, DOI](https://doi.org/10.1037/0022-3514.81.2.322)
- **[MODERATE]†** Åkestam, Rosengren and Dahlén (2017): "femvertising", meaning ads that challenge female stereotypes, lowered reactance and improved ad and brand attitudes among women. — [Psychology & Marketing, DOI](https://doi.org/10.1002/mar.21023) · *Apply:* b
- **[MODERATE]** LLM personas defined by identity flatten and essentialize groups (Wang et al., Section 1). A "female persona" cold reader is likely to apply the very stereotypes this report is trying to separate from evidence. — [arXiv 2402.01908](https://arxiv.org/abs/2402.01908) · *Apply:* c

### Inferences
- **Do not vary angle, tone or proof type by gender** on the basis of a gender label in the audience description. The only defensible (b) instruction is that copy for mixed or unknown audiences should state key information **explicitly** rather than leave it implicit. That serves selective processors and costs comprehensive ones nothing.
- Email is a private reading context. The best-supported mechanism for gendered emotional-ad responses, self-presentation in front of others, mostly does not operate there.
- (c) Avoid gender-defined personas for the cold reader. Use role and situation personas.
- (d) Any real gender difference in response for a given business can only come from send data.

### Gaps
- I found no recent (post-2015), large-sample field evidence on gender differences in response to marketing messages, and no email-specific data.
- I could not verify the Kantar "AdReaction: Getting Gender Right" practitioner data in this session.

## 5. Culture and language: Hofstede and GLOBE, individualist vs collectivist appeals, uncertainty avoidance, power distance, high vs low context, humour, hype, formality. France, Germany, UK, US, Spain and Italy, Maghreb and Middle East, Japan and East Asia

### Takeaway
Adapting appeals to cultural values helps **a little** on average: r ≈ .07 across 67 comparisons. The effect is concentrated in individualist vs collectivist contrasts, mostly the US against East Asia, and it was **absent in European samples**. Western-European experiments (Belgium, UK, Germany, Netherlands, Spain) mostly find the same appeals winning everywhere.

Country explains only about 20% of the variance in values. Hall's high- vs low-context ranking was never measured, and its directness propositions mostly fail empirical tests. The firmest cross-cultural levers are **language itself**: the native language feels more emotional, and the choice of language and register signals identity. There is one notable France finding: French participants were *less* sensitive to the normative quality of evidence than Dutch participants.

Most "the French, Germans or Japanese want X" claims are content analyses (what advertisers do) or practitioner models, not tests of what works.

### Cited Findings
**How much does cultural adaptation matter?**
- **[STRONG; small effect]** Hornikx and O'Keefe (2009, meta-analysis): ads appealing to culturally important values were more persuasive, **r = .073 (d = 0.146), k = 67**. The effect was strongest for individualism–collectivism. There were **no adaptation effects in studies with participants from Europe or from Central and South America**. — [Radboud thesis summarizing the meta-analysis](https://theses.ubn.ru.nl/handle/123456789/7184); [meta-analysis DOI](https://doi.org/10.1080/23808985.2009.11679084)† · *Segment:* weak · *Apply:* b
- **[MODERATE; not read]** An updated meta-analysis covering about 120 comparisons from 1994–2018 is titled "Cultural value adaptation in advertising is effective, but not dependable" (*International Journal of Business Communication*). — [metatoc record](https://metatoc.com/papers/144104-cultural-value-adaptation-in-advertising-is-effective-but-not-dependable-a-meta-analysis-of-25-years-of-experimental-research)
- **[MODERATE]** Hoeken et al. (2007, *Journal of Marketing Communications*) tested students from Belgium, the UK, Germany, the Netherlands and Spain. The modesty and adventure appeals were preferred **regardless of nationality**, and the authors question whether value adaptation is needed in Western Europe. — [Utrecht research portal](https://research-portal.uu.nl/en/publications/is-it-necessary-to-adapt-advertising-appeals-for-national-audienc/)
- **[MODERATE]** Janssen and Hornikx (2019): adapting ads to individualism or collectivism did not raise persuasion or liking among Western Europeans. — [IDEAS](https://ideas.repec.org/a/aza/jcms00/y2019v4i1p55-65.html); [HSTalks](https://hstalks.com/article/5068/adapting-advertising-appeals-to-individualism-or-c/)
- **[MODERATE]†** Han and Shavitt (1994): Korean ads used more collectivist appeals than US ads. In their experiment, collectivist appeals persuaded more in Korea and individualist appeals more in the US, and the effect was stronger for shared products than for personal ones. — [JESP, DOI](https://doi.org/10.1006/jesp.1994.1016)
- **[MODERATE]** Aaker and Williams (1998, *JCR*) found the opposite of naive matching. **Ego-focused** emotions (pride, happiness) persuaded collectivists better, and **other-focused** emotions (empathy) persuaded individualists better. The explanation offered is the novelty of the thought each appeal provokes. — [IDEAS](https://ideas.repec.org/a/oup/jconrs/v25y1998i3p241-61.html) · *Apply:* b ("do not assume intuitive cultural matching")
- **[STRONG]** Taras, Steel and Kirkman (2016): about 80% of the variance in work values is within countries; only 16.6% of individualism variance is between countries. Occupation and socioeconomic status beat country for individualism, but **country beat them for uncertainty avoidance and masculinity**. — [NCSU news](https://news.ncsu.edu/2016/05/nationality-as-work-value-indicator); [Springer DOI](https://link.springer.com/doi/10.1007/s11575-016-0283-x)
- **[STRONG]†** Taras, Kirkman and Steel (2010, meta-analysis): cultural values predict outcomes more strongly for attitudes, emotions and perceptions than for behaviours or performance. — [JAP, DOI](https://doi.org/10.1037/a0018938)
- **[MODERATE, conceptual]†** McSweeney (2002) criticizes Hofstede's assumptions: IBM samples, and national uniformity. — [Human Relations, DOI](https://doi.org/10.1177/0018726702551004)
- **[MODERATE for content correlations; WEAK for effectiveness]†** De Mooij and Hofstede (2010) review how Hofstede's dimensions correlate with advertising styles. For example, high uncertainty avoidance goes with more explanation, expertise and testimonials, and high power distance with status and authority appeals. Most of the evidence is content analysis, the "mirror" of what advertisers do. — [International Journal of Advertising, DOI](https://doi.org/10.2501/S026504870920104X)†

**High vs low context (Hall)**
- **[STRONG, critical review with full text read]** Cardon (2008, *Journal of Business and Technical Communication*) reviewed 224 articles from 1990–2006.
  - Hall's ranking, from lowest to highest context, is: Swiss-Germans, Germans, Scandinavians, North Americans, **French, English**, Italians, Latin Americans, Arabs, Chinese, Japanese. Note that Hall put the French *lower*-context than the English.
  - Hall "did not describe how he conceptualized or measured these rankings".
  - **Directness**, the most-tested proposition, is "the least empirically supported": 1 study supports it, 2 are mixed, and 5 do not support it.
  - Thomas (1998) found that American and Korean business writers were similarly direct, linear and detailed.
  - Richardson and Smith found only a tiny difference on a high-context scale between Japanese and American students (3.00 vs 2.84), with the Japanese at the scale midpoint.
  - Trompenaars classed Japan and the UAE as *low*-context, contradicting Hall.
  - Sources: [journal page](https://journals.sagepub.com/doi/10.1177/1050651908320361); [full-text PDF](https://support.wspa.pl/wp-content/uploads/2020/12/04_Reading-Material_Topic-3.2_A-Critique-of-Halls-Contexting-Model.pdf) · *Apply:* b ("do not use high/low context to set directness by country")
- **[MODERATE]†** Kittler, Rygl and Mackinnon (2011) reviewed how the high- and low-context concept is used and found inconsistent country classifications and weak empirical grounding. — [IJCCM, DOI](https://journals.sagepub.com/doi/10.1177/1470595811398797)

**Evidence types and argument (France vs Netherlands)**
- **[MODERATE; two experiments, N = 600 each]** Hornikx and Hoeken (2007, *Communication Monographs*):
  - France and the Netherlands differed in how persuasive they found anecdotal, statistical, causal and expert evidence.
  - **Dutch participants, but not French ones, found normatively strong evidence more persuasive than weak evidence**, for both statistical and expert evidence.
  - The French–Dutch gap for expert evidence was smaller than the large power-distance difference between the two cultures would predict.
  - Sources: [Utrecht research portal](https://research-portal.uu.nl/en/publications/cultural-differences-in-the-persuasiveness-of-evidence-types-and-); [ISSA 2006 proceedings version](https://rozenbergquarterly.com/issa-proceedings-2006-cultural-differences-in-the-persuasiveness-of-normatively-strong-and-normatively-weak-expert-evidence/?print=pdf) · *Segment:* yes (French-speaking audience) · *Apply:* b, c
- **[MODERATE–WEAK]** In a separate Hornikx paper on lay expectations, both cultural groups expected statistical evidence to be the most persuasive to others, followed by expert, causal and anecdotal evidence. — [Toegepaste Taalwetenschap in Artikelen 73](https://www.jbe-platform.com/content/journals/10.1075/ttwia.73.02hor)

**Hard vs soft sell, humour, emotion, information content**
- **[MODERATE]** Okazaki, Mueller and Taylor (2010, *Journal of International Marketing*) ran a quasi-experiment in the US and Japan. Soft-sell ads were accepted somewhat more uniformly across the two markets, **but hard-sell ads were also accepted fairly uniformly**. The stereotype "soft sell for Japan, hard sell for the US" is weaker in *reception* than in *content*. — [JIM](https://journals.sagepub.com/doi/full/10.1509/jimk.18.2.20). A content study found that **American advertising had become more "Japanese" (soft) over time** — [Okazaki & Mueller 2008 PDF](https://repositorio.uam.es/bitstream/handle/10486/668879/EvolutionIn_Okazaki_IJA_2008.pdf?sequence=2)
- **[STRONG]†** Eisend (2009, meta-analysis): humour increases attention, positive affect and liking of the ad, but **reduces source credibility**. — [JAMS, DOI](https://doi.org/10.1007/s11747-008-0096-y) · *Apply:* b (humour is riskier for an unknown sender whose credibility is the bottleneck)
- **[MODERATE, content]†** Alden, Hoyer and Lee (1993) studied TV ads from Korea, Germany, Thailand and the US. Humour based on incongruity is near-universal; the content of the humour (group vs individual characters, unequal status) varied with individualism and power distance. — [Journal of Marketing, DOI](https://doi.org/10.1177/002224299305700205)
- **[MODERATE, content]** Lascu et al. (2016) compared online fashion-magazine ads: emotional advertising was more prevalent in **France**, sexual advertising in the **US**. — [Journal of Fashion Marketing and Management](https://emeraldinsight.com/insight/content/doi/10.1108/JFMM-09-2014-0063/full/html)
- **[WEAK]** Zandpour et al. (1994, *JAR*) built a model of creative strategy and informativeness fit for 23 countries. A *secondary* source says it found French and Taiwanese audiences more accustomed to an indirect style than US audiences, who accept strong product identification, celebrities and testimonials. — [WARC record](https://www.warc.com/content/article/jar/global-reach-and-local-touch-achieving-cultural-fitness-in-tv-advertising/en-gb/6305)
- **[MODERATE, content]** Al-Olayan and Karande compared 398 ads from Arabic magazines (covering Middle Eastern and North African countries) with 540 US magazine ads. **US ads carried more information, more price information and more comparative claims**, and women appeared more often in them. — [repository record](https://gnanaganga.inflibnet.ac.in:8443/jspui/handle/123456789/8045)

**Language and register**
- **[MODERATE–STRONG; 5 experiments]** Puntoni, de Langhe and van Osselaer (2009, *JCR*): slogans in a bilingual's **native language** feel more emotional than the same slogans in a second language. This is not explained by language stereotypes or comprehension, and it tracks how often the words were met in native-language contexts. — [IDEAS](https://ideas.repec.org/a/oup/jconrs/v35y2009i6p1012-1025.html) · *Segment:* yes · *Apply:* b
- **[MODERATE]** Krishna and Ahluwalia (2008, *JCR*): the choice of language (local, English, or mixed) affects ad effectiveness for **multinationals but not local firms**, and the best format differs for luxuries and necessities. — [IDEAS](https://ideas.repec.org/a/oup/jconrs/v35y2008i4p692-705.html) · *Apply:* b
- **[MODERATE]†** Hornikx, van Meurs and de Boer (2010), with Dutch participants: **easy** English slogans were preferred to their local-language equivalents; *difficult* English slogans were not. — [Journal of Business Communication, DOI](https://doi.org/10.1177/0021943610364524)
- **[WEAK–MODERATE; observational, French]** Aussilhou, Kacha, Lemoine and Zafri (IAE Nice, Lorraine, Paris 1; data processed in late 2022):
  - The sample was 25 brands with French pages and **27,615 posts** from 2012–2022 on Facebook, Instagram and Twitter. **5.2% used *tu*, 52.4% used *vous*, and 42.4% used other forms.**
  - *Tu* posts had more likes (1,895 vs 757), comments (337 vs 141) and total engagement (2,276 vs 948), all significant. Shares were not significantly different (44 vs 50).
  - *Tu* is **concentrated in five brands** (Stabilo, Le Coq Sportif, McDonald's, Coca-Cola, Bic, together 77.5% of *tu* posts): hedonic, youth or sport categories. This is a strong confound.
  - The authors call the design correlational. They also argue that *tu* can read as **manipulative to consumers unfamiliar with the brand** (persuasion knowledge) and **inappropriate for "competent" or prestige brand personalities**.
  - Source: [working paper PDF](https://events.unamur.be/event/81/attachments/97/218/papier%206-3.pdf) · *Segment:* yes · *Apply:* a, b, c
- **[MODERATE]** Lenoir (2015, Erasmus PhD): **informal address works better for warm brands, formal address for competent brands**, across linguistic contexts. — [ERIM defence notice](https://www.erim.eur.nl/research/news/detail/3734-phd-defence-anne-sophie-irene-lenoir/) · *Apply:* b
- **[MODERATE]** De Hoop et al. (*Languages*, 2024) ran a Dutch web experiment with a no-pronoun control. The **formal** pronoun raised estimates of the product's price, which may lift purchase intention. — [DOI 10.3390/languages9090290](https://doi.org/10.3390/languages9090290) (abstract via search; the MDPI page refused automated access)

**Trust and skepticism toward advertising in France**
- **[MODERATE; disclosed-method survey]** YouGov surveyed 18,929 people in 17 countries, from 31 December 2020 to 15 January 2021. Trust in advertising by channel in France:

  | Channel | French trust |
  |---|---|
  | Print | 49% |
  | TV | 48% |
  | Radio | 47% |
  | Search engines | 38% |
  | Websites | 29% |
  | Podcasts | 18% |
  | Social networks | 17% |

  The global average for social networks was 25% (France 17%, UK 10%, Sweden 11%, India 48%). YouGov describes the French as "sceptiques face aux nouvelles formes de publicité". — [YouGov FR](https://yougov.com/fr-fr/articles/34551-les-types-de-publicite-qui-inspirent-confiance)
- **[MODERATE]** Edelman Trust Barometer 2025, France (33,000 respondents in 28 countries, fieldwork October–November 2024):

  | Measure | France |
  |---|---|
  | Trust business | 56% |
  | Trust institutions | 37% |
  | Trust media | 45% |
  | Distrust business leaders | 67% |
  | Think the next generation will be better off | 9% (vs 30% US, 69% China) |

  — [The Media Leader FR](https://fr.themedialeader.com/?p=101607)

**Maghreb (language use)**
- **[WEAK–MODERATE]** A study of Moroccan advertising analysed 34 audiovisual ads on TV, radio and billboards in which Moroccan Arabic (*darija*) is used; the choice of language is linked to the target audience. — [Lingua Posnaniensis](https://pressto.amu.edu.pl/index.php/linpo/article/view/52263). A 2025 Sunergia survey, as summarized in search results and not read in full, reported:
  - *Darija* dominates oral professional communication (69%).
  - In written professional communication, *darija* has 39% and French 32%.
  - About 45% of Moroccans are monolingual in *darija*.
  - Sources: [TelQuel](https://telquel.ma/instant-t/2025/04/21/darija-amazigh-francais-qui-parle-quoi-au-maroc-en-2025_1928078/); [H24info](https://h24info.ma/maroc/societe/voici-les-langues-les-plus-parlees-au-maroc-en-2025-sondage/)

**Reference values (context only)**
- †Classic Hofstede scores (Hofstede, Hofstede & Minkov 2010), not re-verified this session; the commercial site was unreadable. Commonly cited values:

  | Country | Uncertainty avoidance | Power distance | Individualism |
  |---|---|---|---|
  | France | 86 | 68 | 71 |
  | Spain | 86 | 57 | 51 |
  | Italy | 75 | 50 | 76 |
  | Germany | 65 | 35 | 67 |
  | Morocco | 68 | 70 | 46 |
  | US | 46 | 40 | 91 |
  | UK | 35 | 35 | 89 |
  | Japan | 92 | 54 | 46 |

  Source: [The Culture Factor comparison tool](https://www.theculturefactor.com/country-comparison-tool)†

### Inferences
- **What is well established:**
  1. The language of the email should be the one the audience lives in. The native language carries more emotion, and language choice is an identity signal (for example *darija*, French or Modern Standard Arabic in the Maghreb).
  2. Register (*tu*/*vous*, *du*/*Sie*) is a real lever. Its effect depends on **brand personality and familiarity**, not on a country rule.
  3. Cross-national differences in *values* exist but are small next to within-country differences. Uncertainty avoidance is the dimension where country carries the most signal (Taras 2016). France, Spain, Japan and Germany are well above the UK and US on it.
- **Stereotypes without evidence, or with weak evidence:**
  - "Germans or Swiss want low-context directness; the Japanese, Arabs and Chinese want indirectness." The contexting model is unmeasured, and its directness propositions mostly fail (Cardon).
  - "Collectivists respond to group appeals." The average effect is tiny and absent in Europe, and Aaker and Williams found reversals.
  - "Soft sell for Japan." Reception differences are modest.
  - "The French want principles-first argument and rigorous proof." This rests on practitioner models: Meyer's *Culture Map*. The [HBR excerpt](https://hbr.org/2014/05/navigating-the-cultural-minefield) fetched did not show its country placements or method. The one experiment found French participants *less* sensitive to the normative quality of evidence than the Dutch.
- **"French skepticism toward hype"** has *partial* support. Trust in digital ad channels is below the global average (YouGov), and pessimism is high (Edelman). I found no experiment on superlatives or hype with French readers. In France, *trust in business* (56%) is higher than trust in institutions or media, which argues for **specific, checkable claims** over overt promotional tone. That is what the ledger already enforces.
- **Application:**
  - **(a) Register consistency gate (strong candidate).**
    - When the brief or brand voice fixes a register, a deterministic check flags forms of the other one. In French that means *tu, te, t', toi, ton, ta, tes* against *vous, votre, vos*. In German *du, dich, dir, dein* against *Sie, Ihr*, and in Spanish *tú* against *usted*.
    - Mixing registers within one email is always a defect.
    - Default to ***vous*** in French when unspecified. *Vous* outnumbered *tu* about 10:1 even in big-brand social posts (Aussilhou et al.).
    - Allow *tu* only when the brand's own material uses it and the relationship is established.
    - Also check that the output language matches the requested language; `writer.md` already emits a LANGUAGE tag.
  - **(b) Strategist and writer.**
    - Do not adapt the angle by nationality alone.
    - For high-uncertainty-avoidance markets (France, Spain, Germany, Japan), favour risk reducers: concrete detail, guarantees, references, what happens next. This applies doubly in B2B.
    - Offer both statistical and expert or causal evidence when available. Don't rely on anecdote alone.
    - Avoid humour for an unknown sender (it costs credibility).
    - Use easy English loanwords only if the audience uses them.
  - **(c) Cold reader as a French or German B2B buyer:** "Is the register right for a stranger? Is anything promotional that should be factual?" Do not ask the persona to "be French". Ask it to judge register and claim specificity.
  - **(d) Humour, emotional intensity and *tu* vs *vous* effects on response.**

### Gaps
- **Germany, UK, US, Spain and Italy:** I found no reception experiment comparing message styles beyond Hoeken (2007) and the Hornikx studies. UK humour (Weinberger & Spotts 1989) was not verified. I found no data on *du*/*Sie* in German marketing.
- **Laroche et al. (2011) on humour in US, China and France:** the WARC page showed no findings.
- **Biswas et al. (1992) comparing US and French print ads:** findings were not retrieved.
- **Venaik and Brewer (2010, *JIBS*)**, who argue that Hofstede's and GLOBE's uncertainty avoidance measure different constructs, and **GLOBE's negative correlation between values and practices**, were not verified.
- **Arabic-speaking markets:** I found no reception studies on religion and modesty norms, no comparison of *darija* with French in ads, and no data on Gulf vs Maghreb differences. One manuscript (SFU repository) about attitudes to English vs Arabic in ads could not be opened, and its country could not be confirmed.
- **French B2B formality:** I found no data. *Vous* as the B2B default is practitioner consensus (WEAK-FOLKLORE), consistent with Lenoir's finding that formal address suits competent brands.
- **Null results on register:** Student theses on formal vs informal address (Spanish ads; Dutch and German posters) reported null effects, and a 2025 corpus study reportedly found that Spanish and Dutch TV ads mostly use informal *T* forms. These surfaced in search results only (theses.ubn.ru.nl) and were not verified.

## 6. B2B vs B2C buying psychology: buying committees and consensus, personal career risk, emotion in B2B, champion vs economic buyer, rational justification, the 95-5 rule

### Takeaway
B2B purchases are group decisions under personal risk. Brands act as a **risk-reduction heuristic**, and their influence rises again at high purchase risk (peer-reviewed, U-shaped). Most potential buyers are not in-market at any given time (95-5). The famous claims that "B2B is more emotional than B2C" and that "personal value is worth twice business value" come from a Google-commissioned study whose primary report is no longer publicly reachable, so treat them as unverified. The figures on committee size and consensus come from proprietary Gartner and CEB surveys, and could not be re-fetched.

### Cited Findings
- **[MODERATE]** Brown, Zablah, Bellenger and Johnston (2011, *IJRM*) ran two field studies with buying-centre members (n = 206 scenario-based, n = 180 survey). Brands act as a **risk-reduction heuristic**. Brand sensitivity has a **U-shaped** relationship with purchase risk: it is highest at low and at high risk. The pattern is stronger when competitive intensity is low. This contradicts the "rational buyer, brands matter less as stakes rise" view. — [IDEAS](https://ideas.repec.org/a/eee/ijrema/v28y2011i3p194-204.html) · *Segment:* yes (B2B, high-stakes purchase) · *Apply:* b
- **[MODERATE]†** Mitchell (1995) reviewed organizational risk. Buyers face both **personal** risk (career, reputation) and organizational risk, and they reduce it through familiar suppliers, references and more information. — [British Journal of Management, DOI](https://doi.org/10.1111/j.1467-8551.1995.tb00089.x)†
- **[MODERATE; disclosed logic, not an experiment]** The 95-5 rule (LinkedIn B2B Institute, with Ehrenberg-Bass "How B2B Brands Grow"):
  - "95% of your potential buyers aren't ready to buy today."
  - Illustrative purchase cycles: 75% of companies buy computers once every 4 years; 80% change banking services once every 5 years.
  - Ads work by building memories and linking the brand to buying situations (category entry points) before buyers enter the market.
  - Keep lead generation for the in-market 5%, and invest in brand for the rest.
  - 96% of B2B marketers expected the main effect of a campaign within 2 weeks, which the page calls a myth.
  - The page fetched is by Ty Heath. The underlying 2021 report is by John Dawes (Ehrenberg-Bass)†.
  - Source: [LinkedIn B2B Institute](https://business.linkedin.com/marketing-solutions/b2b-institute/b2b-research/trends/95-5-rule) · *Segment:* yes (cold B2B lists are mostly out-of-market) · *Apply:* b, c
- **[MODERATE; proprietary; not re-verified]** Gartner's "B2B buying journey" page has long stated two things: a typical buying group for a complex solution involves **6–10 decision makers**, and buyers spend about **17%** of their buying time meeting potential suppliers, split across all the suppliers they consider. The page refused automated access (HTTP 403) on 29 Oct 2026. — [Gartner](https://www.gartner.com/en/sales/insights/b2b-buying-journey)
- **[MODERATE; proprietary; paywalled, not re-verified]** CEB's article in HBR (Schmidt, Adamson & Bird 2015) is widely cited for two figures: about **5.4 people formally sign off** on a purchase, and the likelihood of purchase falls from **81% with one stakeholder to 31% with six**. — [HBR, "Making the Consensus Sale"](https://hbr.org/2015/03/making-the-consensus-sale)
- **[WEAK-FOLKLORE until re-verified]** Google, CEB and Motista, "From Promotion to Emotion" (2013), is the source usually quoted for three claims: B2B buyers are more emotionally connected to vendors than consumers are to brands; "personal value" (career, pride) has about twice the impact of business value; and only about 14% of buyers see a meaningful difference between suppliers' business value. The primary PDF now returns 404 or redirects to a Gartner sign-in, and the study was commissioned by an ad seller. — [former Think with Google PDF, dead](https://www.thinkwithgoogle.com/_qs/documents/673/promotion-emotion-b2b_research-studies.pdf)
- **[STRONG, cross-domain]** Information density (specific, checkable claims) was the main driver of LLM persuasion (Hackenburg et al. 2025, Section 1). This is consistent with B2B readers' need for material they can repeat to a committee. — [arXiv 2507.13919](https://arxiv.org/pdf/2507.13919)

### Inferences
- **Actionable at segment level, (b):**
  - In B2B, the reader usually has to *sell the purchase internally*. Give the champion portable justification: the problem in their words, a mechanism, specific proof, risk reducers (references, guarantees, implementation effort, reversibility), and a low-commitment next step.
  - Name the other stakeholders' likely concerns (finance, IT or security, operations) without inventing them.
  - In B2B the "emotional" lever is mostly **personal-risk relief and career safety**, consistent with Brown 2011 and Mitchell 1995. Delight is not the lever.
- **Stage logic from 95-5.** A cold B2B list is overwhelmingly out-of-market. Ask for a micro-commitment, or offer something useful to keep. Do not ask for a demo in email 1 unless the brief establishes in-market status. This ties to construal level in Section 2: "why" for distant readers, "how" for near ones.
- **(c)** Read the same email as **two or three committee roles**: the champion, a sceptical economic buyer, and a technical gatekeeper. `persona_bench` already holds drafts fixed and re-reads them as personas. The criterion is "Could I forward this internally without embarrassment, and does it answer my role's first objection?", not "Do I like it?"
- **(a)** A single-ask check, and the substantiation checks the system already has. A B2B-specific soft check: at least one risk-reducing proof element from the ledger (reference, case, certification) when the brief is a high-stakes B2B purchase. This should be a warning, because "judgment never blocks" and the ledger may be thin.
- **Stereotypes to flag.** "B2B buyers are purely rational" is contradicted by the brand-heuristic evidence. "B2B is more emotional than B2C" is unverified (practitioner and commissioned data).

### Gaps
- **Champion vs economic buyer:** I found no peer-reviewed evidence. It is a practitioner sales construct (Miller Heiman; CEB's "mobilizers" in *The Challenger Customer*), so treat it as WEAK-FOLKLORE.
- **Gartner's 2025 survey on buyers' preference for a "rep-free" experience:** not verified.
- **Binet and Field's B2B effectiveness work** (IPA and LinkedIn: brand vs activation split, emotional campaigns in B2B) was not retrieved.
- I found no evidence on B2B in France or the Maghreb.

## 7. Awareness and relationship stage: cold prospect, subscriber, customer, lapsed customer. Proof, length, tone and the ask; brand familiarity; the unknown sender

### Takeaway
Familiarity changes how messages are processed. With an unknown sender, readers scrutinize tactics more and tolerate less: repetition wears out faster, explicit name personalization backfires, and an informal *tu* can read as manipulative. **Third-party proof matters far more for weak or unknown brands than for strong ones.**

For existing customers, relevance built from what the firm knows about their product use works. **Contacting dormant or at-risk customers can wake them up to leave.** Strict "awareness ladder" models (cognition, then affect, then behaviour) lack empirical support, so stage should change the *proof and the ask*, not follow a fixed script.

### Cited Findings
- **[STRONG; review]†** Vakratsas and Ambler (1999, *JM*) reviewed 250+ studies: there is little support for a fixed hierarchy of effects. How advertising works depends on product, involvement and experience. — [DOI](https://doi.org/10.1177/002224299906300103) · *Apply:* b
- **[MODERATE–STRONG]†** Campbell and Keller (2003, *JCR*): ads for **unfamiliar** brands wear out sooner with repetition, and repeated exposure triggers negative thoughts about the tactic being inappropriate. — [DOI](https://doi.org/10.1086/376800) · *Segment:* yes (cold list = unknown sender) · *Apply:* b (sequence variety and pacing for cold sequences), d
- **[STRONG; theory with broad support]†** The Persuasion Knowledge Model (Friestad & Wright 1994): once people recognize a tactic as a tactic, it loses force or backfires. — [JCR, DOI](https://doi.org/10.1086/209380) · *Apply:* b, c
- **[MODERATE–STRONG]** Wattal, Telang, Mukhopadhyay and Boatwright (2012, *ISR*) analysed more than 10 million emails to over 600,000 customers of an online merchant. **Product-based personalization** got a positive response. **Personalized greetings with the customer's name** got a **negative** response, which **familiarity with the firm softened**. — [IDEAS](https://ideas.repec.org/a/inm/orisre/v23y2012i3-part-1p679-697.html) · *Segment:* yes (relationship field) · *Apply:* a, b
- **[MODERATE–STRONG]†** Sahni, Wheeler and Chintagunta (2018, *Marketing Science*) found the opposite direction in randomized field experiments. Adding the recipient's name to the **subject line** increased opens and leads and reduced unsubscribes. The setting differs: subject line, not greeting, and people who had already engaged. — [DOI](https://doi.org/10.1287/mksc.2017.1066) · *Apply:* d (contested; only send data settles it for a given list)
- **[MODERATE–STRONG]†** Ho-Dac, Carson and Moore (2013, *JM*, sales data): positive online reviews **raised sales of weak brands but not of strong brands**. — [DOI](https://doi.org/10.1509/jm.11.0011) · *Segment:* yes · *Apply:* b, c
- **[MODERATE]†** Erdem and Swait (1998): brand credibility lowers perceived risk and the cost of gathering information, which is what an unknown sender lacks. — [JCP, DOI](https://doi.org/10.1207/s15327663jcp0702_02)
- **[STRONG; randomized field experiment]†** Ascarza, Iyengar and Schleicher (2016, *JMR*): proactively recommending a cheaper plan to wireless customers **increased** churn, because the contact broke their inertia. — [DOI](https://doi.org/10.1509/jmr.13.0483) · *Segment:* yes (customers, lapsed) · *Apply:* b, d
- **[STRONG]†** Ascarza (2018, *JMR*, "Retention futility"): targeting the customers at highest churn risk is ineffective; target by predicted *response* to the intervention. — [DOI](https://doi.org/10.1509/jmr.16.0163) · *Apply:* d
- **[MODERATE]†** Kumar, Bhagwat and Zhang (2015, *JM*): whether lost customers come back depends on their first-lifetime behaviour, **why they left**, and the nature of the win-back offer. — [DOI](https://doi.org/10.1509/jm.14.0107) · *Segment:* yes, when the reason is known · *Apply:* b
- **[WEAK; theoretical]** Aussilhou et al. argue that *tu* addressed to consumers unfamiliar with the brand can read as fake closeness and raise scepticism. — [working paper](https://events.unamur.be/event/81/attachments/97/218/papier%206-3.pdf)
- **Context: the MarketingOS prompts already partly encode this.**
  - `backend/prompts/reader.md` and `backend/prompts/duel.md` (lines 8–10) tell the cold reader to "use the relationship and awareness explicitly established in this profile" and to treat an unspecified relationship as unknown.
  - `backend/prompts/critic.md` has a section titled "Audience evidence and awareness stage".
  - `backend/prompts/strategist.md` (around line 470) has cold-prospect rules.
  - Source: local repository, `C:\Users\oussa\Desktop\Workspace\projects\MarketingOS\backend\prompts\`

### Inferences
- **Stage × what changes:**

  | Stage | Proof | Tone and length | The ask |
  |---|---|---|---|
  | **Cold or unknown sender** | Third-party, verifiable proof; say who you are and why you're writing | Restrained; no presumed familiarity; no name-greeting gimmicks; no *tu* in French unless the brand clearly owns it | Low-commitment |
  | **Subscriber** (opted in, low purchase history) | — | Value-first content; the relationship licenses some informality if the brand's voice has it | — |
  | **Customer** | Less third-party proof needed | Relevance from product use (what the business's material says customers do); not generic praise | — |
  | **Lapsed** | — | Address the likely reason for leaving if known; do not invent history | For retention emails to at-risk customers, beware that contact itself can trigger switching: emphasize continuity and value received, not plan comparisons |

  This is (b), keyed to the relationship and awareness fields.
- **(a) Deterministic relationship-presumption checks for "cold" or "unknown":**
  - Flag phrases that assume history ("comme convenu", "suite à votre commande", "welcome back", "as a valued customer", "as you know").
  - Flag first-name merge fields in the greeting, as a warning: the evidence conflicts.
  - Flag *tu* forms in French when the relationship is unknown.
  - For "lapsed", flag claims of specific past interactions not present in the brief.
- **(c) The cold reader, already instructed to honour the relationship, could also ask** (as a stranger): "What in this email lets me check that this sender is real and competent?" That operationalizes Ho-Dac and Erdem & Swait.
- **The awareness-levels framework** (Eugene Schwartz's five levels, from *Breakthrough Advertising*, 1966) is a practitioner heuristic. I found no empirical validation, and Vakratsas and Ambler's review argues against fixed sequences. Use it as vocabulary, not as a rule.

### Gaps
- I found no study measuring the optimal **email length** by stage or familiarity.
- I found no French-language research on cold vs warm email.
- I did not check whether the Sahni and Wattal results replicate in B2B cold outreach.

## 8. Category differences: high vs low involvement, hedonic vs utilitarian, services vs products, luxury vs value

### Takeaway
Matching the appeal to the product's *function* is among the more robust matching effects: utilitarian appeals for utilitarian products, identity or emotional appeals for identity or hedonic ones. This is a contextual match, which the matching meta-analysis finds stronger than matching on individual differences. Involvement sets how much argument quality matters. Hedonic purchases need justification. Scarcity works differently for conspicuous and non-conspicuous goods. Luxury buyers split into those who prefer quiet signals and those who prefer loud ones. Services, being intangible, push readers toward personal sources and credentials. All of these can be inferred from the business's material, so they are the most actionable differences in this report.

### Cited Findings
- **[MODERATE]†** Shavitt (1990): utilitarian products (an air conditioner, coffee) were more persuaded by utilitarian appeals, and social-identity products (perfume, greeting cards) by identity appeals. — [JESP, DOI](https://doi.org/10.1016/0022-1031(90)90072-T) · *Segment:* **yes** (from the product) · *Apply:* b
- **[WEAK–MODERATE; conceptual]†** Johar and Sirgy (1991): value-expressive (image) appeals for value-expressive products, utilitarian appeals for utilitarian products. — [Journal of Advertising, DOI](https://doi.org/10.1080/00913367.1991.10673345)
- **[STRONG]** Context-level matches produce larger matching effects than individual-difference matches (Joyal-Desmarais 2022, Section 1). — [White Rose](https://eprints.whiterose.ac.uk/id/eprint/204130/)
- **[STRONG]†** Involvement (Petty et al. 1983; Johnson & Eagly 1989, Section 2): high-involvement categories reward strong, specific arguments and punish weak ones. — [DOI](https://doi.org/10.1086/208954); [DOI](https://doi.org/10.1037/0033-2909.106.2.290)
- **[MODERATE]†** Okada (2005, *JMR*): hedonic options are harder to justify. In a choice, people favour the more justifiable utilitarian option; evaluated alone, hedonic options are rated higher. — [DOI](https://doi.org/10.1509/jmkr.42.1.43.56889) · *Apply:* b (give hedonic purchases a reason to permit the indulgence)
- **[MODERATE]†** Drolet et al. (2007): product type interacts with age. Younger adults prefer rational ads for utilitarian products; older adults prefer affective ads for both types. — [DOI](https://doi.org/10.1007/s11002-007-9016-z)
- **[MODERATE]** Gierl and Huettl (2010, *IJRM*): **supply-based scarcity** ("limited edition") works better for **conspicuous** products, and **demand-based scarcity** ("almost sold out") for **non-conspicuous** ones. — [IDEAS](https://ideas.repec.org/a/eee/ijrema/v27y2010i3p225-235.html) · *Segment:* yes · *Apply:* b; a (scarcity claims must still be licensed by the ledger)
- **[MODERATE–STRONG]†** Han, Nunes and Drèze (2010, *JM*): luxury consumers differ in how loudly they want status signalled. "Patricians" prefer quiet, subtle branding and "parvenus" loud branding. — [DOI](https://doi.org/10.1509/jmkg.74.4.015) · *Apply:* b (premium positioning calls for restraint, not hype)
- **[MODERATE]†** Ward and Dahl (2014, *JCR*): being rejected by a snobbish salesperson *increased* desire for **aspirational** luxury brands, but not for non-aspirational ones. — [DOI](https://doi.org/10.1086/676980)
- **[WEAK-FOLKLORE; expert opinion]†** Kapferer and Bastien (2009) set out the luxury "anti-laws of marketing": don't pander, keep distance, don't sell overtly. — [Journal of Brand Management, DOI](https://doi.org/10.1057/bm.2008.51)
- **[MODERATE]†** Services:
  - Zeithaml, Parasuraman and Berry (1985) on the problems intangibility creates (tangible cues, word of mouth, credentials) — [JM, DOI](https://doi.org/10.1177/002224298504900203)†.
  - Murray (1991): service buyers rely more on personal sources and word of mouth — [JM, DOI](https://doi.org/10.1177/002224299105500102)†.
  - Mittal (1999), conceptual, on advertising services — [Journal of Service Research, DOI](https://doi.org/10.1177/109467059921003)†.
  - *Segment:* yes · *Apply:* b, c
- **[MODERATE]** Category heterogeneity even inside one study: in Matz 2024, personality matching worked for a Rome getaway (a hedonic experience) but not for sneakers. — [PMC10897294](https://pmc.ncbi.nlm.nih.gov/articles/PMC10897294)
- **[MODERATE]** Brands matter most at low *and* high purchase risk in B2B (U-shape; Brown et al. 2011, Section 6). — [IDEAS](https://ideas.repec.org/a/eee/ijrema/v28y2011i3p194-204.html)

### Inferences
- **The most actionable level for MarketingOS is matching to the product category**, because the knowledge phase already extracts what the offering is and does.
- **(b) Strategist:** classify each offering, recording the source:

  | Product type | What the email should carry |
  |---|---|
  | Utilitarian | Function, mechanism, specifics |
  | Identity or hedonic | Experience, identity, a justification for the indulgence |
  | Service | Make it tangible: who does what, a concrete deliverable, credentials, testimonials |
  | Luxury or premium | Restraint; never hype or discount framing |
  | Conspicuous | Scarcity, if any, framed as "limited supply", never "almost sold out" (and vice versa for non-conspicuous) |

- **(c) Cold reader:**
  - Utilitarian: "Do I know what it does, and what it costs me in effort?"
  - Identity: "Does this feel like it's for someone like me?"
  - Service: "Do I know concretely what I'd get, and from whom?"
- **(a)** The scarcity framing type could be checked against a product-type tag. But scarcity claims already need licensing, so this is low priority.
- **(d)** The size of any category-matched effect for a given business.

### Gaps
- **The FCB and Rossiter-Percy planning grids** (involvement × think/feel) are widely taught. I could not verify their validation studies in this session (Ratchford 1987, *JAR*).
- I found no category-difference evidence specific to email.
- I found no French or Maghreb category studies beyond Lambert-Pandraud and Laurent (perfume, cars).
- **Research-process note:** the shared web-search budget was exhausted about a third of the way through this assignment. Findings marked † come from prior knowledge with DOI pointers and should be spot-checked before they reach the French report.
