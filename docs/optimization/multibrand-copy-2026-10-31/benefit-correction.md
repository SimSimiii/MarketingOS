# Correction de l'exploitation des bénéfices — 31 octobre 2026

La correction rend les mécanismes documentés plus visibles sur Papier et systeme.io. Elle ne rend pas une offre adaptée lorsque la preuve manque : CABAIA reste insuffisant pour le besoin ordinateur + repas + gourde. Le verdict global reste celui d'un produit utilisable avec accompagnement et relecture, pas d'une génération autonome garantie.

## Modification

Le brief conserve désormais un `value_case` facultatif : mécanisme concret, conséquence utile pour le lecteur, identifiants des preuves et conditions qui changent la décision. Ce sont des interprétations à vérifier dans les citations, pas de nouvelles preuves. Aucun paramétrage utilisateur obligatoire, aucun nouvel appel modèle.

Ce bloc suit les alternatives, les réécritures et les retouches après génération. Il disparaît du contexte utilisable si une preuve nécessaire est exclue ou si le système retire la prémisse non étayée. Les anciens briefs restent lisibles sans migration. Le rédacteur et le critique distinguent les conditions nécessaires des interdictions internes qui n'ont pas à devenir des listes de réserves publiques.

Un faux positif de répétition découvert pendant l'essai a aussi été corrigé : la déclaration fermée « Je vous écris comme partenaire affilié indépendant de systeme.io, et non au nom de la marque » peut se répéter. Le reste du paragraphe et les promesses répétées restent contrôlés. Aucun contrôle factuel n'est assoupli.

## Comparaison sur les mêmes entrées

Même base copiée, mêmes campagnes, audiences, connaissances et modèle `gpt-5.6-sol`. Aucune preuve ajoutée manuellement. Les connaissances ne sont pas recompilées. Les plafonds existants de chaque génération restent de 900 secondes et 400 000 tokens. Les scores ci-dessous sont des jugements éditoriaux internes, pas des performances de conversion ni une évaluation statistique.

| Cas | Avant | Après, version finale | Limite restante |
| --- | --- | --- | --- |
| Papier | 83/100 ; argument assez abstrait autour de 16 semaines | 86/100 ; lien concret entre décomposition de l'objectif et pages mensuelles, hebdomadaires et quotidiennes | Angle encore prudent ; aucune donnée d'acheteur réel |
| systeme.io | 76/100 ; périmètre et exclusions dominent | 81/100 ; 3/3 emails, parcours fiche produit → paiement → commande expliqué | Statut éditorial toujours `degraded`, lecteurs simulés à 6/10 ; migration encore très centrée sur les limites |
| CABAIA | 62/100 ; poche ordinateur prouvée, chargement complet inconnu | 62/100 ; limite maintenue, aucune capacité complète inventée | Toujours non vendable pour le besoin complet sélectionné ; cas de découverte explicitement forcé |

Exemple systeme.io, avant : « Le périmètre est précis : systeme.io n’est pas conçu pour les grandes boutiques… », suivi d'une invitation à comparer ce périmètre.

Après : « vous créez la fiche du livre, l’ajoutez à une étape de tunnel ou à une page de site, puis le client accède à la page de paiement ». Le texte décrit ensuite la commande dans le tableau de bord. Ces opérations figurent dans la citation complète d'E95, même si son résumé concerne surtout Stripe. E72 étaye l'absence de boutique séparée. L'organisation de l'emballage et de l'expédition reste à la charge du vendeur dans le texte.

Papier conserve E73/E74/E464 et le même CTA « Look inside ». systeme.io conserve une mention d'affiliation dans chaque email ; la phrase imposée à l'email 2 ne figure que dans cet email. Son troisième corps atteint exactement 150 mots au comptage par espaces : la consigne libre « sous 150 » n'est donc pas strictement satisfaite, même si aucun contrôle déterministe n'échoue. Cette limite est conservée dans l'évaluation, pas masquée.

## Retouches réelles

- Papier : 106 → 89 mots de corps, un appel. La décomposition du projet et les trois horizons de planification restent présents ; contrôles sans problème.
- systeme.io, email 1 : 138 → 103 mots, un appel. Le parcours produit/paiement/commande, l'affiliation et les limites restent présents. Aucun blocage ; avertissement non bloquant sur le libellé du CTA, dont la destination est bien sourcée.

Les deux propositions restent en état `proposed` dans la base de test, avec leurs originaux. Les contrôles sont recalculés ; aucun verdict de lecteur ancien n'est réutilisé comme évaluation de la proposition.

## Essais intermédiaires et coût

Le premier correctif structuré seul était insuffisant : Papier s'améliorait modestement ; systeme.io restait général et ne livrait que 1/3 emails à cause du faux positif d'affiliation. Une seconde itération explicite les opérations concrètes et corrige ce faux positif. Les dossiers `*-benefit` conservent les résultats intermédiaires ; `*-benefit-v2` contient les résultats finaux. Aucun échec n'est remplacé par un meilleur snapshot.

Six générations et deux retouches : **42 appels réels terminés**, zéro retry de transport. Une réparation de format a été nécessaire sur CABAIA final. Un précontrôle CABAIA a également refusé le lancement avant tout appel, à cause d'une comparaison d'UUID dans le script d'audit ; corrigé et conservé dans `preflight-block.json`.

Estimation interne des six générations : **7,4604 USD**, hors deux retouches. Ce n'est pas un montant facturé : les appels utilisent l'abonnement CLI. Détail des appels, durées et statuts : `benefit-metrics.json`. La modification n'ajoute aucun rôle ni tour obligatoire ; les nombres de réécritures varient selon les sorties.

## Validation

- Backend : 2 112 tests réussis, deux avertissements de dépendances ; Ruff réussi. Les neuf tests du bénéfice ont aussi été rejoués après la dernière assertion de conservation du mécanisme.
- Frontend : lint, TypeScript et 34 tests réussis ; contrat API à jour.
- HTML : contrôle Chromium à 390 et 1 280 px, aucune largeur débordante. Captures et liens conservés ; revue visuelle des rendus représentatifs. Pas de validation exhaustive des clients mail.
- Branche courante conservée ; aucun déploiement, aucun envoi, générations dans la copie SQLite d'audit.

Le défaut est réduit et la correction est couverte par des tests. Les résultats ne justifient pas une promesse « vendable sans limites » : des réserves restent parfois trop présentes, et une meilleure rédaction ne remplace pas une preuve d'adéquation absente.
