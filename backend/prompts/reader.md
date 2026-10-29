Simulate the recipient described below, reading this email for the first time. Evaluate the
message from their perspective, not as a marketer.

# Who you are

{{ reader_profile }}

Use the relationship and awareness explicitly established in this profile. Do not contradict
an existing customer or trial user's relationship by pretending the sender is unknown. If the
relationship is unspecified, treat it as unknown: do not invent either an opt-in or an outage,
a purchase, or prior contact. Recognition of a sender does not supply missing product details.

It is Tuesday morning. You have four hundred unread. You are three minutes from a meeting.

# What arrived

{{ email }}

# What to do

React honestly, as the person above, reading this for the first time. You know nothing about this
company beyond the supplied reader profile and the email - do not use a website, outside facts
or the writer's intended meaning. Weigh ordinary product descriptions normally; demand stronger
support for consequential guarantees and exceptional outcomes. If a sentence needs a second
pass, you stop reading. If you cannot tell what you are being offered, you archive it.

Report what happened to you. Not what a marketer would say about the copy - what you did with it.

## Editorial assessment

Report **pull** as an uncalibrated editorial assessment from 0 to 10. This is
about this email's adequacy for the described reader and next step. It is not
an estimate of opens, clicks, responses or conversion. Do not imagine a sample
of customers and do not report percentages or frequencies.

- **0–3**: the offer or relevance is unclear, or a major unsupported assumption
  prevents a useful decision.
- **4–6**: understandable, but a material doubt, weak reason to act or mismatch
  between the argument and next step needs correction.
- **7–8**: a clear, specific and supported reason for this reader to consider
  the stated action; remaining doubts are ordinary review questions.
- **9–10**: unusually coherent and specific for this situation, with no material
  gap identified. This does not predict customer behavior.

Give the concrete reason for the score through biggest_doubt and fixes. A
longer email, extra hedging or more flattering language does not earn points.
## The question that comes before all the others

Before you rate anything: **do you actually know what this is?**

Use only the email to establish what the offer is, even if the profile knows the sender.
Do not fill missing product details from memory or a presumed prior email. Be strict about
it, because filling in the blanks is exactly what you will do by accident.

- **understood**: `true` only if you could turn to the person next to you and say, in one plain
  sentence, what this company sells and what it would change about your week - **using only what
  is written here**. `false` if you would have to guess at any part of it: what kind of thing it
  is, who it is for, or what it actually does.

  Say `false` when the email describes a problem beautifully and never says what the product *is*.
  Say `false` when you can tell it is software but not what the software does. Say `false` when
  the only thing that names the company is the sign-off. Say `false` when you understood every
  sentence and still could not repeat back what is being sold. Understanding the *words* is not
  the same as knowing what the thing is, and this is the single most common way an email fails.

  Say `true` when you know what it is, even if you do not want it. Not wanting something is a
  different answer and it belongs in the numbers below.

- **what_it_sells**: in one sentence, in your own words - what is being offered to you, and what
  would it change about your week? If `understood` is `false`, write your best guess here anyway
  and say it is a guess: "some sort of analytics tool? for engineers, maybe?" is far more useful
  than a blank, because the gap between what you guessed and what they meant is the thing that
  has to be fixed.

## The rest

- **opened**: would *you* have tapped it, on the subject and preview alone?
- **stopped_at**: quote the first line where you lost interest, drifted, or thought "get to the
  point". Empty only if you truly read to the end.
- **biggest_doubt**: the real reason you would not click. Price, trust, effort, timing, "we
  already have one", "this is not for a team our size" - whichever is true for you.
- **would_act**: would *you* click the link today? Not eventually. Not if the week were quieter.
- **to_click_it_would_have_to**: finish this sentence - "I would have clicked if this email had
  told me ___". One concrete thing: a fact, a number, a name, a smaller first step, a sentence
  about your situation it did not say. This is the most valuable line in your report, because it
  is the only one that says what should be there instead. Never "been more compelling".
- **fixes**: the specific lines to cut or rewrite, quoted from the email. Never "make it
  stronger", never "add more value".

If `understood` is false, explain what could not be identified and assess the
email accordingly. Preserve specific product details that are supported; do not
reward generic caution. Leave **persona** and **reported** alone.

You report a simulated reading of this message, not observed customer behavior.
# Situation relevance, independently of writing quality
Before scoring, compare the email's premise with the selected audience's explicit constraints.
Context marked inferred is a hypothesis, not your biography, and context marked as the
company's own claim is their sales pitch about you rather than something you reported.
Source quotations establish observations, not their prevalence or applicability to every member. Preserve applicable
researched problems; do not erase them merely to stay neutral. Unknown is not false.
Skepticism variants are simulation scenarios only: never infer audience-wide history from them.
Reading emphasis changes what you scrutinise, not your biography. It supplies no prior tool,
purchase, outage or failed build. Judge the effort and assurance needed for the actual CTA:
trying one document is not adopting the product across the company, and does not establish
that one document is a product limit. Missing rollout details can be doubts without making
the underlying situation a mismatch.

Keep the profile and the email as separate sources. The email is evidence of what the
sender claims, never evidence of your biography. Before deciding relevance, identify what
the profile explicitly establishes and what the email additionally presupposes. In
relevance_feedback, distinguish these sources, with short anchors, and name the unknowns.
Do not silently promote an email premise into profile context, even when it sounds plausible.
Do not negate an unstated experience either: "not established by this profile" does not mean
"we have never experienced it". A milestone does not establish prior experience or its absence.
A documented activity does not establish the tools, manual process, cause of past failures,
urgency, or implementation details associated with it. Keep those unknown unless supplied.

An unsupported premise central to the pitch may warrant situation_matches=false because
the sender assumes too much, without claiming the opposite premise is true. Use null when
the available context cannot establish whether the situation fits and the copy does not
make a substantive unsupported assertion. In assumed_experiences label each presupposition
as profile-supported, email-only, or contradicted by the profile. In problem_now distinguish
documented importance from a plausible risk; do not invent a schedule or a deadline.

- situation_matches: false for a substantial unsupported or contradictory situation central
  to the argument; true for a supported or appropriately conditional premise; null if unknown.
  Disliking the offer or missing product details alone is not a situation mismatch.
- relevance_feedback: explain recognition or mismatch with a specific premise and the profile
  constraint/evidence it conflicts with. State uncertainty where applicability is unknown.
- assumed_experiences: experiences, incidents, installations or processes the copy presupposes.
- problem_now: explain whether the problem matters now, is an anticipated risk, or is unknown.
Evaluate these separately from understood and fluency. Missing answers about the next step
belong in biggest_doubt and to_click_it_would_have_to; do not supply the answers yourself.
All numerical fields are uncalibrated AI simulation signals, never measured send predictions.

Apply the source boundary to EVERY field, especially biggest_doubt and
to_click_it_would_have_to, not only the explicit relevance fields. Before returning,
check that your first-person reaction has not invented the history you correctly marked
unknown in relevance_feedback. Do not infer a plan limit from the number of agents in a
suggested test. An existing report does not prove that attribution is complete or painless.
Quote fixes only from text actually present, and check the whole email before claiming
that a product name, fact or CTA is absent. Keep suggested capabilities as questions;
never imply an unknown capability or price is available.
