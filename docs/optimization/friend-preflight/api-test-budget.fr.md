# Budget API du test de Mehdi — 14 octobre 2026

Pour un test varié de cinq offres, prévoir **50–100 USD pour une première exploration légère**, ou **100–250 USD** s'il produit plusieurs séquences et variantes. Ce sont des budgets de planification, hors hébergement AWS et taxes, pas des montants déjà dépensés ni des plafonds garantis. Son compte dispose de **50 exécutions mensuelles**, partagées entre campagnes, compilations et recherches. Une exécution de campagne peut produire plusieurs emails.

## Base vérifiable

Le preset de campagne actuel route par défaut vers `gpt-5.6-sol`. Les compilations et rôles de marché utilisent leur propre routage Claude. Les tarifs suivants ont été consultés dans les pages officielles le 14 octobre 2026, traitement standard :

| Modèle utilisé par le projet | Entrée / million | Entrée en cache / million | Sortie / million |
|---|---:|---:|---:|
| GPT-5.6 Sol, contexte ≤272k | $4 | $0,40 | $20 |
| GPT-5.6 Sol, contexte >272k | $8 | $0,80 | $30 |
| Claude Sonnet 5 | $2 | $0,20 | $10 |
| Claude Opus 5 | $5 | $0,50 | $25 |
| Claude Haiku 4.5 | $1 | $0,10 | $5 |

Les écritures de cache peuvent ajouter un surcoût ; les outils web ajoutent leurs frais. La recherche web est affichée à $10 pour 1 000 recherches chez les deux fournisseurs, avec les jetons de contenu facturés en plus. Le nom court du CLI Claude peut résoudre un autre modèle que l'identifiant API fixé dans le projet : il faut lire le modèle effectif pour comparer une facture.

Sources : [modèle GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol), [tarifs OpenAI](https://developers.openai.com/api/docs/pricing), [tarifs Claude](https://platform.claude.com/docs/en/about-claude/pricing). Les tarifs peuvent changer ; aucun modèle plus récent n'a été substitué dans le calcul.

`api-cost-baselines.json` reprend quatre générations locales sauvegardées. Tous leurs appels facturables enregistrés sont sous le seuil de contexte long. Les entrées totales incluent le cache : il est soustrait avant de facturer les entrées fraîches, puis ajouté au tarif du cache.

La ligne MarketingOS ajoutée ci-dessous vient de `../marketingos-self/gpt-enriched/api-token-replay.json` : 45 appels terminés, plus grand appel enregistré 39 525 jetons d'entrée. Les 18 étapes de rôle ne représentent donc pas seulement 18 appels de modèle.

| Cas historique, mode Balanced | Emails | Appels de modèle terminés | Recalcul API avec le cache observé | Recalcul sans remise de cache |
|---|---:|---:|---:|---:|
| Buffer, email SaaS en anglais | 1 | 15 | $1,17 | $1,98 |
| Plausible, email SaaS en anglais | 1 | 22 | $1,35 | $2,38 |
| MarketingOS, pilote SaaS anglais, corpus complété | 2 | 45 | $2,71 | $5,04 |
| iFixit, email en français | 1 | 32 | $2,39 | $4,00 |
| iFixit, séquence de trois emails | 3 | 164 | $8,37 | $17,22 |

Exemple : iFixit un email a consommé 727 868 jetons d'entrée, dont 446 720 en cache, et 54 328 jetons de sortie. Recalcul : `(727868−446720)×4/1M + 446720×0,40/1M + 54328×20/1M = $2,3898`. Sans cache : `$3,9980`.

Ces consommations proviennent des CLI sur abonnement : le recalcul est un **équivalent tarifaire des jetons observés**, pas une facture API. Les API peuvent utiliser moins ou plus de jetons que les CLI, notamment en recherche et raisonnement. Les coûts affichés historiquement par l'application utilisent une table prudente plus ancienne et ne doivent pas être présentés comme la dépense réellement facturée. Les nombres d'étapes ou de rôles ne sont pas les nombres d'appels : ces derniers sont comptés dans les événements `model_call_finished`.

## Scénarios de test

| Parcours choisi | Hypothèses | Budget de planification |
|---|---|---:|
| Exploration légère | 5 offres, 1 compilation + 1 scan concurrentiel + 1 carte d'audience par offre, puis 2 campagnes d'un email par offre : environ 25 exécutions ; ordre de grandeur 250–500 appels de modèle | $50–100 |
| Test plus large | Même préparation, puis 10 campagnes de 3 emails au total : environ 25 exécutions, 30 emails ; ordre de grandeur 700–1 800 appels selon les réécritures | $100–250 |

La préparation par offre reçoit une provision indicative de $3–10 : sa consommation dépend de la taille des sources, du nombre de concurrents, des pages accessibles et du travail d'audience. C'est une hypothèse de budget, pas une moyenne API mesurée. Le test local de MarketingOS a terminé un scan en 3 min 06 (six appels logiques, estimation interne $0,936) et une carte d'audience en 11 min 51 (deux appels logiques, estimation interne $2,979), soit $3,915 pour ces deux opérations. Ces montants utilisent la table interne et les CLI sur abonnement : ils ne sont ni une facture API ni une validation de la provision pour tous les secteurs. La compilation est distincte ; les tours internes des outils web ne sont pas tous représentés par le nombre d'appels logiques.

Une utilisation des 50 exécutions majoritairement pour de longues séquences, beaucoup de sources ou le mode Maximum peut dépasser ces budgets ; prévoir plusieurs centaines de dollars. Le quota de jobs ne constitue pas une limite financière. Pour le premier essai, garder des briefs d'un email, utiliser Balanced, réutiliser la connaissance compilée et dupliquer les briefs seulement pour une comparaison utile. Remapper le marché à chaque petite retouche n'apporte pas une nouvelle preuve et refacture la recherche.

## Dépenses de cette préparation

La correction de session, la modification du quota et les contrôles de connexion n'ont fait aucun appel de modèle via API. Le test d'auto-marketing demandé est local et utilise les fournisseurs CLI sur abonnement ; sa consommation est enregistrée séparément. Les futures générations de Mehdi sur les Lambdas utiliseront les clés API de production et seront facturées par les fournisseurs.

Attention aux tentatives infructueuses : le test local MarketingOS a consommé une estimation interne de 8,5553 USD pour une tentative de deux emails sans livrable, lorsqu'une recherche complémentaire a épuisé le budget de jetons. Les fournisseurs peuvent facturer des appels même si aucune copie finale n'est livrée. Cet exemple sur abonnement n'est pas une facture API, mais confirme que le coût ne doit pas être calculé seulement à partir des emails réussis.

Une seconde tentative locale a atteint 14,9206 USD d'estimation interne pour une séquence incomplète, notamment pendant une recherche publique sur une fonction de l'application privée absente des sources. Ce cas confirme l'intérêt de fournir des documents précis et de commencer par un email. La correction des sources évite de demander à la recherche d'inventer une information interne. Ces coûts CLI ne doivent pas être transposés directement à une facture API.
