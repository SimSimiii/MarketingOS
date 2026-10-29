# Psychology of persuasion and consumer decision-making for written marketing messages (email copy): an evidence-graded inventory

**Grades.** STRONG = meta-analysis, pre-registered or large-scale replication, or large randomized field experiment. MODERATE = single peer-reviewed study, or a large dataset with a disclosed method. WEAK-FOLKLORE = vendor statistics, unreplicated, or failed replication. When a meta-analysis exists but its bias-corrected or low-risk-of-bias subset erases the effect, the grade follows the corrected estimate.

**Application codes (MarketingOS).** (a) deterministic code check on the text; (b) instruction to the strategist or writer prompt; (c) criterion for the cold reader / critic; (d) measurable only with real send data (dead on arrival today: no users, no telemetry, no send data).

**Verification flags.** † = cited to the primary DOI from prior knowledge, not re-opened in this session. The shared web-search budget ran out partway through, so treat † numbers as "check before quoting verbatim in the French report". Every item without † was read during this session (abstract, full text, or the repository or secondary page that the link names).

**Scope note.** The Upworthy / news-headline studies are the largest randomized evidence base on "what makes a person click a short piece of text". But they are not email and not B2B, so applying them here is an inference. Email-specific studies, pricing and offers, testimonials, culture, legal rules and AI-text perception are out of scope and appear only where they are a mechanism's main application.

**At a glance** (details and sources in the sections below)

| Mechanism | Grade | Status change after replication | Best lever |
|---|---|---|---|
| Reciprocity (unconditional value first) | STRONG | stable | b, d |
| Foot-in-the-door / small first step | MODERATE (small, conditional) | — | b |
| "Sign first" honesty commitment | WEAK-FOLKLORE | failed 2020, data fabricated 2021 | avoid |
| Descriptive social norms (true, majority, relevant group) | STRONG at scale, small effects | effects shrink at new sites; boomerang risk | a, b |
| Hotel-towel "same room" norm | WEAK-FOLKLORE (small, context-bound overall effect) | failed 2014; pooled evidence weak | avoid as recipe |
| Authority / source credibility | MODERATE–STRONG, mostly under low involvement | stable | a, b, c |
| Liking (written) | WEAK–MODERATE | — | b, c |
| Scarcity | MODERATE for stated intentions, WEAK for real behaviour | 2022 meta: 94% hypothetical data | a (license it), d |
| Unity / identity wording ("be a voter") | WEAK-FOLKLORE | failed 2016 | avoid |
| ELM: argument quality × elaboration | STRONG | stable | b, c |
| Behavioural / social priming by words | WEAK-FOLKLORE | collapsed 2012–2017 | avoid |
| Curiosity gap | MODERATE: inverted U; vague clickbait WEAK | refined 2025 (registered report) | a (diagnostic), b, d |
| Self-relevance / tailoring | STRONG but small (r ≈ .07) | stable | b, c |
| Negativity in headlines → clicks | MODERATE–STRONG for news; B2B transfer unknown | 2023 registered report | d |
| Reactance / controlling language | STRONG (theory), MODERATE (manipulations) | stable | a (diagnostic), b, c |
| Persuasion knowledge | STRONG (2022 meta) | stable | b, c |
| "But You Are Free" | WEAK-FOLKLORE | low-risk studies null (2023) | none |
| Real reasons for non-trivial asks | MODERATE | placebic "because" fails for bigger asks | b, c |
| Explicit justification / explicit conclusion | MODERATE–STRONG | stable | a, b |
| Concreteness | MODERATE–STRONG (headlines: inverted U) | refined 2025 | a (diagnostic), b |
| Construal-level "fit" | WEAK-FOLKLORE (now) | 27-country multilab: limited evidence (2025/26) | avoid |
| Fluency → truth/liking; repetition → truth | STRONG | meta data critiqued 2021 | a (diagnostic), b |
| "Disfluency makes people think" | WEAK-FOLKLORE | 17-study pooled null (2015) | avoid |
| Narrative transportation | MODERATE–STRONG, small effects | stable | b, c |
| Fear + efficacy | STRONG | stable | b |
| High-arousal emotion → sharing | MODERATE | not re-tested here | d |
| Loss-framed copy beats gain-framed | WEAK-FOLKLORE | null in metas and in a 200k-person RCT | avoid |
| Loss aversion in choice | STRONG but conditional | debated since 2018 | mostly pricing (out of scope) |
| Anchoring / decoy | anchoring STRONG in lab; decoy WEAK with realistic stimuli | decoy failed 2014 | out of scope (pricing) |
| Choice overload | WEAK as a general law; conditional | 2010 null mean, 2015 moderators | a (count asks), b |
| Defaults | STRONG in general; email cannot impose one | bias-corrected "structure" nudges undecided | b, d |
| Zeigarnik (memory for open loops) | WEAK-FOLKLORE | 2025 meta: no memory advantage | avoid |
| Mere exposure | STRONG, inverted U | — | d |
| Endowed progress / goal gradient | MODERATE (two field studies) | no replication found | b (onboarding only) |
| Nudges overall | small: +1.4 pp at scale | 2022 bias-corrected reanalyses | calibrate expectations |
| Friction reduction, simplification, plan prompts | STRONG | stable | a, b, c |
| Fogg B = MAP | WEAK as a tested model | — | b |

---

## Which of Cialdini's principles hold up in field experiments and meta-analyses, under what conditions, and where have famous demonstrations failed to replicate?

### Takeaway
Two principles have the strongest field evidence: reciprocity (give real value unconditionally, before any ask) and descriptive social norms. But norm effects are small, shrink when a programme moves to new sites, and can boomerang. The famous hotel-towel result is best read as a small, context-dependent effect whose "guests in this room" refinement did not replicate. The rest is weaker. Scarcity evidence is almost entirely hypothetical purchase intentions. Commitment effects are small and conditional, and the celebrated "sign first" honesty nudge failed replication and rested on fabricated data. Authority works mainly as a cue for readers who are not thinking hard. Unity and identity wording have no independent support.

### Cited Findings

