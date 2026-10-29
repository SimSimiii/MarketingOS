# Offer, price, risk, trust and proof: what makes people buy (or take the next step)

Notes as of October 2026. Language: English (final report in French).

**Grading key (from the brief):** STRONG = meta-analysis, replication or large field experiment; MODERATE = single peer-reviewed study or large disclosed-method dataset; WEAK-FOLKLORE = vendor/practitioner material or unreplicated claim. **FAILED-REPLICATION** marks a failed or contested replication. **MarketingOS mapping codes:** (a) deterministic code check; (b) strategist/writer prompt instruction; (c) cold-reader/critic criterion (rewrite signal, never blocking); (d) measurable only with real send data. A dagger (†) means the URL is a well-known page I did not re-fetch this session.

**How these notes were verified:** the shared WebSearch budget ran out partway through. After that, claims were checked by fetching primary pages directly, by extracting text from three study PDFs (Barton et al. 2022, Hershfield/Shu/Benartzi, Borborema et al. 2026), and by looking up every journal DOI in the Crossref registry. That lookup found five DOIs I had recalled wrongly (Boulding & Kirmani 1993; Inman & McAlister 1994; Bawa & Shoemaker 2004; Inman, McAlister & Hoyer 1990; Urbany, Bearden & Weilbaker 1988). Their claims were dropped or moved to Gaps rather than cited. Code facts about MarketingOS come from reading the repository and are cited by file path.

---

## 1. Value proposition and perceived value (benefits vs features, outcome specificity, JTBD, cost of inaction, status quo, "doing nothing" in B2B)

### Takeaway
The strong evidence here is about **inertia**, not about "benefits beat features". Status-quo and default effects are large and well replicated. A choice between close alternatives makes people defer. In B2B, practitioner data say most lost deals die to "no decision" rather than to a competitor. Meta-analyses find **no reliable advantage for loss framing** ("cost of inaction") over gain framing. So copy should make the outcome concrete with the business's own facts and make the first step small and safe, rather than dramatise what not buying costs.

