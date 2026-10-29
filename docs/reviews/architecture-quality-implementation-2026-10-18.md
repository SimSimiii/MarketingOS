# MarketingOS — réalisation et validation, 18 octobre 2026

La refonte proposée est intégrée sur la branche `master`. Elle conserve FastAPI, SQLite,
Next.js et l'ordre des étapes piloté par le code. Les comparaisons ont conduit à ajouter
un parcours direct : pour certains emails simples, la planification et les réécritures
achetaient davantage de texte sans améliorer le résultat.

## Changements livrés

- **Intention persistante** : objectif, relation avec le lecteur, faits de l'annonce,
  raison du timing et action souhaitée. Les formulaires de création et de modification
  les conservent. Les anciennes campagnes restent lisibles ; une intention inférée
  est distinguée d'une information fournie par l'utilisateur.
- **Propositions liées aux sources** : références de problème, offre et action,
  justification du choix, destination et limites. Une paraphrase ne casse plus une
  référence valide. Les alternatives changent l'argument entier, avec son action.
  Le rejet d'un problème ne transforme plus automatiquement une annonce en campagne
  sur la première fonctionnalité et sa documentation.
- **Contrat de preuve partagé** : portée, origine, document et références arrivent
  jusqu'au dossier et aux décisions de rédaction. Un changement de métadonnées
  invalide les interprétations concernées, même si le texte est identique. Les
  historiques ne sont pas réécrits et la compilation du même texte reste réutilisable.
- **Contexte sélectionné** : citations complètes, limites des faits retenus et sources
  pertinentes sont présentées sans répéter toutes les représentations du catalogue.
  Le manifeste distingue un fait omis du contexte d'un fait absent des connaissances.
  Les extraits utiles peuvent arriver dès le premier brouillon.
- **Mesure et réparation** : les rapprochements lexicaux restent des indications ;
  ils ne bloquent plus une meilleure version. Les citations réellement dépensées
  restent protégées. Les réparations stratégiques sont bornées et les emails non
  concernés sont conservés sans nouvel appel.
- **Traçabilité** : plan brut, modifications déterministes, plan effectif, intention,
  choix d'action et limites sont enregistrés. Le rapport et l'interface montrent
  les décisions utiles et les réserves du lecteur simulé.

La nouvelle création propose **Automatic / Direct draft / Planned campaign**.
Automatic peut utiliser le parcours direct pour un email d'annonce, activation,
relance ou nurture, avec une action documentée et une destination non ambiguë.
Direct draft permet aussi les autres objectifs à un seul email, avec les mêmes
conditions. Une séquence, une destination inconnue ou une action ambiguë garde
le parcours planifié. Les anciennes politiques conservent leur comportement planifié.

Le parcours direct achète un brouillon et une lecture indépendante. Les contrôles
factuels restent actifs : un brouillon bloqué n'est pas livré. Une réserve éditoriale
est affichée sans déclencher automatiquement des réécritures. Le devis distingue ce
parcours ; avant compilation, il conserve une borne haute prudente. L'historique de
coût ne mélange plus les approches de rédaction.

## Défauts reproduits et corrigés

Le même ancien email Tally, dont le rapport comptait **8 attributions**, en compte
désormais **0** : le nom de l'expéditeur n'est plus assimilé à une attribution client.
L'ancien résultat est conservé. Voir `docs/optimization/architecture-v2/attribution-recount.json`.

Les essais ont également révélé deux défauts supplémentaires :

- `POST` pouvait être traité comme un mot crié et bloquer un email technique valide.
  Les méthodes HTTP sont désormais reconnues par ce contrôle.
- Une recherche de matériel manquant a relié la société synthétique
  `ledgerloop.example` à une vraie entreprise homonyme sur `ledgerloop.co.za`.
  La récupération vérifie maintenant les domaines établis avant la recherche,
  avant les extractions et après les redirections. Un nom identique ne suffit pas.
  Sans origine établie, elle conserve le manque et demande le site de l'entreprise.
  Les domaines réservés des fixtures ne déclenchent pas de recherche réelle.

La restriction de domaine est volontaire : un nouveau domaine de documentation ou
de partenaire doit être établi par les sources fournies avant cette récupération.
Une citation exacte sur le mauvais site ne constitue pas une preuve pour la marque.

## Comparaison qualitative

Six entrées figées : un cas Tally enregistré et cinq cas synthétiques explicitement
étiquetés. Trois de ces derniers sont réservés à la validation. Les trois approches
réutilisent les mêmes connaissances, demandes et modèle de souscription.
La référence est une archive vérifiée par SHA256. Chaque cas partage un plafond de
24 tentatives, 750 000 jetons rapportés et 1 800 secondes actives.

La référence et la proposition utilisent ici un candidat, un lecteur, un critique
et au plus une réécriture. La version simple utilise un rédacteur et un lecteur.
Ce protocole ne compare pas les presets Balanced complets. Les préférences sont
des jugements éditoriaux anonymes, avec inversion de l'ordre, sans mesure de conversion.