**Reciprocity**
- [STRONG] In a field experiment, about 10,000 charity solicitation letters were randomly given no gift, a small gift or a large gift. Relative to no gift, donation frequency rose 17% with the small gift and 75% with the large one, and the earlier working paper reported the gifts were highly profitable for the charity — [Falk 2007, Econometrica](https://www.econometricsociety.org/publications/econometrica/2007/09/01/gift-exchange-field); [IZA DP 1148](https://iza.org/publications/dp/1148)
- [STRONG] Church's (1993) meta-analysis of 38 mail surveys found that prepaid (unconditional) incentives raised response, while promised (conditional) money or gifts did not raise it significantly. Money beat gifts, at an average incentive of about $1.38 in 1989 dollars. Caveat: the prepaid-versus-promised gap was significant only within the four studies that compared both designs head to head — [ASPE review citing Church 1993](https://aspe.hhs.gov/sites/default/files/private/pdf/174381/04.pdf)
- Later survey-methods work (Singer & Ye 2013; Dykema et al. 2015) is cited for the same conclusion: advance incentives beat promised ones — [Survey Practice, Rao 2020](https://www.surveypractice.org/article/12495.pdf)

**Commitment and consistency**
- [MODERATE; small and conditional] Burger's review of foot-in-the-door finds that several processes are at work (self-perception, consistency, commitment, attributions, conformity, reactance). Their combination explains both the successes and the studies where the technique *decreased* compliance. The review identifies the conditions under which it works, building on earlier meta-analyses (Beaman et al. 1983; Dillard et al. 1984) — [Burger 1999, PSPR (CBSM record)](https://cbsm.com/articles/32623-the-foot-in-the-door-compliance-procedure-a-multiple-process-analysis-and-review)
- [WEAK-FOLKLORE; failed] Signing an honesty pledge at the top of a form, rather than the bottom, did not increase honest reporting. Five conceptual replications (n = 4,559) and one high-powered, preregistered direct replication run with the original authors (n = 1,235) all found no effect — [Kristal et al. 2020, PNAS](https://pmc.ncbi.nlm.nih.gov/articles/PMC7132248). In 2021 the original 2012 field data were shown to be fabricated, and the original authors asked PNAS to retract the paper — [Reason / Volokh summary](https://reason.com/volokh/2021/08/22/a-big-study-on-honesty-turns-out-to-be-based-on-fake-data/); [Data Colada](https://datacolada.org/?p=6142)

**Social proof (descriptive norms)**
- The original hotel-towel study: a card saying most guests reuse their towels beat the standard environmental card, and a "guests who stayed in this room" (provincial) norm did best (roughly 44% vs 35% reuse in Study 1†) — [Goldstein, Cialdini & Griskevicius 2008, JCR](https://doi.org/10.1086/586910) †
- [Failed replication] Two German hotels (Study 1 N = 724; Study 2 N = 204): the "75% of guests reused" descriptive-norm card was *not* more effective than the standard environmental message, and the proximity (provincial) effects were inconsistent. An earlier US resort study by Schultz and colleagues found that only the general norm, not the provincial one, beat control — [Bohner & Schlüter 2014, PLoS ONE](https://pmc.ncbi.nlm.nih.gov/articles/PMC4118982/)
- A Bayesian synthesis of seven towel experiments reported a Bayes factor of about 36 in favour of an effect — [Scheibehenne, Jamil & Wagenmakers 2016, Psychological Science](https://dare.uva.nl/id/e1d96b38-85c1-42ec-9899-a65acb417f57). It was contradicted by a reanalysis arguing the Bayes factor was inflated by pooling heterogeneous studies, a one-sided prior and a fixed effect, leaving at best weak evidence — [Carlsson, Schimmack, Williams & Bürkner, Replication Index](https://replicationindex.com/2016/11/28/bayesian-meta-analysis-the-wrong-way-and-the-right-way/). A fully Bayesian re-estimate puts mean reuse at about 50% in control versus 56% with the norm card — [Frontiers opinion](https://frontiersin.org/journals/applied-mathematics-and-statistics/articles/10.3389/fams.2017.00012/full). A meta-analysis of hotel-guest interventions found the norm effect weaker than earlier reports but consistent, a modest increase — [Nisa, Varum & Botelho, repository copy](https://thuvienso.hoasen.edu.vn/items/e533fe78-384b-4ded-850d-cbb86969a901/full)
- [STRONG] UK tax letters (HMRC). Adding social-norm sentences to standard reminder letters raised payment of overdue tax (more than 200,000 people). In a second experiment (119,527 taxpayers), descriptive norms beat injunctive ones, and the best line was "Nine out of ten people in the UK pay their tax on time". There was no evidence that loss framing beat gain framing, and about £9M more was collected over 23 days — [Hallsworth, List, Metcalfe & Vlaev, NBER w20007](https://www.nber.org/papers/w20007); [J Public Econ 2017, Warwick WRAP](https://wrap.warwick.ac.uk/88777)
- [STRONG, with decay] Opower peer-comparison energy reports cut consumption by about 2% on average† — [Allcott 2011](https://doi.org/10.1016/j.jpubeco.2011.03.003) †. Across 111 RCTs (8.6 million households), the first ten sites substantially overstated the effect for the next 101. Early-adopting utilities had more environmentally minded, more responsive customers, and early targeting went to heavy users — [Allcott 2015, "Site selection bias", NBER](https://www.nber.org/papers/w18373)
- [STRONG†; boomerang] Telling households their usage relative to the neighbourhood average *raised* consumption among those already below average, unless an approving injunctive cue (a smiley face) was added — [Schultz et al. 2007, Psych Science](https://doi.org/10.1111/j.1467-9280.2007.01917.x) †
- [MODERATE] A meta-analysis of norm appeals (110 articles) concludes that injunctive norms are under-used and may change behaviour more than assumed — [Rhodes, Shulman & McClaran 2020, Human Communication Research](https://doi.org/10.1093/hcr/hqz023). This conflicts with the HMRC field result that descriptive beat injunctive — [NBER w20007](https://www.nber.org/papers/w20007)
- [STRONG field, single setting] In randomized restaurant tables, showing the "top 5 most popular dishes" raised demand for those dishes by about 13–20%. Showing five dishes *without* a popularity label had no significant effect (no saliency effect), and the effect was modestly stronger for infrequent customers. This is observational learning from popularity — [Cai, Chen & Fang 2009, AER (NBER w13516)](https://www.nber.org/papers/w13516); [Yale ISPS](https://isps.yale.edu/research/publications/isps09-029)

**Authority**
- [MODERATE–STRONG; narrative review of five decades] Main-effect studies favour high-credibility sources, but interaction studies show credibility can be a liability under some conditions. Moderators fall into source, message, channel, receiver and destination variables — [Pornpitakpan 2004, J Applied Social Psychology](https://cir.nii.ac.jp/crid/1363670320943032448)
- [STRONG† classic] Source expertise drove attitudes when the topic had low personal relevance to the reader; argument quality drove them when relevance was high — [Petty, Cacioppo & Goldman 1981, JPSP](https://doi.org/10.1037/0022-3514.41.5.847) †

**Liking**
- [MODERATE] In more than 1,000 real customer-service interactions at two firms (over 30 controls), concrete agent language raised satisfaction. In a second dataset of email exchanges with an online retailer, it raised later purchase volume. Customers read concreteness as evidence that the agent was listening — [Packard & Berger 2021, JCR (Wharton summary)](https://knowledge.wharton.upenn.edu/article/how-language-boosts-customer-satisfaction/)

**Scarcity**
- [MODERATE for intentions; WEAK for behaviour] A meta-analysis of 416 effect sizes from 131 studies found that demand-based scarcity works best for utilitarian products, supply-based scarcity for experiences, and time-based scarcity for high-involvement products — [Barton, Zlatevska & Oppewal 2022, Journal of Retailing (abstract)](https://research.monash.edu/en/publications/scarcity-tactics-in-marketing-a-meta-analysis-of-product-scarcity/). The full text adds:
  - Pooled effects on purchase intentions are about δ ≈ 0.31 (between-subjects designs, k = 156) and 0.48 for within-subjects designs (k = 22).
  - Only 24 of the 416 effect sizes measured actual behaviour and only 6 came from field studies; 384 measured hypothetical situations.
  - The effect is about twice as large for low-familiarity brands (δ = 0.41 vs 0.21).
  - Publication bias was assessed only with Rosenthal's fail-safe N.
  - Lynn's 1991 meta-analysis found r = 0.12 for scarcity on perceived value, with significant heterogeneity.
  - Reactance is named as a likely but untested mechanism when consumers feel their freedom to choose is restricted.

  Source: [Barton et al. 2022, full text](https://pure.bond.edu.au/ws/portalfiles/portal/182976505/Scarcity_tactics_in_marketing.pdf)

**Unity / identity**
- Cialdini's most recent edition adds a seventh lever, "unity" — [Wikipedia, Influence](https://en.wikipedia.org/wiki/Influence:_Science_and_Practice)
- [WEAK-FOLKLORE; failed] Bryan et al. reported large turnout gains (about 11–14 pp) from noun wording ("be a voter") over verb wording ("vote") — [Bryan et al. 2011, PNAS](https://doi.org/10.1073/pnas.1103343108) †. A large field replication found no effect on turnout, both framings did worse than a standard get-out-the-vote message, and later preregistered attempts were also null — [Gerber, Huber, Biggers & Hendry 2016, PNAS](https://pmc.ncbi.nlm.nih.gov/articles/PMC4932923); [Yale ISPS](https://isps.yale.edu/research/publications/isps16-06)

### Inferences
- **Reciprocity.** STRONG for unconditional value in mail. I found no study of "content gifts" in B2B cold email.
  - (b) When the Evidence Ledger holds a genuinely useful free asset (a checklist, a benchmark, a tool), the strategist can make the email *give* it, ungated and with no "in exchange for a call", before or instead of asking.
  - (c) Critic question: "If you never reply, did you still get something?"
  - (d) Only send data can show a reply-rate effect.
  - The prepaid > promised pattern argues against conditional framings ("book a call and get the report").
- **Commitment.** MODERATE and small. The existing strategist rule "smallest verified step" fits the foot-in-the-door literature (b). Never fabricate prior commitments ("as you said…"). A sequence may refer only to actions the reader really took. Drop any "sign first"-style commitment devices: failed and fraudulent.
- **Social proof.** The robust form is a *true*, *majority*, *relevant-group* descriptive norm (HMRC, Opower). There are three known risks: boomerang (Schultz), decay at new sites (Allcott), and messages that publicise how many people do the *wrong* thing.
  - (a) A cheap, principled extension of `gates.py`: license **quantifier words** as well as numerals ("most", "the majority", "thousands of", "leading", and in French "la plupart", "la majorité", "des milliers", "leader", "n°1") against the ledger. A majority claim with no ledger support is a factual claim the code can check, so blocking it fits the "only code blocks" rule.
  - (b) Writer: phrase norms about a relevant peer group only when the ledger has the number, and never stress that "many fail to…".
  - (c) Cold reader: "Do you believe the proof, and is it about people like you?"
  - The popularity-ranking result (Cai et al.) suggests that "most chosen" information works through observational learning. Learning needs a credible count, which again means licensing.
- **Authority.** It mainly helps readers who are *not* scrutinising, which describes a cold reader at open.
  - (a) Credentials, awards, client names and certifications should be licensed like quotations and numbers.
  - (b) Writer: name the source of each claim (see explicitness, section 5).
  - (c) "Who is saying this, and why believe them?"
- **Liking.** Grading for written copy is WEAK–MODERATE. The defensible mechanism is "you listened", shown through concrete references to the reader's situation (Packard & Berger), not flattery.
  - (b) Already present: the writer prompt's "Specifics, not adjectives" and "Recognition, not surveillance" rules (repo observation, `backend/prompts/writer.md`).
  - (c) The existing `situation_matches` criterion in `backend/prompts/reader.md` serves this.
- **Scarcity.** Treat it as a factual claim, never a tactic.
  - (a) Block any deadline or limited-quantity wording the ledger does not support: "until Friday", "only N left", "last chance", "expires", "limited spots", and in French "offre valable jusqu'au", "plus que N", "dernière chance", "places limitées". This is the same licensing logic as for numbers and dates.
  - Its effect on real email behaviour is unmeasured (d), and the meta-analysis evidence is mostly students and hypothetical scenarios.
  - The writer prompt already forbids inventing a deadline (repo observation).
- **Unity / identity.** Do not encode identity-label tricks ("as a founder like you…", "be the kind of leader who…") as rules: the flagship study failed. Mention shared identity only when it is true and in the ledger.

### Gaps
- Meta-analyses of the low-ball technique (Burger & Caputo 2015 is reported to exist) and of door-in-the-face were not retrieved; their status is unverified here.
- No replication or meta-analytic evidence on similarity- or compliment-based liking in *written* marketing was retrieved.
- No independent empirical test of "unity" as a distinct principle was found; only its addition to the book is confirmed.
- No study of reciprocity through free content in cold or B2B email was found.
- The exact effect size from the Nisa et al. hotel meta-analysis was not retrieved.

---

## What do dual-process models (ELM, heuristic-systematic model, System 1/System 2) imply for copy when involvement is high versus low, and what do argument quality and peripheral cues do in each case?

### Takeaway
The ELM's central prediction holds up meta-analytically. Argument quality drives attitude change when readers are motivated and able to think; peripheral cues (source, number of arguments, attractiveness) matter more when they are not. Self-relevance is the main switch that raises elaboration, but more elaboration helps only *strong* arguments. The popular "System 1" add-on, that subtle word primes steer behaviour, collapsed in replication and should not be encoded.

### Cited Findings
- [STRONG] A meta-analysis of the ELM's argument quality × processing type predictions confirmed the central interaction — [Carpenter 2015, Human Communication Research 41(4), 501–534 (citation listed here)](https://www.cambridge.org/core/journals/behavioral-and-brain-sciences/article/abs/how-research-on-persuasion-can-inform-dualprocess-models-of-judgment/4D3F359F440C22BC8354028A608A0D9E). The figure of 134 studies comes from a secondary summary — [Simply Psychology](https://www.simplypsychology.org/elaboration-likelihood-model.html)
- [STRONG† classic] When personal relevance was high, argument quality determined attitudes; when it was low, source expertise did — [Petty, Cacioppo & Goldman 1981](https://doi.org/10.1037/0022-3514.41.5.847) †. Under low involvement, *more* arguments persuaded regardless of quality (argument count acting as a cue); under high involvement, quality dominated — [Petty & Cacioppo 1984, JPSP](https://doi.org/10.1037/0022-3514.46.1.69) †
- [STRONG† classic] In the heuristic-systematic model, heuristic cues such as communicator likability carried more weight under low involvement and message arguments under high involvement — [Chaiken 1980, JPSP](https://doi.org/10.1037/0022-3514.39.5.752) †. People high in need for cognition elaborate more and respond more to argument quality — [Cacioppo, Petty, Feinstein & Jarvis 1996, Psych Bulletin](https://doi.org/10.1037/0033-2909.119.2.197) †
- [MODERATE] Copy that prompts self-referencing increased elaboration and persuasion *when arguments were strong*. When other elaboration-enhancing factors were already present, the benefit was moderated or reversed — [Burnkrant & Unnava 1995, JCR](https://ideas.repec.org/a/oup/jconrs/v22y1995i1p17-26.html). Moderate self-reference enhanced persuasion and extreme self-reference undermined it, and only for highly motivated viewers — [Meyers-Levy & Peracchio 1996, JCR](https://ideas.repec.org/a/oup/jconrs/v22y1996i4p408-23.html)
- [MODERATE field data] Across thousands of Upworthy headline A/B tests, deliberation-related language increased click-through, consistent with the ELM. The effect was stronger when the headline also incited curiosity — [Banerjee & Urminsky 2025, Marketing Science (working-paper PDF)](https://home.uchicago.edu/ourminsky/Banerjee_Urminsky_Headlines.pdf); [published version](https://pubsonline.informs.org/doi/fpi/10.1287/mksc.2021.0018)
- [WEAK-FOLKLORE; collapsed] An R-Index audit of the priming studies in *Thinking, Fast and Slow* rated chapter 4 at 19, with 11 of its 12 cited articles below 50. Kahneman publicly accepted that the evidence was much weaker than he had believed — [Schimmack, Heene & Kesavan 2017](https://replicationindex.com/2017/02/02/reconstruction-of-a-train-wreck-how-priming-research-went-of-the-rails/); [Mind Hacks summary](https://mindhacks.com/2017/02/16/how-replicable-are-the-social-priming-studies-in-thinking-fast-and-slow/). Many Labs 1 replicated anchoring and framing but not flag or currency priming — [Klein et al. 2014, Social Psychology](https://doi.org/10.1027/1864-9335/a000178) †

### Inferences
- A cold email meets a reader with **low motivation** (unsolicited) and **low ability** (skimming in an inbox) at the open and first lines. Peripheral processing governs that stage. The readers who keep going are the ones for whom the opening made the message self-relevant, and for them argument quality decides. This argues for a **two-stage design**:
  - Stage 1 (subject plus first lines): make the reader's situation concrete, to earn elaboration.
  - Stage 2 (body): carry a few strong, specific, licensed arguments, because weak arguments under high relevance backfire (Burnkrant & Unnava).
- (a) `substantiation.py` ("did the email spend the evidence it was built on") is already a code-level proxy for argument quality, and `clarity_gate` makes sure the offer is identifiable on either route. Both are well grounded.
- (b) Strategist: for each email, state what the reader can be assumed to know and care about at open, and put the strongest licensed argument where a skimmer will see it. Do not pad with extra claims to look substantial. The "more arguments" cue works only on non-thinkers and hurts the readers who matter.
- (c) Cold reader: keep `biggest_doubt` as the argument-quality probe. Add an ELM-style thought-listing question: "Which points do you remember, and which one would you argue with?" Unremembered or contested points mark weak arguments.
- Do not encode "power words", priming vocabulary or System-1 word tricks (WEAK-FOLKLORE).

### Gaps
- The full text of Carpenter 2015 (effect sizes, moderators) was not read; the "134 studies" figure comes from a secondary source.
- Critiques that ELM "argument quality" is defined circularly by pretests (O'Keefe) and the unimodel alternative (Kruglanski & Thompson) were not retrieved.
- No study applying the ELM to B2B or cold email was found.

---

## Attention and curiosity: information-gap theory, novelty, self-relevance, and what predicts that a reader opens and keeps reading

### Takeaway
Curiosity follows an inverted U in how much a headline gives away. In the largest registered analysis (8,977 Upworthy tests), making *vague* headlines more concrete raised clicks, making *already concrete* ones more concrete lowered them, and most headlines sat on the "too concrete" side. Clickbait as such does not create more curiosity and can cost credibility. Negative words raise clicks on news and positive words lower them. Tailoring has a small but reliable effect. And field tests show that wording rules taken from the literature get the *sign* wrong about as often as right.

### Cited Findings
- [STRONG† theory] Curiosity arises when attention is drawn to a gap in one's knowledge, and it needs some prior knowledge in order to be felt — [Loewenstein 1994, Psych Bulletin](https://doi.org/10.1037/0033-2909.116.1.75) †. Curiosity peaks at intermediate confidence about the answer (an inverted U) — [Kang et al. 2009, Psych Science](https://doi.org/10.1111/j.1467-9280.2009.02402.x) †
- [MODERATE–STRONG; registered report, about 9k field experiments] Le Quéré & Matias 2025 (Scientific Reports), "When curiosity gaps backfire":
  - Data: 8,977 Upworthy tests and 35,910 headlines, scored with a word-norm concreteness measure (r = 0.61 with human raters).
  - The interaction between a headline's concreteness and the test's mean concreteness was negative (−0.058, p < .001).
  - More concreteness raised click-through only where the competing headlines were vague (about 8.7% of tests) and lowered it where they were already concrete (about 50.9% of tests). In one example, the more concrete variant drew 1.06% clicks against 1.17% (−9.9%).
  - The authors explain the result with information-gap theory, and say omitting too much information backfires.

  Source: [Le Quéré & Matias 2025, Scientific Reports](https://pmc.ncbi.nlm.nih.gov/articles/PMC11704130/)
- [MODERATE–STRONG; thousands of field A/B tests] Banerjee & Urminsky's results (from the working-paper PDF; coefficient sign and significance):
  - Raised click-through: forward-reference cues such as unresolved pronouns, deliberation language, sight-related sensory words, numeric fluency, concreteness, and emotional intensity.
  - Lowered it: "information-seeking" cues (promising to answer a question or teach something), positive emotion, "writer-to-reader" address, and plural social cues.
  - In the Lasso model, fewer effects were significant in the direction the literature predicted (3) than in the opposite direction (6); in the Bonferroni model it was 5 versus 4.
  - The authors conclude that prior research does not reliably predict the *direction* of textual effects.

  Sources: [Banerjee & Urminsky 2025 (PDF)](https://home.uchicago.edu/ourminsky/Banerjee_Urminsky_Headlines.pdf); [Marketing Science](https://pubsonline.informs.org/doi/fpi/10.1287/mksc.2021.0018)
- [MODERATE–STRONG; registered report] Robertson et al. 2023, Nature Human Behaviour, "Negativity drives online news consumption":
  - Each additional negative word raised click-through by 2.3% for an average-length headline, and each positive word lowered it by about 1.0%.
  - Sadness raised click-through; joy and fear lowered it; anger had no significant effect.
  - The analysis covered 12,448 trials and 53,699 headlines after filtering.

  Source: [Robertson et al. 2023 (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10202797/)
- The underlying corpus is 32,487 headline experiments from US media — [Upworthy Research Archive, Matias et al. 2021](https://pure.psu.edu/en/publications/the-upworthy-research-archive-a-time-series-of-32487-experiments-/)
- [MODERATE] Three studies found that clickbait headlines did not generate more curiosity than non-clickbait ones, and that clickbait detectors agreed with each other only 47% of the time — [Penn State, CHI 2021](https://pure.psu.edu/en/publications/does-clickbait-actually-atract-more-clicks-three-clickbait-studie/). In a single-publisher test, headline format (traditional, forward-referencing, question) did not change engagement, but question headlines were seen as less credible — [KQED experiment](https://www.kqed.org/about/13722/experimenting-with-science-news-headline-format-to-maximize-engagement)
- [STRONG; small] Tailored print health messages beat untailored ones on behaviour change (57 studies, N = 58,454, r = .074), with many moderators — [Noar, Benac & Harris 2007, Psych Bulletin](https://pubmed.ncbi.nlm.nih.gov/17592961/)
- [STRONG†] Self-referent encoding improves memory relative to other encoding (the self-reference effect meta-analysis) — [Symons & Johnson 1997, Psych Bulletin](https://doi.org/10.1037/0033-2909.121.3.371) †
- [MODERATE] Second-person "you" is used in narrative persuasion to make people think about someone in their own lives (song-success evidence) — [Packard & Berger 2020, Psych Science, as described in the Banerjee & Urminsky review](https://doi.org/10.1177/0956797620902380). This contrasts with the negative coefficient for "writer-to-reader" cues in headlines — [Banerjee & Urminsky (PDF)](https://home.uchicago.edu/ourminsky/Banerjee_Urminsky_Headlines.pdf)

### Inferences
- **Subject lines and opening lines.** The best-supported rule is *specific about the topic, not a full spoiler*: name the concrete thing (object, number, mechanism) and leave the "how" or "why" to the body. Both extremes lose clicks: vague teasers ("a quick question", "this changes everything") and lines that hand over the whole payoff.
  - The writer prompt's subject rule ("4-8 words, concrete, no clickbait") is consistent with the vague-side finding (repo observation). Most Upworthy headlines were too concrete, though, so "maximally concrete" is not the optimum either.
- (a) A deterministic concreteness score is feasible: word concreteness norms, with named entities scored at the maximum, as Le Quéré & Matias did. Add an unresolved-reference detector for "this/these/here's why" or "voici pourquoi/ce que" with no noun. Use both as *diagnostics* passed to the critic, not gates. Upworthy thresholds will not transfer to B2B email.
- (b) Writer: avoid "learn / discover / find out" promises in subject lines (negative in field data). Avoid upbeat positive-emotion wording as a hook. Do not manufacture negativity: the writer prompt already forbids inventing a problem (repo observation).
- (c) Cold reader: "From the subject alone, what do you expect this email to tell you, and do you want to know?" This tests whether there is a gap *and* whether it can be decoded, the subject-line counterpart of `BlindRead.understood`.
- (d) Where the optimum sits on the concreteness curve, and whether negativity helps or hurts in B2B outreach, can only be learned from send data.
- **Meta-lesson for the judge.** Literature-derived wording heuristics got the sign wrong roughly as often as right (Banerjee & Urminsky), and experts could not pick winning messages (section 6). A model's click estimate (`pull`) is therefore a weak instrument. That supports the project's existing rule that judgment never blocks, and its choice to make comprehension the one thing the reader decides.
- **Self-relevance.** Its effect is reliable but small, and too much backfires (Meyers-Levy & Peracchio). That fits "Recognition, not surveillance".

### Gaps
- Novelty and distinctiveness (von Restorff-type effects) as drivers of reading marketing text were not researched. `sameness.py` is a distinctiveness proxy with no direct evidence behind it here.
- What predicts *continued reading* of a body, as opposed to clicking a headline, has no field evidence comparable to the headline archives. Fluency and friction evidence (sections 5 and 7) is the nearest proxy.
- Transfer from US news headlines to French or B2B email subject lines is untested.
- Email-specific studies of open rates and personalised subject lines are out of scope and covered by other researchers.

---

## Resistance: psychological reactance (controlling language), the Persuasion Knowledge Model, the "But You Are Free" technique, and how overt sales pressure lowers compliance

### Takeaway
Reactance is real and measurable (anger plus negative thoughts), and controlling language is a dependable trigger. Persuasion knowledge, strongest whenever the ulterior motive is obvious (as in any cold sales email), cuts persuasion substantially without erasing it. "But You Are Free", long cited as doubling compliance, shows *no* effect in the only low-risk-of-bias studies and works mainly face to face. The defensible lesson is copy that supports autonomy, is transparent and does not pressure, not a magic phrase.

### Cited Findings
- [STRONG; meta-analysis] Across 20 studies (N = 4,942), reactance is best modelled as an intertwined mix of anger and negative cognitions — [Rains 2013, Human Communication Research](https://academic.oup.com/hcr/article-abstract/39/1/47/4093682). A 50-year review of reactance theory exists — [Rosenberg & Siegel 2018, Motivation Science](https://facultyprofiles.dominican.edu/en/publications/a-50-year-review-of-psychological-reactance-theory-do-not-read-th/)
- [MODERATE] High-controlling health messages ("must", "need to") raised perceived threat to freedom and reactance, and a postscript restoring choice reduced it† — [Miller et al. 2007, Human Communication Research (record)](https://katalog.adlr.link/Record/ai-49-aHR0cDovL2R4LmRvaS5vcmcvMTAuMTExMS9qLjE0NjgtMjk1OC4yMDA3LjAwMjk3Lng?lng=en) †findings. A high-controlling version of a message discouraging meat consumption evoked more reactance — [Information 2019 (DOAJ)](https://doaj.org/article/cdaa13f35c944398b785a82c501fe59a)
- [MODERATE†] Assertive phrasing persuaded when the audience already saw the issue as important, and gentler phrasing worked better otherwise — [Kronrod, Grinstein & Wathieu 2012, Journal of Marketing (record)](https://research.vu.nl/en/publications/go-green-should-environmental-messages-be-so-assertive/) †findings
- [Theory†] The Persuasion Knowledge Model: consumers learn persuasion tactics and use that knowledge to cope with persuasion attempts — [Friestad & Wright 1994, JCR](https://doi.org/10.1086/209380) †
- [MODERATE–STRONG] When a salesperson's ulterior motive is highly accessible, both cognitively busy targets and unbusy observers use persuasion knowledge to discount him. When it is less accessible, busy targets judge him *more* sincere — [Campbell & Kirmani 2000, JCR](https://ideas.repec.org/a/oup/jconrs/v27y2000i1p69-83.html)
- [STRONG; meta-analysis] Across 148 papers and 171 datasets, persuasion-knowledge effects are substantial but do not eliminate persuasion; they reach about 50% of the explanatory power of persuasion, and depend on features of the persuasion process — [Eisend & Tarrahi, Journal of Consumer Psychology 2021/2022 (EconStor)](https://www.econstor.eu/handle/10419/284829)
- Carpenter's original "But You Are Free" meta-analysis (42 studies) reported that people were about twice as likely to say yes — [Carpenter interview 2025](https://muddyrivernews.com/communities/illinois/wiu-professor-chris-carpenter-receives-prestigious-2025-meta-analysis-award/20250717085800/)
- [WEAK-FOLKLORE; status changed 2023] Fillon et al.'s preregistered re-examination, Meta-Psychology vol. 7 (2023):
  - 52 experiments, N = 19,528, 74 effect sizes, overall g = 0.44 [0.36, 0.51].
  - The only significant moderator was face-to-face interaction.
  - R-index 9.77%, expected discovery rate 6%.
  - Only seven studies were rated low risk of bias, and together they show **no effect** (g = 0.11 [−0.18, 0.40]).
  - Articles published before and after Carpenter 2013 do not differ.

  Source: [Fillon, Souchet, Pascual & Girandola 2023, Meta-Psychology](https://open.lnu.se/index.php/metapsychology/article/view/2640)
- Scarcity researchers name reactance as the likely mechanism when consumers feel forced or limited in their freedom to choose, a framework still untested meta-analytically — [Barton et al. 2022](https://pure.bond.edu.au/ws/portalfiles/portal/182976505/Scarcity_tactics_in_marketing.pdf)

### Inferences
- In a cold sales email the ulterior motive is maximally accessible, so the conditions of Campbell & Kirmani's "high accessibility" arm apply by default. Visible tactics (fake familiarity, manufactured urgency, flattery, guilt) are discounted. With persuasion-knowledge effects around half the size of persuasion itself, a tactic-laden email loses much of what the tactic adds.
  - The evidence-consistent strategy is transparency: say what is offered (which `clarity_gate` already enforces) and let the argument carry the weight.
- (a) Two deterministic checks, with different status:
  - **Fake urgency / scarcity**: block unless licensed. This is a truth check, as in section 1.
  - **Controlling-language density**: *diagnostic only*. EN lexicon: "you must", "you need to", "you have to", "don't miss", "act now", "hurry", "last chance". FR: "vous devez", "il faut", "ne manquez pas", "agissez", "dépêchez-vous", "n'attendez plus". Add counts of imperatives, exclamation marks and capitalised words. Feed the result to the critic and the rewrite step rather than blocking, since how controlling a phrase feels is graded taste.
- (b) Writer: recommend rather than command, attach a reason to each ask, offer a low-commitment next step, and keep an explicit exit available. The writer prompt already has a "Permission to browse without…" pattern (repo observation). Kronrod et al. suggest assertiveness is acceptable only when the reader already cares about the issue, which is rarely the case for a cold reader.
- (c) Cold reader: "Which sentence felt like a tactic or like pressure?" and "Did you feel free to ignore this?" A reader can answer these from the text alone.
- **BYAF:** do not encode it as a rule or a gate. The effect rests on high-risk-of-bias studies, and the robust part is face to face. If tried at all, it is a (d) A/B item.

### Gaps
- No study of overt sales pressure in *written* email was retrieved. The evidence here is face-to-face sales (Campbell & Kirmani), health messages and general meta-analyses.
- The full text of Miller et al. 2007 and Kronrod et al. 2012 was not read, so their direction-of-effect statements are †.
- Whether a "the choice is yours" postscript works in marketing email (as opposed to health messages) is unknown.
- Evidence on two-sided messages (acknowledging a limitation to gain credibility; O'Keefe 1999, Eisend 2006) was not retrieved. It matters for MarketingOS's "narrow the argument to the part it improves" practice and should be checked.

---

## Reason-giving, concreteness, processing fluency and readability, narrative transportation, emotion versus rational argument, and identity ("people like us")

### Takeaway
Explicit, real reasons and explicit conclusions reliably help, but a placebic "because" works only for trivial asks. Concrete language helps in field data and signals that the writer listened, though headlines can be too concrete. Fluency raises perceived truth and liking (robust), while the claims that disfluency makes people think harder, and that construal-level "fit" matters, both failed large replications. Narratives persuade with small effects and move intentions more than beliefs; statistics do better for beliefs. Fear works when paired with efficacy. Noun-identity wording failed.

### Cited Findings

**Reasons and explanation**
- [MODERATE; classic, no modern registered replication found] Langer, Blank & Chanowitz 1978, the copier-queue study:
  - Small request (5 pages): about 60% complied with no reason, 93% with a placebic reason ("because I have to make copies") and 94% with a real reason.
  - Large request (20 pages): about 24% complied with no reason, 24% with the placebic reason and 42% with the real reason.

  Sources: [figures as reported by atticusli.com](https://www.atticusli.com/replication-crisis/power-of-because-langer-1978/); [Psychology Today](https://www.psychologytoday.com/ca/blog/brain-wise/201310/the-power-of-the-word-because-to-get-people-to-do-stuff); [original, JPSP](https://doi.org/10.1037/0022-3514.36.6.635) †
- [MODERATE–STRONG; meta-analytic] O'Keefe's meta-analyses of support articulation found that making supporting arguments and information sources more explicit improved persuasiveness and credibility, though not always significantly. The proposed mechanisms are closer scrutiny of a solid argument and explicit support read as a sign of merit. Caveat: weak support may not help — [O'Keefe, ISSA 2002 paper summarising the justification-explicitness meta-analysis](https://rozenbergquarterly.com/issa-proceedings-2002-persuasive-success-and-normatively-desirable-argumentative-conduct-is-it-persuasively-bad-to-be-normatively-good/?print=pdf); [ISSA 1998, citing information sources](https://rozenbergquarterly.com/issa-proceedings-1998-argumentation-explicitness-and-persuasive-effect-a-meta-analytic-review-of-the-effects-of-citing-information-sources-in-persuasive-messages/). A separate meta-analysis of 35 comparisons found explicit conclusions (standpoints) more persuasive than implicit ones — [as summarised in ISSA 2010 proceedings](https://rozenbergquarterly.com/issa-proceedings-2010-variations-of-standpoint-explicitness-in-advertising-an-experimental-study-on-probability-markers/?print=pdf)

**Concreteness and specificity**
- [MODERATE–STRONG; field data] In customer service, concrete agent language raised satisfaction (1,000+ interactions, two firms) and, in email exchanges, later purchases. Example: "I can help you find a firm mattress for your guest room" rather than "I can help you with that" — [Packard & Berger 2021, JCR (Wharton)](https://knowledge.wharton.upenn.edu/article/how-language-boosts-customer-satisfaction/)
- [MODERATE–STRONG] In headlines, concreteness helps only when the competing headlines are vague (the inverted U above) — [Le Quéré & Matias 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC11704130/). Concreteness also appears among the positive headline features in [Banerjee & Urminsky](https://home.uchicago.edu/ourminsky/Banerjee_Urminsky_Headlines.pdf)
- [WEAK-FOLKLORE for "fit" advice; status changed 2025/26] CLIMR, a multilab registered report (AMPPS 2026; 2025 preprint), tested four construal-level predictions:
  - N = 11,775 across 27 countries.
  - The authors found limited evidence for the theory. The spatial-distance effect was d = 0.04 (original 0.55). The social-distance effect went the wrong way (d = −0.27), a result traced to a valence confound (d = 0.006 once controlled).
  - A critical commentary disputes sample quality and reports a temporal-distance effect in a reanalysis and a new study.

  Sources: [APS journal page](https://www.psychologicalscience.org/journals/ampps/25152459261428024/); [City Research Online preprint](https://openaccess.city.ac.uk/id/eprint/36132/)

**Processing fluency and readability**
- [MODERATE] Needlessly complex vocabulary lowered readers' judgements of the author's intelligence — [Oppenheimer 2006, Applied Cognitive Psychology](https://doi.org/10.1002/acp.1178) (DOI confirmed; finding †). Fluency acts as a general metacognitive cue across judgement domains — [Alter & Oppenheimer 2009, PSPR](https://doi.org/10.1177/1088868309341564) †. Easier-to-read statements (high colour contrast) were judged true more often — [Reber & Schwarz 1999](https://doi.org/10.1006/ccog.1999.0386) †
- [STRONG; meta-analysis, with a data critique] Repetition raises the perceived truth of statements (51 studies; a medium effect, d ≈ 0.50, as cited by later reviews; between-items effects larger than within-items), and the effect is interpreted as fluency — [Dechêne et al. 2010, PSPR](https://edoc.unibas.ch/10139). A 2021 registered systematic map says the 2010 meta imputed variances without reporting how many and showed no funnel plot, so its bias conclusions cannot be checked — [Henderson et al. 2021, Psychonomic Bulletin & Review](https://link.springer.com/10.3758/s13423-021-01995-w)
- [WEAK-FOLKLORE; failed] Pooling the original "hard-to-read font improves reasoning" experiment with 16 replications showed no effect on Cognitive Reflection Test accuracy; responses were only slightly slower — [Meyer et al. 2015, JEP: General](https://digitalcommons.georgiasouthern.edu/psych-facpubs/85)
- [MODERATE†] Instructions printed in a hard-to-read font made a task seem harder and more effortful — [Song & Schwarz 2008, Psych Science](https://doi.org/10.1111/j.1467-9280.2008.02189.x) † (replication status not checked)
- [MODERATE; email-specific, secondary coverage; out of scope beyond this mention] Sent to about 7,000 school-board members, a 49-word request drew 4.8% responses against 2.7% for a 127-word version. 29% of the short-version recipients believed the survey would take under five minutes, against 15% for the long version — [Inc. coverage of Rogers & Lasky-Fink](https://www.inc.com/jessica-stillman/double-your-chance-of-getting-a-response-to-emails-by-making-them-shorter.html); [MediaPost](https://www.mediapost.com/publications/article/388988/the-long-and-the-short-of-it-harvard-study-finds.html)

**Narrative transportation**
- [Theory†] Being "transported" into a narrative is associated with story-consistent beliefs — [Green & Brock 2000, JPSP](https://doi.org/10.1037/0022-3514.79.5.701) †
- [MODERATE–STRONG; meta-analysis] Across 132 effect sizes from 76 articles, transportation rises with identifiable characters, imaginable plots and plausible events — [van Laer et al. 2014, JCR](https://openaccess.city.ac.uk/id/eprint/6755/)
- [STRONG; meta-analysis] Narratives have small positive associations with beliefs, attitudes, intentions and behaviours — [Braddock & Dillard 2016, Communication Monographs](https://doi.org/10.1080/03637751.2015.1128555) (DOI †; result as summarised by search). Statistical evidence beat narrative evidence for beliefs and attitudes, while narrative evidence beat it for intentions — [Zebregs et al. 2015, Health Communication](https://pubmed.ncbi.nlm.nih.gov/24836931/)

**Emotion versus rational argument**
- [STRONG; meta-analysis] Fear appeals are effective overall (127 articles, 248 samples, N = 27,372). They are stronger when the message includes **efficacy statements**, depicts high susceptibility and severity, and recommends a one-time behaviour; backfiring is reported as rare — [Tannenbaum et al. 2015, Psych Bulletin](https://pubmed.ncbi.nlm.nih.gov/26501228/)
- [MODERATE†] In New York Times articles, high-arousal emotions (awe, anger, anxiety) increased sharing, sadness decreased it, and positive content was shared more than negative — [Berger & Milkman 2012, JMR](https://doi.org/10.1509/jmr.10.0353) †
- [MODERATE–STRONG] For *clicks* on news headlines, negativity and sadness helped, while joy and fear hurt — [Robertson et al. 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10202797/). Emotional intensity raised click-through and positive emotion lowered it — [Banerjee & Urminsky](https://home.uchicago.edu/ourminsky/Banerjee_Urminsky_Headlines.pdf)

**Identity / "people like us"**
- [WEAK-FOLKLORE; failed] Noun-identity wording did not move behaviour in a large field test — [Gerber et al. 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC4932923)
- [MODERATE] Provincial "people like you / in this room" norms were inconsistent in replications — [Bohner & Schlüter 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4118982/). Local peer comparisons work at scale when they are true and relevant — [Hallsworth et al., NBER](https://www.nber.org/papers/w20007)

### Inferences
- **Reasons.** The robust part of Langer is that for any *non-trivial* ask (a 20-minute call is not a trivial ask), only a real reason helps.
  - (b) Strategist and writer: attach to the ask the reader's own concrete reason for taking the step, drawn from the ledger.
  - (c) Cold reader: "Why would you take the next step?" If the reader cannot answer from the email, the reason is missing or placebic.
  - (a) A lexical check for "because" or "parce que" near the call to action would pass placebic reasons, so it is not recommended as a gate.
  - The project's hard mutation "explanatory beat traded for a benefit" (see CLAUDE.md, `judge_bench`) is exactly the justification-explicitness variable; the meta-analytic support for keeping the explanation is MODERATE–STRONG.
- **Explicit conclusions.** These underpin `clarity_gate`, which blocks drafts that never name the offering: a meta-analytically supported practice, so keep it a gate.
  - (b) Show where each proof comes from (named source, document or customer), since citing sources raised credibility.
- **Concreteness.** Already encoded as "Specifics, not adjectives". Its likeliest mechanism in email is the "they listened" inference (Packard & Berger).
  - (a) A word-norm concreteness score per paragraph can flag abstract-heavy passages as a *diagnostic*. For subject lines it is non-monotonic, so never gate on "more concrete is better".
  - Drop construal-level "fit" rules (abstract benefits for distant decisions, concrete steps for near ones) after the multilab result.
- **Fluency.** It is robust for truth and liking, and the project notes say the judge is measurably poor on form (it twice preferred the wall of text).
  - (a) This is where code should measure: sentence length, paragraph length, rare-word share, word length, wall-of-text detection. Whether any of these *blocks* is a product decision; the research supports them as strong diagnostics, and the outcome link in email is shown only by the email-specific field experiments covered elsewhere.
  - Never use deliberately "harder" formatting to provoke thinking (folklore).
- **Repetition and truth.** Repeating a true claim raises its perceived truth (illusory-truth effect). This sits in tension with the strategist rule that one fact should not be argued five times across a sequence (repo observation, `backend/prompts/strategist.md`).
  - The research supports re-stating the *core* claim across a sequence in different words while varying the evidence. Note the wear-out after many exposures (mere-exposure inverted U, section 6).
- **Narrative.**
  - (b) A short, specific, plausible scene from the reader's day (the writer prompt's "their Friday" example fits) plus one licensed statistic for belief. A customer story must come from the ledger, never be invented (testimonial psychology is out of scope).
  - (c) "Could you picture the situation?"
- **Emotion.** For outreach, the strongest evidence is fear plus efficacy: name a real cost of the status quo *and* a feasible, specific step.
  - Negativity helps news clicks, but B2B transfer is unknown (d), and manufactured pain is already forbidden.
  - (a) A sentiment lexicon could serve as a diagnostic only.
- **Identity.** Do not encode identity labels. Use a relevant peer group only with licensed numbers.

### Gaps
- Folkes (1985), a partial replication of Langer, and any modern preregistered replication of the "because" effect were not retrieved.
- A Kingston University preregistered replication of Hansen & Wänke 2010 (concrete wording raises judged truth) exists ([eprints.kingston.ac.uk/43028](https://eprints.kingston.ac.uk/43028)), but the site was unreachable, so its result is unknown.
- The replication status of Song & Schwarz 2008 and of Oppenheimer 2006 was not checked.
- The *Made to Stick* (Heath & Heath) framework has not been tested as a package; only components such as concreteness have support.
- The emotional-versus-rational evidence from advertising effectiveness databases (Binet & Field, IPA) was not retrieved, and it concerns brand advertising rather than direct response anyway.

---

## Behavioural-economics effects used in marketing (loss aversion and framing, anchoring, decoy, choice overload, defaults, Zeigarnik, mere exposure, endowed progress and goal gradient): current replication status, including the nudge meta-analysis debate

### Takeaway
Loss aversion itself replicates: the mean coefficient is about 1.96 across 607 estimates, and prospect-theory patterns replicated in 19 countries. But it is conditional, and its message-level cousin, "loss-framed copy persuades more", is null in meta-analyses and in a 200,000-person tax RCT. Beyond that:
- the decoy effect largely vanishes with realistic stimuli;
- choice overload averages about zero but appears under complexity and preference uncertainty;
- defaults are large in general, but an email cannot impose one;
- the Zeigarnik memory effect failed a 2025 meta-analysis;
- mere exposure follows an inverted U;
- endowed progress and goal gradient rest on a few field studies.

After publication-bias correction, *information-type* nudges, which is what a marketing email is, show evidence of **no average effect**, while real-world nudge-unit communications average +1.4 pp.

### Cited Findings

**Loss aversion and framing**
- [STRONG] Brown, Imai, Vieider & Camerer 2024, Journal of Economic Literature:
  - 607 estimates from 150 papers, 1992–2017.
  - Mean loss-aversion coefficient 1.955 [1.820, 2.102]; few study characteristics explain the variation.
  - 192 estimates lacked standard errors, which the authors imputed.

  Source: [Brown et al. 2024](https://www.aeaweb.org/doi/10.1257/jel.20221698)
- [STRONG; large replication] The original 1979 prospect-theory items, re-run with 4,098 participants in 19 countries and 13 languages, replicated for 94% of items and 12 of 13 theoretical contrasts, with some attenuation — [Ruggeri et al. 2020, Nature Human Behaviour](https://research.vu.nl/en/publications/replicating-patterns-of-prospect-theory-for-decision-under-risk/)
- [Critique] Loss aversion has been over-generalised. Using it to explain the endowment effect is circular, and status-quo preferences in riskless choice can reflect inertia — [Gal & Rucker 2018, JCP (SSRN)](https://papers.ssrn.com/abstract=3049660); [Gal, Scientific American](https://www.scientificamerican.com/article/why-the-most-important-idea-in-behavioral-decision-making-is-a-fallacy). A reply argued that loss aversion has moderators but is not dead (Mrkva, Johnson, Gächter & Herrmann 2020, JCP), as reported in the debate summaries — [Kitces summary](https://www.kitces.com/blog/loss-aversion-pain-loom-larger-than-gain-gal-rucker-journal-psychology/)
- [STRONG; null for the copy claim] Gain versus loss message framing:
  - Detection behaviours (53 studies, N = 9,145): loss-framed appeals were not generally more persuasive, with a small exception for breast-cancer detection — [O'Keefe & Jensen 2009, Journal of Communication](https://www.cbsm.com/articles/33455-the-relative-persuasiveness-of-gain-framed-and-loss-framed-messages-for-encouraging-disease-detectio)
  - Prevention (93 studies, N = 21,656): a statistically significant but small overall gain-frame advantage that did not hold for other preventive behaviours such as safer sex or skin-cancer prevention — [O'Keefe & Jensen 2007, J Health Communication](https://doi.org/10.1080/10810730701615198) †DOI
  - Across 24 RCTs on cancer prevention and detection, framing barely changed attitudes or intentions — [JMIR 2021 meta-analysis](https://jmir.org/2021/9/e27634)
  - In UK tax letters, loss framing did not beat gain framing — [Hallsworth et al.](https://www.nber.org/papers/w20007)
- [STRONG†] The typology distinguishes attribute framing (describing the same attribute positively or negatively, e.g. "75% lean"), risky-choice framing and goal framing; these behave differently — [Levin, Schneider & Gaeth 1998, OBHDP](https://doi.org/10.1006/obhd.1998.2804) †

**Anchoring and decoy** (main application is pricing, which is out of scope)
- [STRONG† in lab] Many Labs 1 replicated anchoring — [Klein et al. 2014](https://doi.org/10.1027/1864-9335/a000178) †. Anchoring of incentivised willingness to pay was weaker in replication — [Maniadis, Tufano & List 2014, AER](https://doi.org/10.1257/aer.104.1.277) †
- [WEAK-FOLKLORE with realistic stimuli; status changed 2014] Across 19 studies with realistic stimuli, decoys did not raise the target's share, and lowering it ("repulsion") was just as common — [Frederick, Lee & Baskin 2014, JMR](https://marketing.wharton.upenn.edu/wp-content/uploads/2016/10/The-Limits-of-Attraction.pdf). The original authors replied that the effect is robust when the original conditions are essentially replicated — [Huber, Payne & Puto 2014, JMR](https://people.duke.edu/~jch8/bio/Papers/HuberPaynePutoJMR%202014.pdf)

**Choice overload**
- The original jam study: the larger display attracted more stoppers but fewer purchases — [Iyengar & Lepper 2000, JPSP](https://doi.org/10.1037/0022-3514.79.6.995) †
- [STRONG; null mean] The mean choice-overload effect across studies is near zero, with high heterogeneity — [Scheibehenne, Greifeneder & Todd 2010, JCR (PDF)](https://abcwest.cogs.indiana.edu/pmwiki/pdf/scheibehenne.options.2010.pdf)
- [STRONG; conditional] Across 99 observations (N = 7,202), four moderators (choice-set complexity, decision-task difficulty, preference uncertainty, decision goal) make the effect significant once accounted for — [Chernev, Böckenholt & Goodman 2015, JCP](https://www.kellogg.northwestern.edu/academics-research/research/detail/2015/when-product-assortment-leads-to-choice-overload-a-conceptual/)

**Defaults**
- [STRONG] Across 58 studies (n = 73,675), defaults have an effect of d = 0.68 [0.53, 0.83]. They are stronger in consumer domains, weaker in environmental ones, and stronger when the default works through endorsement (seen as a recommendation) or endowment (seen as the status quo). Much of the heterogeneity is unexplained — [Jachimowicz, Duncan, Weber & Johnson 2019, Behavioural Public Policy](https://ideas.repec.org/a/cup/bpubpo/v3y2019i02p159-186_00.html). Organ-donation defaults are the famous example — [Johnson & Goldstein 2003, Science](https://doi.org/10.1126/science.1091721) †

**Zeigarnik / open loops**
- [WEAK-FOLKLORE for memory; status changed 2025] Ghibellini & Meier 2025 (59 publications, per secondary coverage) found **no memory advantage** for unfinished tasks. They did find a general tendency to *resume* interrupted tasks (the Ovsiankina effect) — [Ghibellini & Meier 2025, Humanities & Social Sciences Communications](https://ideas.repec.org/a/pal/palcom/v12y2025i1d10.1057_s41599-025-05000-w.html)

**Mere exposure and repetition**
- [STRONG; meta-analysis] Across 268 curve estimates from 81 articles, liking follows an inverted U over repeated exposure, rising and then flattening or declining — [Montoya et al. 2017, Psych Bulletin](https://researchportal.murdoch.edu.au/esploro/outputs/journalArticle/A-re-examination-of-the-mere-exposure/991005635870307891)

**Endowed progress and goal gradient**
- [MODERATE; single field study] Artificial advancement toward a goal increased persistence; in the car-wash loyalty card, a 10-stamp card with 2 stamps pre-filled was completed more often (about 34% vs 19%†) than an 8-stamp card. Moderators: the reason given for the endowment and the currency of progress. No replication was found — [Nunes & Drèze 2006, JCR](https://ideas.repec.org/a/oup/jconrs/v32y2006i4p504-512.html)
- [MODERATE; field data] In a café reward programme, purchase intervals shrank as members neared the reward (about 20% from first to last stamp), customers "reset" after the reward, and illusory progress (a 12-stamp card with 2 pre-filled) accelerated completion — [Kivetz, Urminsky & Zheng 2006, JMR](https://business.columbia.edu/faculty/research/goal-gradient-hypothesis-resurrected-purchase-acceleration-illusionary-goal)

**The nudge meta-analysis debate**
- Mertens et al. 2022 (PNAS) concluded that choice architecture is an effective, widely applicable tool. Unadjusted random-effects estimates (as tabulated by Maier et al.):

  | Category | d [95% CI] |
  |---|---|
  | Overall | 0.43 [0.38, 0.48] |
  | Decision information | 0.25 |
  | Decision structure | 0.58 |
  | Decision assistance | 0.22 |

  Mertens et al.'s own sensitivity analysis allowed the true effect to be as low as d = 0.08 under severe bias — [Mertens et al. 2022](https://doi.org/10.1073/pnas.2107346118) †DOI; numbers via [Maier et al. 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9351501/)
- [STRONG; status changed 2022] Maier, Bartoš, Stanley, Shanks, Harris & Wagenmakers 2022 (robust Bayesian meta-analysis; BF01 > 1 favours no effect):

  | Category | Bias-corrected d [95% CI] | BF01 | Most-precise-estimate d | BF01 |
  |---|---|---|---|---|
  | Overall | 0.04 [0.00, 0.14] | 0.95 | 0.11 | 0.31 |
  | Information | 0.00 | 33.84 | 0.00 | 10.57 |
  | Structure | 0.12 [0.00, 0.43] | 1.12 | 0.23 | 0.33 |
  | Assistance | 0.01 | 9.05 | 0.01 | 8.00 |

  - Information and assistance nudges: evidence *against* an average effect. Structure nudges: undecided.
  - Strong evidence of publication bias in nearly all subdomains.
  - Heterogeneity in all categories except finance, "which implies that some nudges might be effective".

  Source: [Maier et al. 2022, PNAS letter](https://pmc.ncbi.nlm.nih.gov/articles/PMC9351501/). The authors frame their claim as an absence of evidence rather than evidence of absence — [rejoinder](https://www.bayesianspectacles.org/rejoinder-no-evidence-for-nudging/)
- A third letter found the effect distribution left-truncated, implying more than moderate publication bias — [Bakdash & Marusich 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9351476/). A 2026 blog commentary argues the corrections pulled the mean toward zero without showing that all effects are zero (WEAK; commentary) — [Replication Index 2026](https://replicationindex.com/2026/09/07/what-is-the-effect-of-nudging-43/)
- [STRONG] DellaVigna & Linos 2022, Econometrica: 126 RCTs from two US nudge units covering 23 million people (mostly low-cost written communications such as letters, emails and texts†):
  - Average effect 1.4 pp, an 8.0% increase on a 17.3% control take-up.
  - Academic-journal nudges average 8.7 pp (33.5%) in the working paper.
  - Selective publication combined with low power explains about 70% of the gap.

  Sources: [Econometrica](https://www.econometricsociety.org/publications/econometrica/2022/01/01/rcts-scale-comprehensive-evidence-two-nudge-units); [NBER w27594](https://nber.org/papers/w27594)
- [STRONG; megastudy] 689,693 Walmart pharmacy patients were randomized to 22 text-message reminders or no message:
  - The texts raised vaccination by 2.0 pp on average (6.8%).
  - The best message, two texts three days apart framed as a vaccine "waiting for you", fits the endowment / ownership framing.
  - Neither experts nor lay forecasters picked the winner.

  Source: [Milkman et al. 2022, PNAS](https://bcfg.wharton.upenn.edu/research/a-680000-person-megastudy-of-nudges-to-encourage-vaccination-in-pharmacies/). An earlier doctor's-appointment megastudy similarly found that "reserved for you" ownership texts performed best — [Milkman et al. 2021, PNAS](https://doi.org/10.1073/pnas.2101165118) †

### Inferences
- **Framing.**
  - (b) Do not rewrite benefits as losses by default; there is no meta-analytic or field support for it in messages.
  - (b) Describe licensed attributes positively and accurately (attribute framing), and when naming a cost of the status quo, pair it with efficacy (section 5).
  - Loss aversion matters mostly for offer design and pricing, which are out of scope.
- **Choice overload and asks.** One primary next step is well justified *by the moderators*: a cold reader has high preference uncertainty and a hard decision. "Single CTA lifts conversions X%" statistics are vendor folklore.
  - (a) Code can count distinct asks, links and verbs of request as a diagnostic; the "second ask beside the first" hard mutation is the same variable.
  - (b) Already present: the "smallest verified step".
- **Defaults.** An email cannot set a default, but it can *propose one specific option* (a time slot, a reply number, a pre-chosen resource), the nearest analogue to endorsement. It overlaps with the implementation-intention evidence in section 7.
  - Risk: an assumptive default ("I'll put you down for Tuesday unless…") is controlling language (section 4). The safe form is a proposal plus an exit.
- **Zeigarnik.** Do not use "open loops" or teaser cliff-hangers across a sequence as a memory device; the memory claim failed. The Ovsiankina resumption tendency applies only to tasks the reader actually started, for example an onboarding sequence that points to a genuinely unfinished setup step.
- **Mere exposure and repetition.** Familiarity from a consistent sender and repeated core claim helps up to a point, then wears out. The optimal number of touches is (d) only.
- **Endowed progress / goal gradient.** Use only in onboarding or activation sequences with *real* progress the product records ("2 of 3 steps done"), never invented progress. MODERATE evidence, (b).
- **Calibration.** Real-world written nudges move behaviour by roughly 1–2 percentage points (a 5–10% relative lift). Published lab effects are inflated about fourfold by selective publication, and information-type nudges show no reliable mean effect after correction. Any vendor claim that one copy trick lifts responses by 20–50% should be presumed inflated.
  - Experts cannot predict which message wins (Milkman et al.), and literature-derived wording rules miss the sign half the time (section 3). A model's click forecast is therefore weak, which reinforces that model judgment must not block, and suggests that MarketingOS's quota is better spent on what is checkable (truth, clarity, comprehension, friction) than on predicted persuasion.

### Gaps
- The details of Mrkva et al. 2020 (moderators of loss aversion: stakes, expertise) and a reported 2024 meta-analysis finding lower loss aversion in risky contexts were not retrieved.
- Yang & Lynn 2014 (further evidence against the attraction effect) and any later attraction-effect meta-analysis were not retrieved.
- The optimal-frequency result of Schmidt & Eisend 2015 (advertising repetition meta-analysis) was not retrieved.
- No replication of the endowed-progress effect was found.
- The classification of reminders and social-reference-point nudges within Mertens et al.'s taxonomy is from prior knowledge (†) and should be checked before the report maps "a marketing email" onto the "information" category.

---

## Fogg Behavior Model (motivation × ability × prompt) and friction: what reduces the effort of acting on an email?

### Takeaway
Fogg's B = MAP is a design heuristic, not a tested model. Its "ability" (simplicity) leg, though, is the best-supported lever in this inventory. Large field RCTs show that behaviour changes when you simplify the written message, show the one number that matters, redesign the form, add a timed reminder, prompt a date-and-time plan, or do part of the task for the person, while adding information alone often does nothing.

### Cited Findings
- [WEAK as an empirical model] Fogg's model holds that motivation, ability and a trigger must converge at the same moment for a behaviour to occur. It was presented as a conference paper at Persuasive '09; the trigger was later renamed "prompt". Most published uses apply it as a design framework rather than testing its predictions — [Fogg 2009, ACM DOI](https://www.doi.org/10.1145/1541948.1541999); [Stanford Behavior Design Lab](https://behaviordesign.stanford.edu/resources/fogg-behavior-model)
- [STRONG; field RCT with the IRS] Bhargava & Manoli 2015, AER: mailings to 35,050 Californians likely eligible for the Earned Income Tax Credit (EITC):
  - Complex materials cut take-up by 6 pp and a longer worksheet by 4 pp; showing the potential credit amount raised take-up by 8 pp.
  - Time-to-complete estimates, indemnification, envelope messages and anti-stigma messages had no effect.
  - About $4M of $26M in unclaimed benefits was claimed because of the mailings.

  Sources: [Bhargava & Manoli 2015 (PDF)](https://www.cmu.edu/dietrich/sds/docs/bhargava/bhargava-aer-2015.pdf); [US DOL CLEAR review](https://clear.dol.gov/study/psychological-frictions-and-incomplete-take-social-benefits-evidence-irs-field-experiment)
- [STRONG; field RCTs] Fishbane, Ouss & Shah 2020, Science:
  - Redesigning New York City court summonses so key information was salient, plus text reminders, cut failures to appear by 13–21% (AAAS: 13% for the form alone, 25% with texts) and avoided about 30,000 arrest warrants over three years.
  - Mechanism: people were unaware of, or forgot, the date, rather than deliberately skipping court.

  Sources: [Science paper (ideas42 PDF)](https://www.ideas42.org/wp-content/uploads/2020/10/Behavioral-nudges-reduce-failure-to-appear-for-court_Science.full_.pdf); [AAAS](https://www.aaas.org/news/communication-changes-improve-court-attendance-reduce-arrests)
- [STRONG; field RCT] Bettinger et al. 2012, QJE (the H&R Block financial-aid form experiment):
  - Help completing the federal student-aid application (FAFSA), plus information, raised submission for dependent students by 15.7 pp, and later college attendance, at about $88 per participant.
  - Information alone, without help, had no significant effect.

  Sources: [NBER w15361](https://www.nber.org/papers/w15361.pdf); [J-PAL](https://www.povertyactionlab.org/node/2133)
- [STRONG; field RCT] Milkman et al. 2011, PNAS (3,272 employees):
  - Adding to a reminder mailing a prompt to write down the *date and time* of a planned flu shot raised vaccination by 4.2 pp over a 33.1% control rate; a date-only prompt gave +1.5 pp, not significant.
  - Effects were larger where the clinic ran on a single day.

  Source: [Milkman et al. 2011](https://pmc.ncbi.nlm.nih.gov/articles/PMC3127912). A meta-analysis of implementation intentions reports a medium-to-large effect on goal attainment — [Gollwitzer & Sheeran 2006](https://doi.org/10.1016/S0065-2601(06)38002-1) †
- [STRONG] Plain text reminders raised pharmacy vaccination by 2.0 pp on average — [Milkman et al. 2022](https://bcfg.wharton.upenn.edu/research/a-680000-person-megastudy-of-nudges-to-encourage-vaccination-in-pharmacies/). The average nudge-unit communication effect is 1.4 pp — [DellaVigna & Linos 2022](https://www.econometricsociety.org/publications/econometrica/2022/01/01/rcts-scale-comprehensive-evidence-two-nudge-units)
- [MODERATE; email-specific, secondary coverage] Shorter emails got more responses, and splitting two sentences into two separate text messages raised parent response by 15% — [Inc. coverage of Rogers & Lasky-Fink](https://www.inc.com/jessica-stillman/double-your-chance-of-getting-a-response-to-emails-by-making-them-shorter.html)

### Inferences
- **A friction checklist grounded in the RCTs above**:
  1. Put the one decision-relevant fact up front: what it is, what it costs or yields, and what to do. (Bhargava & Manoli: showing the amount gave +8 pp; complexity cost −6 pp. Fishbane: salience of key information.)
  2. Make the action concrete: verb plus object, and what happens after the click or reply.
  3. Do part of the work for the reader (Bettinger: help beats information). Examples: a proposed time, a pre-written one-line reply ("reply 1 for X, 2 for Y"), a direct link to the exact resource rather than the homepage.
  4. Invite a specific plan (date and time) when the step happens later (Milkman 2011).
  5. Cut words and ideas (Rogers & Lasky-Fink; complexity effects).
- (a) Deterministic, cheap and defensible as diagnostics:
  - Position of the offer and the ask (how many words or sentences before they first appear).
  - Count of distinct asks and links.
  - Presence of a time or effort statement, which must be licensed if numeric (existing number gates).
  - Paragraph and sentence length, wall-of-text detection.
  - The order of first licensed proof versus the ask. Code can compute this because gates know which sentences carry licensed facts; it mirrors the "proof arriving after the ask" hard mutation, though direct evidence for that ordering rule is lacking.
- (b) Strategist: choose the smallest step whose effort the ledger can state honestly, and pre-fill it.
  - Writer: never promise "2 minutes" unless the ledger supports it; the number gate already enforces this.
- (c) Cold reader: "What exactly would you do next, and how long would it take?" If the reader cannot say, the friction is in the text, and a reader with no brief is the right instrument to find it.
- (d) The size of any friction effect on reply or click rates in B2B outreach needs send data.
- **Overall.** Across this inventory, the mechanisms that are both STRONG *and* checkable without send data are: truthful, licensed claims; clarity of the offer; explicit, concrete reasons and proof; low friction and specific next steps; and avoiding controlling or fake-urgency language. MarketingOS's existing architecture already concentrates its blocking checks there. The folklore tactics (BYAF, loss framing, open loops, decoys, identity labels, priming words, vague curiosity gaps) are the ones to keep out of prompts and rules.

### Gaps
- No direct empirical test of the Fogg model's multiplicative structure was found.
- No B2B or cold-email friction experiment (for example, "reply with a number" asks or pre-proposed meeting times) was found.
- The primary Rogers & Lasky-Fink paper was not read; its figures come from press coverage.
- Whether adding a time-and-effort estimate helps in email is unclear: in the IRS experiment, time estimates had *no* effect.
