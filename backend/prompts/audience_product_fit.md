Reassess product requirements for the existing audience candidates below.
Only the product catalogue has changed. No web tools or new market evidence are available.

## Existing audiences and their evidence
{{ candidates }}

## Current product catalogue
{{ capabilities }}

For each candidate return its zero-based candidate_id, the current capability IDs
needed for its stated workflow and need, and a short reason. Old IDs are references
from an earlier extraction, not evidence that the product stopped supporting a function.
Use current IDs only. Include unknown or unsupported capabilities when they are
necessary; never remove an explicit structural requirement because it would make
the audience incompatible. When nothing in the catalogue maps to the requirement,
return an empty list and explain the missing support.

The earlier capability list is an inferred mapping, not a new user constraint.
Do not require every adjacent feature merely because the previous model listed it.
Identify the minimum product support needed for the existing, unchanged workflow.
Preserve platform, operational and hard exclusion constraints. A related feature
is not evidence that a required function or outcome is supported. Plan conditions,
source qualifications and limitations in the catalogue still apply.

Do not invent audiences, rename them, change their need, rewrite market evidence,
assume a purchase, or return new capability descriptions or claims.
