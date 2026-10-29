# Pièges de l'email marketing et de prospection : délivrabilité, obligations légales, dark patterns, accessibilité, sur-sollicitation (état au 29 octobre 2026)

> **How to read these notes.** **Labels:** LEGAL = legal requirement (the official text is cited; none of this is legal advice) · PROVIDER = rule that mailbox providers enforce · BEST PRACTICE = recommended by providers or experts, not enforced as such · MYTH = folklore with no support in provider documentation or expert consensus.
> **MarketingOS route:** [A] = deterministic code check on the subject, preheader, body or rendered HTML · [B] = writer-prompt instruction · [C] = critic or cold-reader criterion, which never blocks · [INFRA] = sending infrastructure or list management. [INFRA] items are outside the copy; MarketingOS can only warn the user about them.
> **Δ** = new, changed or newly applicable in 2025–2026.
> The consolidated checklist is in section 8, under Inferences, in the "Cross-cutting synthesis" sub-heading. It covers hard blocks, soft risks, infrastructure warnings and myths to retire.
> The shared web-search budget ran out near the end of the session. Anything that could not be verified is listed under Gaps, not under findings. Local code observations cite repository paths.

## 1. Mailbox-provider requirements (Gmail, Yahoo, Microsoft; SPF/DKIM/DMARC; RFC 8058; complaint thresholds; Promotions tab; BIMI; what changed in 2025–2026)

### Takeaway
Gmail and Yahoo have required authenticated mail from bulk senders since February 2024, and Microsoft has done so for Outlook.com since 5 May 2025. Authenticated means SPF and DKIM, DMARC at p=none or stricter, and a From: domain aligned with one of them. Gmail and Yahoo also require RFC 8058 one-click unsubscribe, a visible unsubscribe link in the body, and a user-reported spam rate below 0.3% (target below 0.1%). What changed in 2025–2026 is enforcement, not the rules. Gmail moved to temporary and permanent rejections in November 2025, and Microsoft rejects non-compliant mail with 550 5.7.515. Almost all of this is sending infrastructure. The parts that touch the copy are four:
- a visible unsubscribe link;
- an honest From: header and display name;
- no hidden content;
- no promotional content inside transactional mail.

### Cited Findings