| Cas | Appels référence / proposé / simple | Préférence proposé contre référence | Préférence proposé contre simple |
| --- | ---: | --- | --- |
| Tally, annonce | 4 / 6 / 2 | Incomplet : référence bloquée par `POST` | Simple, deux avis concordants |
| Acquisition B2B | 6 / 4 / 2 | Proposé, deux avis concordants | Avis partagés |
| Activation | 6 / 4 / 2 | Avis partagés | Simple, deux avis concordants |
| Relance panier | 6 / 6 / 2 | Avis partagés | Simple, deux avis concordants |
| Atelier B2C | 6 / 6 / 2 | Égalité | Simple, deux avis concordants |
| Service peu documenté | 6 / 13 / 2 | Sortie proposée contaminée par l'homonyme : exclue | Comparaison interrompue au plafond : exclue |

Ces résultats motivent l'option directe. Ils ne permettent pas d'affirmer que le
nouveau parcours planifié rédige systématiquement mieux. Les sorties et échecs
d'origine sont conservés dans `docs/optimization/architecture-v2/comparisons/round2/`.
Le cas panier ne contient pas le mot « email » dans sa demande de rappel ; le
contrat parsé propose donc trois emails par défaut, alors que les trois sorties en
contiennent un. Cette ambiguïté de fixture est conservée et signalée.

Deux essais supplémentaires vérifient le **parcours direct réellement intégré**,
avec chacun un plafond de 4 tentatives, 150 000 jetons et 300 secondes :

| Cas | Appels | Jetons rapportés | Durée | Vérification |
| --- | ---: | ---: | ---: | --- |
| Activation | 2 | 44 446 | 29,92 s | Relation client, connexion du drive, recherche après indexation du premier dossier, bon lien |
| Atelier B2C | 2 | 44 121 | 29,00 s | Matériel et accompagnement inclus, travail à la main sans tour, collecte après cuisson, bon lien |

Les deux sorties passent les contrôles factuels et leur HTML a été inspecté à
1280 et 390 px, sans débordement horizontal. Les destinations des boutons ont été
vérifiées. Les lecteurs simulés restent à 6/10 et les rapports restent `degraded` :
leurs réserves ne sont pas masquées. Ils demandent notamment des précisions de
connexion ou de programme absentes des sources ; le système ne les invente pas.

Revue interne sur la grille annoncée : **88/100 pour l'activation directe**,
**89/100 pour l'atelier direct**, **86/100 pour l'acquisition B2B planifiée**.
Ce sont des appréciations argumentées du coordinateur, pas des mesures clients.
Les retouches restantes sont ordinaires : condenser les répétitions d'indexation,
resserrer le titre de l'atelier et alléger certaines formulations B2B procédurales.
Les cas appartiennent à des pistes distinctes ; ces notes ne prouvent pas un gain
chiffré par rapport à l'ancien 76/100 Tally.

Au total, le journal enregistre **117 tentatives fournisseur et 2 861 510 jetons**,
en incluant le dossier commun, le diagnostic initial exclu, les générations et
les jugements. Il s'agit de quota de souscription. Les équivalents tarifaires du
catalogue enregistrés ne sont pas présentés comme une facture API.

## Validation et installation locale

- Suite backend complète : **1 709 tests réussis**, deux avertissements de dépendances.
- Vérifications ciblées finales : **70**, puis **75**, puis **19 tests réussis**,
  avec recouvrement ; ces nombres ne s'additionnent pas à la suite complète.
- Ruff et cohérence du schéma API : réussis.
- Frontend : lint, TypeScript, **27 tests** et build statique réussis.
- Migration testée sur base jetable, puis sur copie des données locales.
- Formulaire contrôlé sur ordinateur et mobile ; les requêtes de création de cette
  vérification ont été interceptées, sans création de campagne ni génération.

La base locale est migrée jusqu'à `c53a9f27d401`. Son ancien état mélangeait des
tables récentes et huit colonnes de suivi manquantes. Le script a réconcilié les
colonnes, vérifié la correspondance de schéma avant le stamp, puis appliqué les
migrations. Les lignes et valeurs préexistantes ont été vérifiées inchangées.
Sauvegarde : `backend/backups/marketingos-before-architecture-v2-20261017T190950Z.db`.
Audit : `docs/optimization/architecture-v2/local-migration.json`.

## Portée de la conclusion

L'implémentation et les défauts déterministes reproduits sont validés. Les deux
cas directs et le cas B2B donnent des textes utilisables après une revue de marque
ordinaire. Cela valide ces usages observés, pas une qualité universelle.
Les essais ne démontrent ni une conversion future, ni la justesse de toute
affirmation sémantique possible. Une vraie annonce Tally doit préciser ce qui est
nouveau ; une offre de service peu documentée doit fournir sa portée réelle.
Le système conserve ces inconnues au lieu de les combler par des promesses.

Aucun email n'a été envoyé et aucun déploiement de production n'a été effectué.
Les modifications locales antérieures ont été conservées, sans changement de branche.
