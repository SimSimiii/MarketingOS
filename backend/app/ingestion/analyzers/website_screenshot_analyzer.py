from app.ingestion.analyzers.image_analyzer import ImageAnalysisResult, ImageAnalyzer
from app.ingestion.assets.base import Asset
from app.ingestion.documents import KnowledgeDocument

_HERO_KEYWORDS = ("hero",)
_NAV_KEYWORDS = ("nav", "navigation", "menu")
_CTA_KEYWORDS = ("cta", "call-to-action", "call to action", "button")
_CHROME_KEYWORDS = _NAV_KEYWORDS + ("footer", "header")


class WebsiteScreenshotAnalysisResult(ImageAnalysisResult):
    """Adds structural, still-purely-factual fields specific to a webpage
    screenshot on top of the generic image analysis result."""

    hero_present: bool
    navigation_present: bool
    cta_present: bool
    marketing_sections: list[str]
    typography: list[str] | None = None


class WebsiteScreenshotAnalyzer(ImageAnalyzer):
    """Analyzes a webpage screenshot for structure: hero/nav/CTA presence and
    marketing sections. Built entirely on VisionProvider.describe_layout()'s
    region labels - no new vision capability, no strategic/quality judgment
    about the page, only structural detection."""

    output_schema = WebsiteScreenshotAnalysisResult

    async def analyze(self, asset: Asset, content: bytes) -> list[KnowledgeDocument]:
        [document] = await super().analyze(asset, content)
        regions = document.metadata.get("layout", [])
        lowered_regions = [region.lower() for region in regions]

        hero_present = any(any(kw in region for kw in _HERO_KEYWORDS) for region in lowered_regions)
        navigation_present = any(any(kw in region for kw in _NAV_KEYWORDS) for region in lowered_regions)
        cta_present = any(any(kw in region for kw in _CTA_KEYWORDS) for region in lowered_regions)
        marketing_sections = [
            region
            for region, lowered in zip(regions, lowered_regions, strict=True)
            if not any(kw in lowered for kw in _CHROME_KEYWORDS)
        ]
        layout_details = document.metadata.get("layout_details")
        typography = layout_details.get("typography") if isinstance(layout_details, dict) else None

        document.metadata.update(
            {
                "hero_present": hero_present,
                "navigation_present": navigation_present,
                "cta_present": cta_present,
                "marketing_sections": marketing_sections,
                "typography": typography,
            }
        )
        return [document]
