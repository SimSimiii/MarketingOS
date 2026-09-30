/** An email as the tool it is pasted into wants it: three fields, not one. */
export interface EmailParts {
  subject: string;
  preview: string;
  body: string;
}

const SUBJECT = "Subject: ";
const PREVIEW = "Preview text: ";

/**
 * Split a plain-text email into subject, preview line and body.
 *
 * The backend labels the first two lines (`render_plain` in
 * app/marketing/email_copy.py) because every sending tool has a field for
 * each - so copying the whole block meant pasting it, then cutting two lines
 * back out of the body and into their own boxes. Returns null for anything
 * not in that shape, which the caller shows whole, as before.
 */
export function splitEmail(content: string): EmailParts | null {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  if (!lines[0]?.startsWith(SUBJECT) || !lines[1]?.startsWith(PREVIEW)) return null;
  const body = lines.slice(2).join("\n").replace(/^\n+/, "").trimEnd();
  if (!body) return null;
  return {
    subject: lines[0].slice(SUBJECT.length).trim(),
    preview: lines[1].slice(PREVIEW.length).trim(),
    body,
  };
}
