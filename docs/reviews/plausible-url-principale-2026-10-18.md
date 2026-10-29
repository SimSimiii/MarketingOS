# Plausible Analytics — audit réel depuis la seule URL principale

**Parcours complet terminé, avec une correction mesurée du dossier et de l’email.**
Date : 18 octobre 2026. Entrée unique : https://plausible.io/.
Aucun texte commercial, guide, URL d’aide, concurrent, problème ou CTA n’a été ajouté
manuellement aux entrées du générateur. Les consultations indépendantes servent au
contrôle. Deux exécutions ont produit chacune un email ; aucun email n’a été envoyé.

Le quota Claude a permis la reprise au scan d’audiences. La knowledge et le marché
persistés ont été réutilisés. Les opérations passent par les API de l’application,
pas par des clics dans chaque écran : cet audit valide les traitements et les sorties,
pas l’ergonomie de tous les boutons. Le nom de la marque de test a seulement été
remis à son nom officiel par l’ORM, faute de route de renommage ; sources inchangées.

## Bilan par étape

| Étape | Résultat contrôlé | Évaluation |
| --- | --- | --- |
| Import initial | 11 pages, 22 717 mots ; `/docs` présent, aucun guide interne suivi | Défaut reproduit : crawl limité au premier niveau |
| Import corrigé | 12 pages, 12 040 mots, dont sept guides découverts depuis `/docs` | Meilleure couverture utile, avec un budget borné ; pas une lecture exhaustive |
| Knowledge corrigée | 335 faits ; tous les verbatims retrouvés dans les sources stockées ; un candidat rejeté | Bonne traçabilité, mais montants absents de la fiche d’offre malgré leur présence dans la source et le ledger |
| Positioning / Competitors | Six alternatives pertinentes ; cinq sites lus ; 269 comparaisons inconnues et sept différences potentielles | Partiel : repérage utile, justifications concurrentielles encore fragiles |
| Audiences | Sept segments, dix pages contrôlées ; première audience conservée : équipes web du secteur public EU/UK | Usage réel trouvé, mais achat non établi et catalogue produit inadapté |
| Recherche de cette audience | Dix sources, cinq problèmes conservés, cinq éléments rejetés | Citations utiles ; les cinq problèmes reposent sur un seul article de 2023, dont la date n’est pas conservée |
| Dossier v1 | 30 faits ; trois réponses partielles, deux problèmes non couverts ; `GO_NARROW` | Défauts de sélection, de priorisation et de troncature reproduits |
| Dossier v2 corrigé | 30 faits, aucun rejet ; mécanismes de confidentialité en tête, phrases complètes, réserves temporelles explicites | Amélioration vérifiée ; périmètre toujours limité aux équipes gouvernementales nationales/décentralisées |
| Email final | Un email anglais, CTA unique, démo publique accessible sans compte ; rendu navigateur 1280/390 vérifié | Brouillon de découverte utilisable après revue ordinaire ; réserves de l’application conservées |

## Ce que le système lit réellement

Le crawler initial s’arrêtait après les liens de l’accueil. La correction suit une
frontière priorisée jusqu’à deux niveaux, avec le même budget de douze pages et
une concurrence bornée. Les URL finales et la page de découverte sont conservées.
Les redirections externes ne deviennent pas des sources de la marque.

Le corpus corrigé contient notamment les plans, l’essai, le script d’installation,
les intégrations, SSO, 2FA et la sécurité. Il a retrouvé les quatre plans et les
conditions de l’essai. Les 335 citations conservées ont été contrôlées contre les
textes importés. Cela établit la provenance, pas la vérité indépendante de chaque
promesse du fournisseur. Le digest utilisé pour profiler l’offre coupe encore
l’accueil avant les prix : les montants du ledger ne remontent pas dans la fiche
commerciale. Ce défaut reste ouvert.

## Marché et audiences : réserves concrètes

