import assert from "node:assert/strict";
import test from "node:test";
import { rankForArgument } from "../src/lib/proof-relevance.ts";

test("relevant documented capability precedes an unrelated positive customer result", () => {
  const items = [
    { id: "outcome", claim: "A customer doubled feedback responses", verification: "quote_verified" },
    { id: "capability", claim: "Custom domains are included in the Pro plan", verification: "not_checked" },
  ];
  const ranked = rankForArgument(items, "Custom domains", (item) => item.claim);
  assert.deepEqual(ranked.map((item) => item.id), ["capability", "outcome"]);
  assert.equal(ranked[0].verification, "not_checked");
  assert.equal(items[0].id, "outcome");
});

test("empty argument and ties preserve source order; accents match without dropping unknown items", () => {
  const items = ["Rapport sans date", "Abonnement mensuel", "Domaine personnalisé"];
  assert.deepEqual(rankForArgument(items, "", String), items);
  assert.deepEqual(rankForArgument(items, "personnalise", String), [items[2], items[0], items[1]]);
  assert.deepEqual(rankForArgument(items, "inconnu", String), items);
});
