import { redirect } from "next/navigation";

export default async function LinkedInPage({ params }: { params: Promise<{ brandId: string }> }) {
  const { brandId } = await params;
  redirect(`/brands/${brandId}`);
}
