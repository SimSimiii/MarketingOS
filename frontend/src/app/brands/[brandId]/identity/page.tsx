import { BrandSectionHeader } from "../../brand-ui";
import { BrandStyleForm } from "../brand-style-form";
import { api } from "@/lib/api-server";

export default async function BrandIdentityPage({ params }: { params: Promise<{ brandId: string }> }) {
  const { brandId } = await params;
  const brand = await api.getBrand(brandId);
  return <div className="space-y-6"><BrandSectionHeader title="Brand identity" description="Set the visual details used in your branded emails." /><BrandStyleForm brand={brand} /></div>;
}
