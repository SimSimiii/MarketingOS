import { BrandDirectory } from "./brand-directory";
import { api } from "@/lib/api-server";

export default async function BrandsPage() {
  const brands = await api.listBrandOverviews();
  return <BrandDirectory brands={brands} />;
}
