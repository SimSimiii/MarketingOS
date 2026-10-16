"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Check } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api-client";
import type { Brand } from "@/lib/types";
import { refreshPage } from "@/lib/page-data";

const DEFAULT_ACCENT = "#1a56db";

/** The few things a branded email needs to look like it came from someone.
 *
 * Deliberately five fields. A full design system would be a second product,
 * and every one of these is something the owner can answer in a sentence —
 * anything left empty still renders, in the typographic tier that is the
 * right answer for cold mail anyway.
 *
 * It matters that this exists at all: the renderer has supported logos,
 * colour, buttons and footers since it was written, and until there was a
 * form for them every email the system produced came out plain because there
 * was nothing to brand it with. */
export function BrandStyleForm({ brand }: { brand: Brand }) {
  const [logoUrl, setLogoUrl] = useState(brand.logo_url ?? "");
  const [color, setColor] = useState(brand.primary_color ?? DEFAULT_ACCENT);
  const [footer, setFooter] = useState((brand.footer_lines ?? []).join("\n"));
  const [unsubscribe, setUnsubscribe] = useState(brand.unsubscribe_url ?? "");
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await api.updateBrandStyle(brand.id, {
        logo_url: logoUrl.trim() || null,
        primary_color: color.trim() || null,
        footer_lines: footer
          .split("\n")
          .map((line) => line.trim())
          .filter(Boolean),
        unsubscribe_url: unsubscribe.trim() || null,
      });
      toast.success("Saved. Branded emails for this brand will use it from the next run.");
      refreshPage();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save that");
    } finally {
      setSaving(false);
    }
  }

  const accent = /^#[0-9a-fA-F]{6}$/.test(color.trim()) ? color.trim() : DEFAULT_ACCENT;
  const footerLines = footer.split("\n").map((line) => line.trim()).filter(Boolean);

  return (
    <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
    <Card>
      <CardHeader className="pb-1">
        <CardTitle className="text-base">Email appearance</CardTitle>
        <p className="text-sm text-muted-foreground">
          Your logo, accent colour and footer for campaigns using the branded layout.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="logo">Logo URL</Label>
            <Input
              id="logo"
              placeholder="https://acme.com/logo.png"
              value={logoUrl}
              onChange={(event) => setLogoUrl(event.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Most clients block images until the reader allows them, so the brand name shows in
              its place on first open. Never let the logo be the only thing carrying the brand.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="color">Accent colour</Label>
            <div className="flex items-center gap-2">
              {/* A native colour input beside the hex: the picker is how a
                  person chooses a colour, and the field is how they paste the
                  one from their brand guide. */}
              <input
                type="color"
                aria-label="Pick the accent colour"
                value={/^#[0-9a-fA-F]{6}$/.test(color) ? color : DEFAULT_ACCENT}
                onChange={(event) => setColor(event.target.value)}
                className="size-9 shrink-0 cursor-pointer rounded-lg border border-white/10 bg-transparent p-0.5"
              />
              <Input
                id="color"
                placeholder={DEFAULT_ACCENT}
                value={color}
                onChange={(event) => setColor(event.target.value)}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Links, the button, and the rule beside a highlighted offer.
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="unsubscribe">Unsubscribe URL</Label>
          <Input
            id="unsubscribe"
            type="url"
            placeholder="https://acme.com/unsubscribe"
            value={unsubscribe}
            onChange={(event) => setUnsubscribe(event.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Required on marketing mail almost everywhere. The footer only offers it when this
            is set &mdash; a reader who clicks a dead unsubscribe presses the spam button next.
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="footer">Footer lines</Label>
          <Textarea
            id="footer"
            rows={3}
            placeholder={"Acme Ltd\n12 Example Street, Manchester M1 1AA"}
            value={footer}
            onChange={(event) => setFooter(event.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            One per line. Who is sending this, and any postal address the law where you operate
            requires on marketing mail.
          </p>
        </div>

        <div className="flex justify-end border-t border-hairline pt-4">
          <Button onClick={save} disabled={saving}>
            <Check aria-hidden="true" />
            {saving ? "Saving…" : "Save appearance"}
          </Button>
        </div>
      </CardContent>
    </Card>
    <EmailPreview
      brandName={brand.name}
      logoUrl={logoUrl.trim()}
      accent={accent}
      footerLines={footerLines}
      unsubscribe={Boolean(unsubscribe.trim())}
    />
    </div>
  );
}

/**
 * What a branded email will look like with these settings, as they are typed.
 *
 * A colour is a guess until it is seen on a button, and a footer is a guess
 * until it is seen under an email. The lines of the body are placeholders on
 * purpose: this previews the frame the brand controls, not copy nobody wrote.
 */
function EmailPreview({
  brandName,
  logoUrl,
  accent,
  footerLines,
  unsubscribe,
}: {
  brandName: string;
  logoUrl: string;
  accent: string;
  footerLines: string[];
  unsubscribe: boolean;
}) {
  const [brokenLogo, setBrokenLogo] = useState<string | null>(null);
  const showLogo = /^https?:\/\//.test(logoUrl) && brokenLogo !== logoUrl;
  return (
    <aside aria-label="Branded email preview" className="xl:sticky xl:top-6">
      <p className="mb-3 text-[0.6875rem] font-medium uppercase tracking-[0.18em] text-muted-foreground">
        Live preview
      </p>
      <div className="overflow-hidden rounded-2xl bg-[#f6f6f8] shadow-[0_30px_60px_-20px_oklch(0_0_0/70%)] ring-1 ring-white/10">
        <div className="flex items-center gap-1.5 border-b border-black/5 bg-white px-4 py-2.5">
          <span className="size-2.5 rounded-full bg-[#ff5f57]" />
          <span className="size-2.5 rounded-full bg-[#febc2e]" />
          <span className="size-2.5 rounded-full bg-[#28c840]" />
          <span className="ml-3 truncate text-[0.6875rem] text-neutral-500">Inbox · {brandName}</span>
        </div>
        <div className="p-5">
          <div className="rounded-xl bg-white p-6 shadow-sm">
            <div className="mb-5 flex h-9 items-center">
              {showLogo ? (
                // eslint-disable-next-line @next/next/no-img-element -- a user-supplied URL on any host
                <img
                  src={logoUrl}
                  alt={brandName}
                  className="max-h-9 max-w-[10rem] object-contain"
                  onError={() => setBrokenLogo(logoUrl)}
                />
              ) : (
                <span className="text-base font-semibold text-neutral-900">{brandName}</span>
              )}
            </div>
            <div className="space-y-2" aria-hidden="true">
              <div className="h-2.5 w-11/12 rounded-full bg-neutral-200" />
              <div className="h-2.5 w-full rounded-full bg-neutral-200" />
              <div className="h-2.5 w-4/5 rounded-full bg-neutral-200" />
            </div>
            <div className="my-5 border-l-[3px] py-1 pl-3" style={{ borderColor: accent }}>
              <div className="h-2.5 w-3/4 rounded-full bg-neutral-200" aria-hidden="true" />
            </div>
            <span
              className="inline-block rounded-md px-4 py-2 text-xs font-semibold text-white"
              style={{ backgroundColor: accent }}
            >
              Call to action
            </span>
            <p className="mt-4 text-xs text-neutral-500">
              Links look <span className="underline" style={{ color: accent }}>like this</span>.
            </p>
          </div>
          <div className="space-y-0.5 px-2 pt-4 text-center text-[0.6875rem] leading-relaxed text-neutral-500">
            {footerLines.length > 0 ? (
              footerLines.map((line) => <p key={line}>{line}</p>)
            ) : (
              <p className="italic text-neutral-400">Footer lines appear here</p>
            )}
            {unsubscribe && <p className="pt-1 underline">Unsubscribe</p>}
          </div>
        </div>
      </div>
    </aside>
  );
}
