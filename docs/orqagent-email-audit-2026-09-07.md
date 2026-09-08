# Audit de la génération orqAgent du 5 septembre 2026

Audit réalisé le 7 septembre 2026, par lecture SQLite en mode `ro`, sans importer l'application, modifier la base ni lancer de génération.

## Périmètre et références

- Base : `backend/marketingos.db`.
- Brand : `78013376199f464f962a44702513e895`.
- Campagne : `d64df4b040084d4b872835ab4b0e279d`, « 03/09 new ».
- Exécution : `450799812b404a1ca88472a51d2c5a57`.
- Email retrouvé à l'identique : `84664e47848c40148cefd79ac457abc7`.
- Connaissance utilisée : version 4, `928b3db8bc1e48d4bf6cb05a4536d01e`.
- Recherche audience pertinente : `ad66fb2ac83441ecb180fc3174bf8264`.
- Dossier pertinent : `ba364f881f15407495d110c49f2ee53c`.

Il s'agit d'un audit de fidélité aux documents et raisonnements enregistrés. Ce n'est pas une validation du fonctionnement réel d'orqAgent ni une nouvelle vérification des pages externes. Les documents de connaissance actuellement stockés ne constituent pas nécessairement des copies immuables à la date de génération ; les citations de la version 4 et le brief conservé permettent de retracer les affirmations centrales.

## Origine de l'argumentaire

La demande utilisateur exige un seul email de lancement, professionnel, sans hype. La description du produit est simplement « a saas ». La campagne sélectionne l'audience « Teams whose OpenAI Assistants API agents went dark on 26 August 2026 ».

L'argument du coût de sortie existe déjà dans le dossier produit/audience : « The licensed answer is exit cost, not longevity ». Il est développé par le Strategist, puis repris par le rédacteur. Il n'est pas fourni dans la demande utilisateur. L'email résulte donc du site enrichi par la recherche audience et le dossier, pas du seul site.

## Affirmations et portée

| Affirmation | Base retrouvée | Conclusion |
| --- | --- | --- |
| Changer le modèle en un champ | E143 cite la landing page : « switch models with a single field » | Fidèle à la source pour le changement de modèle dans orqAgent. |
| Agent configuré avec documents, guardrails et endpoint REST | E45 cite la documentation ; E17 établit l'appel sans SDK | Description du produit bien appuyée. |
| Compte gratuit | Les documents proposent tous une inscription gratuite | Appuyé ; ne pas en déduire des quotas précis sans résoudre les divergences. |
| Migration en un après-midi plutôt qu'une semaine | Les sources parlent d'intégration en quelques minutes et de premier appel en moins de cinq minutes ; le Strategist introduit explicitement le contraste après-midi/semaine | Extrapolation de la mise en route vers une migration complète. Pas de mesure de migration retrouvée dans les éléments examinés. |
| Repointage du client existant suffisant | E17 prouve HTTP sans SDK ; la documentation décrit un contrat propre avec `user_input`, `session_id`, `agent_response` et `X-API-Key` | Ne démontre pas la compatibilité avec le client existant. Parler d'adaptation de l'appel, pas seulement de nouvelle URL. |
| « Most teams » créent dynamiquement les assistants | Recherche : un témoignage « My application is dynamically creating Assistants » | Une pratique observée devient une majorité sans base quantitative. « If your app creates assistants dynamically » conserverait la pertinence. |
| Rien à exporter de l'autre côté | Recherche : témoignages de difficultés d'export et de lacunes d'outils | La recherche synthétise déjà ces témoignages en absence générale ; le texte renforce encore cette certitude. Ces témoignages ne suffisent pas à établir l'état exhaustif des possibilités techniques. |
| « There is no importer » | Le dossier dit qu'aucune preuve ne permet de promettre un importeur | L'absence de preuve est transformée en preuve d'absence. Décrire le parcours manuel documenté suffit. |
| « Every platform » impose son abstraction | Généralisation explicite dans le brief stratégique | Aucun inventaire exhaustif ne justifie cette universalité dans les éléments examinés. |
| Coût de sortie réduit | BYOK, HTTP, changement de modèle : bases présentes, revendication de non-dépendance sur le site | Angle plausible, mais changer de fournisseur de modèle dans orqAgent ne prouve pas la facilité de quitter orqAgent. |
| « Went dark » | Expression déjà dans l'audience sélectionnée | Ce n'est pas une personnalisation inventée uniquement par le rédacteur. L'audience demeure une hypothèse de ciblage, pas une preuve de panne chez chaque destinataire. |

## Ce que les évaluateurs avaient déjà vu

Le rapport interne indique `run_status: degraded`, `pull: 6`, `clean: true`, `landed: false`, `understood: true`, `rewrites_stopped_helping: true`. Les trois lecteurs comprennent le produit ; leurs notes sont 6, 6 et 5. Deux révisions sont rapportées et les deux challengers ont perdu leur comparaison avec la version conservée.

Le premier lecteur formule exactement la contradiction commerciale : critiquer les abstractions des plateformes puis demander d'adopter celle d'orqAgent. Les autres réclament davantage de détails sur le prix, la récupération documentaire ou la crédibilité du fournisseur. Ces avis sont simulés ; leurs estimations de clics ne sont pas des résultats réels.

La ligne d'exécution porte néanmoins `status: COMPLETED`. Ce contraste avec le rapport dégradé est constaté en base ; cet audit ne conclut pas à un bug de présentation sans examen du contrat et de l'interface.

## Autre limite des sources

Les documents stockés divergent sur les offres : la documentation mentionne trois agents et 500 runs gratuits, la tarification un agent et 100 exécutions. Le Pro est présenté avec des agents illimités dans certains documents et dix sur la page de tarification. Cela explique pourquoi demander mécaniquement davantage de chiffres pourrait dégrader la copie.

## Décision proposée

Conserver la liberté de construire un angle commercial à partir des capacités. Cibler une correction du passage recherche/dossier vers brief stratégique : ne pas convertir un témoignage en majorité, une absence de documentation en absence de fonctionnalité, ni un délai de premier appel en délai de migration complète.

Utiliser ce cas comme régression gratuite avant toute nouvelle génération : un agent configure son modèle en un champ, mais aucune compatibilité de migration ni durée totale n'est établie. Le brief doit pouvoir proposer un essai sur un assistant et ses documents sans promettre une migration transparente. Cette correction peut d'abord porter sur les consignes existantes et n'exige pas un nouvel appel de modèle.

Après cette correction ciblée, tester la répétabilité sur d'autres offres. Ce cas confirme une capacité de synthèse commerciale utile ; il ne suffit pas à établir la fiabilité générale ni la volonté de payer.
