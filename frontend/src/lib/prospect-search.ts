import type { LinkedInSearchRequest, MappedSegment } from "./types";

export interface ProspectSearchFilters {
  target: "companies" | "people" | "venues";
  source: "web" | "linkedin";
  query: string;
  roles: string;
  industries: string;
  companySizes: string;
  geographies: string;
  languages: string;
  signals: string;
  exclusions: string;
  limit: number;
}

function list(value: string): string[] {
  return [...new Set(value.split(",").map((item) => item.trim()).filter(Boolean))];
}

/** Consumer audiences are searched through public reach channels. Company-level
 * research signals stay optional: a profile cannot prove a private buying need. */
export function prospectSearchRequest(
  segment: MappedSegment,
  filters: ProspectSearchFilters,
): LinkedInSearchRequest {
  const venues = filters.target === "venues";
  return {
    segment_name: segment.name,
    query: filters.query.trim() || segment.name,
    target: filters.target,
    source: venues ? "web" : filters.source,
    limit: filters.limit,
    criteria: {
      roles: venues ? [] : list(filters.roles),
      industries: list(filters.industries),
      company_sizes: venues ? [] : list(filters.companySizes),
      geographies: list(filters.geographies),
      languages: list(filters.languages),
      profile_signals: list(filters.signals),
      corroboration: venues ? [] : segment.signals.slice(0, 10),
      exclusions: list(filters.exclusions),
      rationale: "",
      basis: `Audience: ${segment.name}; edited before search`,
    },
  };
}
