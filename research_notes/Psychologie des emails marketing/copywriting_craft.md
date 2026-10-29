# Copywriting craft for marketing emails: practitioner knowledge (direct response, lifecycle, cold B2B)

Reading key. Each finding carries a status tag: **CONSENSUS** (most respected practitioners agree), **CONTESTED** (they disagree, and the note says on what) or **ANECDOTAL** (one practitioner's habit, or a single unverified source). `data:` says whether measured data exists, and whose. `apply:` says how MarketingOS could use the rule: **a** = deterministic code check, **b** = instruction in the strategist or writer prompt, **c** = criterion for the cold reader or critic, **d** = only testable with real send data. Lines marked *(illustr.)* are examples I wrote to illustrate a rule; they are not quotes. A `[x]` inside one is a placeholder that MarketingOS would have to license from the Evidence Ledger. On source quality: I could not read the primary texts of *Breakthrough Advertising*, *Tested Advertising Methods*, *Great Leads*, the *Boron Letters* or the *Robert Collier Letter Book* in full. Claims about them rest on summaries by working copywriters, publishers and practitioners, and are flagged as such. Search also turned up many SEO-spam "PDF copy" hosts for these books. I did not use them. Project facts about MarketingOS (gates, mutations, bench results) come from the repo's `CLAUDE.md` and are given as file paths, not URLs.

---

## 1. Schwartz's five levels of awareness and five stages of market sophistication: what copy fits each, and how a planner decides

### Takeaway
These are two independent settings. **Awareness** describes the *reader at the moment of this email*: how much they already know about their problem, the solution category, your product and your offer. It decides what the email leads with and how much it has to say. The less aware the reader, the more indirect the opening and the longer the argument; the most aware need only the offer. **Sophistication** describes the *market*: how many similar promises buyers have already heard. It decides what kind of claim can still land: a plain claim, a bigger claim, a mechanism, a better mechanism, or identification. An email planner can infer awareness mostly from data it already holds (how the contact came in, what they did) and sophistication from a competitor scan. Neither label can be validated without send data.

### Cited Findings
**Awareness**
- The five levels from *Breakthrough Advertising* (1966) are unaware, problem aware, solution aware, product aware and most aware. **CONSENSUS**: this is the default vocabulary of direct-response copywriting. `data: none` `apply: b` — [ActiveCampaign (B. Elias, 2023)](https://www.activecampaign.com/blog/marketing-stages-awareness-and-buyer-cycle); [Optimize Smart](https://optimizesmart.com/blog/schwartz-five-stages-of-awareness-in-marketing/); [Leadgen Economy](https://www.leadgen-economy.com/blog/five-stages-awareness-lead-generation/)
- What fits each level, in Benyamin Elias's summary (6 June 2023). Note that all five readings are his paraphrase, not Schwartz's own text. **CONSENSUS** `data: none` `apply: b (the strategist assigns a level and a lead), c (the critic checks that the lead fits the stated level)` — [ActiveCampaign](https://www.activecampaign.com/blog/marketing-stages-awareness-and-buyer-cycle)
  - *Unaware*: usually not worth marketing to directly. If you must, open on a problem everyone shares (the classic toothpaste "film" ad) or on "people like you" social proof.
  - *Problem aware*: needs longer copy. Reflect the pain, show that solutions exist, introduce the product as one option, then prove it is the best.
  - *Solution aware*: help them choose by showing what competitors lack.
  - *Product aware*: make the case that you are the best choice, with benefits, features and proof.
  - *Most aware*: make the offer, back it with a strong guarantee, then say less and get out of the way.
  - In one line: lead with the pain (unaware and problem aware), the differentiator (solution aware), benefits plus proof (product aware), or the offer (most aware).
- Diagnosis: ask what the prospect already believes. Past experience with the category lowers the load; someone who has exercised before needs less convincing than someone who never has. **ANECDOTAL** as stated (one summary), though every other source is consistent with it. `apply: b` — [ActiveCampaign](https://www.activecampaign.com/blog/marketing-stages-awareness-and-buyer-cycle)
- Masterson and Forde's *Great Leads* turns awareness into six types of opening, each matched to an awareness level: **Offer, Promise, Problem-Solution, Secret, Proclamation, Story**. **CONSENSUS** within the Agora/AWAI school. I only had secondary summaries, one of which contains factual errors. `data: none` `apply: b` — [BeFreed summary](https://www.befreed.ai/book/3606f9a5-4a51-4c8b-977c-daefd5accbde); [Write With AI on Great Leads](https://writewithai.substack.com/p/great-leads-kickstart-part-3-when); [The Book Nerd](https://thebooknerd.beehiiv.com/p/the-rule-of-one-the-timeless-copywriting-principle-most-marketers-ignore); [AWAI, "Mastering the lead"](https://www.awai.com/2008/10/mastering-the-lead/)
  - Promise leads suit readers who know the problem and know that solutions exist.
  - Problem-Solution leads suit readers who may not know the problem or its solution. The summaries warn against dwelling on the pain for too long.
  - Secret leads usually hold the product back until later in the copy.
  - Proclamation leads open on a bold claim; Story leads engage through narrative.

**Sophistication**
- Sophistication is a separate setting, described as the "sister concept" to awareness. Awareness is about the individual buyer's knowledge; sophistication is about how tired the whole market is of claims. **CONSENSUS** — [Selfstorming framework page](https://www.selfstorming.com/tools/libraries/frameworks/market-sophistication); [ONES summary](https://ones.com/blog/?p=1145983)
- The five stages. Labels vary between write-ups but the logic stays the same. The named mistake is making yet another claim to a market that has heard them all and stopped listening. **CONSENSUS** on the logic; secondary sources only. `data: none` `apply: b (strategist); partly a (see Inferences on sameness.py)` — [Selfstorming](https://www.selfstorming.com/tools/libraries/frameworks/market-sophistication); [ONES](https://ones.com/blog/?p=1145983)
  1. First to market: a simple, direct claim works.
  2. Bigger claim: enlarge or sharpen the same promise.
  3. Mechanism: explain the distinctive way the product works.
  4. Better mechanism: an improved or more detailed mechanism.
  5. Identity and experience: once claims are used up, sell belonging and identification.
- A pitfall in the secondary literature: some guides swap Schwartz's market sophistication for an unrelated "audience sophistication" (low, middle or high technical vocabulary). The ActiveCampaign piece does exactly this, so it is a source on awareness only, not on the sophistication stages. — [ActiveCampaign](https://www.activecampaign.com/blog/marketing-stages-awareness-and-buyer-cycle)

### Inferences
- **A planner's rule for awareness** (`apply: b`, verifiable only by `d`). Unlike a print advertiser, an email planner usually knows how the contact came in and what they did, and that is the cheapest signal of awareness:

  | Contact or trigger | Likely level | Lead (Great Leads type) | Length |
  |---|---|---|---|
  | Cold prospect, never contacted | unaware to problem aware | problem or observation (Problem-Solution); Story only if the offering comes up early | short (cold-B2B norms, §4) |
  | Subscriber who came in through content on topic X | problem aware on X | Promise or Problem-Solution | medium |
  | Trial or freemium user | product aware | Promise plus proof, one next step | short to medium |
  | Cart or checkout abandoner | most aware | Offer (reminder plus reassurance) | very short |
  | Lapsed customer | product aware (knows you, has a reason not to come back) | what changed, plus offer | short |
  | Existing customer, cross-sell | most aware of the brand; solution or product aware of the new item | Promise or news | medium |

- **Within a sequence**, awareness can only be assumed to rise for readers who engaged. Lavender reports that most emails are deleted within three seconds (§4), so each email should stand on its own. It should restate the one fact it depends on rather than count on an earlier email having been read.
- **A planner's rule for sophistication** (`apply: b`, partly `a`). A competitor scan can count how many rivals already make the same main promise.
  - If the campaign's main claim is already common, the market is at stage 3 or later: lead with the mechanism (how and why it works), not the claim.
  - If rivals also explain their mechanisms, the market is at stage 4 or 5: use a sharper mechanism or identification.
  - MarketingOS already has a deterministic version of this: `app/market/sameness.py` blocks a closed list of frames every competitor uses, which amounts to forbidding stage-1 and stage-2 claims in a stage-3+ market. The strategist's brief could carry an explicit `sophistication_stage` derived from the rival scan, and the writer prompt could change the type of claim based on it.
- **The mechanism stage matches an existing mutation.** The bench mutation that trades "the explanatory beat" for a benefit (`mutations.HARD_MUTATIONS`) removes exactly the stage-3 element, which is also Hopkins's and John E. Kennedy's reason-why (§2). This is evidence that the project already treats explanation as load-bearing.
- **Tension with MarketingOS's comprehension veto.** The indirect openings *Great Leads* prescribes for the least aware (Secret, Proclamation, Story) put off naming the offering. Meanwhile `clarity_gate` blocks a draft that never names the offering where the reader is looking, and `BlindRead.understood` vetoes any draft the panel could not decode. A workable reconciliation: allow an indirect lead only as a one-to-three-sentence setup, with the offering named before the midpoint, and prefer such leads for subscribers who opted in (newsletter, nurture) over cold outreach.
- **Cold reader** (`apply: c`). To test whether the email fits the awareness level without leaking the brief, give the reader only a reader state, such as "you have never heard of this company and don't think you have this problem". That is a persona, not the brief, so the read stays cold; `persona_bench` is the existing low-cost version.
- **Good and bad lines by awareness level** *(illustr.)*:
  - Most aware. Good: "Your cart is saved, and returns stay free for 30 days." Bad: "Discover a new era of comfort." (a lecture to someone ready to buy)
  - Product aware. Good: "Setup takes [x] days. Here's what [named customer] did in week one." Bad: "We're the leading solution."
  - Solution aware. Good: "Most schedulers make clients pick a slot; this one fills cancellations by itself." Bad: "Packed with powerful features."
  - Problem aware. Good: "If no-shows cost you [x] slots a week, here's what one clinic changed." Bad: "Introducing our AI-powered platform."
  - Unaware. Good: "Last spring a Lyon dentist noticed her Tuesday mornings were always half empty." Bad: the product name and a feature list in line one.
- **One product written for each sophistication stage** *(illustr.)*:
  1. "Send invoices from your phone."
  2. "Get paid in [x] days instead of [y]."
  3. "It texts the client a payment link the moment you mark the job done. That's why it's faster."
  4. "…and it re-sends at the hour that client usually pays."
  5. "For tradespeople who'd rather be on the tools than chasing money."

### Gaps
- I could not read *Breakthrough Advertising* itself. The stage labels and any diagnostic advice of Schwartz's own come from secondary summaries.
- No primary Copyhackers or Joanna Wiebe article on awareness or sophistication came up in search.
- I found no measured comparison of emails matched to the reader's awareness level against mismatched ones, and no published method for scoring market sophistication from a competitor scan. The counting rule above is my own inference.

---

## 2. Classic direct-response principles (Hopkins, Caples, Ogilvy, Sugarman, Halbert, Collier, Kennedy): which still hold for email

### Takeaway
Still valid, and agreed on:
- be specific, and give the reason why (Hopkins, John E. Kennedy);
- make the "headline" carry self-interest or news (Caples, Ogilvy); in email the headline is the sender name, subject line and preheader together;
- every line's job is to get the next line read (Sugarman);
- start from what is already on the reader's mind (Collier);
- build each piece on one big idea (Ogilvy, as formalised later by Masterson).

What does not carry over as is:
- print-era measurement claims such as Ogilvy's five-to-one headline ratio;
- coupon-keyed testing, which needs send data;
- long copy as a default, which is contested for email (§7).

### Cited Findings
- **Hopkins, *Scientific Advertising* (1923).** **CONSENSUS** `data: Hopkins's own coupon-keyed tests (historical, not email)` `apply: a (MarketingOS gates already license numbers and quotes; substantiation checks that evidence is actually used), b, c` — [Intercom](https://www.intercom.com/blog/book-every-marketer-must-read); [BestWriting summary](https://bestwriting.com/scientific-advertising-summary); [Psychotactics](https://psychotactics.com/?p=21313); [Drayton Bird, "Ogilvy on Hopkins"](https://draytonbird.com/?p=2365)
  - Generic boasts and superlatives only say what everyone expects, and leave no impression.
  - A definite statement is usually believed, and actual figures are not discounted.
  - Case: every shaving-soap brand used the same stock claims until a newcomer stated specific facts.
  - Every word costs money, so every claim has to carry weight.
  - Ogilvy is reported to have said every marketer should read the book.
  - Dates conflict: one listing gives 1966, probably a reprint.
- **Reason-why, and "salesmanship in print" (John E. Kennedy, Lord & Thomas).** Ads are selling done in print, and the copy should tell the reader the reason to buy rather than expect them to work it out. **CONSENSUS** `apply: b (each claim comes with its "because"), c ("Did the email say why this works, or why now?")` — [Advertising Hall of Fame](https://advertisinghalloffame.org/inductee/john-e-kennedy/); [Daniel Levis](https://www.daniellevis.com/salesmanship-in-print-unlikely-meeting-secret-unlimited-riches/); [Antoine Buteau on Lasker](https://www.antoinebuteau.com/lessons-from-albert-lasker/)
  - Kennedy met Albert Lasker in 1904 and published the reason-why articles in 1905.
  - Lasker hired Hopkins in 1908, and the two spread reason-why copy.
  - One Hall of Fame bio dates the meeting to 1889, which looks like an error.
- **Caples.** The best headlines appeal to the reader's self-interest or give news; curiosity is a third, supporting ingredient. **CONSENSUS** as headline doctrine. `data: Caples's mail-order split tests (historical)` `apply: b (subject-line prompt), c (subject-line critic), d` — [VeryGoodCopy](https://www.verygoodcopy.com/verygoodcopy-blogs-10/the-best-headlines); [WriteToDone](https://writetodone.com/the-art-and-science-behind-neck-snapping-headlines/); [ACM Ubiquity](https://ubiquity.acm.org/article.cfm?id=3492344)
- **Ogilvy.** `data: print era; none for email` — [Swipefile](https://swipefile.com/five-times-as-many-people-read-the-headlines-david-ogilvy); [Social Media Today](https://www.socialmediatoday.com/news/how-to-write-powerful-headlines-for-your-online-content-infographic/554489/); [Antoine Buteau on Ogilvy](https://www.antoinebuteau.com/lessons-from-david-ogilvy/); [AWAI, "The Power of One"](https://awai.com/2010/08/the-power-of-one-one-big-idea/)
  - About five times as many people read the headline as read the body (*Ogilvy on Advertising*, 1983, about print). The figure's sourcing is loose. **CONSENSUS** that the headline comes first.
  - For a great many products, long copy sells more than short. **CONTESTED** for email (§7).
  - Every great campaign rests on one big idea. Masterson credits Bill Bonner's account of Ogilvy for the concept. **CONSENSUS**
- **Sugarman, the "slippery slide".** Every element exists to get the next one read: the headline gets the first sentence read, the first sentence gets the second read. His first sentences were extremely short. He pictured a greased playground slide, and changed his word from "slope" to "slide" to sharpen the image. **CONSENSUS** `apply: b (short first sentence, no throat-clearing), a (first-sentence length check), c ("Where did you stop reading?")` — [Book Summaries #02](https://booksummaries.substack.com/p/book-summary-02-advertising-secrets); [Samuel Thomas Davies](https://samuelthomasdavies.com/book-summaries/business/the-adweek-copywriting-handbook); [Alexandra Allen](https://alexandraallen.substack.com/p/the-slide-and-the-guinea-pig); [VeryGoodCopy on Sugarman's headlines](https://www.verygoodcopy.com/verygoodcopy-blogs-8/joe-sugarman-headlines?format=amp)
- **Halbert.** **CONSENSUS** (widely taught), secondary sources only. `apply: b (the sender is a person, and the email looks plain and personal when it is meant to read as 1:1); the starving crowd is about targeting rather than copy (list strategy, d)` — [Shortform](https://www.shortform.com/blog/the-boron-letters-gary-halbert/); [Start & Grow](https://startandgrow.substack.com/p/the-unforgettable-journey-of-gary); [Irregular Reveries](https://buttondown.email/shime/archive/irregular-reveries-11-copywriting-lessons-from/)
  - *A-pile and B-pile*: people sort their mail into what they open and what they bin, and mail that looks personal goes to the A-pile.
  - *Starving crowd*: in his hamburger-stand thought experiment, the one advantage worth having is an audience already hungry for what you sell.
  - The *Boron Letters* were written to his son from prison, around 1984.
- **Collier.** Join the conversation already going on in the reader's mind. The line is widely attributed to him, but I could not verify the exact passage in *The Robert Collier Letter Book*. A publisher's summary paraphrases his method as entering the prospect's mind, turning features into benefits and steering attention to action. **CONSENSUS**: it is the root of today's "trigger" and "premise" in cold email (§4). `apply: b (the opening refers to the reader's current situation), c ("Was the first line about something you were already thinking about?"), d` — [ActiveCampaign, Collier quotes](https://www.activecampaign.com/blog/robert-collier-quotes); [Quotefancy](https://quotefancy.com/quote/1547595/Robert-Collier-Always-enter-the-conversation-already-taking-place-in-the-customer-s-mind); [Skoobe (publisher description)](https://www.skoobe.de/books/robert-collier/the-robert-collier-letter-book-the-ultimate-guide-for-copywriting)
- **Dan Kennedy.** A low-quality aggregator credits him with calling PAS (problem, agitate, solve) the most reliable sales formula ever invented. I could not check this against Kennedy's own work. **ANECDOTAL** (attribution) — [il.ly](https://il.ly/marketing/pas-framework)

### Inferences
- **How each classic transfers to email, and to MarketingOS:**

  | Classic principle | Email form | Where MarketingOS could enforce it |
  |---|---|---|
  | Specificity (Hopkins) | named customers, figures, concrete events, never "best-in-class" | `a`: gates already license numbers, quotes and URLs; `substantiation.py` checks that evidence is spent |
  | Reason-why (J. E. Kennedy, Hopkins) | every claim followed by its "because": a mechanism, a cause or a why-now | `b` writer rule; `c` critic: "Can you say *why* it works?"; the explanatory-beat mutation already tests it |
  | Self-interest or news headline (Caples, Ogilvy) | sender name, subject and preheader together carry a benefit or a piece of news | `b` subject-line prompt; `c` subject-line critic; `d` |
  | Slippery slide (Sugarman) | short first sentence; each paragraph ends on a reason to read the next | `a` first-sentence length and paragraph length; `c` "where did you stop reading?" |
  | Collier's conversation | open on the reader's trigger or situation, not on the sender | `b`; `c`; `d` for real relevance |
  | A-pile (Halbert) | a person as sender; a plain, personal look for 1:1-style emails | `b` |
  | One big idea (Ogilvy) | one angle per email, one big idea per campaign | `b` brief schema; `a` CTA count; `c` "state the one idea" |

- **What carries over only through send data**: Hopkins's and Caples's split testing (`d`). MarketingOS's free substitute is the duel judge, which `CLAUDE.md` describes as reliable on content and poor on form. That matches the classics' own emphasis: content principles (specificity, reason-why, proof) are judgeable, while form principles (short sentences, short first line) should live in code.
- **The bench's hard mutations restate classic DR rules.** A "hollowed-out testimonial" is a loss of specificity (Hopkins, and Harry Dry's falsifiability in §3). "Proof arriving after the ask" breaks the classic order of case before close, and Gong's advice to sell the conversation before asking for the meeting (§4). "A second ask beside the first" breaks the single response of the Rule of One (§3). The mutation set is therefore a faithful encoding of classic DR craft, which strengthens the case for keeping it as the benchmark.
- **Good and bad lines** *(illustr.)*:
  - Hopkins. Bad: "Unmatched quality and service." Good: "Every jar is weighed twice; [x]% of orders ship the same day."
  - Reason-why. Bad: "It's faster." Good: "It's faster because it skips the bank-transfer step."
  - Sugarman. Bad: "In today's fast-paced business environment, many companies are finding that…" Good: "Tuesday was a bad day."

### Gaps
- Caples's often-repeated warning that curiosity alone underperforms has no reliable citation in what I found.
- Not sourced in this round: Dan Kennedy's "message-to-market match", and his doctrines on deadlines and urgency.
- Sugarman's list of psychological triggers is not sourced. A SciMark Report piece titled "raising obvious objections defuses them" came up in a Sugarman search, but I did not check whether it is attributed to him ([SciMark](https://scimark.substack.com/i/119261047/insight-raising-obvious-objections-defuses-them)). Objection-raising therefore stays weakly sourced.
- I did not access the primary texts of Caples, Halbert or Collier.

---

## 3. Modern frameworks and when each fits (AIDA, PAS, BAB, FAB, the 4 U's, one idea and one ask, JTBD and the Value Proposition Canvas, the big idea, voice of customer, Handley, Shleyner, Harry Dry)

### Takeaway
The named formulas are mostly orderings of the same few moves: attention, problem, desire or proof, action. They differ in where they start. PAS and BAB start from the reader's current situation, which suits problem-aware and solution-aware readers. FAB starts from the product, which suits product-aware and most-aware readers. AIDA is the generic skeleton. The more useful modern contributions are **constraints and tests** rather than orderings:
- one idea, one emotion, one ask (the Rule of One, Handley);
- the 4 U's and Harry Dry's three tests: can I visualise it, can I falsify it, could nobody else say it;
- Jobs-to-be-Done and the Value Proposition Canvas, as inputs for finding the angle;
- Joanna Wiebe's voice of customer, as the source of vocabulary.

### Cited Findings
- **AIDA** (attention, interest, desire, action) is an older formula traced back to the golden days of print marketing. **CONSENSUS** as a generic skeleton. `apply: b` — [Crazy Egg, AIDA vs PAS](https://www.crazyegg.com/blog/aida-vs-pas/)
- **PAS** (problem, agitate, solve): identify the problem, intensify the emotional urgency, then present the solution. Some practitioners add an Outcome step (PASO) that pictures life after the solution. It is recommended across channels, cold email included, and fits when the reader must first be shown the problem. Practitioners warn against over-agitating: one guide is titled "without being cringy", and *Great Leads* warns against dwelling on the pain (§1). **CONSENSUS** that it is useful; **CONTESTED** on how hard to agitate. `apply: b` — [Copyblogger](https://copyblogger.com/problem-agitate-solve/); [dsebastien](https://concepts.dsebastien.net/concept/problem-agitate-solve/); [Copywrite Matters, PASO](https://www.copywritematters.com/paso-copywriting-formula/); [Crazy Egg, AIDA vs PAS](https://www.crazyegg.com/blog/aida-vs-pas/); [Crazy Egg, PAS without being cringy](https://www.crazyegg.com/blog/?p=99420)
- **BAB** (before, after, bridge): the current problem, life once it is solved, and the product as the bridge between them. It is used as a contrast device and recommended especially for email. PAS by comparison dwells on life if the problem *persists*. **CONSENSUS** `apply: b` — [Mirasee](https://mirasee.com/blog/copywriting-formulas/); [Pipl.ai](https://pipl.ai/glossary/bab-formula)
- **FAB** (features, advantages, benefits): what the product does, why that helps, and what it means for the reader. It works best for product-focused copy (e-commerce, landing pages). **CONSENSUS** `apply: b, c (the critic flags a feature never translated into what it means for the reader)` — [Mirasee](https://mirasee.com/blog/copywriting-formulas/); [Mailchimp, copywriting formulas](https://mailchimp.com/it/resources/copwriting-formulas/)
- **The 4 U's.** **CONSENSUS** as a headline checklist; authorship **CONTESTED** (sources credit either Michael Masterson at Agora or Robert Bly's *The Copywriter's Handbook*). `apply: c (subject-line critic); partly a (specificity = a licensed number or name is present; uniqueness = the swap test)` — [Unbounce podcast](https://unbounce.com/podcast/copywriting-formula-4-u/); [Tilda](https://blog-en.tilda.cc/tpost/phf20rupg1-4-principles-to-write-a-powerful-headlin); [BAM](https://bamadv.com/blog/headline-writing-rules/); [Goodreads notes on *The Copywriter's Handbook*](https://www.goodreads.com/notes/18924199-the-copywriter-s-handbook/8309350-craig)
  - The four: useful (tangible and practical), unique, urgent (a reason to act now) and ultra-specific (facts and figures).
  - Uniqueness test: could you swap in another business's name? If so, the line is not unique.
  - Method: iterate until at least three of the four answers are yes.
- **The Rule of One** (Masterson and Forde): one big idea, one core emotion, one captivating story, one desirable benefit, one inevitable response. The test is whether the copy is anchored to a single concept or scattered across several. **CONSENSUS** `apply: b (the brief carries exactly one idea, one benefit and one ask), a (count the CTAs and links), c (the cold reader can state the one idea)` — [AWAI, "The Power of One"](https://awai.com/2010/08/the-power-of-one-one-big-idea/); [AWAI, copywriting tip #1](https://awai.com/2013/10/one-big-idea-copywriting-tip-1); [AWAI, choosing a big idea](https://awai.com/2013/05/six-steps-for-choosing-and-using-a-big-idea); [The Book Nerd](https://thebooknerd.beehiiv.com/p/the-rule-of-one-the-timeless-copywriting-principle-most-marketers-ignore)
- **Ann Handley.** Know the one thing you want to say, and write to one specific person rather than a crowd. Oddly, the more specific the writing is to one person, the more universal it can feel. An email carrying four or five calls to action should make you reconsider the send. **CONSENSUS** `apply: b, c` — [Litmus, featuring Ann Handley](https://www.litmus.com/blog/how-to-write-great-email-copy); [MarketingProfs podcast](https://marketingprofs.com/podcasts/2019/41542/writing-email-ann-handley-marketing-smarts); [Pam Didner podcast](https://pamdidner.com/podcasts/write-for-the-audience-of-one/)
- **Harry Dry (Marketing Examples)** has three tests, from his talk with David Perell. **CONSENSUS**-compatible: these restate Hopkins and the 4 U's in testable form. `apply: c (critic rubric); a for falsifiability (gates and ledger) and for uniqueness (sameness and the swap test)` — [Upgrow](https://upgrow.io/blog/harry-dry-copywriting-3-rules); [Impact Thinking](https://impactthinking.beehiiv.com/p/harry-dry-3-rules-copywriting); [Demand Curve #202](https://www.demandcurve.com/newsletters/growth-newsletter-202); [Chaindesk summary of the talk](https://chaindesk.ai/tools/youtube-summarizer/learn-great-copywriting-in-76-minutes-harry-dry-TUMjnmfsPeM)
  - Can I visualise it? Use concrete nouns and active verbs.
  - Can I falsify it? Make claims that can be proved true or false.
  - Can nobody else say this? Volvo's odometer claim is given as the example.
  - Three no's mean you have written rubbish; three yeses mean you are onto something. Rewrite until the copy passes all three.
- **Joanna Wiebe (Copyhackers), voice of customer.** **CONSENSUS** among conversion copywriters. `data: published case studies exist; I did not verify them` `apply: b (the knowledge phase pulls customers' phrasing out of the business's own material; the writer reuses it), a (quotations licensed by the gates)` — [Wistia interview](https://wistia.com/learn/marketing/joanna-wiebe-conversion-copywriting); [Everyone Hates Marketers podcast](https://podcast.everyonehatesmarketers.com/episodes/best-of-3-steps-to-write-copy-that-converts); [Microcopy Examples](https://microcopyexamples.substack.com/p/use-the-voice-of-the-customer); [Simon & Schuster, *The Copyselling System*](https://www.simonandschuster.ca/books/The-Copyselling-System/Joanna-Wiebe/9781637748886)
  - Mine reviews and other unfiltered posts (Amazon, TripAdvisor), alongside interviews and user tests.
  - The customer's own phrasing becomes headlines and bullet points almost word for word.
  - Her book is *The Copyselling System*.
  - Unverified: one profile says Copyhackers is being repositioned as JoannaWiebe.co in 2026 ([Favikon](https://www.favikon.com/blog/who-is-joanna-wiebe)).
- **Jobs-to-be-Done and the Value Proposition Canvas.** **CONSENSUS** (product-strategy tools that copywriters adopted). `apply: b (the strategist picks the angle as a job plus a pain or gain that the business can license)` — [HBS Working Knowledge, milkshake](https://www.library.hbs.edu/working-knowledge/clay-christensens-milkshake-marketing); [Chris Lema](https://chrislema.com/markdown/improve-your-product); [Think Insights, VPC](https://thinkinsights.net/strategy/value-proposition-canvas); [Loughborough, Value Proposition and Customer Profiles (PDF)](https://www.lboro.ac.uk/media/media/students/len/documents/Value%20Proposition%20and%20Customer%20Profiles.pdf)
  - Christensen's milkshake research found that most buyers bought the shake to do the same job; asking about attributes such as sweetness missed that job.
  - The canvas maps customer jobs (functional, social, emotional), pains (bad experiences and risks) and gains (wanted outcomes) against pain relievers and gain creators.

### Inferences
- **When each framework fits** (a starting point, not a law):

  | Framework | Awareness | Email types | Single email | Across a sequence |
  |---|---|---|---|---|
  | PAS | problem aware (and unaware, if the problem is universal) | cold first touch, nurture, launch to a cold list | 1–2 lines of problem, 1–2 of consequence, solution plus proof, ask | E1 problem, E2 cost or story, E3 solution plus proof, E4 offer |
  | BAB | problem or solution aware | welcome, onboarding, case-study email | before → after → how | onboarding: each email moves one "before" to an "after" |
  | FAB | product or most aware | launch, promotion, feature announcement | each feature becomes its "so you can…" | one feature per email |
  | AIDA | any (generic) | promotion, newsletter feature | hook → interest → proof → CTA | rarely useful as a sequence plan |
  | 4 U's, Dry's tests | any | subject lines, first lines, claims | checklist after drafting | — |
  | Rule of One | any | all | one idea, one benefit, one ask | one big idea per campaign; one facet per email |

- **A rule for choosing the angle** (strategist, `b`). Angle = (the reader's job, pain or gain, taken from JTBD and voice of customer) × (a differentiator the business can license and nobody else could say, per Dry's test and the 4 U's) × (the claim type set by market sophistication) × (the opening set by awareness). If no licensed differentiator passes the "nobody else" test, the honest fallback is the mechanism (how it works), or specific proof (who it worked for).
- **Objection handling, as these frameworks imply it.** The usual home is the step between proof and ask: a guarantee for the most aware (§1), a peer's story for the product aware (§4), a mechanism for a sceptical market (§1). In a sequence, one email can be given over to the main objection. That is my inference; I found no dedicated practitioner source on objection handling in email (see Gaps).
- **MarketingOS mappings.** The Rule of One maps to the "second ask" mutation and to a deterministic count of CTAs. Dry's falsifiability maps to the gates. Dry's "nobody else could say this" maps to `sameness.py`, plus a possible swap test: replace the brand name with a rival's and ask the reader whether the sentence is still true. Voice of customer maps to the knowledge artifacts (the repo has `knowledge_audience`, `knowledge_voice` and `knowledge_evidence` prompts). Customer phrasing can be used freely as vocabulary; verbatim quotes go through the gates.
- **Good and bad lines** *(illustr.)*:
  - FAB. Bad: "Offline mode." Good: "Offline mode: log the visit in a basement and it syncs when you're back upstairs."
  - Dry's visualise test. Bad: "Streamline your workflow." Good: "Close the laptop at 6 with the invoices already sent."
  - Swap test. Bad: "Trusted by businesses everywhere." (any rival could say it) Good: "Built by two former [named trade] owners in [city]."
  - Handley's one person. Bad: "Dear valued customers…" Good: "You told us March is your busiest month, so here's one thing to do before it."

### Gaps
- **Eddie Shleyner**: I verified no rule of his own. His site, VeryGoodCopy, came up only as a host for lessons on Caples's and Sugarman's headlines.
- Not sourced in this round: the origin of AIDA (usually credited to E. St. Elmo Lewis); who coined BAB and FAB.
- I found no measured head-to-head comparison of the frameworks.
- I did not retrieve Wiebe's published case-study numbers, or primary Copyhackers posts on review mining (a 2014 Amazon review-mining post exists according to search, but was not opened).
- I found no dedicated practitioner source on objection handling in email.

---

## 4. Cold B2B outreach craft (Gong, Lavender, Josh Braun, Becc Holland, 30 Minutes to President's Club)

### Takeaway
Practitioners converge strongly on one skeleton:
1. open with a reason it is this person, now (a trigger, premise or observation);
2. name a problem in their terms;
3. give one line of credible proof;
4. state the solution in a sentence;
5. ask about interest, not for time.

Keep the email very short, plain and conversational. Vendor data supports interest-based CTAs on the first touch (Gong) and short, simple emails (Lavender; Hunter finds a much smaller length effect). What kills replies: asking for a meeting slot cold, pitching before the problem, fake or generic personalisation, promotional subject lines, formal stiffness, images and graphics, and repeating "any thoughts?" bumps.

### Cited Findings
- **Gong Labs: call-to-action study** (Devin Reed, published 27 May 2020, updated 6 March 2026). **CONSENSUS** on the direction. `data: vendor-measured` `apply: b (first touch = interest CTA; once the prospect engages = specific CTA), a (flag a day or time request in a cold first touch), d` — [Gong](https://www.gong.io/blog/this-surprising-cold-email-cta-will-help-you-book-a-lot-more-meetings)
  - 304,174 emails; success was a meeting booked within 10 days.
  - Three types of CTA: *specific* (a set day and time), *open-ended* (a meeting at no set time) and *interest* (asking whether the topic is worth learning more about).
  - The interest CTA performed best in cold email. A specific-time ask succeeded 15% of the time cold, against 37% in active deals (deal stage: specific 37%, open-ended 32%, interest 25%).
  - Gong's explanation: asking for time triggers loss aversion, so sell the conversation before the meeting. The body must give enough context to make the CTA compelling.
- **A counterpoint.** A Growleads post citing Jason Bay's analysis of 85 million cold emails says offer-based CTAs beat interest CTAs on *reply rate*. That is a different metric and dataset from Gong's meetings booked. **CONTESTED** — [Growleads](https://growleads.io/blog/interest-based-ctas-vs-meeting-requests-study/)
- **Lavender best practices** (Will Allred, 19 February 2026; dataset size not stated, presumably correlational). **CONSENSUS** on the direction. `data: vendor, correlational` `apply: a (every item is computable), b` — [Lavender](https://www.lavender.ai/blog/6879935-lavender-best-practices)
  - Emails of 0–50 words get 23% more replies.
  - Emails at a 3rd-to-7th-grade reading level get 1.66 times more replies.
  - Emails with no long sentences get 1.57 times more replies.
  - Mobile-optimised emails get 24% more replies; prospects are 8 times more likely to open on mobile. Keep paragraphs to four lines or fewer, with double line breaks.
  - Neutral to slightly formal emails get 11% more replies. Limit passive voice and conditionals.
  - Average reading time is 11 seconds, and most emails are deleted within 3 seconds.
  - Use contractions and fragments; cut adverbs, adjectives and transition phrases; avoid tautologies. Combine the pronouns *I*, *we* and *you* with specific names.
- Lavender's 2026 benchmark sampled 231,818 cold emails (as of 4 February 2026). I did not retrieve its findings. — [Lavender benchmark report](https://www.lavender.ai/blog/the-cold-email-benchmark-report)
- **Hunter.io** (34 million cold emails). 20–39 words had the highest average reply rate, but rates across length bands sat close together (about 3.5% to 4%), and Hunter concludes word count is no silver bullet. This tempers Lavender's effect size. — [Hunter](https://hunter.io/blog/cold-email-word-count)
- **Lavender's email structure**: an observation, then the problem or insight drawn from it, then credibility for speaking to that problem, then the solution, then an interest-based CTA. **CONSENSUS** — [Lavender, email writing ideas](https://lavender.ai/blog/email-writing-ideas); see also [Lavender, personalisation backups](https://lavender.ai/blog/personalize-your-cold-email-build-backups)
- **30 Minutes to President's Club** (Armand Farrokh and Nick Cegelski), from a compilation of their episodes and guides. **CONSENSUS**, from a secondary compilation. `data: the voicemail figure only` — [Antoine Buteau compilation](https://www.antoinebuteau.com/lessons-armand-farrokh-and-nick-cegelski.md)
  - *Structure*: the "3×3" cold email is a personalised problem, a one-sentence solution and an interest-based CTA. Guest Jason Bay's "Triple T" is trigger, tension, trust.
  - *Form*: plain text, no pictures or graphics; plain, conversational wording, because formality does not signal credibility.
  - *Subject line*: short, personalised, tied to a specific trigger, never a promotional headline.
  - *Specificity*: what they call "dangerous specificity" means naming the specific problem and the concrete change, with no vague talk of efficiency.
  - *Ask*: a small question about interest before any request for a meeting.
  - *Follow-up*: one short bump in the same thread, then vary; do not keep repeating a bare "any thoughts?". Their "Triple Touch" combines email, phone and LinkedIn, each touch raising a *different* problem.
  - *Voicemail*: a voicemail pointing to a same-day email reached a 5.87% reply rate, against 2.73%.
  - *Research*: guest Kyle Coleman's 5×5×5 is five minutes of research, five insights, five minutes of writing.
  - *Openings*: their cold-call rule is never to open with small talk such as asking how the prospect's day is going.
- **Anthony Natoli's three-email sequence (on 30MPC).** Email 1 introduces the problem you solve for the persona; email 3 replies within the thread with social proof such as a customer story; the observation sits in the middle of the template. — [ContactOut, Natoli framework (PDF)](https://blog.contactout.io/wp-content/uploads/2023/10/30MPC-Anthony-Natoli-3-Step-Nugget-Framework-1.pdf)
- **Josh Braun, "poke the bear".** A single, low-pressure question that brings up a problem the prospect has not yet named, in place of a feature pitch. He calls these "illumination questions". A good one needs real knowledge of the segment's operational pain, not a mail-merge field. Secondary sources disagree on what his framework is called: "4T" (trigger, think, third-party credibility, talk) or "5T" (adding "tell"). **CONSENSUS**-compatible; secondary sources only. — [11x guide](https://www.11x.ai/guides/josh-braun-cold-outreach-method); [PhoneBurner "Unblocked", ep. 8](https://www.phoneburner.com/unblocked/eps-08); [Something Inc.](https://somethinginc.com/blog/poke-the-bear-vs-ai-volume-outbound-debate/)
- **Becc Holland (Flip the Script), personalisation at scale.** Research once, find one strong premise, and use that premise to hook every touch of the cadence. Line one is the premise: it answers "why now?" from the research and is entirely about the prospect. Never fake a premise; when a prospect has no digital footprint, fall back to relevance to their role. **CONSENSUS**-compatible; secondary sources only. — [Antoine Buteau on Becc Holland](https://www.antoinebuteau.com/lessons-from-becc-holland/); [Signum.ai (a ~21-day multichannel cadence)](https://signum.ai/blog/how-to-build-b2b-outbound-sales-and-do-personalization-at-scale/). John Barrows' interview page redirected and could not be retrieved: [jbarrows.com](https://jbarrows.com/blog/becc-holland-on-personalization-at-scale/).

### Inferences
- **The consensus first touch**, in four to six lines and well under 100 words, given Lavender's 0–50 and Hunter's 20–39 *(illustr.)*:
  1. **Trigger or premise**, which is Collier's conversation. Good: "Saw you're opening a second site in Nantes." Bad: "Hope you're doing well!" or "My name is… and I work at…"
  2. **Problem in their terms**, sometimes as one of Braun's illumination questions. Good: "Second sites usually double the scheduling work before they double revenue." Bad: "We help companies optimise operations."
  3. **Proof**: one specific peer result, licensed. Good: "[Named peer] cut it to [x] hours a week." Bad: "Trusted by leading brands."
  4. **One-line solution.** Good: "We run the rota for both sites from one screen." Bad: a feature list.
  5. **Interest CTA.** Good: "Worth a look?" or "Open to seeing how they set it up?" Bad (cold): "Can you do Tuesday at 4pm for 30 minutes?"
- **Sequence plan.** Practitioners leave two choices open:
  - Re-use one premise across every touch (Holland), or raise a different problem per touch (30MPC's Triple Touch). This is **CONTESTED** in practice, and the choice likely depends on how strong the premise is: a strong trigger can carry the whole cadence, while a weak one should be replaced by new angles.
  - A shared pattern: E1 problem; E2 a short bump in the same thread; E3 social proof in the thread (Natoli); later touches bring new angles or problems, never a bare "any thoughts?".
  - Once the prospect engages, switch to a specific-time CTA (Gong).
- **What kills replies** (from the inverse of the sourced advice): a meeting request with a fixed time on the first touch; pitching the product before the problem; fake or generic personalisation; promotional subject lines; formal, stiff wording; images and graphics; long sentences and a high reading grade; vague efficiency claims; repeated contentless bumps.
- **MarketingOS mappings.**
  - `a`: word count, reading grade, long-sentence count, paragraph length, number of links and images, and a regex flag for a day-and-time request in a first touch are all deterministic. They are the form rules the duel judge is known to miss, according to `CLAUDE.md`: `stock_phrase_open` was caught 2 times out of 6, and the judge twice preferred the wall of text. That makes code their natural home.
  - The premise must be a *licensed* fact (from research or the ledger), never invented. That is Holland's "never fake a premise" turned into a gate. The repo's `prospect_*` and `relevance_dossier` prompts look, by their names, like the natural source of premises.
  - `c`: questions for the cold reader: "Do you know why this person wrote to *you*, now?"; "What would you reply, in one line?"; "What did they ask you to do, and how big a commitment is it?"
  - `d`: reply rates and meetings booked.
  - Gong's ranking of CTAs is a meeting-booking result from 2020 data. Turning it into a hard gate would over-fit vendor data, so it is better as a writer instruction plus a non-blocking flag.

### Gaps
- I could not retrieve primary material from Josh Braun or Becc Holland (talks, posts). The framework names and quotes come from compilations.
- A "Problem Prompter" framework by DemandJen, from a Gong × 30MPC series, came up in search, but I could not confirm its page or its details.
- Gong's cold-stage percentages for the interest and open-ended CTAs were not readable as text (only the specific CTA's 15%).
- I did not fetch Gong's wider guidance (for example the "7 Laws of Highly Effective Sales Emails" PDF).
- No source in this round lists banned email openers ("I hope this finds you well", "My name is…"). The only sourced opener ban is 30MPC's small-talk rule, and that one is for cold calls.

---

## 5. Lifecycle email craft: welcome, onboarding, nurture and newsletter, launch, promotion, cart and browse abandonment, win-back, re-engagement, post-purchase and review request

### Takeaway
Each lifecycle email has one job, set by its trigger, and the trigger also tells you the reader's awareness: an abandoner is most aware, a new subscriber problem aware, a lapsed customer product aware. Practitioners agree on the *set* of flows and on single-purpose emails. Most specific numbers on timing and lift come from email-tool and agency vendor blogs and are directional at best. The most cited practitioner framework for onboarding is Val Geisler's Dinner Party Strategy: don't serve the main course first; guide the guest one step at a time.

### Cited Findings
- **The core automated flows** are welcome, abandoned cart or checkout, post-purchase, win-back and a sunset flow for dormant contacts. Build welcome, cart and post-purchase first, then the rest by priority. **CONSENSUS** `apply: b (sequence templates)` — [Shulex](https://insight.shulex.com/blog/flows-for-ecommerce-emails); [ATTN Agency](https://www.attnagency.com/blog/klaviyo-flows-ecommerce)
- **Timing and structure claims** from vendor blogs. These came up together, and I could not tie each claim to one URL. **ANECDOTAL/vendor** `data: vendor claims, unverified` `apply: b for structure, d for timing and lift` — [Justuno](https://www.justuno.com/blog/the-highest-converting-lifecycle-marketing-emails-your-ecommerce-company-should-be-sending); [Sendlane](https://www.sendlane.com/blog/effective-lifecycle-email-marketing); [Woobox](https://cdn.woobox.com/articles/ecommerce-email-sequences); [Shulex](https://insight.shulex.com/blog/flows-for-ecommerce-emails); [ATTN Agency](https://www.attnagency.com/blog/klaviyo-flows-ecommerce); [MarTech](https://martech.org/5-email-lifecycle-programs-you-need-and-one-to-drop/)
  - *Cart*: emails at about 1 hour, 24 hours and 72 hours. A three-email series is said to lift revenue 56% over a single email, with an incentive such as free shipping. Test an immediate send against a delayed one.
  - *Win-back*: start at 90–180 days since the last purchase, or set the trigger from each customer's typical gap between purchases. Send at least three emails; 45% are said to open the later ones. Then a sunset step for those who never respond.
  - *Welcome*: one guide puts the incentive in email four, not email one, and takes people out of the flow once they order.
  - *Post-purchase*: runs about 30–90 days and includes a review request and replenishment reminders.
- **Val Geisler's Dinner Party Strategy (onboarding).** **CONSENSUS** on the metaphor; the detailed structure is unverified. `apply: b` — [Forget the Funnel](https://forgetthefunnel.com/saas-email-marketing-for-humans); [Privy](https://www.privy.com/blog/val-geislers-dinner-party-strategy); [Intercom podcast](https://www.intercom.com/blog/podcasts/fix-my-churns-val-geisler-on-how-to-supercharge-your-email-onboarding); [Engage.so](https://engage.so/blog/how-to-convert-free-trials-into-paying-customers-with-the-dinner-party-strategy/)
  - Onboarding is like hosting a dinner party: you don't rush guests to the main course.
  - Applied to new subscribers: welcome them into the community and teach them the brand.
  - Her bio reports a 209% rise in conversions for onboarding emails she rewrote, with no baseline given.
  - One write-up describes six onboarding emails, but I could not confirm that structure as her own.
- **Newsletters and nurture**: Ann Handley says to know the one thing, write to one person, and not carry four or five CTAs (§3). **CONSENSUS** — [Litmus](https://www.litmus.com/blog/how-to-write-great-email-copy)
- **Promotional emails to the most aware**: make the offer with a strong guarantee and say less (§1). **CONSENSUS** — [ActiveCampaign](https://www.activecampaign.com/blog/marketing-stages-awareness-and-buyer-cycle)

### Inferences
- **Each type's job and structure.** This synthesis rests on the cited pieces plus the awareness logic of §1. Everything not cited above is my inference. "Ask" means the one call to action.

  | Type | Job | Awareness | Typical structure | Ask | What kills it | MarketingOS |
  |---|---|---|---|---|---|---|
  | Welcome | deliver what was promised, set expectations, take a first step | problem or solution aware | thanks → what was promised (link or incentive) → what's coming and how often → one first step | one first action | a product brochure, five links, an incentive that isn't where it was promised | `b`; `a` (one primary link); `c` "what happens next?" |
  | Onboarding (SaaS) | get the user to the first value moment, one step at a time (dinner party) | product aware | triggered by behaviour; one step per email; the why of that step; a peer example | do the step | a feature tour; several asks; sent on a calendar regardless of what the user did | `b`; `d` (activation) |
  | Nurture or newsletter | build trust and keep problem awareness alive | problem or solution aware | one idea, one story or insight, a soft link | soft or none | four or five equal-weight CTAs | `b`; `c` "the one thing" |
  | Launch | news, then why it is different (FAB plus mechanism if the market is stage 3+) | product aware (customers) or solution aware (prospects) | news headline (Caples) → what's new → how it works → who it's for → ask | try or see it | hype words, nothing a rival couldn't say | `b`; `a` (sameness); `c` swap test |
  | Promotion | offer for those ready to buy | most aware | offer → why now (a real reason) → guarantee or risk-reversal → ask | buy | a long argument to people who only need the offer; urgency with no reason | `b`; `a` (deadline and price licensed) |
  | Cart or browse abandonment | remind, reassure, then, if policy allows, incentivise | most aware | E1 the reminder (the item itself); E2 answer the likely objection (returns, shipping, sizing); E3 incentive or last call | return to cart | guilt-tripping; an incentive in E1 that trains people to abandon carts | `b`; `d` (timing) |
  | Win-back | give a lapsed customer a reason to come back | product aware | what changed or what you missed → proof → offer → then sunset | come back | "we miss you" with no reason | `b`; `d` |
  | Re-engagement or sunset | confirm interest, or say goodbye | unclear | honest question → one click to stay | stay subscribed | guilt; hiding the opt-out | `b` |
  | Post-purchase or review | reassure, help them use it, then ask for a review once it has been used | most aware | confirmation → how to get the most from it → (later) review request → replenishment | use it, then review it | asking for a review before delivery; upselling in the receipt | `b`; `d` |

- **Sequences inside each flow follow the awareness ladder.** The first email assumes the least, and each later one adds one element (proof, objection, offer). That is classic DR and matches Natoli's in-thread proof email in cold outreach (§4).

### Gaps
- I retrieved no practitioner-grade (non-vendor) source on the structure of launch sequences, the structure of promotional emails, re-engagement copy or review-request copy. I did not fetch Really Good Emails or Litmus pieces on these types.
- I could not retrieve Val Geisler's own list of stages (the Forget the Funnel page is a workshop landing page).
- I found no source that distinguishes browse-abandonment copy from cart-abandonment copy.

---

## 6. Subject line and preheader craft, opening lines, the P.S., signature and sender identity, storytelling in short emails, tone and voice, readability

### Takeaway
In email, the "headline" is the sender name, subject line and preheader read together. The classic rule still applies: self-interest or news, specific, and in cold B2B short, personal and never promotional. The preheader should *add* to the subject, not repeat it. The opening line belongs to the reader: their situation, their trigger, never the sender's self-introduction or small talk. Its job is to get the second line read. Readability has the strongest data in this area (vendor-measured): short, plain sentences, a low reading grade and short paragraphs. Evidence on the P.S. is old, from print, and second-hand. I found no measured data on the ratio of "you" to "we".

### Cited Findings
- **Subject lines.** The best headlines appeal to self-interest or give news (Caples). The headline is read far more than the body (Ogilvy, print). Check against useful, unique, urgent, ultra-specific (the 4 U's). For cold email, keep the subject short and personalised, tie it to a trigger, and avoid a promotional headline (30MPC). **CONSENSUS** `apply: b, c; partly a (length, ALL CAPS, overlap with the preheader); d (opens)` — [VeryGoodCopy](https://www.verygoodcopy.com/verygoodcopy-blogs-10/the-best-headlines); [Swipefile](https://swipefile.com/five-times-as-many-people-read-the-headlines-david-ogilvy); [Unbounce](https://unbounce.com/podcast/copywriting-formula-4-u/); [Antoine Buteau, 30MPC compilation](https://www.antoinebuteau.com/lessons-armand-farrokh-and-nick-cegelski.md)
- **Preheaders.** **CONSENSUS** on not repeating the subject. `apply: a (overlap ratio between subject and preheader), b, d` — [Drip preheader tester](https://www.drip.com/email-preheader-tester); [Listrak](https://www.listrak.com/blog/inboxes-are-where-the-opens-happen); [beehiiv](https://www.beehiiv.com/blog/email-preview-text-examples); [Sender](https://www.sender.net/email-preheader-text/)
  - Complement the subject; don't repeat it. Drip's tester penalises a preheader that overlaps the subject by more than 55%, and Listrak advises against repeating the subject line.
  - Curiosity is easy to overdo (beehiiv).
  - Vendors recommend A/B-testing curiosity-led against value-led preheaders.
- **Opening lines.** **CONSENSUS** `apply: b; a (length of the first sentence; a blacklist of stock openers); c` — [Book Summaries #02](https://booksummaries.substack.com/p/book-summary-02-advertising-secrets); [Antoine Buteau on Becc Holland](https://www.antoinebuteau.com/lessons-from-becc-holland/); [Antoine Buteau, 30MPC](https://www.antoinebuteau.com/lessons-armand-farrokh-and-nick-cegelski.md); [Lavender](https://www.lavender.ai/blog/6879935-lavender-best-practices); [BeFreed on Great Leads](https://www.befreed.ai/book/3606f9a5-4a51-4c8b-977c-daefd5accbde)
  - The first sentence's job is to get the second read, and Sugarman kept his very short.
  - Line one is the premise: "why now", and entirely about the prospect (Holland).
  - Never open with small talk (30MPC, cold calls).
  - Most emails are deleted within 3 seconds (Lavender).
  - Choose the type of opening by the reader's awareness (*Great Leads*, §1).
- **The P.S.** A fundraising practitioner writes that eye-tracking studies show the P.S. is the most-read part of a letter: readers look at the signature, then drop to the P.S. He does not cite the studies. I could not confirm the usual attribution to Siegfried Vögele. **ANECDOTAL** for email. `data: print/direct mail, uncited` `apply: b (optional: restate the single benefit or the deadline), c, d` — [NonProfit PRO (Jeff Brooks)](https://nonprofitpro.com/article/be-first-your-block-experience-these-wonders-marketing-world-176679/7)
- **Signature and sender identity.** Mail that looks personal lands in the opened pile (Halbert). Cold email should be plain text with no graphics (30MPC). Combine pronouns with specific names (Lavender). **CONSENSUS** for 1:1-style email. `apply: b` — [Shortform, Boron Letters](https://www.shortform.com/blog/the-boron-letters-gary-halbert/); [Antoine Buteau, 30MPC](https://www.antoinebuteau.com/lessons-armand-farrokh-and-nick-cegelski.md); [Lavender](https://www.lavender.ai/blog/6879935-lavender-best-practices)
- **Storytelling.** The Rule of One allows one captivating story per piece, and *Great Leads* uses the Story lead for the least aware readers. **CONSENSUS** in principle. `apply: b, c` — [AWAI](https://awai.com/2010/08/the-power-of-one-one-big-idea/); [BeFreed on Great Leads](https://www.befreed.ai/book/3606f9a5-4a51-4c8b-977c-daefd5accbde)
- **Tone and voice.** Neutral to slightly formal emails got 11% more replies in Lavender's data, which also advises limiting passive voice and conditionals. 30MPC says to be plain and conversational, because formal language does not signal credibility. Read together, these advise against stiffness, not against politeness. **CONSENSUS** on plain and unstiff; the degree of formality is mildly **CONTESTED**. `apply: b; a (passive-voice and conditional counts)` — [Lavender](https://www.lavender.ai/blog/6879935-lavender-best-practices); [Antoine Buteau, 30MPC](https://www.antoinebuteau.com/lessons-armand-farrokh-and-nick-cegelski.md)
- **Readability** (Lavender's figures, §4). A 3rd-to-7th-grade reading level was associated with 1.66 times more replies, no long sentences with 1.57 times, and paragraphs of at most four lines on mobile. Use contractions and fragments, cut adverbs and transitions. Hunter shows the length effect is small. **CONSENSUS** on the direction. `data: vendor` `apply: a` — [Lavender](https://www.lavender.ai/blog/6879935-lavender-best-practices); [Hunter](https://hunter.io/blog/cold-email-word-count)

### Inferences
- **Deterministic form checks** (`a`). These are the right home for this section's rules, because the project's own bench found the judge poor on form. All are cheap and need no model call:
  - subject length, and ALL CAPS or exclamation marks;
  - the share of words the preheader shares with the subject;
  - the first sentence's word count;
  - a blacklist of stock openers, kept by the project (the source base for its entries is thin, see Gaps);
  - the reading grade, with a French readability formula for French copy;
  - the number of long sentences;
  - the longest paragraph, in characters or lines;
  - passive-voice and conditional counts;
  - the number of links and of distinct asks.
  Most should be measures or wide bands rather than blocks, because the underlying data is vendor-correlational.
- **Pronouns.** A non-blocking metric could be the number of sentences about the sender ("we", "our") before the first sentence about the reader ("you"). It is a proxy for Collier's rule, not a sourced ratio.
- **A story in a short email** *(my inference)* is two or three sentences: a specific person, a moment, a change. Then one line connecting it to the reader, then the ask. The story's facts must be licensed (a named customer, a real number), which is exactly where MarketingOS's gates and `substantiation.py` apply.
- **The P.S.** should hold one thing only: the benefit restated, the deadline, or the answer to the main objection. A P.S. that introduces a second offer breaks the Rule of One, and would trip the "second ask" mutation.
- **The sign-off** is a real person's name and role. Per `clarity_gate`'s design, the sign-off answers *who sent this*, not *what this is*, so it cannot be where the offering gets named.
- **Good and bad lines** *(illustr.)*:
  - Subject, cold. Bad: "Revolutionise Your Workflow Today!!!" Good: "Second site in Nantes"
  - Subject, lifecycle. Bad: "Newsletter #42" Good: "The 3 orders most likely to arrive late"
  - Preheader. Bad: it repeats the subject. Good: "One of them is avoidable this week."
  - Opening. Bad: "I hope this email finds you well." Good: "Your March prices went up [x]%."
  - P.S. Bad: "P.S. Also check out our new app!" Good: "P.S. The [x]% price holds until Friday, then goes back up."

### Gaps
- I found no measured data on the ratio of "you" to "we", or on the effect of sender names in marketing email (person versus brand).
- I found no controlled study of the P.S. in email. The eye-tracking evidence is from print and uncited.
- Not researched in this round: storytelling structures for sequences, such as Andre Chaperon's "soap opera sequence" or Ben Settle's daily story emails.
- The thresholds Lavender uses for a "long sentence", and how it measures reading grade, are not stated on its page.

---

## 7. Where practitioners disagree, and what each disagreement depends on

### Takeaway
Most disagreements dissolve once you fix four variables:
- the reader's **awareness**;
- the **relationship** (cold, opted in, customer);
- the **size of the commitment** asked;
- the **metric** each practitioner optimised (replies, meetings, clicks, revenue).

Long copy, several CTAs and designed HTML belong to engaged, opted-in, retail and promotional contexts. Short copy, a single interest-based ask and plain text belong to cold and 1:1-style contexts. Curiosity against clarity in subject lines has no settling evidence.

### Cited Findings
- **Long copy against short.** **CONTESTED**: it depends on awareness, the commitment asked and the relationship. `apply: b (a length budget per awareness level and type), a (word bands), d` — [Antoine Buteau on Ogilvy](https://www.antoinebuteau.com/lessons-from-david-ogilvy/); [ActiveCampaign](https://www.activecampaign.com/blog/marketing-stages-awareness-and-buyer-cycle); [Lavender](https://www.lavender.ai/blog/6879935-lavender-best-practices); [Hunter](https://hunter.io/blog/cold-email-word-count)
  - For: Ogilvy, for a great many products (print).
  - In the middle: Schwartz's school, via Elias, says problem-aware readers need longer copy and most-aware readers less.
  - Against, for cold email: Lavender (0–50 words did best).
  - Hunter's 34 million emails show only a small length effect.
- **One CTA or several.** **CONTESTED** only for newsletters and long promotional emails. For single-purpose emails, one ask is **CONSENSUS**. I found no sourced defence of multiple *different* asks. `apply: a (count distinct asks and links), b` — [Litmus/Handley](https://www.litmus.com/blog/how-to-write-great-email-copy); [AWAI](https://awai.com/2010/08/the-power-of-one-one-big-idea/); [Gong](https://www.gong.io/blog/this-surprising-cold-email-cta-will-help-you-book-a-lot-more-meetings)
  - Handley: an email with four or five CTAs should make you reconsider.
  - The Rule of One's single inevitable response.
  - Gong measured the *type* of CTA, not how many.
- **Plain text against designed HTML.** **CONTESTED**: it depends on the relationship and the content (1:1 and cold against retail with product imagery). `data: HubSpot and Litmus A/B tests (dated, audience-specific)` `apply: b (a format per type), d` — [HubSpot](https://blog.hubspot.com/marketing/plain-text-vs-html-emails-data); [Litmus test](https://www.litmus.com/blog/the-results-are-in-a-b-testing-html-vs-plain-text-emails); [Litmus community poll](https://www.litmus.com/blog/html-vs-plain-text-emails-the-email-community-says/); [Antoine Buteau, 30MPC](https://www.antoinebuteau.com/lessons-armand-farrokh-and-nick-cegelski.md)
  - HubSpot's A/B tests found that HTML lowered open rates, and the richer the HTML, the lower the opens. In one test the HTML version had a 21% lower click-through rate, which with the open rate meant 51% fewer clicks. First published in 2015, updated 2021, on HubSpot's own audience.
  - Litmus ran its own test on a webinar programme. A secondary source reports plain text produced about 60% of webinar conversions among existing customers and about 49% among non-customers. Litmus concluded there is no one-size-fits-all answer.
  - In a Litmus community poll, 68.3% voted for HTML.
  - 30MPC prescribes plain text for cold email.
- **Curiosity against clarity in subject lines.** **CONTESTED**, with no settling data. `apply: d (only an A/B split on a real list settles it)` — [VeryGoodCopy](https://www.verygoodcopy.com/verygoodcopy-blogs-10/the-best-headlines); [Upgrow](https://upgrow.io/blog/harry-dry-copywriting-3-rules); [Subscribers That Buy](https://subscribersthatbuy.substack.com/p/the-wrong-subject-line-trick); [beehiiv](https://www.beehiiv.com/blog/email-preview-text-examples)
  - For clarity, implicitly: Caples ranks self-interest and news above curiosity, and Harry Dry's visualisable, falsifiable claims push the same way.
  - For curiosity: one Substack post claims it wins in welcome emails, with an unsourced 23%.
  - Vendors say test it, and warn that curiosity is easy to overdo.
  - I found no controlled, published comparison.
- **Interest CTA against specific CTA against offer.** **CONTESTED**: it depends on the stage of the relationship and on the metric. — [Gong](https://www.gong.io/blog/this-surprising-cold-email-cta-will-help-you-book-a-lot-more-meetings); [Growleads](https://growleads.io/blog/interest-based-ctas-vs-meeting-requests-study/)
  - Gong: interest for cold, specific for active deals.
  - Jason Bay's data, via Growleads: offer-based CTAs beat interest on reply rate.
- **One premise across the cadence, or a new problem per touch.** **CONTESTED**: it likely depends on how strong the trigger is (my inference). — [Antoine Buteau on Becc Holland](https://www.antoinebuteau.com/lessons-from-becc-holland/); [Antoine Buteau, 30MPC](https://www.antoinebuteau.com/lessons-armand-farrokh-and-nick-cegelski.md)
  - Holland: one researched premise hooks every touch.
  - 30MPC's Triple Touch: each touch raises a different problem.
- **How hard to agitate.** **CONTESTED**: it depends on awareness and on the stakes. — [Copyblogger](https://copyblogger.com/problem-agitate-solve/); [Crazy Egg](https://www.crazyegg.com/blog/?p=99420); [Write With AI on Great Leads](https://writewithai.substack.com/p/great-leads-kickstart-part-3-when)
  - PAS makes agitation central.
  - *Great Leads* warns against dwelling on the pain, and practitioners publish guides on using PAS "without being cringy".
- **Depth of personalisation against volume.** **CONTESTED**: practitioners argue whether to research each prospect or send at volume. — [Something Inc., poke the bear vs AI volume](https://somethinginc.com/blog/poke-the-bear-vs-ai-volume-outbound-debate/); [Antoine Buteau on Becc Holland](https://www.antoinebuteau.com/lessons-from-becc-holland/); [Antoine Buteau, 30MPC](https://www.antoinebuteau.com/lessons-armand-farrokh-and-nick-cegelski.md)
  - There is an explicit public debate between "poke the bear" questions and AI-driven high-volume outbound.
  - Holland says research once and reuse the premise; Coleman's 5×5×5 caps research at minutes.
- **Formality.** Lavender's data favours neutral to slightly formal (+11%); 30MPC says conversational. **Mildly CONTESTED**; probably compatible, since both argue against stiffness. — [Lavender](https://www.lavender.ai/blog/6879935-lavender-best-practices); [Antoine Buteau, 30MPC](https://www.antoinebuteau.com/lessons-armand-farrokh-and-nick-cegelski.md)

### Inferences
- **Defaults for MarketingOS** where practitioners disagree (`b`; each verifiable only by `d`). Because there is no send data, choose the default that fails safe on *comprehension*: that is the one thing the cold reader may veto, and the one the gates already protect.

  | Question | Cold first touch | Opted-in nurture or newsletter | Promotion, cart, win-back |
  |---|---|---|---|
  | Length | ≤ ~100 words (Lavender, Hunter) | as long as the one idea needs | short; the offer leads |
  | Asks | one interest ask | one primary link; secondary links allowed in a digest format | one ask, which may repeat (same target) |
  | Format | plain text, sent from a person | plain or light HTML | HTML acceptable (product images) |
  | Subject | clear and specific, tied to the trigger | clarity by default; curiosity only from a known sender | offer or news, clear |
  | Agitation | one line of consequence, stated as fact | light | none (the reader already wants it) |

- **Where code should take a side and where it should not.** Code can enforce what is CONSENSUS and computable: one ask, licensed specifics, offering named, readable form. It should only *measure* what is CONTESTED (length, format, curiosity), so that real send data can settle those later. This mirrors the project's existing split between gates that block and judgment that never blocks (`CLAUDE.md`).
- **A recurring confound.** Practitioners optimise different metrics: Gong counts meetings, Lavender and Hunter replies, HubSpot opens and clicks, vendors revenue. Before importing a "rule" as a threshold, MarketingOS should note which metric it was optimised for.

### Gaps
- I found no controlled, published test that settles curiosity against clarity in subject lines.
- I found no sourced practitioner defence of several *different* CTAs in one email. The usual counter-position, newsletters and digests, is practice rather than documented argument in what I found.
- The HubSpot and Litmus format tests are dated and audience-specific. I found no recent (2025–2026) replication.
- No source quantifies how the right length changes with awareness. Schwartz's "longer for the less aware" is qualitative.
