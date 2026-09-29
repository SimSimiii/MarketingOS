import { BrandLayoutView } from "./brand-layout-view";

/**
 * One exported page per route under /brands/<id>, built for the placeholder
 * "_": brand ids cannot be known at build time. The CloudFront function in
 * frontend/template.yaml serves it for every real id, and the views read the
 * real one from the address bar - see useRouteIds in lib/page-data.
 */
export function generateStaticParams() {
  return [{ brandId: "_" }];
}

export default function BrandLayout({ children }: { children: React.ReactNode }) {
  return <BrandLayoutView>{children}</BrandLayoutView>;
}
