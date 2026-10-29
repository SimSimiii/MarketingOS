# Validation multi-marques — 26 octobre 2026

**Reprise en cours le 26 octobre, après rétablissement du quota. Confirmation commerciale toujours en attente des quatre parcours.** Les anciens échecs de quota restent archivés. systeme.io a recompilé les sources corrigées (v2, 118 faits, neuf appels) et son scan est lancé. CABAIA termine sa compilation ; aucun nouvel email n’est encore noté.

Objectif : décider si un ami exerçant dans l'e-commerce et l'affiliation peut tester une bêta accompagnée. Quatre marques nouvelles et deux langues ; cela ne démontre ni une compatibilité universelle, ni la conversion réelle, ni la volonté de payer.

## Protocole

Voir `protocol.json`. Une seule homepage par marque, aucun fait ni lien utile ajouté au générateur, première audience exacte, stratégie auto, un email, preset balanced. Aucun email envoyé. Au plus deux jobs modèles simultanés.

Le seuil fixé avant les résultats exige au moins trois cas utiles sur quatre, dont un e-commerce physique et la promotion par un affilié indépendant. Un cas utile exige un email évalué à 85/100 minimum, des étapes amont utiles et sourcées, un rendu ordinateur/mobile et un CTA vérifiés. Une réserve matérielle n'est pas effacée par une bonne note d'email.

## Défaut trouvé avant les parcours complets

Les formulaires d'achat étaient supprimés avec leur contenu : le prix de 45 € du lunch bag CABAIA disparaissait. Les adresses CDN des images surchargeaient aussi le corpus. Correction générique dans l'extracteur HTML : conserver le texte commercial des formulaires ; garder les descriptions accessibles et les liens des images, sans leur adresse technique. Les formulaires de recherche/localisation restent exclus.

Les quatre premiers imports sont conservés. Les deux compilations déjà lancées ont terminé et leurs compteurs sont archivés. L'amendement A1 est consigné avant la correction : les quatre marques sont ensuite réimportées et évaluées sur un même code corrigé. Ce n'est donc pas un baseline complet de quatre parcours sur le code initial.

Validation gratuite : **1 953 tests backend réussis**, Ruff propre ; trois régressions spécifiques protègent prix/conditions/formulaires, descriptions d'images et exemples de code littéraux.

| Marque | Caractères avant → après | Lots de lecture avant → après | Texte écarté après |
|---|---:|---:|---:|
| CABAIA | 242 409 → 149 582 | 18 → 12 | 0 |
| Papier | 188 828 → 85 038 | 16 → 7 | 0 |
| systeme.io | 92 248 → 71 817 | 8 → 6 | 0 |
| RTINGS.com | 29 279 → 25 705 | 3 → 2 | 0 |

Ces lots sont calculés par le planificateur réel sans appel modèle. Ils ne constituent pas une mesure de latence.

## Réserves de couverture constatées

- CABAIA : huit pages de produits/accessoires, avec du bruit de panier et des recommandations encore présents. Le prix vérifié est récupéré après réimport normal.
- Papier : douze pages substantielles mais surtout des guides ; un seul produit individuel. Ne pas extrapoler les conditions de livraison ou de personnalisation.
- systeme.io : les pages fonctionnalités sont substantielles, mais les cartes des tarifs payants rendent `null`. Les limites du gratuit restent documentées. L'expéditeur du scénario est un partenaire affilié indépendant, sans commission, revenu, lien de suivi ni expérience personnelle inventés.
- RTINGS.com : six des huit pages ne livrent que des menus au collecteur. Le navigateur affiche pourtant l'article public complet sur les appareils photo. C'est une limite réelle de collecte/rendu ; les faits vus dans le navigateur n'ont pas été injectés au générateur. La homepage et la page d'abonnement sont exploitables pour un périmètre plus étroit.

## Résultats finaux

### Notes des étapes effectivement inspectées

Notes éditoriales de couverture, après correction ; elles ne mesurent pas une conversion.