### Cited Findings
- **[STRONG]** Status quo bias: in experiments and field data (health-plan and retirement-allocation choices), people disproportionately keep the current option even when alternatives are equivalent or better. Widely replicated since. — [Samuelson & Zeckhauser 1988, J. Risk & Uncertainty](https://doi.org/10.1007/BF00055564)
- **[STRONG]** Defaults meta-analysis: the average default effect is d = 0.68, with large heterogeneity explained by why the default works (endorsement, endowment, effort). — [Jachimowicz et al. 2019, Behavioural Public Policy](https://doi.org/10.1017/bpp.2018.43)
- **[WEAK-FOLKLORE]** B2B "no decision": Dixon & McKenna analysed about 2.5 million recorded sales conversations from several dozen companies, from transactional to complex B2B sales. They report that 40-60% of qualified deals are lost to "no decision" (customer indecision) rather than to a competitor. Summaries describe the often-quoted "56%" figure inconsistently. Their prescription is to Judge indecision, Offer a recommendation, Limit exploration and Take risk off the table. Proprietary dataset, vendor-analysed (Tethr), not peer-reviewed. — [Matt Dixon interview, CustomerThink](https://customerthink.com/the-problem-of-customer-indecision-and-how-to-get-over-it-interview-with-matt-dixon/); [book page, Penguin](https://www.penguin.com.au/books/the-jolt-effect-9780593538104)
- **[MODERATE]** Choice conflict produces deferral: adding a second attractive option raised the share of people who chose to defer or keep searching. — [Tversky & Shafir 1992, Psychological Science](https://doi.org/10.1111/j.1467-9280.1992.tb00047.x). People choose the no-choice option more when the alternatives are similarly attractive. — [Dhar 1997, JCR](https://doi.org/10.1086/209506)
- **[STRONG]** Gain vs loss framing: meta-analyses find no significant persuasive advantage for loss-framed messages, either for prevention behaviours — [O'Keefe & Jensen 2007, J. Health Communication](https://doi.org/10.1080/10810730701615198) — or for detection behaviours — [O'Keefe & Jensen 2009, J. Communication](https://doi.org/10.1111/j.1460-2466.2009.01417.x). Caveat: the domain is health messaging, not commercial offers.
- **[MODERATE]** Missing an attractive opportunity makes people less likely to take a later, somewhat less attractive one ("inaction inertia"). This is the evidence-backed version of the "cost of waiting", and it is about missed *offers*, not missed outcomes. — [Tykocinski, Pittman & Tuttle 1995, JPSP](https://doi.org/10.1037/0022-3514.68.5.793) (replication details in Q5)
- **[MODERATE]** Outcome specificity and numbers: numerical precision in advertising claims acts as a credibility signal (studied with environmental claims). — [Xie & Kronrod 2012, J. Advertising, "Is the Devil in the Details?"](https://doi.org/10.1080/00913367.2012.10672460). Boundary: very precise anchors backfire with *experts*, who read them as low competence. — [Loschelder et al. 2016, Psychological Science, "The Too-Much-Precision Effect"](https://doi.org/10.1177/0956797616666074)
- **[WEAK-FOLKLORE]** Jobs-to-be-done is a practitioner framework (people "hire" a product for a job in a circumstance). No controlled test of JTBD-framed copy against other framings was located. — [Christensen et al. 2016, HBR†](https://hbr.org/2016/09/know-your-customers-jobs-to-be-done)
- **[local code fact]** MarketingOS's judge bench already treats "the explanatory beat traded for a benefit" as damage the judge must detect, because it is invisible to the gates. In effect, a benefit asserted without its mechanism is treated as worse copy. — [CLAUDE.md, Evaluation section](../../CLAUDE.md)

### Inferences
- In B2B the main competitor is **deferral**. The levers the evidence supports are: one recommended path rather than a menu (Tversky & Shafir; Dhar; JOLT's "Offer/Limit"), a smaller and more reversible next step than the purchase itself, and removing risk (Q3). More benefits do not address any of these.
- The evidence gives no general reason to prefer "cost of inaction" framing over gain framing. It is also the framing that most tempts a model to invent ("you're losing 6 hours a week"). So it should be allowed only when the loss itself is a licensed fact.
- Benefits vs features: the honest synthesis is **feature → mechanism → outcome**, with the outcome stated only in licensed terms. This matches MarketingOS's existing stance (the explanatory-beat mutation) and its licensing constraint. An outcome with no number can still be concrete: what the reader will see or do differently.
- **Driver: concrete outcome / value**
  - Evidence the business must supply: METRIC entries with subject, unit and timeframe (EvidenceContext); OUTCOME proof (a number someone other than the company attached); FEATURE entries that explain the mechanism.
  - If missing: describe the mechanism and what changes in the reader's workflow, without numbers. Never estimate the reader's own figures.
  - (a) `evidence_gate` already blocks unlicensed numbers. A cheap addition would be a lexical flag on second-person quantified-loss constructions ("you're losing / costing you / wasting") that requires a METRIC entry.
  - (b) Strategist: name, in each brief, the status-quo alternative the reader would otherwise keep and the smallest next step. Writer: state one outcome, in licensed terms, attached to its mechanism.
  - (c) Cold reader: "What would you get, and what would trying it cost you?" (extends `BlindRead.understood`). Critic: flag benefit claims with no mechanism.
  - (d) Whether gain vs loss framing changes replies or clicks for a given business.
- **Driver: status quo / "doing nothing"**
  - Evidence: switching facts (migration support, setup steps and time) only if documented.
  - If missing: make the CTA a zero-commitment step (reply, view a documented example) instead of the purchase.
  - (a) None beyond the existing CTA gates (`call_to_action_gate`, `planned_call_to_action_gate`, `repeated_call_to_action_gate`).
  - (b) Prompt: one ask per email and no option lists (also consistent with the existing "second ask beside the first" mutation).
  - (c) Critic: "Is there a reason this reader would not just leave things as they are?"
  - (d) Deferral and decision rates.

### Gaps
- No peer-reviewed controlled test of benefit-led vs feature-led copy was found. "Feature fatigue" (Thompson, Hamilton & Rust 2005, JMR) is relevant, but its DOI could not be verified in Crossref this session, so it is not cited.
- The JOLT figures (40-60%, 56%) come from a book and interviews; the primary method is not disclosed.
- Gartner-style B2B buying-journey statistics could not be checked once the search budget ran out.
- No commercial-offer meta-analysis of gain vs loss framing was located; the health-domain result is transferred by inference.

---

## 2. Price presentation (charm/left-digit, precise vs round, anchoring and reference prices, decoy, rule of 100, discount vs bonus, partitioning, temporal reframing, zero price, pain of paying, subscription framing)

### Takeaway
Left-digit (charm-price) effects are among the best-replicated findings in pricing, in both lab and very large field datasets. But in MarketingOS **the price is a licensed fact**, so price endings are the business's decision, not the copy's. What copy controls is framing:
- which licensed figure to show (unit, period, plan);
- whether to show a reference price (only if documented; reference prices work, which is exactly why invented ones are tempting);
- how to express a discount (percent vs amount; weak evidence);
- whether to show mandatory surcharges (hiding them raises spending at first, but unexpected extra costs are the top cited reason for abandoning a purchase);
- per-day reframing (strong field evidence for small recurring amounts, but the derived numbers must be licensed);
- the word "free" (a strong pull, with a retention cost).

Decoy effects and incidental anchoring have **contested replications**.

### Cited Findings
**Left-digit / charm pricing**
- **[MODERATE]** 9-ending prices are judged disproportionately smaller when the leftmost digit changes ($2.99 vs $3.00) — the left-digit effect in magnitude judgments. — [Thomas & Morwitz 2005, JCR](https://doi.org/10.1086/429600)
- **[STRONG]** Field experiments in a mail-order catalog: $9-ending prices increased demand, including relative to a *lower* price. — [Anderson & Simester 2003, Quantitative Marketing & Economics](https://doi.org/10.1023/A:1023581927405)
- **[STRONG]** Wholesale used-car prices drop discontinuously at 10,000-mile odometer thresholds, showing left-digit inattention even in a high-stakes market. — [Lacetera, Pope & Sydnor 2012, AER](https://doi.org/10.1257/aer.102.5.2206)
- **[STRONG]** Lyft: demand falls discontinuously when a fare crosses a whole-dollar threshold ($13.99 vs $14.00). The study uses over 600 million sessions plus a field experiment, and estimates a profit opportunity of about $160M a year. — [List, Muir, Pope & Sun 2023, Review of Economic Studies](https://www.restud.com/left-digit-bias-at-lyft/); [summary](https://academicnewsletter.sufe.edu.cn/info/343441)
- **[STRONG]** Retail scanner data: a quarter to a third of prices end in 99. Consumers react to the one-cent drop to a 99 ending as if it were a 15-25 cent cut, while firms price as if it were worth 1.5-3 cents. — [Strulov-Shlain, via Chicago Booth Review](https://www.chicagobooth.edu/review/retailers-underestimate-power-penny-pricing)
- **[MODERATE]** When price signals quality, sellers use round prices; 9-endings carry a low-price image. — [Stiving 2000, Management Science](https://doi.org/10.1287/mnsc.46.12.1617.12078). Round prices "feel right" for feeling-based purchases and non-round prices for cognition-based ones. — [Wadhwa & Zhang 2015, JCR](https://doi.org/10.1086/678484)
- **[MODERATE]** Alternative ending: 1-endings (e.g., $2111) can read more like a discount than 9-endings, and a year-long field study found higher click-through for them in online ads. — [Journal of Retailing and Consumer Services study (Koç University record)](https://research.hub.ku.edu.tr/entities/publication/40ee3f08-f81e-45a1-9d58-85fbcbc0d837/full)

**Precise vs round prices**
- **[MODERATE]** Buyers underestimate the magnitude of precise prices (e.g., $395,425 judged lower than $395,000). In data on about 27,000 home sales (South Florida, Long Island), precise list prices were associated with sale prices closer to asking. Coverage reports that round-priced homes sold for about 0.73% less. — [Thomas, Simon & Kadiyali 2010, Marketing Science](https://doi.org/10.1287/mksc.1090.0512); [coverage, strategy+business](https://strategy-business.com/article/re00007)
- **[MODERATE]** Precise anchors produce smaller adjustments than round ones. — [Janiszewski & Uy 2008, Psychological Science](https://doi.org/10.1111/j.1467-9280.2008.02057.x). With experts, overly precise anchors backfire. — [Loschelder et al. 2016](https://doi.org/10.1177/0956797616666074)

**Anchoring and reference prices**
- **[STRONG]** An integrative review (meta-analysis) of comparative price advertising: advertised reference prices ("was X, now Y") raise deal and value perceptions. — [Compeau & Grewal 1998, J. Public Policy & Marketing](https://doi.org/10.1177/074391569801700209). A separate meta-analysis of how price presentation affects perceived savings exists (findings not retrieved, see Gaps). — [Krishna, Briesch, Lehmann & Yuan 2002, J. Retailing](https://doi.org/10.1016/S0022-4359(02)00072-6)
- **[STRONG]** Meta-analysis: price is positively related to perceived quality. — [Rao & Monroe 1989, JMR](https://doi.org/10.1177/002224378902600309)
- **[STRONG, field]** Sale signs raise demand even when the price does not change. — [Anderson & Simester 1998, Marketing Science](https://doi.org/10.1287/mksc.17.2.139). They become less effective as more products carry them, i.e., the signal's credibility dilutes. — [Anderson & Simester 2001, Marketing Science](https://doi.org/10.1287/mksc.20.2.121.10194)
- **FAILED-REPLICATION (incidental anchoring on willingness to pay):** the well-known result that arbitrary anchors such as social-security digits shift WTP — [Ariely, Loewenstein & Prelec 2003, QJE](https://doi.org/10.1162/00335530360535153) — came out much weaker in a replication. — [Maniadis, Tufano & List 2014, AER, "One Swallow Doesn't Make a Summer"](https://doi.org/10.1257/aer.104.1.277). A WTP/WTA anchoring meta-analysis exists (estimates not retrieved). — [Li, Maniadis & Sedikides 2021, J. Behavioral & Experimental Economics](https://doi.org/10.1016/j.socec.2020.101629)

**Decoy (asymmetric dominance)**
- **[MODERATE]** Original finding: adding an asymmetrically dominated option raises the share of the option that dominates it. — [Huber, Payne & Puto 1982, JCR](https://doi.org/10.1086/208899). A meta-analysis found asymmetric effects for higher- vs lower-quality brands, with patterns that may not generalise across segments. — [Heath & Chatterjee 1995, JCR](https://doi.org/10.1086/209449); [record](https://ideas.repec.org/p/hal/journl/hal-00670480.html)
- **FAILED-REPLICATION:** in 2014 JMR replications the effect was small or absent under realistic stimuli. Yang & Lynn report 91 attempts across 23 product categories and 73 choice sets, and found that verbal or pictorial descriptions largely eliminate the effect (counts as given in a secondary summary). — [Frederick, Lee & Baskin 2014](https://doi.org/10.1509/jmr.12.0061); [Yang & Lynn 2014](https://doi.org/10.1509/jmr.14.0020); [secondary summary](https://atticusli.com/replication-crisis/decoy-effect-asymmetric-dominance/). A field experiment on a flight aggregator with more than 140,000 search sessions found no evidence of the effect among recommended options. — [Rafai et al. 2022, Decision Support Systems](https://www.skema.edu/en/faculty-and-research/publications/no-evidence-attraction-effect-among-recommended-options-large)
- **[MODERATE, field data] Counterpoint:** at an online diamond retailer, shoppers rarely noticed decoy-dominant pairs (11-25% detection). When they did, the dominant diamond's sale hazard rose 1.8-3.2 times, and the effect lifted gross profit by 14.3%. — [Wu & Cosguner 2020, Marketing Science](https://doi.org/10.1287/mksc.2020.1231)

**Percent vs absolute discount ("rule of 100")**
- **[MODERATE]** Which framing is perceived as the larger saving depends on price level: percentage framing favoured for low-priced products, absolute (dollar) framing for high-priced ones. This is the academic root of the popular "rule of 100". — [Chen, Monroe & Lou 1998, J. Retailing](https://doi.org/10.1016/S0022-4359(99)80100-6). As a precise threshold, the "rule of 100" itself is **WEAK-FOLKLORE**.

**Discount vs bonus quantity**
- **[MODERATE]** A bonus pack ("50% more") sold substantially better than an economically equivalent price discount in a field study. The mechanism is "base value neglect": people ignore what a percentage is a percentage *of*. A mall intercept and lab studies set boundary conditions. — [Chen, Marmorstein, Tsiros & Rao 2012, J. Marketing](https://doi.org/10.1509/jm.10.0443); [abstract record](https://experts.umn.edu/en/publications/when-more-is-less-the-impact-of-base-value-neglect-on-consumer-pr/). The "over 70%" sales lift for hand lotion is an author's description in an interview (**WEAK** as a figure). — [interview](https://vivekkaul.com/2012/07/15/people-prefer-50-free-to-33-lower-price/)

**Price partitioning and drip fees**
- **[MODERATE]** Partitioned prices (base price + surcharge) lowered recalled total cost and raised demand. — [Morwitz, Greenleaf & Johnson 1998, JMR](https://doi.org/10.1177/002224379803500404). A later review concludes that effects depend on how the surcharge is perceived. — [Greenleaf et al. 2016, J. Consumer Psychology](https://doi.org/10.1016/j.jcps.2015.04.006)
- **[STRONG, field]** StubHub: showing fees only at checkout raised spending compared with upfront all-in prices. — [Blake, Moshary, Sweeney & Tadelis 2021, Marketing Science, "Price Salience and Product Choice"](https://doi.org/10.1287/mksc.2020.1261). Posting tax-inclusive prices on shelves reduced demand by about 8% in a store experiment. — [Chetty, Looney & Kroft 2009, AER](https://doi.org/10.1257/aer.99.4.1145)
- **[MODERATE]** Among abandoners (excluding "just browsing"), 40% cite extra costs (shipping, tax, fees), the top reason, and 12% say they couldn't see or calculate the total cost up front. — [Baymard Institute, cart abandonment](https://baymard.com/lists/cart-abandonment-rate)

**Temporal reframing ("pennies a day")**
- **[MODERATE]** Framing a cost as a small daily amount makes small ongoing expenses the comparison set and raises compliance for small amounts. — [Gourville 1998, JCR](https://ideas.repec.org/a/oup/jconrs/v24y1998i4p395-408.html)
- **[STRONG, field]** Field experiment on a savings app (Acorns): the same roughly $150 a month framed as $5/day enrolled **29.9%**, vs **10.3%** at $35/week and **7.1%** at $150/month, roughly four times as many. The tripled participation gap between the highest and lowest income brackets in the monthly frame disappeared in the daily frame. But one-month retention was lower in the daily frame (**75%** vs 85% weekly and 86% monthly). The paper also cites prior work showing the preference reverses for large amounts (aggregated frames are preferred when the per-day figure is large). — [Hershfield, Shu & Benartzi, field experiment (SSRN version)](https://anderson-review.ucla.edu/wp-content/uploads/2021/03/Hershfield_Shu_Benartzi_2018_SSRN-id3097468.pdf)
- **[WEAK]** An unpublished dissertation found pennies-a-day framing helped for charity but not for consumer products. — [LSU dissertation](https://repository.lsu.edu/gradschool_dissertations/2217). No direct replication of Gourville 1998 was found.

**Zero price**
- **[MODERATE]** Cutting a price to zero shifts demand far more than an equal cut elsewhere (Hershey's Kisses vs Lindt truffles), which the authors attribute to affect. — [Shampanier, Mazar & Ariely 2007, Marketing Science](https://doi.org/10.1287/mksc.1060.0254). Supported in a Moroccan telecom experiment, though there the affect explanation was only partial. — [Driouchi et al., MPRA](https://mpra.ub.uni-muenchen.de/32352/). A secondary summary reports no zero-price effect in the Swedish prescription-drug market (**WEAK**). — [The Decision Lab](https://thedecisionlab.com/reference-guide/psychology/zero-price-effect). No failed direct replication of the original experiments was found.

**Pain of paying**
- **[MODERATE]** Mental accounting ties payments to consumption, so people prefer prepaying for consumption ("the pain of paying"). — [Prelec & Loewenstein 1998, Marketing Science](https://doi.org/10.1287/mksc.17.1.4). Willingness to pay was substantially higher when paying by credit card (sealed-bid ticket auctions). — [Prelec & Simester 2001, Marketing Letters](https://doi.org/10.1023/A:1008196717017). Replication status not checked (see Gaps).

**Subscription vs one-off framing**
- **[MODERATE]** "Payment depreciation": a payment's pull on usage fades as time passes since the payment. — [Gourville & Soman 1998, JCR](https://doi.org/10.1086/209533)
- **[MODERATE]** Many customers choose flat rates even when pay-per-use would be cheaper, and are content with that choice; the flat-rate bias did not raise churn, while the pay-per-use bias did. — [Lambrecht & Skiera 2006, JMR](https://doi.org/10.1509/jmkr.43.2.212)
- **[STRONG, field; working paper]** A European newspaper randomised more than 2 million potential subscribers into auto-renew vs auto-cancel trials (crossed with 2- vs 4-week offers and €0 vs €0.99). Auto-renewal raised subscription rates in the first four months (+20%) and new-subscriber revenue (+21%). But about half of auto-renewal takers paid for a subscription they did not want, and 24-36% of potential subscribers did not subscribe in the first weeks after an auto-renewal offer, i.e., consumers anticipated their own inertia. After one year revenue was equivalent. After two years auto-renewal had produced 10% fewer new subscribers, and auto-renewed subscribers rarely read the paper. — [Miller, Sahni & Strulov-Shlain, via Stanford GSB](https://www.gsb.stanford.edu/insights/auto-renew-snags-new-subscribers-its-not-good-way-keep-them)

### Inferences
- **The copy cannot use charm or precision pricing.** The price must be reproduced exactly as licensed (rounding $49.99 to "under $50" or "about $50" is a new number). Left-digit and precision evidence belongs in an *offer-design note to the business*, not in the writer.
- **A recurring theme:** framings that lower the purchase threshold recruit more marginal buyers. Daily framing enrolled four times as many but retained fewer at one month; auto-renewal won early and lost later; free-trial customers are harder to retain (Q3). Without send data MarketingOS cannot measure this trade-off, so it should default to the honest, transparent version of each framing.
- **Reference prices** are strong (meta-analysis) precisely because they are cheap to fabricate. They are allowed only when the material documents both prices and their dates.
- **Decoys** apply to plan tables, not to a one-ask email. With mixed replication evidence, there is nothing to build.
- **Driver: which licensed price to show (unit, period, total)**
  - Evidence: PRICE entries with currency, unit (per seat, per month), billing period, and conditions (VAT, setup fee, minimum term) in `EvidenceContext.conditions`; plans in `OfferSheet.plans`.
  - If missing: do not mention price or hint at it ("affordable"). Point the CTA at a zero-cost step.
  - (a) Per CLAUDE.md, `evidence_gate` licenses every number, so a derived figure such as "$1.64/day" would presumably fail (not tested here). Proposal: a deterministic *derived-price* generator that computes per-day, per-month and per-year equivalents from a PRICE entry, adds them to the evidence index with provenance, and offers per-day only below a small threshold (the literature shows reversal for large amounts). Also proposed: when a PRICE entry has conditions (excl. VAT, + setup), any email that quotes the price must carry them, in the same pattern `OfferSheet.ground_guarantees` already applies to guarantees.
  - (b) Writer: show the total or recurring cost the reader actually pays, and include mandatory components. Never imply a lower all-in price.
  - (c) Cold reader: "Do you know what this would cost you, and when?"
  - (d) Conversion and retention effects of daily vs monthly framing.
- **Driver: discounts and promotions**
  - Evidence: regular price, promo price or amount, eligibility, start and end date (`temporal_scope`).
  - If missing: no discount language at all; `intent.py` already says "Do not invent a discount, deadline or reason they stopped" for recovery emails.
  - (a) If both prices are licensed, code can compute the percent and absolute forms (both then licensed). Choosing between them by price level is a **weak** heuristic, so a prompt-level hint at most. "Was/now" language with no licensed regular price should be blocked.
  - (b) Prompt: express the saving in the form the material uses, or the computed equivalent; "bonus quantity" framing only if the offer really is extra quantity.
  - (c) Critic: does the discount read as credible (dated, with a reason) or as a perpetual sale? Anderson & Simester show credibility dilutes with overuse.
  - (d) Which framing lifts clicks.
- **Driver: "free" / zero price**
  - Evidence: `OfferSheet.free_entry`, or a PRICE entry of 0 with its limits (trial length, credit-card requirement).
  - If missing: never say free, trial or "no cost".
  - (a) Lexical check: "free", "no cost", "trial", "$0" require `free_entry` or a zero-price entry. "100% free" is already in the spam vocabulary.
  - (b) Strategist: for cold readers, prefer a licensed free first step as the CTA (zero-price pull), keeping the true limits.
  - (c) Critic: are the limits of "free" clear?
  - (d) Retention of buyers acquired with "free".
- **Driver: subscription terms**
  - Evidence: renewal and cancellation terms, verbatim.
  - If missing: say nothing about renewal.
  - (a) If a trial is mentioned and the ledger holds renewal terms, require them.
  - (b) Prompt: state renewal terms plainly; transparent terms beat traps in the long run (Miller et al.).
  - (d) Long-run subscriber counts.

### Gaps
- Abraham & Hamilton (2018, JMR) meta-analysis of partitioned pricing could not be verified once search ran out (DOI unknown), so it is not cited.
- Findings of the Krishna et al. 2002 and Li et al. 2021 meta-analyses were not retrieved (titles and DOIs verified only).
- A PLOS ONE paper reportedly failing to reproduce left-digit or perceptual-fluency effects in a large online experiment appeared only as a title fragment in search results. Unverified.
- Replication status of the credit-card premium was not checked. Chen, Monroe & Lou's (1998) results on discount vs bonus were not retrieved. The reported reversal of the bonus preference for "vice" foods was attributed inconsistently in search summaries and is unverified.
- No study was found on price presentation *inside emails* (e.g., whether to show price in a cold email at all).

---

## 3. Risk and trust (money-back guarantees and risk reversal, free trials, reversibility, credibility signals, brand familiarity, sender identity)

### Takeaway
Risk-reduction devices work when they are **specific, credible and cheap to use**:
- A meta-analysis shows return-policy leniency raises purchases, with dimension-specific effects on returns.
- A long free trial does not beat a short one (a 7-day trial beat 14 and 30 days in a large field experiment).
- Reversible decisions are easier to make but less satisfying afterwards.
- A third-party assurance seal was studied in a field setting.

For an *unfamiliar* sender, trust comes from verifiable specifics, a real and identifiable organisation and person, up-front disclosure and promotional restraint. Unfamiliar brands lean more on cues in general (scarcity effects are twice as large for them), so verifiability matters most exactly where MarketingOS's users are.

### Cited Findings
- **[MODERATE, theory]** A money-back guarantee can signal quality because transaction costs make offering one costly for low-quality sellers. — [Moorthy & Srinivasan 1995, Marketing Science](https://doi.org/10.1287/mksc.14.4.442)
- **[STRONG]** Meta-analysis of return-policy leniency (22 papers, five dimensions: money, time, effort, scope, exchange). Money leniency (e.g., full refund) increases purchases and also returns. Summaries disagree on the details: one reports that money and effort leniency raise purchases while time and exchange leniency reduce returns; the AMA write-up says time and effort leniency raise purchases less than money leniency but likely lead to fewer returns. Read the paper before quoting specifics. — [Janakiraman, Syrdal & Freling 2016, J. Retailing](https://doi.org/10.1016/j.jretai.2015.11.002); [UT Dallas news](https://news.utdallas.edu/?p=11491); [AMA summary](https://www.ama.org/2017/09/20/lenient-return-policies-can-increase-sales/)
- **[MODERATE]** In remote purchasing, return-policy leniency shapes a two-stage decision: whether to order, then whether to keep. — [Wood 2001, JMR](https://doi.org/10.1509/jmkr.38.2.157.18847)
- **[MODERATE]** 13% of abandoners cite an unsatisfactory returns policy and 19% did not trust the site with card details. — [Baymard Institute](https://baymard.com/lists/cart-abandonment-rate)
- **[STRONG, field]** SaaS field experiment with random assignment to 7-, 14- or 30-day trials: the **7-day** trial maximised acquisition, retention and profit. The evidence points to consumer learning; long inactive stretches at the end of a trial predict non-conversion. A simple short-trial-for-all policy beat several personalised policies. — [Yoganarasimhan, Barzegary & Pani, Management Science (paper PDF)](https://faculty.washington.edu/hemay/Free_Trial.pdf)
- **[MODERATE]** Customers acquired through free trials are harder to retain (digital TV service). — [Datta, Foubert & Van Heerde 2015, JMR](https://doi.org/10.1509/jmr.12.0160)
- **[STRONG, field]** Consumers anticipate subscription traps: auto-renewal deterred sign-ups and produced fewer subscribers after two years (details in Q2). — [Stanford GSB](https://www.gsb.stanford.edu/insights/auto-renew-snags-new-subscribers-its-not-good-way-keep-them)
- **[MODERATE]** People prefer decisions they can reverse and predict no loss of satisfaction, yet are less satisfied with reversible outcomes. — [Gilbert & Ebert 2002, JPSP](https://doi.org/10.1037/0022-3514.82.4.503)
- **[MODERATE]** Web credibility study with more than 2,500 participants (2,684): "design look" was the most frequently mentioned credibility cue (46.1% of comments). — [Fogg et al. 2003, DUX](https://doi.org/10.1145/997078.997097)
- **[WEAK-FOLKLORE/MODERATE]** Stanford Guidelines for Web Credibility: make claims easy to verify; show there is a real organisation behind the site; highlight expertise; show honest, trustworthy people; make it easy to get in touch; use restraint with promotional content; avoid errors. — [Stanford Persuasive Tech Lab†](https://credibility.stanford.edu/guidelines/index.html)
- **[WEAK-FOLKLORE/MODERATE]** NN/g's four credibility factors: design quality; up-front disclosure (prices, fees, terms); comprehensive, correct and current content; connection to the rest of the web. Qualitative usability research. — [Nielsen Norman Group†](https://www.nngroup.com/articles/trustworthy-design/)
- **[MODERATE]** Empirical investigation of the value of third-party assurance seals in online retailing (field data); the published research note reports a conversion benefit. Effect size not retrieved this session. — [Özpolat, Gao, Jank & Viswanathan 2013, Information Systems Research](https://doi.org/10.1287/isre.2013.0489)
- **[STRONG]** Brand familiarity as a moderator: scarcity cues raised purchase intentions about **twice as much for low-familiarity brands** (δ = 0.41) as for high-familiarity ones (δ = 0.21). — [Barton, Zlatevska & Oppewal 2022, J. Retailing](https://doi.org/10.1016/j.jretai.2022.06.003)
- **[MODERATE]** Anticipating regret and responsibility shifts choice toward the well-known, conventional option; familiarity works as a risk reducer. — [Simonson 1992, JCR](https://doi.org/10.1086/209290)
- **[MODERATE]** A "verified buyer" badge improved the odds of purchase by 15%. — [Spiegel Research Center](https://spiegel.medill.northwestern.edu/how-online-reviews-influence-sales/). Reviews from reviewers who disclose identity information were rated more helpful and were associated with sales. — [Forman, Ghose & Wiesenfeld 2008, ISR](https://doi.org/10.1287/isre.1080.0193)
- **[local code fact]** `spam_gate` is **BLOCKING**. Its vocabulary includes "money back guarantee", "risk free", "no obligation", "limited time only" and "act now", matched by plain substring on lowercased text, so the hyphenated "money-back guarantee" and "risk-free" are *not* caught. — [backend/app/marketing/gates.py, `_SPAM_TERMS` and `spam_gate`](../../backend/app/marketing/gates.py). `OfferSheet.guarantees` are kept in the source's own wording with their conditions, because "only its actual quotation licenses a guarantee". — [backend/app/knowledge/artifacts.py, `OfferSheet.ground_guarantees`](../../backend/app/knowledge/artifacts.py). The ledger has GUARANTEE and CERTIFICATION kinds and an `EvidenceContext` with conditions, temporal scope and limitations. — [backend/app/knowledge/ledger.py](../../backend/app/knowledge/ledger.py). A grep found no guarantee- or deadline-specific gate in `gates.py` besides the spam vocabulary.

### Inferences
- **Specific beats generic for risk reversal.** "If X doesn't do Y within 30 days, we refund you" is verifiable (Stanford's "make it easy to verify"; NN/g's up-front disclosure), whereas "money-back guarantee" is a label the spam gate bans. The spam gate thus accidentally pushes toward the better-supported form. But its hyphen blind spot lets the label through, and it bans words rather than requiring a licence for the concept.
- A **short trial** with clear limits is better supported than a long one. Copy should present the business's actual trial and not dress up a longer one as more generous.
- **Reversibility** ("monthly, cancel anytime") lowers the barrier to deciding, so it is legitimate to state when licensed. Its downside (lower satisfaction) is outside the copy's reach.
- **For unknown senders** (most MarketingOS users): identifiable person and role, a real company, licensed verifiable links, precise facts and no hype. These map onto existing gates (`evidence_gate`, `stock_phrase_gate`, `spam_gate`) plus a sign-off that names a real person.
- **Driver: guarantee / risk reversal**
  - Evidence: GUARANTEE entry, verbatim, with conditions (window, eligibility, claim procedure).
  - If missing: mention only licensed reversibility facts (monthly billing, data export), or the smallness of the next step. Never "risk-free" or "no risk".
  - (a) Proposed `guarantee_gate`: any refund, guarantee or "no risk" language requires a GUARANTEE entry and must reproduce its condition tokens (numbers via `evidence_gate`, words by lexical overlap with `verbatim`). Fix the spam gate's hyphen and space blind spot by normalising separators before matching.
  - (b) Writer: state the guarantee as terms, not a label, close to the ask.
  - (c) Cold reader: "If this didn't work for you, what would happen?"
  - (d) Purchase lift vs refund rate.
- **Driver: free trial**
  - Evidence: trial length, what is included, whether a card is required, what happens at the end.
  - If missing: offer a demo or reply instead.
  - (a) "trial", "no credit card" and "N days" require licensed entries (numbers are already licensed).
  - (b) Prompt: give the end-of-trial terms.
  - (c) Critic: are trial limits clear?
  - (d) Conversion and retention.
- **Driver: credibility and sender identity**
  - Evidence: real sender name and role, company facts, CERTIFICATION/AWARD entries, licensed URLs (docs, status page, public pricing).
  - If missing: rely on precision and verifiability of what *is* licensed.
  - (a) Existing gates; possible check that the sign-off carries a licensed person or role.
  - (b) Prompt: give the reader one way to verify (a licensed URL).
  - (c) Cold reader: "Who is writing, and could you check what they claim?"
  - (d) Reply and trust effects.

### Gaps
- Boulding & Kirmani (1993), on warranties signalling quality only when the firm is credible, could not be cited because the recalled DOI belonged to a different paper.
- No field experiment on guarantees or trials inside email campaigns, or in B2B, was found.
- Evidence on "person vs company" as sender is email-specific and out of scope; no verified peer-reviewed source.
- The link between brand familiarity and trust (mere exposure, Ehrenberg-Bass) was not verified this session. The effect size of the Özpolat et al. seal study was not retrieved.

---

## 4. Social proof and testimonials (credible testimonials, number of reviews and ratings, blemishing, B2B case studies and logos, quantified results, backfire)

### Takeaway
Reviews and popularity information reliably move behaviour: two meta-analyses (which disagree on volume vs valence) and randomised field experiments. Returns diminish after the first handful of reviews, and purchase likelihood dips as the average rating nears 5. Credibility rises with specificity, disclosed identity, similarity to the reader, explicit endorsement language ("I recommend"), and a mild negative placed after the positives. Social proof **backfires** when it says that the undesired behaviour is common (negative descriptive norms). In the scarcity meta-analysis, popularity-based ("demand") cues had **no effect in advertisements** and none for high-involvement products. For B2B logos and case studies there is no rigorous evidence.

### Cited Findings
- **[MODERATE; method not disclosed on page]** Spiegel Research Center: a product with five reviews had a purchase likelihood 270% greater than one with none. Displaying reviews raised conversion 190% for lower-priced and 380% for higher-priced products. Marginal benefit diminishes rapidly after the first five reviews. Purchase likelihood "typically peaks at ratings in the 4.0-4.7 range" and then falls toward 5.0. Verified-buyer badges improved the odds of purchase by 15%. **Note:** the brief's "4.2-4.5" range does **not** appear on the Spiegel page, which says 4.0-4.7. — [Spiegel Research Center, "How Online Reviews Influence Sales"](https://spiegel.medill.northwestern.edu/how-online-reviews-influence-sales/). Peer-reviewed counterpart by Spiegel-affiliated authors (findings not retrieved): Maslowska, Malthouse & Bernritter 2017, "Too good to be true: the role of online reviews' features in probability to buy", International Journal of Advertising 36(1). — [Goldsmiths research record](https://research.gold.ac.uk/view/creator/Maslowska=3AEwa=3A=3A.html)
- **[STRONG]** eWOM elasticity meta-analysis: the sales elasticity of valence (0.417) exceeds that of volume (0.236). — [You, Vadakkepatt & Joshi 2015, J. Marketing](https://doi.org/10.1509/jm.14.0169). **Conflict:** another meta-analysis finds eWOM *volume* more strongly associated with sales than valence, moderated by platform, product and metric. — [Babić Rosario et al. 2016, JMR](https://doi.org/10.1509/jmr.14.0380)
- **[MODERATE]** Popularity bias: people chose products with more reviews even when the statistics implied lower quality. — [Powell, Yu, DeWolf & Holyoak 2017, Psychological Science](https://doi.org/10.1177/0956797617711291). Average user ratings correspond poorly with objective quality scores, yet consumers rely on them heavily. — [de Langhe, Fernbach & Lichtenstein 2016, JCR](https://doi.org/10.1093/jcr/ucv047)
- **[MODERATE]** Negative reviews raised sales of books by relatively unknown authors (about +45%) and lowered them for established authors (about −15%), via awareness. — [Berger, Sorensen & Rasmussen 2010, Marketing Science](https://doi.org/10.1287/mksc.1090.0557)
- **[MODERATE; no independent replication found]** Blemishing effect: a small dose of negative information *after* positive information raises evaluations, but only under low-effort processing and only if the negative is mild (four studies, lab and field). — [Ein-Gar, Shiv & Tormala 2012, JCR](https://ideas.repec.org/a/oup/jconrs/doi10.1086-660807.html); [Stanford GSB summary](https://gsb.stanford.edu/insights/positive-effect-negative-information)
- **[MODERATE]** Readers assume ambiguous reviewers are similar to themselves, and similar reviewers persuade more. — [Naylor, Lamberton & Norton 2011, JMR](https://doi.org/10.1509/jmkr.48.3.617). Explicit endorsements ("I recommend it") persuade more than implicit ones ("I liked it"). — [Packard & Berger 2017, JMR](https://doi.org/10.1509/jmr.15.0248). Disclosing reviewer identity is associated with helpfulness and sales. — [Forman et al. 2008](https://doi.org/10.1287/isre.1080.0193)
- **[STRONG, field]** In a randomised natural field experiment at a restaurant chain, displaying the top-5 dishes raised demand for those dishes by roughly 13-20%. — [Cai, Chen & Fang 2009, AER](https://doi.org/10.1257/aer.99.3.864). On a wedding-vendor website, popularity information disproportionately helped *narrow-appeal* vendors. — [Tucker & Zhang 2011, Management Science](https://doi.org/10.1287/mnsc.1110.1312)
- **[STRONG]** Scarcity meta-analysis, effects of demand-based (popularity) scarcity on purchase intentions:
  - utilitarian products: δ = 0.41;
  - high-involvement products: δ = 0.08 (not significant);
  - advertisements: δ = −0.03 (not significant, k = 5);
  - scarcity overall raised *perceived popularity* most of all (δ = 0.71). — [Barton et al. 2022](https://doi.org/10.1016/j.jretai.2022.06.003)
- **[MODERATE, field]** Backfire. At Petrified Forest, a sign stating that many past visitors stole wood (a negative descriptive norm) produced 7.92% theft, vs 1.67% for an injunctive sign. — [Cialdini et al. 2006, Social Influence](https://doi.org/10.1080/15534510500181459); [Cialdini 2003, Current Directions](https://doi.org/10.1111/1467-8721.01242). Descriptive-norm feedback caused a "boomerang" among below-average energy users, which an added injunctive cue (approval) prevented. — [Schultz et al. 2007, Psychological Science](https://doi.org/10.1111/j.1467-9280.2007.01917.x)
- **[local code fact]** MarketingOS proof types: testimonial ("somebody said it worked, in their own words"), customer ("a named company that uses it"), outcome ("a number somebody other than the company attached to it"), review, listing, mention. — [backend/app/market/proof.py](../../backend/app/market/proof.py). The audience prompt already states: "One testimonial establishes that customer's experience, not prevalence across a segment." — [backend/prompts/knowledge_audience.md](../../backend/prompts/knowledge_audience.md). The judge bench treats "the testimonial kept and hollowed out" as a hard mutation. — [CLAUDE.md](../../CLAUDE.md)

### Inferences
- **What a credible testimonial carries** (combining the findings above): a concrete experience or outcome in the customer's own words; disclosed identity (name, role, company); similarity to the reader's segment; an explicit recommendation; optionally a mild caveat *after* the praise. The last two can only be used if they are in the quotation; copy cannot add them.
- **"Hollowed-out" testimonials** lose exactly these elements: specificity, identity, outcome. That explains why the mutation is damaging, and suggests its deterministic half (identity present, quote verbatim) can be a code check.
- **Counts and ratings** are numbers, so they are licensed by `evidence_gate`. They also need recency (`temporal_scope`) and the platform. A perfect rating is not necessarily an asset; copy should not "clean up" a 4.6 into "five-star".
- **Negative-norm sentences** ("most teams fail to…", "70% of companies still don't…") are the copy form of the Petrified Forest sign. They can normalise inaction and are a classic sales-email opener.
- **B2B logos and case studies:** in the absence of rigorous research, the nearest evidence (identity disclosure, similarity, precise outcomes) suggests that a *named, similar customer with a specific outcome* beats a list of logos.
- **Driver: testimonial / customer proof**
  - Evidence: TESTIMONIAL entries verbatim, with attribution and permission; CUSTOMER names; OUTCOME numbers with source and date.
  - If missing: offer verifiability instead of popularity (a licensed link to docs or a sample output, a named founder or sender, the mechanism explained). Never "customers love us" or "trusted by teams".
  - (a) Quotation licensing already exists. Additional check: when a quotation is used and the entry has attribution, the attribution must appear. Proof that arrives after the ask is already a judge mutation; ordering could be checked deterministically.
  - (b) Strategist: pick proof from the reader's segment; one proof per need (already in prompts: "Do not … add testimonials without a related need").
  - (c) Cold reader: "Who said this, and are they like you?"
  - (d) Lift from proof vs no proof.
- **Driver: numbers of users, ratings, reviews**
  - Evidence: count or rating plus platform plus date, from REVIEW or METRIC entries.
  - If missing: omit.
  - (a) `evidence_gate`, plus a staleness check against `temporal_scope`.
  - (c) Critic: does the claim read as too good to be true?
- **Driver: negative social proof**
  - (a) Non-blocking lexical *warning* (judgment-adjacent): "most / many / the majority of / X% of [people, teams, companies] [don't, fail, still, struggle]".
  - (b) Writer: do not open with the prevalence of the problem; open with what this reader can do.
  - (c) Critic criterion: "Does any sentence tell the reader that most people like them don't act?"
  - (d) Effect on response.

### Gaps
- No peer-reviewed evidence was found on customer-logo walls, B2B case-study formats or before/after testimonials. Vendor surveys exist but were not retrieved.
- The Maslowska et al. (2017) findings, and therefore a peer-reviewed source for any "4.2-4.5" peak, were not retrieved. No independent replication of the blemishing effect was found. The hotel-towel norm study's replication controversy was not verified this session.

---

## 5. Urgency and scarcity (real vs fake deadlines, limited quantity vs time, procrastination, reaction to detected manipulation, trust cost)

### Takeaway
Scarcity cues raise stated purchase intentions (meta-analysis δ ≈ 0.31) and perceived quality and value. But the effect depends heavily on the product: for **utilitarian** products, time- and supply-based cues had **zero** effect (popularity cues worked), and the evidence is overwhelmingly hypothetical lab scenarios. Real, short deadlines reduce procrastination. Missing a deal depresses acceptance of a later, worse offer (inaction inertia, replicated mainly for *large* differences). Manipulative urgency "works" when mild, but aggressive versions trigger backlash, and consumers who anticipate traps avoid them. Direct evidence on trust loss *after detection* of fake scarcity is thin.

### Cited Findings
- **[STRONG]** Barton, Zlatevska & Oppewal 2022 (131 studies, 416 effect sizes) — [J. Retailing](https://doi.org/10.1016/j.jretai.2022.06.003); [record](https://ideas.repec.org/a/eee/jouret/v98y2022i4p741-758.html); [PDF](https://pure.bond.edu.au/ws/portalfiles/portal/182976505/Scarcity_tactics_in_marketing.pdf):
  - Overall effects: purchase intentions δ = 0.31, willingness to pay 0.47, perceived quality 0.47, value 0.37, exclusivity 0.52, popularity 0.71, attitudes 0.15.
  - By source, on purchase intentions: supply-based 0.39 (k = 64), time-based 0.34 (k = 27), demand-based 0.28 (k = 90). The differences are **not** significant (Q(2) = 1.76, p = .41).
  - Utilitarian products: demand-based 0.41, supply-based **−0.02**, time-based **0.02** (k = 6).
  - Hedonic products: supply-based 0.55, time-based 0.32, demand-based 0.17.
  - High-involvement products: time-based 0.63, supply-based 0.50, demand-based 0.08 (not significant).
  - In advertisements: supply-based 0.69, time-based 0.26, demand-based −0.03 (not significant).
  - Low- vs high-familiarity brands: 0.41 vs 0.21.
  - Methodological moderators: 178 of 193 effect sizes used hypothetical manipulations and only 15 actual ones (0.35 vs 0.31, no significant difference); 152 of 190 effect sizes came from student samples. Within-subject designs inflate effects (0.48 vs 0.11 for mixed designs).
  - An earlier quantitative review (Lynn 1991) reported an effect on perceived value of r = 0.12.
  - A second meta-analysis exists. — [Ladeira et al. 2023, Psychology & Marketing](https://radar.brookes.ac.uk/radar/file/609e47cf-0367-4af7-82ac-9ab7154e2a2c/1/Psychology%20and%20Marketing%20-%202023%20-%20Ladeira.pdf)
- **[MODERATE, field]** Shorter redemption deadlines on gift certificates led to *more* redemption than longer ones; people predicted the opposite, because long deadlines invite procrastination. — [Shu & Gneezy 2010, JMR](https://doi.org/10.1509/jmkr.47.5.933)
- **[STRONG; replicated with conditions]** Inaction inertia. Original finding — [Tykocinski, Pittman & Tuttle 1995](https://doi.org/10.1037/0022-3514.68.5.793). A preregistered replication-extension in Brazil (N = 436) found the effect in 6 of 12 comparisons across the four original scenarios, with money-involving scenarios behaving differently. It also reports that the only earlier direct replication (Chen et al. 2021) found the effect only when the missed offer was *much* better. — [Borborema et al. 2026, Meta-Psychology](https://doi.org/10.15626/MP.2023.3960)
- **[MODERATE]** Dark-pattern experiments (US adults; acceptance of a dubious identity-theft protection plan): 11% control, 26% mild dark patterns, 42% aggressive. Aggressive patterns produced strong backlash; mild ones did not. Less-educated participants were more susceptible to mild patterns. — [Luguri & Strahilevitz 2021, J. Legal Analysis](https://academic.oup.com/jla/article/13/1/43/6180579); [rates in Strahilevitz slides, CPPA](https://cppa.ca.gov/meetings/materials/20220329_30_day_1_item_2c_strahilevitz.pdf)
- **[MODERATE, large dataset]** A crawl of about 11,000 shopping sites catalogued 1,818 dark-pattern instances (on 1,254 sites), including countdown timers and limited-time or low-stock/high-demand messages, some of them demonstrably deceptive. Prevalence, not effect. — [Mathur et al. 2019, PACM HCI (CSCW), "Dark Patterns at Scale"](https://doi.org/10.1145/3359183)
- **[STRONG, field]** Consumers anticipate traps and avoid them (auto-renewal deterred take-up and lost subscribers by two years; see Q2). — [Stanford GSB](https://www.gsb.stanford.edu/insights/auto-renew-snags-new-subscribers-its-not-good-way-keep-them)
- **[WEAK]** In a small experiment (N = 180), fear and scarcity ads raised purchase intention but lowered perceived ethicality and trust (a "persuasion paradox"). — [SynapseSocial record](https://www.synapsesocial.com/papers/6a08aa44280cd4e998e8d71e)
- **[local code fact]** MarketingOS already forbids invented urgency in prompts:
  - critic.md: "do not request invented urgency" — [backend/prompts/critic.md](../../backend/prompts/critic.md)
  - writer.md: "Do not invent a problem, deadline or staffing story" — [backend/prompts/writer.md](../../backend/prompts/writer.md)
  - reader.md: "do not invent a schedule or a deadline" — [backend/prompts/reader.md](../../backend/prompts/reader.md)
  - intent.py, for recovery emails — [backend/app/marketing/intent.py](../../backend/app/marketing/intent.py)
  - strategist.md lists "proof, then the objection, then the deadline" as one possible shape — [backend/prompts/strategist.md](../../backend/prompts/strategist.md)

  No deterministic urgency check exists apart from the spam vocabulary ("limited time only", "act now", "urgent action required").

### Inferences
- **Honest urgency has three licensed parts:** a real deadline or limit, its reason, and what changes afterwards (price returns to X, the cohort closes). Each must be in the material (`EvidenceContext.temporal_scope`).
- **For most MarketingOS offers (utilitarian B2B), the meta-analysis predicts little from time or supply cues.** The more useful "why now" is the reader's own documented trigger (audience research already models triggers). Inventing one is already forbidden in prompts.
- **Fake deadlines carry costs beyond the moment:**
  - backlash from aggressive pressure (Luguri);
  - avoidance by sophisticated consumers (Miller et al.);
  - by inference from inaction inertia, a missed "deadline" followed by the same or a worse offer from the same sender is less likely to be taken up, and a deadline that gets re-offered teaches the list to ignore deadlines (the latter is an inference, not tested).
- **A sequence that runs a real deadline** should not follow it with a much worse offer (inaction inertia is strongest for large differences). Shorter real windows beat long ones (Shu & Gneezy).
- **Driver: deadline / limited time**
  - Evidence: date and time with timezone, reason, post-deadline terms.
  - If missing: no time pressure at all. Rely on making the next step small (Q1 and Q6).
  - (a) Proposed `urgency_gate` (lexical, BLOCKING when unlicensed): "last chance", "ends", "expires", "closing", "deadline", "only until", "today only", "this week only", "before it's gone", "hurry", "don't miss". Each requires an Evidence entry with `temporal_scope`. Dates and numbers are already covered by `evidence_gate`. Normalise hyphens and spaces as for the spam terms.
  - (b) Strategist: use a deadline only when it is licensed, and place it after proof (existing shape).
  - (c) Cold reader: "Is there a reason to act now that you believe? Did anything feel like pressure?" Critic: urgency without a reason counts as a copy defect.
  - (d) Optimal window length; unsubscribe and complaint cost of urgency.
- **Driver: limited quantity / capacity**
  - Evidence: a real cap (seats, cohort size, inventory) and its date.
  - If missing: omit.
  - (a) The number goes through `evidence_gate`; words like "spots", "seats left", "almost full" need a licensed cap.
  - (c) Critic: is the cap plausible and explained?
  - (d) Effect on response.
- **Candidate judge-bench mutations** (billed but needing no send data, for (c)): "an invented deadline added to a control email"; "a negative-norm opener inserted". The first should be caught by the proposed gate and works as a gate test. The second is judge territory. Both measure whether the cold reader penalises pressure.

### Gaps
- No peer-reviewed study was found that isolates the trust loss after consumers *detect* fake scarcity (search ended). An attribution to "Omar et al. 2021; Wang et al. 2025" seen in a skills file is unverified.
- No disclosed-method field experiment on countdown timers or "N people viewing" messages was found. Booking.com's own experiment results were not located.
- The Barton meta-analysis is mostly hypothetical, student-sample purchase intentions, so field purchase effects are much less documented.
- A "same company vs different company" moderator of inaction inertia appeared in a search summary and was not verified.

---

## 6. Objections and hesitation (main reasons buyers don't act; pre-empting objections; FAQs; "who this is not for")

### Takeaway
The documented reasons people do not complete a purchase are unexpected costs, distrust, effort (account creation, long processes), slow delivery and returns policy (Baymard, e-commerce). In B2B, practitioner data point to indecision. Pre-empting an objection works when the copy **raises it and refutes it**: refutational two-sided messages beat one-sided ones, while non-refutational two-sided messages are *less* persuasive. Choice overload is **not** a general effect (meta-analytic mean near zero); it appears under complexity and preference uncertainty. No rigorous evidence was found on FAQs or on "who this is not for" copy.

### Cited Findings
- **[MODERATE; large practitioner survey, sample size not shown on page]** Reasons for abandoning checkout, among those not "just browsing": extra costs too high 40%; delivery too slow 20%; did not trust the site with card information 19%; account creation required 18%; checkout too long or complicated 17%; website errors 17%; returns policy 13%; could not see the total cost up front 12%; card declined 10%; not enough payment methods 9%. 42% of US online shoppers abandoned because they were "just browsing". The documented average abandonment rate is 70.22% across 50 studies (2006-2025). — [Baymard Institute](https://baymard.com/lists/cart-abandonment-rate)
- **[WEAK-FOLKLORE]** B2B: indecision ("no decision") is the main loss reason, and the remedy is a recommendation, limited exploration and risk removal. — [Dixon interview](https://customerthink.com/the-problem-of-customer-indecision-and-how-to-get-over-it-interview-with-matt-dixon/)
- **[MODERATE]** Switching costs come in three types: procedural (economic risk, evaluation, learning, setup), financial (lost benefits, monetary loss) and relational (personal and brand relationships). — [Burnham, Frels & Mahajan 2003, JAMS](https://doi.org/10.1177/0092070302250897)
- **[STRONG]** Meta-analysis: two-sided messages that *refute* the opposing arguments are more persuasive than one-sided messages; two-sided messages that merely *acknowledge* them are less persuasive. — [O'Keefe 1999, Communication Yearbook / Annals of the ICA](https://doi.org/10.1080/23808985.1999.11678963). In advertising, two-sidedness can raise credibility, depending on the amount and importance of the negative information. — [Eisend 2006, IJRM, "Two-sided advertising: A meta-analysis"](https://doi.org/10.1016/j.ijresmar.2005.11.001)
- **[STRONG]** Choice overload: the meta-analytic mean effect is about zero, with high heterogeneity. — [Scheibehenne, Greifeneder & Todd 2010, JCR](https://doi.org/10.1086/651235). Its moderators are choice-set complexity, decision-task difficulty, preference uncertainty and decision goal. — [Chernev, Böckenholt & Goodman 2015, J. Consumer Psychology](https://doi.org/10.1016/j.jcps.2014.08.002)
- **[MODERATE]** Choice conflict leads to deferral. — [Tversky & Shafir 1992](https://doi.org/10.1111/j.1467-9280.1992.tb00047.x); [Dhar 1997](https://doi.org/10.1086/209506)
- **[local code fact]** Prompts already say: "Do not turn the email into a FAQ or add testimonials without a related need." — [backend/prompts/critic.md](../../backend/prompts/critic.md); [backend/prompts/writer.md](../../backend/prompts/writer.md). `capability_scope_gate` blocks claims beyond the documented scope. — [backend/app/marketing/gates.py](../../backend/app/marketing/gates.py)

### Inferences
- **One objection per email, refuted with evidence**, matches the meta-analysis: raise only an objection the email can answer from licensed facts. Naming an objection and leaving it unanswered is the non-refutational case that lowers persuasion.
- **Map Baymard's checkout reasons to email objections:**
  - cost surprise → state the total and mandatory components (Q2);
  - trust → verifiability (Q3);
  - effort → describe the next step concretely ("reply with your URL"); state setup time only if documented;
  - fit → segment-specific proof (Q4);
  - timing → a licensed "why now" or none (Q5).
- **"Who this is not for"** has no direct evidence. Indirect support comes from the credibility benefits of two-sided messages and the blemishing effect. But disqualifiers are *claims*: they must come from the business's documented scope (e.g., "not built for teams over 50 seats" only if the material says so), or they risk misrepresenting it. `capability_scope_gate` is the natural place.
- **FAQs** belong on a page, not in the email. Linking a licensed FAQ URL is the email-level equivalent.
- **Driver: objection pre-emption**
  - Evidence: documented answers (onboarding steps, integrations, migration support, security posture, terms).
  - If missing: do not raise the objection. Make the ask small instead.
  - (a) Possibly a lexical detector of objection markers ("you might be wondering", "worried that", "but what about") that requires a licensed fact in the same or the next sentence (only a heuristic).
  - (b) Strategist: name, per brief, the single most likely objection for this reader and the licensed fact that answers it (the existing brief shape already includes an objection slot).
  - (c) Cold reader: "What would stop you from replying?" Critic: an objection raised and not answered is a defect.
  - (d) Which objections actually block replies.
- **Driver: disqualifying copy**
  - Evidence: documented exclusions or ideal-customer statements.
  - If missing: none.
  - (a) `capability_scope_gate`.
  - (c) Does the disqualifier read as honest or as a gimmick?
  - (d) Lead quality.

### Gaps
- No rigorous study was found on FAQ sections or "who this is not for" copy and conversion.
- Baymard's data concern e-commerce checkout, not email replies. No disclosed-method B2B dataset on objection prevalence was verified.

---

## 7. Free value first and reciprocity (lead magnets, samples, free audits): does it raise conversion?

### Takeaway
Unconditional gifts reliably increase reciprocation in field settings:
- charity mail: +17% donation frequency with a small gift, +75% with a large one;
- retail (2026 JAMS paper): spending up to +31.7%, with gift value barely mattering.

"Free" also has outsized pull (zero-price effect). But **more free is not better**: a 7-day trial beat 14- and 30-day trials, and free-trial customers retain worse. There is **no** peer-reviewed evidence on lead magnets or free audits as such. Gated "free" offers are conditional exchanges, not the unconditional gifts the reciprocity evidence covers.

### Cited Findings
- **[STRONG, field]** Charity mailing with roughly 10,000 solicitation letters: the relative frequency of donations rose 17% with a small gift and 75% with a large gift. — [Falk 2007, Econometrica, "Gift Exchange in the Field"](https://doi.org/10.1111/j.1468-0262.2007.00800.x)
- **[MODERATE+; single paper with two field experiments and five lab studies]** Unconditional gifts (e.g., a small Lego set or coffee sample at the store entrance, no purchase required) raised total transactional spending by up to 31.66%. Low-value gifts (about $0.50) were nearly as effective as more expensive ones, and effects held for new and existing customers. Gratitude drove loyalty while felt obligation drove immediate spending. — [Fombelle et al. 2026, JAMS](https://doi.org/10.1007/s11747-025-01129-x); [BI Business Review summary](https://www.bi.no/en/research/business-review/articles/2026/03/giving-without-asking/)
- **[WEAK]** An older pharmacy study of gifts given on entry (200 subjects). — [Friedman & Herskovitz 1990](https://www.emeraldinsight.com/doi/abs/10.1108/19355181199000006)
- **[MODERATE, field]** In natural field experiments, salespeople reciprocated compliments and tips given in advance by giving more product weight, i.e., reciprocity operates in market exchanges. — [Experimental Economics 2017](https://link.springer.com/article/10.1007/s10683-017-9536-1)
- **[MODERATE]** Zero-price pull. — [Shampanier et al. 2007](https://doi.org/10.1287/mksc.1060.0254). **[STRONG, field]** Short (7-day) trials beat longer ones. — [Yoganarasimhan et al.](https://faculty.washington.edu/hemay/Free_Trial.pdf). **[MODERATE]** Free-trial customers are harder to retain. — [Datta et al. 2015](https://doi.org/10.1509/jmr.12.0160)
- A registered trial on "the power of (un)conditional gifts" exists (results not retrieved). — [AEA RCT Registry](https://www.socialscienceregistry.org/trials/2908)

### Inferences
- **In email, the closest analog to an unconditional gift is useful content delivered in the email itself.** That means a documented insight, template or example from the business's material, not a link that asks for something in return. A free audit or call is a *conditional exchange* (the reader gives time and data). The reciprocity evidence does not cover it; it is better thought of as a low-cost next step (Q1 and Q6).
- **Gift value barely matters** (Fombelle). So a small, genuinely useful, *real* item can suffice, but it must exist in the material: an invented "free checklist" is a fabricated offer.
- Lowering the threshold (free, long trials) again trades conversion for customer quality. MarketingOS cannot measure that without send data.
- **Driver: free value first**
  - Evidence: the free asset (guide, template, sample output, audit) exists in the material or `OfferSheet.free_entry`, with its terms.
  - If missing: give value by explanation (a mechanism or insight from licensed facts) inside the email. Never promise a resource.
  - (a) A resource noun ("guide", "checklist", "template", "audit", "sample") combined with "free" or "get" should require a licensed URL or `free_entry`. URLs are already licensed.
  - (b) Strategist: for cold readers, consider an email whose payload *is* the value (no ask beyond a reply), within the existing one-ask rule.
  - (c) Cold reader: "Did you get something useful even if you never reply?"
  - (d) Reply and conversion lift from value-first emails; downstream quality.

### Gaps
- No peer-reviewed evidence was found on lead magnets, gated content or free audits and B2B conversion.
- The devaluation of free gifts-with-purchase (Raghubir 2004; Kamins, Folkes & Fedorikhin 2009) is relevant but was not verified.
- The 2026 retail study's per-experiment sample sizes and its long-run loyalty effect sizes were not on the summary page.

---

## 8. Emotions in purchase decisions (anticipated regret, FOMO, relief, pride, identity and status vs rational justification)

### Takeaway
Feelings measurably drive evaluations: an empirical generalisation across more than 1,000 TV commercials. Anticipated regret pushes people toward safe, familiar choices and underlies inaction inertia. People need *reasons* to justify hedonic purchases (justification, effort, a charity tie-in). Identity appeals can **backfire** when they dictate who the reader is. FOMO is largely conceptual or correlational in the marketing literature, and no direct evidence on "relief" appeals was found. Gain vs loss framing differences are negligible on average.

### Cited Findings
- **[STRONG; empirical generalisation]** Ad-evoked feelings influenced brand evaluations across consumer responses to more than 1,000 TV commercials. — [Pham, Geuens & De Pelsmacker 2013, IJRM](https://doi.org/10.1016/j.ijresmar.2013.04.004)
- **[MODERATE]** Anticipating regret and responsibility shifts choice toward the well-known, conventional option. — [Simonson 1992, JCR](https://doi.org/10.1086/209290). Regret avoidance is one proposed mechanism of inaction inertia. — [Borborema et al. 2026](https://doi.org/10.15626/MP.2023.3960)
- **[WEAK-FOLKLORE]** FOMO marketing appeals: a conceptual model, not an experiment. — [Hodkinson 2016, J. Marketing Communications](https://doi.org/10.1080/13527266.2016.1234504). The scarcity meta-analysis interprets the large supply-scarcity effect for *experiences* (δ = 0.60 vs 0.21 for demand-based) as fear of missing out. — [Barton et al. 2022](https://doi.org/10.1016/j.jretai.2022.06.003)
- **[MODERATE]** Identity marketing backfires when it threatens consumers' agency in expressing their identity. — [Bhattacharjee, Berger & Menon 2014, JCR](https://doi.org/10.1086/676125). People diverge from others in identity-signalling product domains. — [Berger & Heath 2007, JCR](https://doi.org/10.1086/519142)
- **[MODERATE]** Justification: hedonic options do better when evaluated alone, utilitarian ones when choices are compared and must be justified. — [Okada 2005, JMR](https://doi.org/10.1509/jmkr.42.1.43.56889). Effort licenses indulgence. — [Kivetz & Simonson 2002, JMR](https://doi.org/10.1509/jmkr.39.2.155.19084). Charity incentives work better for frivolous than for practical products (guilt relief). — [Strahilevitz & Myers 1998, JCR](https://doi.org/10.1086/209519)
- **[STRONG]** Loss framing is no better than gain framing on average (health domain). — [O'Keefe & Jensen 2007](https://doi.org/10.1080/10810730701615198); [2009](https://doi.org/10.1111/j.1460-2466.2009.01417.x)

### Inferences
- **Emotional claims about the reader are inferences about a person the system has never met.** "You're probably frustrated…" is unlicensed in spirit even though it carries no number. Safer sources of emotion: (i) documented buyer language from audience research (complaints, triggers, already modelled in `knowledge_audience.md`); (ii) the felt consequence of a licensed fact; (iii) relief as the *absence* of a documented pain once the mechanism is explained.
- **Regret cues are honest only when the consequence is real** (a real deadline or price change). Otherwise they are fake urgency (Q5).
- **Identity:** offer an identity-consistent choice ("teams that review every claim before sending…") rather than a prescription ("as a serious marketer you must…"), which the agency finding predicts will backfire.
- **Rational justification** remains necessary even for emotional appeals (Okada; Kivetz & Simonson), which is consistent with MarketingOS's insistence on mechanism and licensed proof.
- **Driver: emotional framing**
  - Evidence: documented customer phrases (TESTIMONIAL, audience research), documented stakes.
  - If missing: describe the situation concretely and let the reader supply the feeling.
  - (a) Possibly a non-blocking flag for second-person emotion attributions ("you're frustrated", "you're tired of", "you're worried") without a licensed buyer phrase.
  - (b) Writer: no identity prescriptions; one justification fact per emotional claim.
  - (c) Cold reader: "Did the email tell you how you feel? Was it right?"
  - (d) Response to emotional vs factual openers.

### Gaps
- No verified source on "relief" appeals.
- Binet & Field (IPA databank) on emotional vs rational campaigns: self-selected award entries, not verified this session.
- No verified experimental FOMO study (a small N = 161 experiment appeared in search results but its source could not be pinned down).
- Bryan et al.'s "be a voter" identity-noun effect and its large failed field replication (Gerber et al. 2016) are relevant but were not verified this session.
- Whether an LLM cold reader responds to emotional, scarcity or price-format cues the way humans do is unknown. That is a validity question for every (c) criterion above, and no evidence was found.
