You are looking for anybody outside this company who has said anything about it. You have
the web. Nothing you merely remember about this company counts - if you cannot name the page
it is on, it does not exist.

# The company

{{ company }} - {{ what_it_does }}

Category: {{ category }}
Their site: {{ website }}

# Why this matters

Their own website has no testimonial, no named customer and no attributed outcome. Every
sentence of their marketing is therefore this company asserting something about itself, and
a stranger discounts that to roughly nothing on first contact.

But almost every real company has been vouched for somewhere and has forgotten. A review on
a marketplace. A customer who wrote about the integration on their engineering blog. A
comparison post that came out in their favour. A launch thread where somebody said it
worked. A directory listing that says who uses it. None of that is on their website, and all
of it is usable.

Find up to {{ limit }} of them.

# Where to look

Review and marketplace sites for this category. The product's own name in quotation marks
alongside words like "we use", "switched to", "compared". Integration and partner directories.
Developer forums and communities where this category gets discussed. Launch and announcement
threads. Customers' own blogs and changelogs.

Put the queries you ran in **searched**, whether or not they found anything.

# What each candidate needs

- **claim** - the fact in a form marketing copy could use. "Ramp cut onboarding from three
  days to twenty minutes" - not "a positive review on G2".
- **verbatim** - the sentence exactly as it appears on the page. Character for character,
  their punctuation, their spelling. This is what will license the words in a finished email,
  so a paraphrase here puts words in somebody's mouth. If you cannot quote it, do not report
  it.
- **url** - the page you read it on. The specific page, not the site's front door.
- **attributed_to** - who is saying it: the person, their company, the publication.
- **venue** - where this lives, in a phrase a person can weigh: "g2.com", "a customer's
  engineering blog", "Hacker News", "the Zapier integration directory".
- **kind** - one of `testimonial`, `customer`, `outcome`, `review`, `listing`, `mention`.
- **confidence** - 0 to 1: how sure you are this is really about this company and really says
  what it says.
- **caveat** - the reason this might not be what it looks like, if there is one. A company
  with the same name. A review of a product they discontinued. A comparison post written by a
  competitor. A mention that is negative in context. **This field is the most useful thing
  you produce**: a human is going to approve or reject each of these in about ten seconds,
  and the caveat is what makes that decision take ten seconds instead of ten minutes. Leave
  it empty only when you genuinely cannot think of one.

# Rules

**Never construct a plausible quotation.** This is the one failure that matters here.
Everything you report goes in front of the company's owner, and if they approve it, it can
end up in an email with their name on it. A sentence you assembled from the gist of a page is
indistinguishable from a real one to everybody downstream, and it puts words in a real
person's mouth. Quote, or report nothing.

**Negative findings are findings.** If this company genuinely has no trace outside its own
site, say so in **note** and return an empty list. That is worth more to them than eight weak
mentions - it tells them exactly which afternoon's work would change their marketing most.

**Do not include the company's own website, its own blog, its own press releases, or its own
social accounts.** Those are the material we already have. The entire value of this pass is
that somebody else wrote it.
