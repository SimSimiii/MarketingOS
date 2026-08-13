/** Mirrors the five reasoning roles in backend/app/marketing (plus the two
 * that judge the whole set). Used only for display - labels and the "not
 * started yet" roster placeholder - so a mismatch with the backend would
 * affect wording, never behavior.
 *
 * There is no registry to mirror any more: the roles are fixed by the
 * pipeline rather than looked up at runtime, which is exactly why this list
 * can be a constant. */
export interface RoleInfo {
  id: string;
  name: string;
  role: string;
}

export const ROLE_CATALOG: RoleInfo[] = [
  {
    id: "knowledge_compiler",
    name: "Knowledge Compiler",
    role: "Reads your material into facts the copy may claim",
  },
  {
    id: "strategist",
    name: "Strategist",
    role: "Decides what the campaign says, and in what order",
  },
  { id: "email_writer", name: "Email Writer", role: "Writes each email from its brief" },
  {
    id: "blind_reader",
    name: "Blind Reader",
    role: "Reads each draft cold, knowing nothing about the product",
  },
  {
    id: "conversion_critic",
    name: "Conversion Critic",
    role: "Turns what the reader felt into what to change",
  },
  {
    id: "sequence_reviewer",
    name: "Sequence Reviewer",
    role: "Reads the finished emails as one sequence",
  },
];