Positioning et Competitors déclenchent le même scan : il n’a été lancé qu’une fois.
Les alternatives sont GA4, Fathom, Simple Analytics, Matomo, PostHog et Umami.
L’URL applicative GA4 n’a pas fourni de texte lisible, sans repli marketing/docs.
Les justifications brutes du scout ne sont pas toujours réconciliées avec les pages :
le contraste tarifaire Fathom est trompeur, et présenter funnels/segments comme
une différence Matomo ignore leur présence chez Plausible. Des délais de politique
SSO/quota sont aussi classés comme « vitesse ».
Sources de contrôle : [tarifs Fathom](https://usefathom.com/pricing),
[fonctions Plausible](https://plausible.io/features).
La carte conserve heureusement beaucoup d’inconnus plutôt que d’affirmer une supériorité.

La première audience a des acheteurs, situations et signaux observables. Les pages
[mygov.scot](https://www.mygov.scot/cookies) et
[GOV.WALES](https://www.gov.wales/details-about-cookies-govwales) déclarent Plausible
aux côtés d’autres outils. Cela ne démontre ni un remplacement complet ni un achat
Cloud payant. Le catalogue automatique, encore orienté agents IA, dérive à tort
« knowledge base » d’une intégration HelpDocs et « agent API keys » de limites API
génériques. Les sept listes de capacités requises restent vides. Ce défaut transversal
n’a pas été corrigé en remplissant manuellement le cas Plausible.

La recherche approfondie concentre ses cinq problèmes sur un
[article GDS du 27 mars 2023](https://gds.blog.gov.uk/2023/03/27/sharing-data-and-lessons-from-our-google-analytics-4-upgrade/).
La synthèse initiale le décrit au présent, sans date de publication ni avertissement.
Cinq problèmes ne sont donc pas cinq corroborations indépendantes. Le dossier corrigé
qualifie explicitement cette ancienneté, mais l’extraction de dates reste à corriger.

## Correction et comparaison des emails

Le premier email utilisait un avis SEO avant d’expliquer qu’il ne prouvait pas
l’adéquation au secteur public. Sa démo était réelle, mais son argument faible.
Trois causes ont été isolées avant modification :

- Une intégration préférée rendait obligatoires toutes les réserves des autres
  intégrations de la même page. La sélection dépassait son budget et écartait les
  mécanismes produit pertinents. Les réserves respectent maintenant leur sujet explicite.
- Le dossier coupait aux trente premières entrées avant de regarder la priorité.
  LEAD/SUPPORT et les décisions WITHHOLD sont désormais préservées avant le contexte.
- Les explications étaient coupées au milieu de clauses. La première phrase complète
  est conservée ; une sortie pathologiquement longue est rejetée plutôt que tronquée.

Le prompt distingue aussi une omission de sélection d’une absence de capacité et
part du besoin explicite de l’audience avant un groupe de plaintes issues d’une source.
Aucun appel modèle n’a été ajouté. Quatre tests de régression couvrent ces frontières,
dont la conservation des limites du même sujet. La version d’interprétation du dossier
est passée à 5 pour rendre les anciens dossiers obsolètes.

| Contrôle | Premier email | Email après correction |
| --- | --- | --- |
| Argument | Opinion SEO peu pertinente | Absence de cookies/identifiants persistants, données sources/pages/objectifs consultables |
| Preuves dépensées détectées | Aucune ; faux négatif sur une paraphrase attribuée | E261 et E324 |
| Appels modèle terminés (compteur rectifié) | 38 | 26 |
| Durée d’exécution | 8 min 13 s | 4 min 05 s |
| Jetons entrée + sortie rapportés | 1 050 122 | 591 489 |
| Lecture simulée | 6/10 | 6/10 |
| Jugement interne du coordinateur | 74/100 | 85/100 |

La comparaison garde la même marque, le même corpus, la même audience, la même
recherche et la même demande. Le dossier est la variable corrigée ; une seule paire
observée ne garantit pas une baisse reproductible de coût ou de durée.

La grille interne est stable : faits 25, audience/offre 20, spécificité 20,
continuité objet/texte/CTA 15, finition/rendu 10, absence de promesses non soutenues
et répétition 10. Scores : 24/16/7/9/9/9 puis 24/18/13/13/8/9. C’est un jugement
éditorial informé, pas une mesure client ou une prédiction de conversion.

Le second email est un premier contact clair et utilisable après personnalisation
et revue de marque ordinaires. Il reste formel et un peu répétitif. Les lecteurs
simulés demandent un accès plus direct aux justificatifs techniques/juridiques :
cette réserve reste visible. L’API dit `completed`, mais le pipeline dit `degraded`,
avec `needs_review=true` et `landed=false`. Ces états n’ont pas été modifiés pour
faire apparaître le test comme réussi. Le seuil du coordinateur pour un brouillon
de découverte est atteint ; l’application ne le déclare pas prêt à envoyer.

Le rendu a été inspecté dans un navigateur, pas dans tous les clients email.
La destination a été ouverte réellement : tableau de bord avec données, sans
connexion obligatoire. Aucun résultat de conformité n’a été promis au destinataire.

## Quota, tests et suites utiles

L’audit complet représente **107 appels modèle terminés et 3 814 593 jetons rapportés**,
diagnostic initial et comparaison inclus, plus une tentative antérieure refusée au
quota dont les jetons ne sont pas disponibles. Le cas corrigé seul compte 88 appels,
avec ses deux dossiers et ses deux emails. Ces compteurs incluent les lectures
cachées selon le reporting des fournisseurs ; ce ne sont ni des jetons tous nouveaux,
ni une facture API. Le coût en quota reste important pour un seul parcours.

Compteurs rectifiés le 18 octobre : les anciens 17/9 comptaient des groupes d'agents,
pas les appels modèle individuels. Le recompte des événements `model_call_finished`
donne 38/26 ; leurs sommes de jetons correspondent aux totaux déjà publiés. Les
copies et leurs scores éditoriaux restent inchangés. Le suivi des nouvelles
corrections est séparé dans [le rapport de fiabilité](plausible-fiabilite-2026-10-18.md).

**1 720 tests backend passent**, plus Ruff `app tests` propre et vérification du diff.
Les 38 tests ciblés passent. Deux avertissements de dépendances demeurent.
Aucun frontend modifié pendant cette reprise. Les modifications restent sur `master`,
sans commit ni envoi.

Les priorités restantes sont : catalogue de capacités général et correctement attribué ;
dates/actualité et corroboration de recherche ; sections tarifaires du digest ;
réconciliation des justifications concurrentielles. Le test ne valide pas le système
pour toutes les marques et ne démontre aucune conversion réelle. Aucun nouveau run
payant n’est nécessaire pour conclure ce cas.

## Livrables et reprise

[Email final HTML](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/plausible-root-url/after-crawler-fix/runs/8ff9a800-0e38-4ada-80ae-36869fca4544/email-1.html) · [Texte final](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/plausible-root-url/after-crawler-fix/runs/8ff9a800-0e38-4ada-80ae-36869fca4544/email-1.txt) · [Rendu mobile](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/plausible-root-url/after-crawler-fix/runs/8ff9a800-0e38-4ada-80ae-36869fca4544/email-390.png)

[Comparaison complète](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/plausible-root-url/after-crawler-fix/compare-9c56d23a-8ff9a800.json) · [Dossier v2](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/plausible-root-url/after-crawler-fix/dossier-v2-full.json) · [État durable](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/plausible-root-url/after-crawler-fix/state.json) · [Journal](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/plausible-root-url/after-crawler-fix/journal.md)

[Procédure réutilisable](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/operations/brand-audit.md) · [Compteurs détaillés](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/plausible-root-url/usage-summary.json)

L’API d’audit corrigée est sur **http://localhost:8003**, renseigné dans le cas.
Le runner doit recevoir `--base-url http://localhost:8003`. Les anciens serveurs
n’ont pas été arrêtés après un refus antérieur du contrôle automatique. Le frontend
existant garde sa cible de proxy : ne pas confondre son ancien backend avec cette
instance corrigée. Les réponses et statistiques terminales de chaque étape sont
sauvegardées ; les registres de jobs restent locaux au processus.
