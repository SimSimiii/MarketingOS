# Relecture des premiers résultats MarketingOS

## Canny — Intercom

La suite capture, extraction, regroupement et triage répond au brief. Le bouton visible cite Intercom mais son attribut HTML ouvre la page des prix. L’export texte affiche également la page des prix comme destination finale. Le rapport avait identifié un CTA sans destination vérifiée avant l’export. Le brouillon demande deux retouches locales pour être prêt. [HTML exporté](canny-intercom/marketingos-1.html), [rapport de génération](canny-intercom/result.json), [intégration officielle](https://canny.io/integrations/intercom).

- Remplacer « Autopilot then merges detected duplicates. Repeated requests are consolidated before the feedback is triaged to the appropriate team. » par « Autopilot flags likely duplicates. Depending on your settings, your team can review the suggestions or let Autopilot merge them. » Cela évite de présenter la fusion comme automatique dans toute configuration. [Aide Autopilot](https://help.canny.io/en/articles/8202451-autopilot).
- Aligner le bouton et le lien sur [See how to connect Intercom](https://canny.io/integrations/intercom).

## Canny — fusions

L’email exporté reprend la lacune des sources dans le corps. Il renvoie aux prix au lieu d’expliquer comment le lecteur peut examiner les doublons suggérés. Il faut remplacer l’argument, le préheader et la destination. La réécriture indépendante est la même pour les deux outils, à partir de la page d’aide ajoutée à la relecture. [HTML exporté](canny-review/marketingos-1.html), [texte corrigé](chatgpt-review.md#canny--fusions), [aide Autopilot](https://help.canny.io/en/articles/8202451-autopilot).

## Bannerbear — variantes

Le texte conserve bien le modèle unique et les deux entrées. Il passe directement à la requête HTTP et nomme `IMAGE_DATA`, un exemple qui ne dit pas comment le marketeur choisit les champs à modifier. Le lien vers la référence API est valide, mais le guide de première prise en main correspond mieux au public et à l’action. Deux retouches locales rendent le brouillon exploitable. [HTML exporté](bannerbear-variants/marketingos-1.html), [Image API](https://www.bannerbear.com/v5/products/image-api/), [premiers pas](https://www.bannerbear.com/v5/help/getting-started/).

- Remplacer le paragraphe de la requête par « Choose one product-banner template and decide which layers should change, such as the product name and image. Render once with the first product’s details, then render again with the same template and the second product’s details. The other layers keep their original values. »
- Remplacer la phrase et le bouton qui renvoient à la référence API par [See how to make your first banner](https://www.bannerbear.com/v5/help/getting-started/).

## Bannerbear — crédits

Le calcul de base est juste et le texte donne un repère utile sur les 30 crédits, à condition de conserver l’échelle et d’écarter les autres opérations qui consomment des crédits. Le préheader doit rendre cette condition visible. Le bouton d’inscription détourne le lecteur de l’étape d’évaluation. Deux retouches locales suffisent. [HTML exporté](bannerbear-credits/marketingos-1.html), [FAQ des crédits Bannerbear](https://www.bannerbear.com/pricing/).

- Préheader corrigé : « At scale 1, budget one base credit for JPG or two for JPG plus PNG. »
- Remplacer le bouton d’inscription par [Review the credit calculation](https://www.bannerbear.com/pricing/).
