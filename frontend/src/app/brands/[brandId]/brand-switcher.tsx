"use client";

import { usePathname, useRouter } from "next/navigation";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Brand } from "@/lib/types";

/** Move between businesses without leaving the section you were reading.
 *
 * Switching swaps the brand segment of the current path and keeps the rest,
 * so somebody comparing two markets lands on the other brand's market rather
 * than on its overview. */
export function BrandSwitcher({ brand, brands }: { brand: Brand; brands: Brand[] }) {
  const router = useRouter();
  const pathname = usePathname();

  if (brands.length < 2) return null;

  return (
    <Select
      value={brand.id}
      onValueChange={(value) => {
        if (!value || value === brand.id) return;
        router.push(pathname.replace(`/brands/${brand.id}`, `/brands/${value}`));
      }}
    >
      <SelectTrigger className="w-56" aria-label="Switch brand">
        {/* Base UI renders the raw value unless it is told how to label one,
            and a UUID is not a brand name. */}
        <SelectValue>
          {(value: string) => brands.find((option) => option.id === value)?.name ?? brand.name}
        </SelectValue>
      </SelectTrigger>
      <SelectContent>
        {brands.map((option) => (
          <SelectItem key={option.id} value={option.id}>
            {option.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
