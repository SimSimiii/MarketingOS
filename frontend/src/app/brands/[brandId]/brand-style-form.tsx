"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api-client";
import type { Brand } from "@/lib/types";

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
  const router = useRouter();
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
      router.refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save that");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">How this brand&rsquo;s email looks</CardTitle>
        <p className="text-sm text-muted-foreground">
          Used when a campaign asks for the branded look. Cold sequences stay plain whatever is
          set here &mdash; a template is the tell that a message came from a marketing tool, and
          it converts worse on exactly the mail this system writes most.
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
                className="size-9 shrink-0 cursor-pointer rounded-md border border-input bg-transparent"
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

        <div className="flex justify-end">
          <Button size="sm" onClick={save} disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
