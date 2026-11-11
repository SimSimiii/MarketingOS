# Crisp — new-brand acceptance on v29

Protocol recorded before creation: only official name and homepage, default objective and automatic audience choice, no extra sources/facts/CTA, no override. Separately inspect all upstream stages, copy and export. Previous Help Scout failure is preserved.

Iteration 1 delivered one factually clean email, but reader pull 6/10 and needs_review=true: exact paid price missing for cost-sensitive buyer. Inspecting compiler intake identified source-order starvation: long pricing sections could not fit after customer pages consumed the compact budget. Fix compact reading to prioritize homepage/pricing and first sections across documents, retaining exact text and at most two extraction calls. Keep the original delivered run unchanged. Revalidate cold on the same homepage in a new isolated brand instance; no manual facts or URLs.