| Étape /10 | CABAIA | Papier | systeme.io | RTINGS.com |
|---|---:|---:|---:|---:|
| Import initial, conservé | 4 | 6 | 6,5 | 4 |
| Import après correction | 7 | 7 | 6,5 | 4 |
| Compilation après correction | Échec quota | Non exécutée | Échec quota | Non exécutée |
| Catalogue de capacités | Non noté | Non noté | Non noté | Non noté |
| Concurrents | Non noté | Non noté | Non noté | Non noté |
| Positionnement | Non noté | Non noté | Non noté | Non noté |
| Carte d'audiences | Non noté | Non noté | Non noté | Non noté |
| Recherche d'audience | Non noté | Non noté | Non noté | Non noté |
| Dossier de pertinence | Non noté | Non noté | Non noté | Non noté |
| Génération / livraison | Non noté | Non noté | Non noté | Non noté |
| Consultation / CTA / rendu final | Non noté | Non noté | Non noté | Non noté |
| Email /100 | Aucun asset | Aucun asset | Aucun asset | Aucun asset |

Les deux compilations sur les imports initiaux ont terminé : CABAIA, 415 faits, 21 appels, 808,67 secondes ; systeme.io, 151 faits, 11 appels, 486,47 secondes. Leurs artefacts et compteurs sont conservés, mais ils ne valident pas les corpus corrigés. Chez systeme.io, le profil signale des tarifs payants illisibles alors que la liste globale des gaps est vide : la remontée des lacunes mérite une vérification supplémentaire.

Les compilations corrigées ont toutes deux échoué sur le quota : systeme.io après huit appels terminés, au moment de la passe audience ; CABAIA après onze appels terminés. Les captures finales exposent encore leurs anciens artefacts v1, ce qui ne constitue pas une compilation réussie des nouveaux corpus. Ce n'est pas une note de qualité négative sur un email : aucun email n'a été produit. Aucun lancement Papier/RTINGS supplémentaire après le refus de quota, aucun changement de modèle ni achat de crédits.

### Ce que tu peux décider maintenant

- **Inviter ton ami à découvrir et éprouver le produit avec toi : oui**, en présentant explicitement un test exploratoire. Ses cas réels peuvent être utiles, mais le présent audit ne certifie pas encore une bêta autonome réussie.
- **Lui affirmer que le parcours e-commerce et affiliation est validé de bout en bout : non.** Le seuil préalable de trois cas utiles sur quatre n'est pas encore démontré.
- **Vendre une promesse « tous sites / toutes marques » : non.** RTINGS fournit déjà un contre-exemple de couverture et les tarifs dynamiques de systeme.io constituent une autre restriction.

Il ne s'agit pas de conclure que le système est adapté uniquement à Fathom : l'échantillon actuel ne permet pas encore de trancher sa généralisation de bout en bout. Il montre des capacités de collecte sur d'autres marques, un défaut générique corrigé, et deux limites concrètes encore ouvertes.

### Phases restantes avant confirmation

1. **Collecte** : signaler clairement les pages peu substantielles / rendues côté navigateur et les tableaux tarifaires illisibles. Étudier un mécanisme générique si ces types de sites font partie du périmètre commercial ; ne pas promettre leur prise en charge avant retest.
2. **Knowledge** : terminer les quatre compilations sur le code corrigé et examiner prix, produits, conditions et gaps. Les anciens artefacts ne doivent pas remplacer cette vérification.
3. **Marché → audience → dossier** : exécuter et noter le scan partagé, le catalogue, la première audience exacte, sa recherche et ses fits, sans sélection opportuniste.
4. **Email** : produire un vrai asset par cas admis, vérifier l'identité de l'affilié, l'absence de faux résultats et le passage des preuves vers le brief. Conserver tout refus.
5. **Livraison** : inspecter les rendus ordinateur/mobile et la vraie destination du CTA, puis appliquer la grille /100 et le seuil fixé avant les résultats.

Les limites commerciales sont distinctes de l'indisponibilité temporaire de quota. Les fichiers de cas et snapshots permettent de reprendre sans recréer les marques et sans effacer les tentatives.
