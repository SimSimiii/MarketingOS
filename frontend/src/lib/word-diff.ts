/** One run of text in a diff: kept, added by the proposal, or removed from
 * the version it was asked of. */
export interface DiffPart {
  kind: "same" | "added" | "removed";
  text: string;
}

/** Above this many token pairs the table stops being cheap. An email is a
 * few hundred words, so this only trips on something that is not one - and
 * then the diff degrades to whole lines rather than freezing the page. */
const MAX_CELLS = 400_000;

function tokens(text: string): string[] {
  // Words with their trailing whitespace, so joining the parts back
  // together reproduces the text exactly, line breaks included.
  return text.replace(/\r\n/g, "\n").match(/\S+\s*|\s+/g) ?? [];
}

function lines(text: string): string[] {
  return text.replace(/\r\n/g, "\n").match(/[^\n]*\n|[^\n]+/g) ?? [];
}

/**
 * What changed between two versions of an email, word by word.
 *
 * A longest-common-subsequence table rather than a library: the inputs are
 * one email each, the output is three kinds of span, and the whole thing is
 * small enough to test by hand. Adjacent parts of one kind are merged so the
 * page renders a phrase as one highlight rather than as a run of words.
 */
export function diffWords(before: string, after: string): DiffPart[] {
  let a = tokens(before);
  let b = tokens(after);
  if (a.length * b.length > MAX_CELLS) {
    a = lines(before);
    b = lines(after);
  }
  const rows = a.length + 1;
  const cols = b.length + 1;
  const table = new Uint32Array(rows * cols);
  for (let i = a.length - 1; i >= 0; i -= 1) {
    for (let j = b.length - 1; j >= 0; j -= 1) {
      table[i * cols + j] = a[i].trim() === b[j].trim()
        ? table[(i + 1) * cols + j + 1] + 1
        : Math.max(table[(i + 1) * cols + j], table[i * cols + j + 1]);
    }
  }
  const parts: DiffPart[] = [];
  const push = (kind: DiffPart["kind"], text: string) => {
    const last = parts[parts.length - 1];
    if (last && last.kind === kind) last.text += text;
    else parts.push({ kind, text });
  };
  let i = 0;
  let j = 0;
  while (i < a.length && j < b.length) {
    if (a[i].trim() === b[j].trim()) {
      push("same", b[j]);
      i += 1;
      j += 1;
    } else if (table[(i + 1) * cols + j] >= table[i * cols + j + 1]) {
      push("removed", a[i]);
      i += 1;
    } else {
      push("added", b[j]);
      j += 1;
    }
  }
  while (i < a.length) push("removed", a[i++]);
  while (j < b.length) push("added", b[j++]);
  return parts;
}

/** Words added and removed, for a one-line summary beside the diff. */
export function diffStats(parts: DiffPart[]): { added: number; removed: number } {
  const count = (kind: DiffPart["kind"]) =>
    parts.filter((part) => part.kind === kind)
      .reduce((total, part) => total + (part.text.match(/\S+/g)?.length ?? 0), 0);
  return { added: count("added"), removed: count("removed") };
}
