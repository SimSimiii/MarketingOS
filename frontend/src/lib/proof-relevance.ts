/** Transparent word matching for browsing evidence; never a factual or fit verdict. */
export function rankForArgument<T>(items: readonly T[], argument: string, text: (item: T) => string): T[] {
  const words = (value: string) => new Set(value.normalize("NFKD").replace(/\p{M}/gu, "")
    .toLowerCase().match(/[\p{L}\p{N}]{3,}/gu) ?? []);
  const query = words(argument);
  if (!query.size) return [...items];
  const scored = items.map((item, index) => {
    const terms = words(text(item));
    return { item, index, matches: [...query].filter((word) => terms.has(word)).length };
  });
  return scored.sort((a, b) => b.matches - a.matches || a.index - b.index).map(({ item }) => item);
}