**Gmail — PROVIDER**
- **All senders to personal Gmail accounts (since 1 February 2024):** SPF or DKIM; valid forward and reverse DNS (PTR); TLS; a user-reported spam rate in Postmaster Tools below 0.3%; RFC 5322 formatting; no impersonation of Gmail From: headers. The guidelines warn that "Gmail will begin using a DMARC quarantine enforcement policy" on its own domain — [Google, Email sender guidelines](https://support.google.com/a/answer/81126)
- **Senders of 5,000+ messages a day, in addition:** SPF *and* DKIM; DMARC, whose policy "can be set to none"; a From: domain aligned with the SPF or DKIM domain. Marketing and subscribed messages must support one-click unsubscribe and include "a clearly visible unsubscribe link in the message body" — [Google, Email sender guidelines](https://support.google.com/a/answer/81126)
- **Definition of a bulk sender:** "close to 5,000 messages or more to personal Gmail accounts within a 24-hour period". All mail from the same primary domain counts together, subdomains included. The status is permanent: "Bulk sender status doesn't have an expiration date" — [Google, sender guidelines FAQ](https://support.google.com/a/answer/14229414)
- **Spam-rate thresholds:** "Keep spam rates reported in Postmaster Tools below 0.10% and avoid ever reaching a spam rate of 0.30% or higher" — [Google, Email sender guidelines](https://support.google.com/a/answer/81126). The rate is calculated daily. Since June 2024, a bulk sender above 0.3% is ineligible for mitigation, and becomes eligible again only after 7 consecutive days below 0.3% — [Google FAQ](https://support.google.com/a/answer/14229414)
- **One-click unsubscribe headers:** two headers are required: `List-Unsubscribe-Post: List-Unsubscribe=One-Click`, and `List-Unsubscribe` with an HTTPS URL. A mailto link or a link to a web page does not satisfy the requirement on its own. Transactional messages such as password resets and reservation confirmations are excluded. Senders with existing unsubscribe links had until 1 June 2024 to comply — [Google FAQ](https://support.google.com/a/answer/14229414)
- **Unsubscribe link in the body:** it does not have to be one-click and may lead to a preference page — [Google FAQ](https://support.google.com/a/answer/14229414)
- **Processing time:** the FAQ recommends honouring unsubscribes "within 48 hours". Its requirements table lists failure to do so as an issue that leaves "Delivery support or mitigations unavailable". A missing one-click header does not by itself cause automatic rejection, but it makes spam reports more likely and removes mitigation eligibility — [Google FAQ](https://support.google.com/a/answer/14229414)
- **Δ Enforcement since November 2025:** "Starting November 2025, Gmail is ramping up its enforcement on non-compliant traffic". Non-compliant messages "will experience disruptions, including temporary and permanent rejections". Temporary failures carry 4.7.x codes and permanent ones 5.7.x codes. New domains face an "accelerated timetable" — [Google FAQ](https://support.google.com/a/answer/14229414); corroborated by [Spam Resource, Nov 2025](https://www.spamresource.com/2025/11/google-warns-sender-requirements.html) and [Red Sift](https://redsift.com/blog/gmails-enforcement-ramps-up-what-bulk-senders-need-to-know)
- **Δ Compliance dashboard:** Postmaster Tools has a new "Compliance status dashboard" at postmaster.google.com/v2/sender_compliance — [Google FAQ](https://support.google.com/a/answer/14229414)
- **Content and format rules in the same guidelines:**
  - "Don't use HTML and CSS to hide content in your messages."
  - "Don't mix different types of content in the same message"; the example given is promotions inside sales receipts.
  - "Web links in the message body should be visible and easy to understand."
  - Don't impersonate other domains or senders.
  - Put only one address in the From: header, and use the same From: address for messages of the same category.
  - Display names should identify the sender. They should not contain the subject, message content, or emojis that imitate graphics.
  - Source: [Google, Email sender guidelines](https://support.google.com/a/answer/81126)

**Yahoo — PROVIDER (enforcement from February 2024, "gradually rolled out" over the first half of 2024, and "subject to change")**
- **All senders:** SPF or DKIM; a spam rate "below 0.3%"; valid forward and reverse DNS; compliance with RFC 5321 and 5322 — [Yahoo Sender Hub, best practices](https://senders.yahooinc.com/best-practices/)
- **Bulk senders:**
  - SPF and DKIM.
  - DMARC at p=none or stricter that passes. Relaxed alignment of the From: domain with SPF or DKIM is acceptable.
  - A one-click list-unsubscribe header for marketing and subscribed mail. The RFC 8058 POST method is "highly recommended"; mailto is acceptable.
  - A visible unsubscribe link in the body.
  - Unsubscribes honoured "within 2 days".
  - Spam rate below 0.3%, which Yahoo computes on mail delivered to the inbox.
  - Source: [Yahoo Sender Hub](https://senders.yahooinc.com/best-practices/)
- **Practices Yahoo asks for:**
  - Send only to users who asked for the mail, and honour the frequency they signed up for.
  - Don't buy lists or use pre-checked opt-in boxes.
  - Use confirmed opt-in.
  - Separate marketing mail from transactional mail by IP and DKIM domain.
  - Join the Complaint Feedback Loop.
  - Use DKIM keys of at least 1024 bits, and ARC if you forward mail.
  - Source: [Yahoo Sender Hub](https://senders.yahooinc.com/best-practices/)
- **Content:** Yahoo prohibits "deceptive subject lines" and "false or misleading header information". It publishes no guidance on URL shorteners, images, attachments or hidden text — [Yahoo Sender Hub](https://senders.yahooinc.com/best-practices/)

**Microsoft Outlook.com — PROVIDER, Δ 2025**
- **Announcement and scope:** announced on 2 April 2025 and enforced from 5 May 2025, for senders of more than 5,000 messages a day to Outlook.com, Hotmail.com and Live.com — [Mailgun](https://www.mailgun.com/blog/deliverability/microsoft-sender-requirements/); [Microsoft Tech Community announcement](https://techcommunity.microsoft.com/blog/outlook/strengthening-email-ecosystem-outlook%E2%80%99s-new-requirements-for-high%E2%80%90volume-senders/4399730)
- **Requirements:** "Domains sending more than 5,000 emails per day to Outlook.com accounts must fully be compliant with SPF, DKIM, and DMARC". DMARC must be "At least p=none (p=reject is recommended)" and aligned with SPF or DKIM, preferably both — [Outlook.com postmaster policies](https://substrate.office.com/ip-domain-management-snds/Postmaster/Policies)
- **Non-compliant mail:** it is sent to the junk folder. If the problems persist, it may be rejected with `550; 5.7.515 Access denied, sending domain [SendingDomain] does not meet the required authentication level` — [Outlook.com postmaster policies](https://substrate.office.com/ip-domain-management-snds/Postmaster/Policies). Mailgun reports junk first and full rejection "at a later date, not yet set" — [Mailgun](https://www.mailgun.com/blog/deliverability/microsoft-sender-requirements/). Some third-party sources describe immediate rejection, and one notes that Microsoft's own post is inconsistent on the point — [Suped](https://www.suped.com/learn/email-deliverability/what-are-the-new-microsoft-email-sender-requirements-and-observed-enforcement-bounces). **Sources conflict.**
- **Other postmaster rules:**
  - After a permanent 5xx error, "the sender must not attempt to retransmit that message to that recipient".
  - After several non-delivery responses, the sender "must cease further attempts".
  - The unsubscribe mechanism must be "clearly documented and easy for recipients to find and use".
  - Source: [Outlook.com postmaster policies](https://substrate.office.com/ip-domain-management-snds/Postmaster/Policies)
- **What Microsoft does not require:** it publishes no numeric complaint threshold, and it has not explicitly required RFC 8058. It does recommend reply-capable From and Reply-To addresses, a functional visible unsubscribe link, list hygiene, and transparent subject lines and headers — [Mailgun](https://www.mailgun.com/blog/deliverability/microsoft-sender-requirements/)

**RFC 8058, the standard behind one-click unsubscribe (Proposed Standard, January 2017)**
- **Headers:** the sender places one `List-Unsubscribe` header, which "MUST contain one HTTPS URI", and one `List-Unsubscribe-Post` header whose only content is `List-Unsubscribe=One-Click` — [RFC 8058](https://www.rfc-editor.org/rfc/rfc8058)
- **The URI:** it "MUST contain enough information to identify the mail recipient and the list" and "SHOULD include an opaque identifier" that is hard to forge — [RFC 8058](https://www.rfc-editor.org/rfc/rfc8058)
- **The POST request:** it "MUST NOT include cookies, HTTP authorization, or any other context information", and the sender "MUST NOT return an HTTPS redirect" — [RFC 8058](https://www.rfc-editor.org/rfc/rfc8058)
- **DKIM:** the message must carry at least one valid DKIM signature that covers both headers. Without that signature, receivers "SHOULD NOT offer a one-click unsubscribe" — [RFC 8058](https://www.rfc-editor.org/rfc/rfc8058)

**BIMI — an optional provider feature**
- **DMARC:** Gmail requires a policy of quarantine or reject at pct=100. "BIMI doesn't support DMARC policies that have the p option set to none" — [Google Workspace, set up BIMI](https://knowledge.workspace.google.com/admin/security/set-up-bimi) (redirected from [support.google.com/a/answer/10911320](https://support.google.com/a/answer/10911320))
- **Certificates:** a Verified Mark Certificate (VMC, recommended) requires a registered trademark and displays a checkmark in Gmail. A Common Mark Certificate (CMC) needs no trademark — [Google Workspace, set up BIMI](https://knowledge.workspace.google.com/admin/security/set-up-bimi)
- **Logo:** SVG Tiny Portable/Secure, at least 96×96 px, 32 KB or less recommended. It can take up to 48 hours to appear, and trademarking takes 6 to 12 months — [Google Workspace, set up BIMI](https://knowledge.workspace.google.com/admin/security/set-up-bimi)

**Gmail Promotions tab, annotations and "Manage subscriptions"**
- **Annotations:** Promotions annotations include deal badges, Deal Cards and rich image annotations. Gmail "automatically groups and highlights emails in the Promotions tab that people are most likely to engage with". These highlights "are not ads and happen automatically based on a number of factors". Only consumer accounts see the new Promotions tab — [Google for Developers, Promotions tab](https://developers.google.com/workspace/gmail/promotab)
- **Δ "Manage subscriptions":** announced on 8 July 2025, it rolled out on the web first, then Android (14 July) and iOS (21 July). It is one view listing a user's subscriptions, and Gmail sends the unsubscribe request on the user's behalf — [Google Workspace Updates](https://workspaceupdates.googleblog.com/2025/07/manage-email-subscriptions-in-gmail.html); [Google blog](https://blog.google/products/gmail/new-manage-subscriptions-unsubscribe/)

### Inferences
- **Who the bulk rules apply to.** Gmail's bulk rules are defined against *personal Gmail accounts* ([FAQ](https://support.google.com/a/answer/14229414)). Cold B2B email to company domains is filtered by corporate gateways (Microsoft 365, Google Workspace, third-party filters), which do not publish rules in this form. The provider rules are still the right baseline: authentication failures are penalised everywhere.
- **Small businesses using a free mailbox as sender.** A business that sends marketing through a platform with a `@gmail.com` From: address will fail DMARC, because Gmail quarantines mail that impersonates its own domain ([Google guidelines](https://support.google.com/a/answer/81126)). This is a high-value warning, because it concerns exactly the small businesses MarketingOS serves.
- **The 0.1% target at small volumes.** 0.1% is one complaint per 1,000 messages. On a list of a few hundred, a single complaint exceeds 0.3%. The spam rate is mostly shaped by targeting and consent, not by copy. The copy-level lever is recognisability: does the recipient know why they got this, and who sent it?

| Rule | Label | Status / date | Touches the copy? | MarketingOS route |
|---|---|---|---|---|
| SPF + DKIM, DMARC ≥ p=none, From: aligned (≥ 5k/day) | PROVIDER | Gmail and Yahoo since Feb 2024; Δ Microsoft since 5 May 2025; Δ Gmail rejections since Nov 2025 | No | [INFRA] pre-send warning |
| SPF or DKIM, PTR, TLS, RFC 5322 (all Gmail senders) | PROVIDER | since Feb 2024 | No | [INFRA] |
| No marketing sent "From: @gmail.com" through a third-party platform | PROVIDER | in force | Partly (sender identity) | [A] if a sender address is stored, flag consumer-mailbox domains; [INFRA] |
| RFC 8058 one-click headers | PROVIDER (Gmail and Yahoo bulk; Microsoft: a functional unsubscribe is expected) | deadline June 2024 | No (headers) | [INFRA] |
| Visible unsubscribe link in the body | PROVIDER, and LEGAL (sections 3 and 5) | in force | **Yes** (footer) | [A] block export of a marketing email with no unsubscribe link or ESP merge tag |
| Unsubscribe honoured within 48 h (Gmail) / 2 days (Yahoo) | PROVIDER | in force | No | [INFRA] |
| Spam rate < 0.1%, never ≥ 0.3% | PROVIDER | in force | Indirectly | [INFRA]; [C] "would this recipient recognise why they got this?" |
| No content hidden with HTML/CSS | PROVIDER (Gmail) | in force | **Yes** | [A] in the renderer (see section 2 on the hidden preheader) |
| No promotional content in transactional mail | PROVIDER (Gmail), and LEGAL (CNIL, section 3) | in force | **Yes** | [A] category tag; [B] |
| Links visible and understandable | PROVIDER (Gmail guideline) | in force | **Yes** | [A] link text vs destination (section 2) |
| Display name = the sender, one address in From:, no subject or emoji in the display name | PROVIDER (Gmail) | in force | Yes, if MarketingOS proposes a sender name | [A] |
| BIMI | PROVIDER feature (optional) | in force | No | [INFRA] (nice to have; requires DMARC quarantine/reject) |
| Promotions annotations | Optional | — | No (markup) | Out of scope |

### Gaps
- Microsoft: it is unclear whether rejection with 5.7.515 is now immediate or comes after a junk-folder phase. Microsoft's pages and third-party observations disagree, and the Tech Community post did not render.
- French mailbox providers (Orange, SFR, Free, La Poste) were not researched. Their requirements matter for French B2C lists and were out of budget.
- Apple iCloud Mail sender requirements were not researched.
- No data was found on how Gmail ranks mail inside Promotions, beyond "most likely to engage".
- The decommissioning timeline for Postmaster Tools v1 was not verified.

## 2. Content-level deliverability: which content signals still matter, and what is folklore

### Takeaway
Filtering at the major providers is driven by reputation, authentication and engagement. "Spam trigger word" lists are folklore (MYTH), and content usually ranks a distant third behind IP and domain reputation. A few content patterns are still worth checking deterministically: hidden text, links whose visible text does not match their destination, image-only messages, HTML with no text part, and shouting. Gmail names some of them directly, and rule-based engines still used by some corporate and hosting filters (SpamAssassin) score them. They are cheap to avoid, and most of them are also accessibility failures.

### Cited Findings
- **Al Iverson (Spam Resource, writing since 2001)** calls the idea that avoiding a short list of words guarantees the inbox "absolute bullshit". Filters "are not so simplistic that just a word or two from a static list are going to tank your inbox placement". Content is "usually a distant third place, behind IP and domain sending reputation", and content problems are "the exception, not the rule"; he sees them most often at Microsoft, on subject lines — [Spam Resource, "Take your spam trigger words and go away", Nov 2022](https://www.spamresource.com/2022/11/take-your-spam-trigger-words-and-go-away.html)
- **Secondary summaries of expert comments, including Word to the Wise:** filters do not block on keywords alone; reputation, authentication and engagement are central; "the idea that 'free' is a spam trigger is a myth". Genuinely deceptive or spammy content is still penalised — [Suped knowledge base](https://www.suped.com/knowledge/email-deliverability/content/do-spam-trigger-words-affect-email-deliverability); [Suped, why spam-word lists are bad advice](https://www.suped.com/knowledge/email-deliverability/content/why-are-articles-listing-spam-words-to-avoid-considered-bad-advice) *(secondary; the original Word to the Wise posts were not retrieved)*
- **The content rules Gmail does publish** are about hiding, disguise and legibility, not about vocabulary: don't hide content with HTML/CSS ("Hiding content might cause messages to be marked as spam", per the guidelines); links should be "visible and easy to understand"; don't mix content types; no deceptive display names — [Google, Email sender guidelines](https://support.google.com/a/answer/81126)
- **Yahoo** bans "deceptive subject lines" and "false or misleading header information" — [Yahoo Sender Hub](https://senders.yahooinc.com/best-practices/)
- **Rule-based scoring (SpamAssassin, legacy 3.3.x rule list).** These rules score patterns; none blocks a message on its own. The rule list includes:
  - `HTML_IMAGE_ONLY_04…32` (image-dominant HTML with little text) and `HTML_IMAGE_RATIO_02…08` (low ratio of text to image area);
  - `HTTPS_HTTP_MISMATCH` and `SPOOF_COM2OTH` / `SPOOF_COM2COM` / `SPOOF_NET2COM` (domain-spoofing patterns in links);
  - `HTML_FONT_LOW_CONTRAST` (text colour close to the background), which is how hidden text is detected;
  - `SUBJ_ALL_CAPS` (subject entirely in capitals);
  - `MIME_HTML_ONLY` and `MIME_HTML_MOSTLY` (no plain-text part);
  - money phrases in the subject, such as `FS_AT_NO_COST` and `SUBJ_DOLLARS`.
  - That list has **no** rule specifically for "free" and no URL-shortener rule — [Apache SpamAssassin, tests 3.3.x](https://spamassassin.apache.org/old/tests_3_3_x.html)
- **MarketingOS hides its preheader on purpose.** The renderer hides the preheader in the message body so that it is not said twice ("Hidden in the message itself, so it is not said twice") — [backend/app/marketing/render_html.py, `_preheader`, l.374–381](C:\Users\oussa\Desktop\Workspace\projects\MarketingOS\backend\app\marketing\render_html.py)
- **MarketingOS `spam_gate` is BLOCKING and partly built on the myth.** It blocks any draft that contains one of 18 English phrases (`_SPAM_TERMS`: "act now", "limited time only", "risk free", "no obligation", "winner"…). It also blocks any word of 4+ consecutive capitals not on an allowlist, repeated `!`/`?`, more than 2 `!`, and a call to action reading "click here", "here" or "read more" — [backend/app/marketing/gates.py, l.237–306](C:\Users\oussa\Desktop\Workspace\projects\MarketingOS\backend\app\marketing\gates.py)
- **The allowlist covers English acronyms only.** It contains English compliance acronyms such as "GDPR" but not their French equivalents, so "RGPD", "CNIL", "URSSAF" and "SIRET" match `\b[A-Z]{4,}\b` and would block a French draft — [gates.py, l.243–265](C:\Users\oussa\Desktop\Workspace\projects\MarketingOS\backend\app\marketing\gates.py)

### Inferences

| Content signal | Verdict | Label | MarketingOS route |
|---|---|---|---|
| "Spam word" lists ("free", "act now", "winner"…) | Not a filtering driver at the major providers | **MYTH** | Remove as a *blocking* deliverability reason. Phrases that carry legal risk (false urgency, "free", "guaranteed") belong to claim licensing (section 4), not a word list |
| ALL CAPS, "!!!" | Weak rule-based score; reads as shouting | BEST PRACTICE (weak signal) | [A] advisory, not blocking; allowlist the acronyms of each locale (RGPD, CNIL…) |
| Image-only email, little text | Scored by rule engines; fails accessibility (section 7); the message is lost when images are blocked | BEST PRACTICE | [A] in the renderer: the text carries the message, never an image of text |
| Visible text that looks like a URL or domain but points elsewhere | Phishing heuristic (SpamAssassin spoof rules); Gmail asks for understandable links | BEST PRACTICE (+ PROVIDER guideline) | [A] if the anchor text contains a domain, it must match the href's registrable domain |
| Public URL shorteners (bit.ly…) | Shared-domain reputation risk | BEST PRACTICE (primary source not retrieved, see Gaps) | [A] flag shortener domains; [B] use the brand's own domain |
| Hidden text (display:none content, text in the background colour, tiny fonts) | Gmail: may be marked as spam; SpamAssassin `HTML_FONT_LOW_CONTRAST` | PROVIDER | [A] the renderer allows exactly one hidden block, the preheader, and it must say the same thing as the visible copy (no stuffing, no other claims) |
| HTML only, no text/plain part | Weak signal (`MIME_HTML_ONLY`) | BEST PRACTICE (weak) | [A] always export a plain-text version beside the HTML; the ESP builds the MIME ([INFRA]) |
| Deceptive subject or false header | Yahoo prohibits it; also unlawful (sections 3 and 5) | PROVIDER + LEGAL | [A] partial (fake "Re:"/"Fwd:" prefixes); [C] does the subject match the body? |
| Attachments in cold email | Not verified | BEST PRACTICE (unverified) | [B] no attachments in first-touch emails |

- **The hidden preheader** is standard industry practice and there is no evidence it is penalised. It is, however, literally "content hidden with CSS". The safe interpretation is that the hidden preheader must repeat or introduce visible copy and never add claims that appear nowhere else.
- **The `spam_gate` word list both over-blocks and under-blocks.** It blocks a *true* "limited time only" deadline, which is lawful. It misses false urgency in French ("dernière chance", "aujourd'hui seulement") and English variants not on the list ("today only", "ends tonight"). Licensing deadline claims against a dated offer fact, which `evidence_gate` already does for numbers and prices, is the deterministic version of what the list approximates (see section 4).
- **Re-justify the "click here" rule under WCAG 2.4.4** (link purpose, section 7) rather than spam vocabulary. The rule is good; the stated reason is weak.

### Gaps
- Spamhaus, M3AAWG and Validity documentation on URL shorteners, link counts, spam traps and content fingerprints was not retrieved; the search budget ran out.
- The shortener verdict above therefore rests on a common expert position, not on a fetched primary source.
- No primary source was retrieved on attachments in cold email, link-count thresholds, or image-to-text ratios such as the folklore "60/40". Treat any numeric ratio as unsourced.
- Microsoft's documentation on content filtering (SmartScreen, Defender for Office 365) was not retrieved, although Iverson says content problems show up there most often.
- The SpamAssassin list consulted is legacy (3.3.x); current rule sets evolve.

## 3. France/EU law: GDPR, ePrivacy, CPCE L34-5, CNIL guidance (B2C opt-in, B2B opt-out, soft opt-in, identification, unsubscribe, retention, tracking pixels), sanctions 2023–2026, ePrivacy Regulation

### Takeaway
In France, email prospecting of individuals requires prior consent: free, specific, informed and unambiguous, with no pre-ticked box and no consent through terms and conditions. There are two exceptions:
- **Soft opt-in:** existing customers, for similar products from the same company, with an opt-out offered at collection and in every message.
- **B2B:** professionals may be prospected without consent if the message relates to their profession, they were informed, and they can object.

Every message must identify the sender, offer a free and simple way to stop, and carry a subject that relates to the offer.

Three things changed in 2025–2026:
- CNIL rewrote its prospecting guidance on 10 June 2026. It now separates prospecting from transactional and relational mail, and forbids hiding promotional content inside transactional mail.
- CNIL's recommendation on email tracking pixels (adopted 12 March 2026, published 14 April 2026) makes consent the rule for open tracking, with narrow exemptions. It applies to B2B too.
- Enforcement hit inbox advertising (Google, €325M, September 2025) and partner and data-broker consent (2025). The ePrivacy Regulation is dead; Directive 2002/58 and L34-5 remain the law.

### Cited Findings

**The text: CPCE article L34-5 — LEGAL, in force**
- **The ban:** direct prospecting by email using a natural person's contact details is banned without that person's prior consent. Consent is defined as "toute manifestation de volonté libre, spécifique et informée". Prospecting means "tout message destiné à promouvoir, directement ou indirectement, des biens, des services ou l'image d'une personne vendant des biens ou fournissant des services" — [L34-5 reproduced by Baumann Avocats](https://www.baumann-avocats.com/CPCE/article-l34-5-du-code-des-postes-et-des-communications-electroniques.php); official code on [Légifrance (CPCE)](https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006070987/)
- **The existing-customer exception, for email only.** Prospecting by email is allowed when all three conditions hold:
  1. the contact details were collected from the recipient themselves during a sale or a service;
  2. the prospecting concerns similar products or services from the same person or company;
  3. the recipient was offered, clearly and unambiguously, a free and simple way to object, both at collection and in each email.
  - Source: [L34-5 (Baumann reproduction)](https://www.baumann-avocats.com/CPCE/article-l34-5-du-code-des-postes-et-des-communications-electroniques.php)
- **Rules for every message:**
  - It must give valid contact details where the recipient can, free of charge, ask for the messages to stop.
  - It is forbidden "de dissimuler l'identité de la personne pour le compte de laquelle la communication est émise".
  - It is forbidden "de mentionner un objet sans rapport avec la prestation ou le service proposé".
  - Source: [L34-5 (Baumann reproduction)](https://www.baumann-avocats.com/CPCE/article-l34-5-du-code-des-postes-et-des-communications-electroniques.php)
- **Enforcement:**
  - CNIL oversees compliance where natural persons' details are used.
  - Consumer-protection agents (articles L511-3 and L511-21 of the Code de la consommation, i.e. DGCCRF) also investigate breaches. They can impose an administrative fine capped at €3,000 for a natural person and €15,000 for a legal person (as reproduced; to be verified on Légifrance).
  - Source: [L34-5 (Baumann reproduction)](https://www.baumann-avocats.com/CPCE/article-l34-5-du-code-des-postes-et-des-communications-electroniques.php)

**Δ CNIL guidance rewritten on 10 June 2026 — LEGAL interpretation by the regulator**
- **B2C:** prior consent, "libre, spécifique, éclairé et univoque". "L'utilisation d'une case pré-cochée est interdite". "L'acceptation de conditions générales d'utilisation ne peut pas suffire". Consent can be withdrawn at any time — [CNIL, « La prospection commerciale par courrier électronique, SMS-MMS et automate d'appel », 10 June 2026](https://www.cnil.fr/fr/la-prospection-commerciale-par-courrier-electronique-sms-mms-et-automate-dappel)
- **Soft opt-in:** limited to existing customers and to "produits ou services similaires fournis par la même entreprise". Creating an account is not enough: "la simple création d'un compte ne signifie pas qu'il y aura une commande éventuelle" — [CNIL, 10 June 2026](https://www.cnil.fr/fr/la-prospection-commerciale-par-courrier-electronique-sms-mms-et-automate-dappel)
- **B2B:**
  - Prospecting can rest on legitimate interest if its subject is "en rapport avec la profession de la personne démarchée", with a right to object.
  - If the data is already held or was bought from third parties, the person must have been told it might be used for prospecting, and must be able to object.
  - Generic addresses of legal persons (info@, contact@, commande@) "ne sont pas soumises aux principes rappelés ci-dessus".
  - Source: [CNIL, 10 June 2026](https://www.cnil.fr/fr/la-prospection-commerciale-par-courrier-electronique-sms-mms-et-automate-dappel)
- **Each message:** the recipient must be able to "prendre connaissance de l'identité de l'organisation qui l'émet", and to refuse further messages "par un moyen simple". The page cites CPCE L32 and L34-5, and GDPR articles 4(11), 6, 7 and 21 — [CNIL, 10 June 2026](https://www.cnil.fr/fr/la-prospection-commerciale-par-courrier-electronique-sms-mms-et-automate-dappel)
- **Δ Three categories of email:**
  - **Prospecting:** messages that promote products, services or the company's image. Consent is required, subject to the exceptions above.
  - **Transactional:** welcome emails, account alerts, delivery notices, order confirmations, invoices, password resets. They rest on the contract.
  - **Relational:** follow-up of a customer relationship with no direct promotional purpose, such as usage tips or security alerts. They rest on legitimate interest, which must stay reasonable and not intrusive, "for example through overly frequent messages".
  - Transactional and relational messages "ne doivent pas être utilisés pour dissimuler un contenu promotionnel". A message with "contenu promotionnel significatif" may be reclassified as prospecting.
  - A publisher's newsletter whose aim is to push readers toward a paid subscription is prospecting even if its content is informational.
  - Source: [CNIL, « Communications par voie électronique aux prospects et clients : quelles règles respecter ? », 10 June 2026](https://www.cnil.fr/fr/communication-electronique-quelles-regles)
- **Δ Suppression list ("liste repoussoir"):**
  - Objection is "absolu" and needs no justification; it must be simple and free at collection and in each message.
  - CNIL recommends keeping the objection record "au minimum 3 ans", ideally as hashes of the address rather than a nominative list.
  - Hashed data is still personal data.
  - Source: [CNIL, liste repoussoir, 10 June 2026](https://www.cnil.fr/fr/comment-utiliser-une-liste-repoussoir-pour-respecter-lopposition-la-prospection)
- **Retention of prospect data:**
  - CNIL doctrine since simplified norm no. 48: 3 years from collection or from the last contact *initiated by the prospect*. A click on a link in an email counts as such a contact; an open does not — [Lettre des Réseaux](https://www.lettredesreseaux.com/P-1973-454-A1-plus-que-10-mois-pour-mettre-en-conformite-ses-fichiers-clients-et-prospects.html); [donneespersonnelles.fr](https://donneespersonnelles.fr/dernier-contact-prospect-conservation) *(secondary; no current official CNIL page on this point was retrieved)*
  - Δ CNIL applied it in 2025: a company kept inactive prospects for four years and treated an email open as proof of an "active" contact; CNIL found this insufficient — [HLC Avocats, panorama of CNIL decisions 2025 (SAN-2025-002)](https://hlc.com/fr/publications/panorama-des-deliberations-de-la-cnil-en-2025-quand-les-sanctions-precedent-les-recommandations)

**Δ Tracking pixels in email (CNIL recommendation, deliberation no. 2026-042) — LEGAL (art. 82 Loi Informatique et Libertés, the French transposition of ePrivacy art. 5(3)), as interpreted by CNIL**
- **Dates and transition:** adopted on 12 March 2026 and published on 14 April 2026. For addresses collected before publication, senders had three months to "informer clairement les destinataires de l'utilisation de pixels" so that they could object. The recommendation covers both senders and their technical providers, and CNIL will check compliance during inspections — [CNIL press release](https://cnil.fr/fr/recommandation-pixel-suivi-courriels)
- **What the FAQ (22 July 2026) says:**
  - **Deliverability exemption.** Measuring deliverability individually is exempt only for emails tied to a service the person requested (transactional mail, or mail the person consented to), and only using strictly necessary data — generally the date of the last open, used to spot inactive recipients (Q7).
  - **When consent is required.** Recording anything more, such as the time of the open, requires consent (Q5). Marketing sent under the soft opt-in cannot rely on the deliverability exemption (Q5, Q15).
  - **Security exemption.** Limited to user-centred cases, such as pixels in authentication or password-reset emails; general fraud prevention is not covered (Q13).
  - **Aggregate statistics.** Data from an exempt pixel may be aggregated into a campaign open rate (Q6). Collecting "anonymous" data through a pixel is not exempt in itself, because article 82 applies whether or not the data is personal (Q18).
  - **Tracked links (redirects).** The recommendation does not cover them directly, but article 82 still applies, case by case (Q1).
  - **B2B is included,** professional addresses among them (Q3).
  - **Responsibility.** An email platform that inserts pixels only for the sender is a processor; if it also uses them for itself, it is a joint controller. A contract clause alone does not prove consent (Q4).
  - **Collecting consent.** Consent does not have to be collected per email category (Q21). It must be "retiré aussi facilement qu'il a été donné" (Q23).
  - **Non-opening** is a signal to stop, reduce or change channel, not a refusal of consent (Q8).
  - **The transition is over.** Where no information had been sent by 14 July 2026, pixels that require consent must stop (Q26).
  - Source: [CNIL, FAQ on the pixel recommendation, 22 July 2026](https://cnil.fr/fr/faq-recommandation-pixels-courriers-electroniques)
- **A law firm's reading:** consent is "la règle de principe", and a recipient's inaction on a consent request means no consent — [Seban Avocats](https://www.seban-associes.avocat.fr/le-pixel-invisible-des-courriels-sort-de-lombre/). This is consistent with consent doctrine. It is a different question from FAQ Q8, which is about non-opening.

**GDPR information duty for data not collected from the person — LEGAL, in force since 2018**
- Under GDPR article 14(3)(b), where data is used to communicate with the person, the article 14 information is due "at the latest at the time of the first communication" — [GDPR, EUR-Lex](https://eur-lex.europa.eu/eli/reg/2016/679/oj) *(official text; not re-fetched in this session)*. This is what CNIL's "informed and able to object" condition for bought B2B data rests on.

**Sanctions 2023–2026 involving email prospecting or the inbox**
- **Δ Google, €325M, announced 3 September 2025.** €200M against Google LLC and €125M against Google Ireland.
  - Ads shown between emails in Gmail's "Promotions" and "Social" tabs required consent under L34-5; about 53 million users had seen them unlawfully.
  - The decision also covered consent to cookies at account creation.
  - CNIL ordered Google to stop, under a penalty of €100,000 per day.
  - Source: [CNIL, press release](https://cnil.fr/fr/publicites-inserees-entre-les-courriels-et-cookies-la-cnil-sanctionne-google-dune-amende-de-325)
- **Δ €3.5M, decision of 30 December 2025 (SAN-2025-017), published 22 January 2026.** A loyalty-programme operator sent members' email addresses or phone numbers to a social network for targeted advertising, from 2018 onwards, affecting more than 10.5 million people.
  - Consent was invalid, because the signup form said nothing about it.
  - CNIL also found failures on information, security, the impact assessment (DPIA) and cookies.
  - CNIL cites "une case à cocher mentionnant clairement la finalité" as the mechanism that would have worked.
  - Source: [CNIL](https://www.cnil.fr/fr/transmission-de-donnees-un-reseau-social-des-fins-publicitaires-sanction)
- **Δ December 2025:** five simplified sanctions against candidates in the 2024 European and legislative elections for sending prospecting messages — [CNIL](https://www.cnil.fr/fr/prospection-politique-sanction-candidats-2024)
- **Δ 15 May 2025: two data-broker decisions (SAN-2025-001 and SAN-2025-002).**
  - Contest entry forms used a single « JE PARTICIPE » button for both entry and consent to partner marketing, with a near-invisible refusal link.
  - The companies could not prove consent collected two years earlier.
  - Relying on partners' contractual warranties does not relieve the controller of its duty to check.
  - Amounts are not given in the source.
  - Source: [HLC Avocats](https://hlc.com/fr/publications/panorama-des-deliberations-de-la-cnil-en-2025-quand-les-sanctions-precedent-les-recommandations)
- **Simplified procedures:** CNIL issued 67 unpublished sanctions under its simplified procedure in 2025, mostly against very small firms, SMEs and liberal professions — [HLC Avocats](https://hlc.com/fr/publications/panorama-des-deliberations-de-la-cnil-en-2025-quand-les-sanctions-precedent-les-recommandations)
- **Groupe Canal+, €600,000, 2023:** prospecting and data-subject rights — [CB News](https://www.cbnews.fr/node/79735); [LexisVeille](https://www.lexisveille.fr/prospection-commerciale-et-droits-des-personnes-canal-sanctionne-par-la-cnil)

**Δ ePrivacy Regulation: withdrawn**
- The Commission listed it for withdrawal in its 2025 work programme (11 February 2025) because "no agreement is expected from the co-legislators". Secondary sources report approval in July 2025 and publication in the Official Journal in October 2025. The 2002 ePrivacy Directive remains the applicable framework — [Hunton](https://www.hunton.com/privacy-and-cybersecurity-law-blog/european-commission-withdraws-eprivacy-regulation-and-ai-liability-directive-proposals); [EDRi](https://edri.org/our-work/the-eprivacy-regulation-proposal-has-been-withdrawn-but-the-fight-for-your-privacy-is-far-from-over/); [Lewis Silkin](https://www.lewissilkin.com/en/insights/2025/02/19/long-awaited-eprivacy-regulation-is-finally-dead-102k0fn)

### Inferences

| Rule | Label | Status | MarketingOS route |
|---|---|---|---|
| B2C: prior, specific consent; no pre-ticked box; T&Cs not enough | LEGAL (L34-5; GDPR 4(11), 7) | in force; Δ guidance of 10 Jun 2026 | [INFRA] list provenance. MarketingOS should ask, per campaign, what legal basis the list rests on (consent / soft opt-in / B2B) and adapt the brief |
| Soft opt-in: an existing customer (sale or service), similar products, same company, opt-out at collection and in each email | LEGAL | in force | [A] opt-out present; [C]/strategist: the offer must be "similar" to what was bought |
| B2B: legitimate interest; message related to the profession; informed + able to object; generic addresses excluded | LEGAL (CNIL doctrine) | in force | [C] *professional relevance* criterion: does the email explain why it concerns this role? [B] the strategist states that link in the brief; [INFRA] list provenance |
| Bought or third-party data: art. 14 information at the latest in the first email | LEGAL (GDPR 14(3)(b)) | in force | [A] cold prospecting: a footer slot for "where your data came from / privacy policy link" is present (placeholder filled by the user); [INFRA] |
| Every message: sender identity; valid free means to stop; no concealed identity; subject related to the offer | LEGAL (L34-5) | in force | [A] footer has the legal name + unsubscribe; [A] partial subject checks (fake "Re:"); [C] subject matches body |
| Δ Transactional and relational mail must not carry significant promotion | LEGAL (CNIL 10 Jun 2026) + PROVIDER (Gmail) | in force | [A] every email is tagged prospecting / transactional / relational; offers, prices and calls to buy are blocked in the latter two; [B] |
| Δ Hashed suppression list, kept ≥ 3 years | LEGAL (objection) / CNIL recommendation | 10 Jun 2026 | [INFRA] |
| Prospects kept 3 years from the last contact *they* initiated; a click counts, an open does not | LEGAL (CNIL doctrine; Δ sanction 2025) | in force | [INFRA] |
| Δ Tracking pixels: consent is the rule; narrow exemptions (individual deliverability for requested or consented mail, security) | LEGAL (art. 82 LIL as interpreted by CNIL) | published 14 Apr 2026; transition ended 14 Jul 2026; FAQ 22 Jul 2026 | [INFRA] ESP setting; [A] the renderer never inserts a pixel itself |
| Δ Ads inside the inbox are prospecting that requires consent | LEGAL (L34-5; CNIL v. Google 2025) | — | Does not concern the copy |
| Δ ePrivacy Regulation | Withdrawn; Directive 2002/58 and L34-5 remain | 2025 | — |

- **Tracking pixels in cold B2B email to French addresses.** These recipients have neither requested a service nor consented. The deliverability exemption covers only mail tied to a requested service or to consent (FAQ Q7, Q15), and B2B is covered (Q3). In practice, an open-tracking pixel in a cold B2B email is therefore unlawful without consent the recipient has not given. This inference needs legal confirmation, but MarketingOS should warn about it, because most cold-email tools track opens by default.
- **Content marketing and nurture sequences are prospecting.** On the CNIL test (purpose, not tone), a "valuable", educational nurture email is prospecting if its purpose is to sell. MarketingOS sequences should be classified as prospecting by default.
- **The "objet sans rapport" ban is the French counterpart of US deceptive-subject rules.** Together with the ban on concealing identity, it is the legal ground for blocking fake "Re:"/"Fwd:" subjects and senders who hide the company behind a first name.

### Gaps
- The current L34-5 text was read through a law firm's reproduction, not directly on Légifrance; the DGCCRF fine caps (€3,000 / €15,000) should be checked on Légifrance.
- That L34-5 derives from the LCEN (loi n° 2004-575) and transposes article 13 of Directive 2002/58 is background knowledge, not re-verified in this session.
- The CNIL fine against Orange (€50M, reported for December 2024, over ads disguised as emails in webmail) appears only in an unreliable guide; the CNIL page could not be fetched (404).
- Amounts for the two May 2025 data-broker decisions are not in the source.
- Not retrieved: a complete official list of CNIL email-prospecting sanctions for 2023–2026; the CNIL page on prospect retention after the June 2026 rewrite; the status of CNIL's guidance on data collected by partners.
- **Digital Omnibus (November 2025 proposal):** its possible effect on GDPR and ePrivacy (e.g., moving the cookie rule into the GDPR) and its legislative status in October 2026 were not verified.
- The French law requiring opt-in for *telephone* prospecting (loi n° 2025-594, reportedly applicable from August 2026) is outside email scope and was not verified.

## 4. EU consumer-protection rules that constrain the copy (UCPD, the Omnibus price-reduction rule and Aldi Süd, fake reviews, greenwashing (2024/825, Green Claims), dark-pattern sweeps, the Digital Fairness Act, AI Act article 50)

### Takeaway
The UCPD blacklist already bans, in all circumstances:
- false "very limited time" claims;
- misleading "free";
- disguised paid editorial content;
- posing as a non-trader;
- fake or unverified reviews;
- persistent unwanted email solicitation.

Since 2022, any announced price reduction must state the prior price, meaning the lowest price of the previous 30 days, and since Aldi Süd (CJEU, 26 September 2024) the percentage must be computed on that price.

Directive 2024/825 has applied since 27 September 2026 and bans generic environmental claims ("eco-friendly", "green"…) unless the business can prove recognised excellent environmental performance. France had not transposed it as of October 2026.

The Green Claims Directive has been stalled since June 2025, and the Digital Fairness Act is not yet proposed (expected Q4 2026).

AI Act article 50 has applied since 2 August 2026, but its text-disclosure duty covers text published to inform the public on matters of public interest. That is not an ordinary marketing email, so no "written by AI" label is required on one.

Most of these claim rules can be checked deterministically by **licensing** the claim against a dated fact, the way MarketingOS already licenses numbers and quotations.

### Cited Findings

**UCPD 2005/29/EC, Annex I (practices unfair in all circumstances) — LEGAL, in force since 2005; transposed in France in the Code de la consommation**
- **Point 7:** "Falsely stating that a product will only be available for a very limited time…" (in order to elicit an immediate decision) — [Directive 2005/29/EC Annex I, legislation.gov.uk (EU text as of 2020)](https://www.legislation.gov.uk/eudr/2005/29/annex/I); consolidated text on [EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02005L0029-20220528)
- **Point 11:** "Using editorial content in the media to promote a product where a trader has paid for the promotion…" without making that clear — [Annex I](https://www.legislation.gov.uk/eudr/2005/29/annex/I)
- **Point 20:** "Describing a product as 'gratis', 'free', 'without charge' or similar if the consumer has to pay anything other than…" the unavoidable cost of responding, collecting or delivery — [Annex I](https://www.legislation.gov.uk/eudr/2005/29/annex/I)
- **Point 22:** "Falsely claiming or creating the impression that the trader is not acting for purposes relating to his trade…" — [Annex I](https://www.legislation.gov.uk/eudr/2005/29/annex/I)
- **Point 26:** "Making persistent and unwanted solicitations by telephone, fax, e-mail or other remote media…" — [Annex I](https://www.legislation.gov.uk/eudr/2005/29/annex/I)

**Directive (EU) 2019/2161 ("Omnibus") — LEGAL, applicable since 28 May 2022**
- **Price reductions:** it inserts article 6a into the Price Indication Directive 98/6/EC. Any announced price reduction must indicate the prior price, which is the lowest price applied over at least 30 days before the reduction — [Directive 2019/2161, EUR-Lex](https://eur-lex.europa.eu/eli/dir/2019/2161/oj/eng)
- **Reviews:** it adds points 23b and 23c to the UCPD blacklist, on fake consumer reviews and endorsements and on false claims that reviews are verified — [Directive 2019/2161](https://eur-lex.europa.eu/eli/dir/2019/2161/oj/eng)
- **Fines:** it sets maximum fines of at least 4% of annual turnover, or €2M — [Directive 2019/2161](https://eur-lex.europa.eu/eli/dir/2019/2161/oj/eng)

**Aldi Süd, CJEU C-330/23, judgment of 26 September 2024 — LEGAL interpretation**
- A price reduction announced in an advertisement must be determined on the basis of the lowest price applied by the trader during at least the 30 days before the reduction. In the case, bananas were advertised with €1.69 struck through and a "-23%" computed from €1.69, while the lowest price of the previous 30 days was €1.29. The reduction must be computed from €1.29. Showing the 30-day low in a footnote does not cure a percentage computed on another base — [CJEU press release no. 152/24](https://curia.europa.eu/jcms/upload/docs/application/pdf/2024-09/cp240152en.pdf) ([FR](https://curia.europa.eu/jcms/upload/docs/application/pdf/2024-09/cp240152fr.pdf)); [Noerr](https://www.noerr.com/en/insights/impact-of-the-cjeu-ruling-on-discount-advertising-in-europe-what-it-means-for-businesses)

**Δ Directive (EU) 2024/825, "empowering consumers for the green transition" (EmpCo) — LEGAL, applicable since 27 September 2026**
- **Dates:** the transposition deadline was 27 March 2026, and the provisions apply from 27 September 2026 — [Luxembourg Conseil d'État opinion on bill 8648](https://wdocs-pub.chd.lu/docs/Dossiers_parlementaires/8648/20260323_Avis.pdf). The directive is unaffected by the fate of the Green Claims proposal — [CMS UK](https://cms.law/en/gbr/legal-updates/the-eu-green-claims-directive-where-are-we-now-and-what-s-next)
- **Content:** generic environmental claims are banned ("respectueux de l'environnement", "écologique", "vert"…) unless recognised excellent environmental performance can be shown — [CMS France](https://cms.law/en/fra/legal-updates/greenwashing-en-attendant-la-transposition-de-la-directive-empco-en-france-la-mise-en-conformite-s-impose); [KPMG Avocats, January 2026](https://kpmg.com/av/fr/avocats/eclairages/2026/01/transposition-de-la-directive-empowering-consumers.html)
- **France:**
  - Not transposed as of October 2026. Transposition is planned through the DDADUE bill (articles 20 and 21), reportedly adopted by the Senate in February 2026 and still pending at the Assemblée nationale — [ShippyPro](https://www.shippypro.com/blog/en/the-green-claims-directive-greenwashing-obligations-from-september-27-2026) *(vendor blog)*
  - France is reportedly one of 20 late Member States — [Que Choisir](https://www.quechoisir.org/actualite-greenwashing-l-encadrement-des-allegations-environnementales-se-fait-attendre-n177194/)
  - **Sources disagree** on whether enforcers can act before transposition.

**Green Claims Directive (proposed March 2023) — stalled**
- On 20 June 2025 the Commission announced its intention to withdraw the proposal. It later clarified that the proposal had not been formally withdrawn, and the Council, where a blocking minority formed after Italy withdrew its support, has to decide how to proceed. No 2026 update was found — [Latham & Watkins](https://www.lw.com/en/insights/european-commission-announces-intention-to-withdraw-eu-green-claims-directive-proposal); [CMS UK](https://cms.law/en/gbr/legal-updates/the-eu-green-claims-directive-where-are-we-now-and-what-s-next); [Taylor Wessing](https://www.taylorwessing.com/en/insights-and-events/insights/2025/07/green-claims-richtlinie)

**EU dark-pattern sweep (CPC network), results published 30 January 2023**
- National authorities screened 399 retail sites; 148 (37%) used at least one of three dark patterns. 42 used fake countdown timers and 54 steered consumers toward particular choices such as subscriptions. 27 of the sites' 102 apps used them too — [European Commission, IP/23/418](https://ec.europa.eu/commission/presscorner/api/files/document/print/en/ip_23_418/IP_23_418_EN.pdf)

**Δ Digital Fairness Act — not yet proposed**
- **Timing:** the European Parliament's legislative train lists it as a Commission initiative for Q4 2026 — [European Parliament, legislative train](https://www.europarl.europa.eu/legislative-train/theme-protecting-our-democracy-upholding-our-values/file-digital-fairness-act). One firm expects a draft on 11 November 2026, and does not expect the act in force before the end of 2028 — [CMS](https://cms.law/en/aut/legal-updates/inside-the-eu-s-planned-digital-fairness-act-digital-design-subscription-traps-and-influencer-marketing) *(single source for the date)*
- **Content:** 62% of stakeholders in the Fitness Check supported stronger protection against dark patterns. Options include a longer UCPD blacklist, a general ban on dark patterns and a "fairness by design" duty — [Goodwin, November 2025](https://www.goodwinlaw.com/en/insights/publications/2025/11/alerts-practices-antc-from-dark-patterns-to-fair-play); [CMS](https://cms.law/en/aut/legal-updates/inside-the-eu-s-planned-digital-fairness-act-digital-design-subscription-traps-and-influencer-marketing)

**Δ AI Act (Regulation 2024/1689), article 50 — LEGAL, applicable since 2 August 2026**
- **50(1), providers:** AI systems that interact directly with people must tell them so, unless it is obvious — [AI Act art. 50](https://artificialintelligenceact.eu/article/50/)
- **50(2), providers:** providers of AI systems that generate synthetic text, among other media, must ensure the outputs are "marked in a machine-readable format and detectable as artificially generated or manipulated" — [AI Act art. 50](https://artificialintelligenceact.eu/article/50/)
- **50(4), deployers.** Deployers of a system that generates text "published with the purpose of informing the public on matters of public interest" must disclose that it is AI-generated. The duty does not apply where the content "has undergone a process of human review or editorial control" and a person "holds editorial responsibility" for its publication — [AI Act art. 50](https://artificialintelligenceact.eu/article/50/)
- **50(5):** the information must be given "in a clear and distinguishable manner" and "at the latest at the time of the first interaction or exposure" — [AI Act art. 50](https://artificialintelligenceact.eu/article/50/)
- **Commission guidelines (final, 20 July 2026):**
  - "Public interest" covers areas such as politics, public administration, justice and public health.
  - The editorial exception "requires substantive human review, not a cursory check", and any material AI change after sign-off removes it.
  - The 50(2) marking duty has carve-outs (short text, source code, translations, closed-loop use), but consumer-facing AI cannot use them.
  - Generative systems already on the market before 2 August 2026 have until 2 December 2026 to apply 50(2).
  - A Code of Practice on transparency of AI-generated content is "an adequate voluntary tool to demonstrate compliance".
  - Source: [Stephenson Harwood](https://www.stephensonharwood.com/post/102nfqh/eu-ai-act-update-european-commission-adopts-guidelines-on-article-50-transparenc/)
- **Digital Omnibus status (conflict).** One source says the Omnibus on AI entered into force on 27 July 2026 as "Regulation (EU) 2026/1744"; others say it was still awaiting formal adoption — [CSA research note, July 2026](https://labs.cloudsecurityalliance.org/research/csa-research-note-eu-ai-act-article-50-transparency-20260729/); [Baker Botts, September 2026](https://www.bakerbotts.com/thought-leadership/publications/2026/september/eu-ai-act-article-50-transparency-obligations-go-live). **Unresolved.**

### Inferences

| Claim in the copy | Label | Status | MarketingOS route |
|---|---|---|---|
| Deadline or urgency ("dernière chance", "aujourd'hui seulement", "J-2", "today only", "ends tonight", a countdown) | LEGAL (UCPD Annex I.7 when false; Washington CEMA, section 5) | in force; Δ US case law 2025–26 | **[A]** a deadline claim must be licensed by a dated offer fact in the Evidence Ledger or offer sheet (end date ≥ the claimed date); otherwise block. [B] never invent a deadline |
| Scarcity ("plus que 3 places", "stock limité") | LEGAL (UCPD art. 6 misleading action; I.7 when it is time-based) | in force | [A] licensed by a stock or capacity fact; [B] |
| "Gratuit" / "free" / "offert" | LEGAL (UCPD I.20) | in force | [A] licensed by the offer sheet (no cost beyond the unavoidable); [C] are the conditions visible? |
| Price reduction ("-30 %", "au lieu de", "était 99 €", strikethrough) | LEGAL (PID art. 6a; CJEU C-330/23) | since 28 May 2022; CJEU 26 Sep 2024 | **[A]** requires a fact typed "prior price = lowest price over 30 days"; the percentage is recomputed from it and must match |
| Reviews, testimonials, "X clients satisfaits", "vérifié" | LEGAL (UCPD I.23b/23c; FTC rule, section 5) | since 2022 | [A] already partly covered: `evidence_gate` licenses quotations and numbers against the user's material; extend it to the *attribution* (a named person or company must exist in the material). [B] no invented testimonial or persona |
| Generic environmental claims ("écologique", "vert", "durable", "respectueux de l'environnement", "neutre en carbone", "eco-friendly", "climate neutral") | LEGAL (Dir. 2024/825) | Δ applicable 27 Sep 2026; FR transposition pending | **[A]** FR/EN term list: block unless licensed by evidence of a recognised certification or label; [B] |
| Paid or advertorial content presented as editorial; sender posing as a peer or customer | LEGAL (UCPD I.11, I.22) | in force | [B] no fake editorial or newsletter framing; no "a friend recommended you…"; [C] |
| Persistent unwanted email solicitation | LEGAL (UCPD I.26) | in force | [INFRA] honour stops; [B] strategist: bounded sequence length (section 8) |
| AI disclosure in a marketing email (art. 50(4)) | **Not required** for ordinary marketing (inference) | Δ 2 Aug 2026 | No check. Marketing email is not text published to inform the public on matters of public interest |
| Art. 50(2) machine-readable marking (providers of generative systems) | LEGAL, for providers | Δ 2 Aug 2026 / 2 Dec 2026 transition | **Open question:** is MarketingOS itself a "provider" of an AI system that generates text, placed on the market under its own name? Needs legal review; outside the copy |

- **Licensing generalises.** The deterministic pattern that already works in MarketingOS (a claim must be licensed by the Evidence Ledger) extends to deadlines, scarcity, "free", price reductions, testimonial attribution and green claims. Each of these is unlawful when *false* and lawful when true, which is exactly what a word list cannot tell apart and a ledger can.
- **Article 50(4) and newsletters on public-interest topics.** A brand newsletter on politics, justice or public health could fall under 50(4). The human-review exception then requires *substantive human* review. MarketingOS's cold reader is a model and does not count; only the user's own review can provide the exception.
- **No AI label, but deception rules still apply.** Article 50 requires no "written by AI" mention on marketing email. Fabricated human signatories, personas or testimonials remain unlawful under the UCPD (I.22, I.23c), and under the FTC rule for AI-generated fake reviews (section 5).

### Gaps
- The exact text of UCPD points 23b and 23c and of the new article 13 could not be quoted, because EUR-Lex pages did not render. Their content is confirmed only in summary.
- The French transposition of article 6a (Code de la consommation; the ordonnance of 2021) was not verified.
- Earlier French rules on green claims were not verified: AGEC law bans on "biodégradable" and "respectueux de l'environnement" on products, and Climat et Résilience law conditions on "neutre en carbone".
- The status of France's EmpCo transposition rests on vendor and consumer-press sources, not on the parliamentary record.
- Green Claims: no 2026 status found.
- The regulation number and entry into force of the Digital Omnibus on AI are conflicting and unresolved.
- The 2023 sweep's figure for "hidden information" was not confirmed.

## 5. US, Canada, UK: CAN-SPAM, the FTC reviews rule and Endorsement Guides, deceptive subjects and fake urgency, CASL, UK PECR and the Data (Use and Access) Act 2025

### Takeaway
- **United States.** CAN-SPAM is an opt-out regime covering B2B as well. It requires accurate headers, a subject that reflects the content, ad identification, a physical postal address, and an opt-out that works for 30 days and is honoured within 10 business days, with fines of up to $53,088 per email.
- **US, fake reviews.** The FTC's 2024 rule bans fake reviews, including AI-generated ones; the first warning letters went out in December 2025.
- **US, Washington State.** The 2025–2026 US surprise is state law. Since Brown v. Old Navy (April 2025), any false or misleading subject line, false urgency included, is actionable under Washington's CEMA. More than 100 suits followed. A June 2026 amendment cut damages to $100 and added a knowledge requirement.
- **Canada.** CASL is consent-based: implied consent lasts 2 years after a purchase or 6 months after an inquiry; messages must identify the sender and carry an unsubscribe that is honoured within 10 business days; penalties reach $10M.
- **United Kingdom.** PECR allows B2B email to corporate subscribers without consent. Since 5 February 2026 the Data (Use and Access) Act has raised PECR fines to £17.5M or 4% of turnover and added a charity soft opt-in.

### Cited Findings

**United States: CAN-SPAM (15 U.S.C. 7701 et seq.; 16 CFR 316) — LEGAL, in force since 2004**
- **Requirements:**
  - Routing and From/To/Reply-To information must be accurate and identify who initiated the message.
  - The subject "must accurately reflect the content of the message".
  - The message must clearly and conspicuously disclose that it is an advertisement; the law allows flexibility on how.
  - It must give a valid physical postal address: a street address, a USPS post-office box, or a registered private mailbox.
  - It must explain clearly how to opt out, offering a return email address or an internet-based method, with an option to stop all marketing. The mechanism must work for at least 30 days, and opt-outs must be honoured within 10 business days, with no fee and nothing asked beyond an email address.
  - Opted-out addresses may not be sold or transferred.
  - Source: [FTC, CAN-SPAM Act: A Compliance Guide for Business](https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business)
- **Scope and penalties:**
  - The law "makes no exception for business-to-business email".
  - A company "can't contract away" its responsibility by hiring a marketing provider.
  - The "primary purpose" test decides what counts as commercial; transactional and relationship messages are read narrowly.
  - Penalties reach $53,088 per violating email.
  - Source: [FTC compliance guide](https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business)

**FTC Rule on Consumer Reviews and Testimonials (16 CFR 465) — LEGAL**
- **Adoption:** announced on 14 August 2024 after a 5–0 vote, and effective 60 days after publication in the Federal Register — [FTC press release](https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials)
- **What it bans:**
  - fake reviews and testimonials, including AI-generated ones and those from people who do not exist;
  - incentives conditioned on a particular sentiment;
  - undisclosed reviews by insiders;
  - company-controlled sites presented as independent;
  - review suppression;
  - fake social-media indicators.
  - Civil penalties are available against knowing violators.
  - Source: [FTC press release](https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials)
- **Δ First enforcement:** on 22 December 2025 the FTC sent its first warning letters under the rule, to 10 unnamed companies — [Venable](https://www.venable.com/insights/publications/2025/12/ftc-signals-heightened-enforcement-of-new); [Arnold & Porter](https://www.arnoldporter.com/en/perspectives/blogs/consumer-products-and-retail-navigator/2026/01/ftc-warning-letters-over-consumer-review-rule); [BCLP](https://www.bclplaw.com/en-US/events-insights-news/early-reviews-are-in-ftc-flags-potential-violations-of-consumer-reviews-rule.html)

**FTC dark-pattern report — regulatory finding**
- The staff report "Bringing Dark Patterns to Light" (15 September 2022) lists among its problems countdown timers that suggest a limited-time offer that does not exist, ads disguised as independent content, buried terms, cancellation obstacles and data-sharing traps — [FTC press release](https://www.ftc.gov/news-events/news/press-releases/2022/09/ftc-report-shows-rise-sophisticated-dark-patterns-designed-trick-trap-consumers); [report page](https://www.ftc.gov/reports/bringing-dark-patterns-light)

**Δ Washington State: Commercial Electronic Mail Act (CEMA) — LEGAL (state law)**
- **Brown v. Old Navy (Wash. Sup. Ct., 17 April 2025, 5–4).** CEMA reaches *any* false or misleading information in a commercial email's subject line, not only misstatements about the email's commercial nature. The subject lines at issue were "Today Only!" and "Three Days Only!" for promotions that ran longer — [Fenwick](https://www.fenwick.com/insights/publications/washington-supreme-court-expands-email-subject-line-restrictions-under-cema); [AFS Law](https://www.afslaw.com/perspectives/fashion-counsel/washington-cema-litigation-targets-promotional-email-subject-lines-and)
- **Litigation:** more than 100 CEMA suits followed — [K&L Gates, July 2026](https://www.klgates.com/Litigation-Minute-CEMA-ingly-Endless-Litigation-Meets-Legislative-Limits-Washington-States-Legislative-Response-to-the-Email-Marketing-Litigation-Surge-7-9-2026)
- **No federal preemption:** in Ma v. Nike (W.D. Wash., January 2026) the court held that CAN-SPAM does not preempt this CEMA provision — [Faegre Drinker](https://www.faegredrinker.com/zh/insights/publications/2026/1/federal-court-upholds-washington-state-commercial-electronic-mail-act-against-can-spam-preemption-argument)
- **HB 2274, effective 11 June 2026:**
  - statutory damages reduced from $500 to $100 per violation;
  - plaintiffs must show the sender knew, or that knowledge can fairly be implied, that the subject was false or misleading;
  - a good-faith defence covers a sale extended because of unforeseen circumstances;
  - knowingly false urgency remains actionable.
  - Source: [K&L Gates](https://www.klgates.com/Litigation-Minute-CEMA-ingly-Endless-Litigation-Meets-Legislative-Limits-Washington-States-Legislative-Response-to-the-Email-Marketing-Litigation-Surge-7-9-2026)

**Canada: CASL (S.C. 2010, c. 23) — LEGAL, in force since 2014**
- **s. 6(1)–(2):** sending a commercial electronic message is prohibited without express or implied consent. The message must identify the sender, give contact information, and include an unsubscribe mechanism — [CASL, Justice Laws](https://laws-lois.justice.gc.ca/eng/acts/E-1.6/FullText.html)
- **s. 10(9)–(10), implied consent:** through an existing business relationship, i.e. a purchase "within the two-year period" before the message, or an inquiry "within the six-month period" — [CASL](https://laws-lois.justice.gc.ca/eng/acts/E-1.6/FullText.html)
- **s. 11:** the unsubscribe address must remain valid for at least 60 days, and requests must be honoured no later than 10 business days — [CASL](https://laws-lois.justice.gc.ca/eng/acts/E-1.6/FullText.html)
- **s. 20(4):** maximum penalty of $1M for an individual and $10M for any other person — [CASL](https://laws-lois.justice.gc.ca/eng/acts/E-1.6/FullText.html)
- **Conspicuous publication (CompuFinder, Federal Court of Appeal, 2020):** an address published conspicuously does not license harvesting from third-party directories or from sites that refuse unsolicited email. The message must relate to the recipient's business role — [BLG](https://www.blg.com/insights/2020/07/federal-court-of-appeal-rules-casl-constitutionally-valid-and-provides-interpretive-guidance); [Torys](https://www.torys.com/insights/publications/2020/06/fca-confirms-casl-is-constitutional-but-limits-business-communications-exemption)

**United Kingdom: PECR (2003) — LEGAL**
- **Individual subscribers:** consent, or the soft opt-in. The soft opt-in requires an existing customer who bought or negotiated a similar product, and a simple opt-out at collection and in every message. It does not cover prospective customers or bought-in lists.
- **Every message:** "You must not disguise or conceal your identity", and you must provide a valid contact address to opt out.
- **B2B:** "You can email or text any corporate body". Sole traders and some partnerships count as individuals; a "do not email" list of businesses that objected is good practice.
- **Guidance status:** the ICO page says it is "under review" because of the DUAA.
- Source: [ICO, electronic mail marketing](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guide-to-pecr/electronic-and-telephone-marketing/electronic-mail-marketing/)

**Δ Data (Use and Access) Act 2025 (Royal Assent 19 June 2025)**
- **In force:** commencement order no. 6 (SI 2026/82) brought the PECR amendments into force on 5 February 2026:
  - maximum PECR fine of £17.5M or 4% of global turnover, "whichever is higher";
  - a soft opt-in for charities;
  - relaxed cookie exemptions;
  - wider enforcement powers.
  - The ICO "is very active when it comes to PECR breaches".
  - Source: [Lewis Silkin, February 2026](https://www.lewissilkin.com/insights/2026/02/09/uk-data-reform-becomes-reality-what-this-means-for-you-and-what-you-need-to-do-n-102mh5x); [Addleshaw Goddard](https://www.addleshawgoddard.com/en/insights/insights-briefings/2025/data-protection/data-use-and-access-act-2025-top-7-changes/)
- **Direct marketing definition:** PECR and the UK GDPR now share one: "the communication (by whatever means) of advertising or marketing material which is directed to particular individuals" — [Mayer Brown](https://www.mayerbrown.com/de/insights/publications/2025/06/the-data-use-and-access-act-pecr-reform-rules-relating-to-electronic-marketing-and-cookies-in-the-uk)
- **B2B:** the government considered extending PECR's marketing rules to B2B and did not — [Mayer Brown](https://www.mayerbrown.com/de/insights/publications/2025/06/the-data-use-and-access-act-pecr-reform-rules-relating-to-electronic-marketing-and-cookies-in-the-uk)
- **Conflict:** the ICO page still says the soft opt-in does not cover charity fundraising. That page predates the DUAA changes and is flagged as under review.

### Inferences

| Rule | Label | Status | MarketingOS route |
|---|---|---|---|
| CAN-SPAM: subject reflects content, accurate headers | LEGAL (US) | in force | [A] fake "Re:"/"Fwd:" prefixes on a first-touch email; [C] subject–body match |
| CAN-SPAM: physical postal address + opt-out (30 days / 10 business days) | LEGAL (US) | in force | [A] footer slots: postal address and opt-out; [INFRA] processing time |
| CAN-SPAM: ad identification | LEGAL (US) | in force | [B]/[A] flexible: the footer or opening states that this is a commercial message (see Gaps on the consent exception) |
| FTC reviews rule | LEGAL (US) | eff. 2024; Δ letters 22 Dec 2025 | [A] testimonials and quotations licensed against the user's material; [B] |
| Washington CEMA: no false or misleading subject line, urgency included | LEGAL (WA) | Δ Apr 2025 ruling; Δ amended 11 Jun 2026 | [A] licensing of deadlines and claims *in the subject line* (the strictest place) |
| CASL: consent, identification (name + mailing address + phone/email/web), unsubscribe valid 60 days, honoured ≤ 10 business days | LEGAL (CA) | since 2014 | [INFRA] consent; [A] identification footer + unsubscribe; [C] for conspicuous publication, does the message relate to the role? |
| PECR: individuals need consent or soft opt-in; corporate subscribers may be emailed; no concealed identity; opt-out address | LEGAL (UK) | Δ fines ×35 since 5 Feb 2026 | [INFRA] list provenance; [A] identity + opt-out |

- **One footer serves every jurisdiction.** A single footer block covers the identification requirements of France, the EU, the US, Canada and the UK: legal name, physical postal address, one other contact channel, a working unsubscribe link, and for cold prospecting a privacy or data-source line. It is fully deterministic to check: are the slots present and filled? This is the strongest "hard rule" candidate in the whole checklist.
- **The subject line is the highest-risk place for a false claim.** CAN-SPAM, CEMA, L34-5 ("objet sans rapport") and Yahoo's rules all target it.

### Gaps
- **FTC Endorsement Guides** (revised June 2023, 16 CFR 255): not re-verified in this session.
- **Deceptive "Re:"/"Fwd:" subjects:** no FTC enforcement action specifically targeting them was found; the search budget was exhausted.
- **CAN-SPAM penalty:** the inflation adjustment for 2026 above $53,088 was not verified.
- **CAN-SPAM ad identification:** whether the requirement lapses when the recipient gave prior affirmative consent was not verified.
- **CASL:** the CRTC guidance page refused the fetch (403). The status of the private right of action, and the rule that express consent does not expire, were not verified.
- **UK:** whether the DUAA changed how "sent" versus "received" emails are counted for enforcement was not verified; the exact conditions of the charity soft opt-in are not detailed.
- **Other US states:** California (B&P 17529.5) and others were not researched.

## 6. Dark patterns and manipulative tactics in email: regulatory findings and research on trust

### Takeaway
Regulators treat most email dark patterns as already unlawful, with no new law needed:
- fake countdowns and deadlines;
- fake replies and forwards;
- disguised ads and advertorials;
- promotion hidden inside transactional mail;
- bait-and-switch subjects;
- obstructed unsubscribe.

The tools are the UCPD blacklist, L34-5, CAN-SPAM and state laws such as Washington's CEMA, and the Digital Fairness Act is expected to add a general ban. Experimental evidence (Luguri & Strahilevitz) shows mild dark patterns work without visible backlash, while aggressive ones provoke it. That favours a strict policy: the cost does not show up in the short-term metric.

### Cited Findings
- **EU sweep (2023):** 37% of 399 online shops used dark patterns; 42 of them used fake countdown timers — [European Commission, IP/23/418](https://ec.europa.eu/commission/presscorner/api/files/document/print/en/ip_23_418/IP_23_418_EN.pdf)
- **FTC report (2022):** its targets include non-existent limited-time countdowns, ads disguised as independent content and cancellation mazes; "These traps will not be tolerated" (Samuel Levine, FTC) — [FTC press release, 15 September 2022](https://www.ftc.gov/news-events/news/press-releases/2022/09/ftc-report-shows-rise-sophisticated-dark-patterns-designed-trick-trap-consumers)
- **Legal bases already available:** UCPD Annex I.7 (false limited time), I.11 (undisclosed paid editorial), I.22 (posing as a non-trader) and I.26 (persistent unwanted email) — [Directive 2005/29/EC Annex I](https://www.legislation.gov.uk/eudr/2005/29/annex/I)
- **Promotion disguised as service mail:** "ne doivent pas être utilisés pour dissimuler un contenu promotionnel" — [CNIL, 10 June 2026](https://www.cnil.fr/fr/communication-electronique-quelles-regles); Gmail: "Don't mix different types of content in the same message" — [Google](https://support.google.com/a/answer/81126)
- **Ads disguised in the inbox:** sanctioned as prospecting without consent — [CNIL v. Google, September 2025](https://cnil.fr/fr/publicites-inserees-entre-les-courriels-et-cookies-la-cnil-sanctionne-google-dune-amende-de-325)
- **False urgency in subject lines:** actionable in Washington ("Today Only!") — [Fenwick](https://www.fenwick.com/insights/publications/washington-supreme-court-expands-email-subject-line-restrictions-under-cema)
- **Deceptive subjects and headers:** banned by Yahoo — [Yahoo Sender Hub](https://senders.yahooinc.com/best-practices/); a subject "sans rapport" is banned in France — [L34-5](https://www.baumann-avocats.com/CPCE/article-l34-5-du-code-des-postes-et-des-communications-electroniques.php); the subject must reflect content under CAN-SPAM — [FTC](https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business)
- **Unsubscribe obstruction:** the opt-out must be simple and free ("par un moyen simple") — [CNIL](https://www.cnil.fr/fr/la-prospection-commerciale-par-courrier-electronique-sms-mms-et-automate-dappel). RFC 8058 forbids a POST that needs cookies, authentication or a redirect — [RFC 8058](https://www.rfc-editor.org/rfc/rfc8058). CAN-SPAM bans requiring anything beyond an email address or more than one page visit — [FTC](https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business)
- **Research on effectiveness and backlash (Luguri & Strahilevitz, Journal of Legal Analysis, 2021).** In a representative US sample, mild dark patterns more than doubled the share of people who stayed enrolled in an unwanted plan, and aggressive ones almost quadrupled it. Aggressive patterns generated a powerful backlash; mild ones did not. Less-educated subjects were significantly more susceptible to mild patterns — [SSRN](https://papers.ssrn.com/abstract=3431205); [Oxford Academic, JLA 13(1):43](https://academic.oup.com/jla/article/13/1/43/6180579); [Public Citizen summary](https://clpblog.citizen.org/luguri-strahilevitz-paper-on-how-online-companies-manipulate-consumers-using-dark-patterns-and-udap/)
- **Δ What is coming:** the DFA may add a general ban on dark patterns and a "fairness by design" duty — [Goodwin](https://www.goodwinlaw.com/en/insights/publications/2025/11/alerts-practices-antc-from-dark-patterns-to-fair-play)

### Inferences

| Tactic in email | Label | Legal basis | MarketingOS route |
|---|---|---|---|
| Fake countdown, invented deadline ("expire ce soir" when it does not) | LEGAL | UCPD I.7; CEMA; FTC | [A] deadline licensing; [B] |
| Fake "Re:" / "Fwd:" / "TR :" / "RE :" on a first message, or a subject imitating an ongoing conversation | LEGAL (deceptive subject) | CAN-SPAM; L34-5 "objet sans rapport"; UCPD art. 6 | **[A]** block a reply or forward prefix when there is no prior message in the thread (only a follow-up within a sequence may use it, and only if it truly replies to the previous email) |
| Bait-and-switch: the subject promises X and the body sells Y | LEGAL | L34-5; CAN-SPAM; UCPD art. 6 | [C] cold reader: does the subject match what the body offers? (cannot be checked deterministically) |
| Ad presented as editorial or a personal note; "a friend told me about you"; a fake persona | LEGAL | UCPD I.11, I.22, I.23c | [B]; [C] |
| Promotion hidden in a transactional or relational email | LEGAL + PROVIDER | CNIL 2026; Gmail | [A] category tag |
| Confirmshaming ("Non merci, je préfère perdre de l'argent") in the CTA or the unsubscribe | BEST PRACTICE / legal risk (aggressive practice, UCPD arts. 8–9) | UCPD general clauses; CNIL "moyen simple" | [B] no guilt-loaded refusal option; [C] |
| Hidden, tiny or unlabelled unsubscribe | LEGAL + PROVIDER | L34-5; CAN-SPAM; Gmail "clearly visible" | [A] the unsubscribe link has legible text and contrast (section 7) |
| Fake scarcity or fake social proof ("1 243 personnes regardent") | LEGAL | UCPD art. 6, I.23c | [A] licensed by a fact; [B] |

- **Mild manipulation hides its cost.** Because mild dark patterns raise conversion without visible backlash (Luguri & Strahilevitz), any optimisation that rewards a short-term outcome will drift toward them. In MarketingOS the duel judge and the cold reader estimate pull or clicks. This is an argument for keeping these checks in deterministic gates that the judge cannot overrule, which matches the architecture.
- **A gap in the evidence.** No study measuring the long-term engagement or unsubscribe effects of fake urgency *in email specifically* was found (see Gaps). The trust argument rests on the general dark-pattern literature and on enforcement.

### Gaps
- Email-specific research was not retrieved: studies of manipulative tactics in political emails (fake "Re:", false deadlines), and panel studies of fake urgency's effect on unsubscribe or complaint rates.
- The ICPEN/GPEN 2024 dark-pattern sweep was not retrieved.
- No FTC case specifically on fake reply subjects was found.

## 7. Accessibility: what makes an email accessible, and whether the European Accessibility Act applies

### Takeaway
WCAG 2.2 is the reference, and most of what it asks of an email can be checked deterministically:
- text alternatives for images;
- presentation-only layout tables;
- language declared on the right element;
- a contrast of at least 4.5:1;
- link text that says what happens;
- no information carried by colour alone;
- no images of text;
- text that can be resized;
- real headings;
- a plain-text alternative.

The 2026 Email Markup Consortium audit found serious or critical defects in 99.88% of 376,348 emails, mostly missing attributes (`dir`, `lang` where clients keep it, `alt`, `role="presentation"`). Whether the European Accessibility Act (applicable since 28 June 2025) covers marketing emails is unsettled. The clearest case is transactional email inside a B2C e-commerce flow; B2B mail is generally considered outside. MarketingOS's renderer already does several things right, and misses `dir` and a `lang` that survives clients which strip the `<html>` element.

### Cited Findings
- **WCAG 2.2** is a W3C Recommendation (current edition dated 12 December 2024). Relevant success criteria:
  - **1.1.1 Non-text Content (A):** non-text content has a text alternative "that serves the equivalent purpose".
  - **1.3.1 Info and Relationships (A):** structure conveyed by presentation "can be programmatically determined".
  - **1.4.1 Use of Color (A):** colour is not the only visual means of conveying information.
  - **1.4.3 Contrast (Minimum) (AA):** at least 4.5:1, and 3:1 for large text.
  - **1.4.4 Resize Text (AA):** text can be resized up to 200% without loss.
  - **1.4.5 Images of Text (AA):** use text rather than images of text.
  - **2.4.4 Link Purpose (In Context) (A):** the purpose of each link can be determined from its text, alone or with its programmatic context.
  - **2.4.6 Headings and Labels (AA):** headings and labels describe the topic or purpose.
  - Source: [W3C, WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- **Δ Email Markup Consortium, Email Accessibility Report 2026:**
  - 376,404 emails collected between May 2025 and May 2026; 376,348 tested with Parcel's automated checker.
  - 99.88% had "Serious" or "Critical" defects; only eight emails passed.
  - Most common defects: missing `dir` (97.41%), missing body-level `lang` (95.66%), images without alt (47.88%), and about 84% of layout tables not marked as presentation.
  - None of 10,566 emails sent through Substack, Shopify or Beehiiv passed every automated check.
  - The results are automated checks only; reading order and meaning still need a person.
  - Source: [beSpacific summary of the EMC report](https://www.bespacific.com/?p=125394); [Harvard TagTeam mirror](https://tagteam.harvard.edu/hub_feeds/2087/feed_items/18322019) *(secondary summaries; emailmarkup.org was not reached)*
- **European Accessibility Act (Directive (EU) 2019/882):**
  - Applicable from 28 June 2025 — [Customer.io](https://customer.io/learn/privacy-and-security/european-accessibility-act)
  - The directive does not mention email or newsletters. Vendors generally treat B2C marketing and transactional emails as in scope — [Upland Adestra](https://uplandsoftware.com/adestra/resources/blog/european-accessibility-act/); [Badsender](https://www.badsender.com/en/2025/02/18/european-accessibility-act)
  - Narrower readings put B2B outside and only e-commerce flows inside. The Swedish regulator PTS reportedly holds that only the parts of a site belonging to the e-commerce service are covered — [Voyado](https://help.engage.voyado.com/hc/en-gb/articles/20451970101148-Understanding-the-Accessibility-Act-Tillg%C3%A4nglighetsdirektivet-and-what-it-means-for-you-as-a-Voyado-customer)
  - Official text: [EUR-Lex 2019/882](https://eur-lex.europa.eu/eli/dir/2019/882/oj/eng)
- **What MarketingOS's renderer does today:**
  - It sets `lang` on `<html>` only, after validating the language code, and sets no `dir`.
  - Layout tables carry `role="presentation"`, and the logo has an `alt`.
  - It declares `color-scheme: light`, so that Apple Mail and Outlook do not invert the palette badly.
  - The preheader is hidden.
  - The unsubscribe line renders only when an unsubscribe URL is configured.
  - Source: [backend/app/marketing/render_html.py, l.340–381, 699, 711–724](C:\Users\oussa\Desktop\Workspace\projects\MarketingOS\backend\app\marketing\render_html.py)

### Inferences

| Accessibility rule | Label | MarketingOS route |
|---|---|---|
| `lang` and `dir` on the content wrapper as well as on `<html>` (webmail clients often drop `<html>`/`<body>` attributes; inference from the "body-level lang" metric) | BEST PRACTICE (WCAG 3.1.1, 1.3.1) | [A] renderer fix + check |
| `alt` on every `<img>` (empty `alt=""` for decorative images); the message never carried by an image | BEST PRACTICE (WCAG 1.1.1, 1.4.5); LEGAL where the EAA applies | [A] |
| `role="presentation"` on layout tables | BEST PRACTICE (WCAG 1.3.1) | [A] already done |
| Contrast ≥ 4.5:1 for body text, footer and unsubscribe link included | BEST PRACTICE (WCAG 1.4.3) | [A] computable from the renderer palette (`scale.muted` on the footer is the place to check) |
| Descriptive link and CTA text (not "cliquez ici") | BEST PRACTICE (WCAG 2.4.4) | [A] already partly done by `spam_gate`; re-justify it under accessibility and add the French forms |
| Information never carried by colour alone | BEST PRACTICE (WCAG 1.4.1) | [A] partial (links underlined); [C] |
| Real headings, short paragraphs, logical reading order | BEST PRACTICE (WCAG 1.3.1, 2.4.6) | [A] renderer structure; [C] reading order |
| A plain-text alternative to the HTML | BEST PRACTICE | [A] export; [INFRA] MIME |
| Dark mode: no inverted, illegible callouts | BEST PRACTICE | [A] already handled by declaring light-only (a trade-off: no native dark mode) |
| EAA conformance | LEGAL *if in scope*: clearest for transactional email in B2C e-commerce; marketing email disputed; B2B generally outside | [INFRA]/legal note |

- **Accessibility and deliverability point the same way.** Most accessibility fixes are pure renderer attributes and can be checked deterministically. Fixing them costs no model calls and also removes the deliverability weak signals in section 2 (image-only messages, hidden text, low contrast).

### Gaps
- The official EMC report on emailmarkup.org was not reached (403); its figures come from secondary summaries.
- The EAA definition of "e-commerce services" (article 3) could not be quoted from EUR-Lex in this session.
- No official national position (France or other Member States) on whether marketing emails fall under the EAA was found.
- The text of WCAG 3.1.1 (Language of Page) was truncated in the fetch; it is cited from the known criterion number only.
- The Litmus and Email on Acid accessibility guides, and dark-mode guidance, were not retrieved.

## 8. Over-mailing and list hygiene (frequency fatigue, consent decay, bought lists, why mailing unengaged contacts hurts deliverability)

### Takeaway
The providers and the regulators converge on the same rules:
- send only to people who asked;
- honour the frequency they signed up for;
- never buy lists;
- stop mailing addresses that bounce;
- sunset or reconfirm inactive contacts.

Unengaged recipients hurt deliverability, because reputation and complaint rates now drive filtering. They also hurt legal standing: in 2025 CNIL sanctioned treating an open as "activity" in order to keep prospects for four years, and its 2026 pixel FAQ tells senders to stop, reduce frequency or change channel when mail is not opened. Persistent unwanted email is blacklisted under the UCPD. Consent decay has hard legal clocks in Canada (2 years / 6 months) and France (3 years from the last contact the prospect initiated). No authoritative "decay rate" figure was found, so treat circulating numbers as folklore.

### Cited Findings
- **Yahoo's list rules:**
  - "Send only to users who requested mail" and honour the frequency they signed up for.
  - Don't buy lists or use pre-checked boxes; use confirmed opt-in.
  - Monitor hard and soft bounces and inactive recipients; "Remove invalid recipients from your list promptly"; consider reconfirming inactive subscribers.
  - Source: [Yahoo Sender Hub](https://senders.yahooinc.com/best-practices/)
- **Microsoft's bounce rules:** never resend after a permanent 5xx error, and stop sending to an address after several non-delivery responses — [Outlook.com postmaster policies](https://substrate.office.com/ip-domain-management-snds/Postmaster/Policies)
- **Gmail's complaint thresholds:** below 0.10%, never 0.30%; losing mitigation above 0.3% — [Google](https://support.google.com/a/answer/81126); [Google FAQ](https://support.google.com/a/answer/14229414)
- **Δ Unsubscribing is now easier:** Gmail's "Manage subscriptions" (July 2025) puts every list's unsubscribe in one place — [Google Workspace Updates](https://workspaceupdates.googleblog.com/2025/07/manage-email-subscriptions-in-gmail.html)
- **Frequency in relational mail:** relational messages must stay reasonable and not intrusive, "for example through overly frequent messages" — [CNIL, 10 June 2026](https://www.cnil.fr/fr/communication-electronique-quelles-regles)
- **Δ Non-opening:** it should lead the sender to treat the channel as ineffective, and to stop, reduce frequency or use another channel. The deliverability exemption exists precisely to spot inactive recipients and remove them — [CNIL pixel FAQ, Q7–Q8, 22 July 2026](https://cnil.fr/fr/faq-recommandation-pixels-courriers-electroniques)
- **Δ Opens are not activity:** keeping inactive prospects four years on the basis of opens was sanctioned in 2025 — [HLC Avocats](https://hlc.com/fr/publications/panorama-des-deliberations-de-la-cnil-en-2025-quand-les-sanctions-precedent-les-recommandations). The 3-year retention runs from the last contact the prospect initiated; a click counts, an open does not — [Lettre des Réseaux](https://www.lettredesreseaux.com/P-1973-454-A1-plus-que-10-mois-pour-mettre-en-conformite-ses-fichiers-clients-et-prospects.html)
- **Persistent unwanted email** is blacklisted: UCPD Annex I.26 — [Directive 2005/29/EC](https://www.legislation.gov.uk/eudr/2005/29/annex/I)
- **Consent clocks (Canada):** implied consent expires 2 years after a purchase or 6 months after an inquiry — [CASL s. 10(10)](https://laws-lois.justice.gc.ca/eng/acts/E-1.6/FullText.html)
- **Bought lists:** the UK soft opt-in never covers bought-in lists — [ICO](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guide-to-pecr/electronic-and-telephone-marketing/electronic-mail-marketing/). In France, the controller must verify partner-collected consent, and contractual warranties are not enough — [HLC Avocats (SAN-2025-001/002)](https://hlc.com/fr/publications/panorama-des-deliberations-de-la-cnil-en-2025-quand-les-sanctions-precedent-les-recommandations). Yahoo: no purchased lists — [Yahoo](https://senders.yahooinc.com/best-practices/)
- **Δ Suppression list:** at least 3 years, hashed — [CNIL](https://www.cnil.fr/fr/comment-utiliser-une-liste-repoussoir-pour-respecter-lopposition-la-prospection)

### Inferences
- **What sits within MarketingOS's reach.** Over-mailing is mostly [INFRA] (cadence, sunsetting, suppression), but MarketingOS decides two things that bear on it:
  - **Sequence length and spacing.** The strategist should cap the number of touches and space them, so that a sequence cannot become "persistent and unwanted" under UCPD I.26.
  - **Stop conditions written into the brief:** stop on reply, stop on unsubscribe, end after the last touch.
  - Both are [B] instructions to the strategist plus an [A] structural check, such as a maximum number of touches per sequence and a minimum spacing.
- **No authoritative decay rate.** No authoritative figure for annual list decay or "consent decay" was found. Treat circulating numbers (e.g., "22.5% per year") as **MYTH until sourced**. The verifiable consent clocks are legal ones: CASL's 2 years / 6 months and France's 3 years from the last contact the prospect initiated.

#### Cross-cutting synthesis: checklist by implementation route (synthesis of sections 1–8)

**HARD — deterministic, may block (the claim is checkable on the text, the HTML or the facts)**
1. **Identification footer present and filled** (FR L34-5 / CNIL, US CAN-SPAM, CA CASL, UK PECR): legal name of the sender, physical postal address, one other contact channel, a working unsubscribe link or ESP merge tag. For cold prospecting, add a line on the data source and privacy policy (GDPR art. 14). Block export of a *prospecting* email that lacks them.
   - *Today the renderer silently omits the unsubscribe line when no URL is set ([render_html.py l.711–724](C:\Users\oussa\Desktop\Workspace\projects\MarketingOS\backend\app\marketing\render_html.py)). The right behaviour is "not sendable as marketing" with a stated reason.*
2. **Deadline and urgency claims are licensed** by a dated offer fact; block them otherwise (UCPD I.7; CEMA). This applies with extra strictness in the **subject line**.
3. **Price-reduction claims are licensed** by a "lowest 30-day price" fact; any percentage is recomputed from it (PID art. 6a; CJEU C-330/23).
4. **"Gratuit" / "free" / "offert"** is licensed by the offer sheet (UCPD I.20).
5. **Testimonials, reviews, "X clients", "vérifié":** the quotation *and its attribution* are licensed against the user's material (UCPD I.23b/c; FTC rule). This extends the existing `evidence_gate`.
6. **Generic environmental claims** (FR/EN list) are blocked unless licensed by evidence of a recognised certification (Dir. 2024/825, Δ applicable 27 September 2026).
7. **No fake "Re:" / "Fwd:" / "TR :"** on an email that is not truly a reply in its thread (CAN-SPAM; L34-5 "objet sans rapport"; UCPD art. 6).
8. **Category integrity:** an email tagged transactional or relational may not contain offers, prices or calls to buy (CNIL 2026; Gmail).
9. **No hidden content** other than the preheader, and the preheader must not contain claims absent from the visible copy (Gmail).
10. **Links:** an anchor text that contains a domain must match its href; flag public shorteners (BEST PRACTICE / Gmail).
11. **Accessibility attributes:** `lang` + `dir` on the wrapper, `alt` on every image, `role="presentation"`, contrast ≥ 4.5:1 including the footer, descriptive CTA text in each locale, a plain-text alternative exported (WCAG 2.2).
12. **Sequence structure:** a maximum number of touches and a minimum spacing (UCPD I.26; CNIL "not overly frequent").

**SOFT — critic or cold-reader criteria (never block)**
- Does the subject truthfully announce what the body offers (bait-and-switch; CAN-SPAM; L34-5)?
- B2B: does the email make its relevance to *this role* obvious (CNIL B2B condition; CASL conspicuous publication)?
- Soft opt-in: is the offer "similar" to what the customer bought?
- Is there confirmshaming or guilt-loaded refusal language?
- Would the recipient recognise who sent this and why they received it (complaint-rate lever)?

**WRITER INSTRUCTIONS [B]**
- Never invent a deadline, scarcity, discount, testimonial, persona or certification.
- No fake editorial, personal-note or friend-referral framing.
- No reply prefixes unless replying.
- No attachments or shorteners in first-touch email.
- No guilt-loaded opt-out wording.
- Name the company plainly in the sign-off.

**INFRA WARNINGS (pre-send checklist shown to the user; outside the copy)**
- **Authentication:** SPF + DKIM + DMARC ≥ p=none aligned (Gmail and Yahoo 2024; Δ Microsoft May 2025; Δ Gmail rejections since November 2025). Never send marketing through a platform "From: @gmail.com".
- **Unsubscribe and complaints:** RFC 8058 one-click headers; unsubscribes processed within 48 h / 2 days (CAN-SPAM: 10 business days); spam rate < 0.1%.
- **Legal basis of the list:** consent / soft opt-in / B2B with professional relevance; no bought lists; art. 14 notice for third-party data.
- **Δ No open-tracking pixels without consent for French recipients,** B2B included (CNIL 2026). This probably rules out pixels in cold email.
- **Suppression and retention:** a hashed suppression list kept ≥ 3 years; prospects purged 3 years after the last contact they initiated (opens do not count); bounces suppressed; inactive contacts sunset.
- **Regional rules:** Canadian recipients need CASL consent; for UK sole traders, B2C rules apply.

**RETIRE OR RELABEL (MYTH)**
- **Blocking on "spam words"** (`_SPAM_TERMS` in [gates.py l.237–242](C:\Users\oussa\Desktop\Workspace\projects\MarketingOS\backend\app\marketing\gates.py)) has no support in provider documentation or expert consensus. Replace it with claim licensing (items 2–4 above) or make it advisory.
- **ALL CAPS and "!!!"** are weak, readability-grade signals; make them advisory. Add locale acronyms ("RGPD", "CNIL", "URSSAF", "SIRET") to `_SHOUTING_ALLOWED`; otherwise French compliance copy is blocked.
- **"Image-to-text ratio" numbers and annual "list decay" percentages** are unsourced; do not encode them.

**NOT REQUIRED**
- An "AI-generated" label on ordinary marketing email (AI Act 50(4) covers public-interest publications).
- **Open legal question:** whether MarketingOS is a 50(2) "provider" with text-marking duties (transition to 2 December 2026).

### Gaps
- M3AAWG, Spamhaus and Validity primary documents on spam traps, recycled traps, sunset policies and confirmed opt-in were not retrieved; the search budget was exhausted.
- No authoritative source was found on frequency fatigue thresholds or consent decay outside the legal clocks. Performance statistics are covered by other researchers.
- The ICO's position on consent "degrading over time" was not retrieved.
- Whether any regulator has set a numeric maximum frequency for prospecting email: none was found.
