export function customEmailRequest(count: number, brief: string): string {
  if (!Number.isInteger(count) || count < 1 || count > 12) {
    throw new Error("Choose between 1 and 12 emails.");
  }
  if (brief.trim().length < 10) {
    throw new Error("Describe what these emails should achieve (at least 10 characters).");
  }
  return `Write exactly ${count} emails.\n\n${brief.trim()}`;
}
