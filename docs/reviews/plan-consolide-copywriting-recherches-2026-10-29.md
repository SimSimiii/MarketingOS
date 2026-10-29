# MarketingOS — analyse critique des recherches et nouveau plan d’optimisation

Date : 29 octobre 2026. Livrable de recherche et de conception ; aucune modification du générateur dans cette intervention.

## 1. Décision principale

**Conserver l’architecture déterministe, réparer d’abord la fiabilité en français, puis améliorer la qualité des décisions éditoriales.** Le chantier ne consiste pas à ajouter une liste de « biais psychologiques » au prompt. Il consiste à donner au rédacteur les bonnes informations, une intention précise, une liberté créative encadrée et une évaluation adaptée à la situation.

Claude apporte une contribution importante : des défauts de contrôle très concrets, des angles morts sur les conditions commerciales et une critique utile des juges automatiques. Mon précédent plan apportait davantage sur la cohérence entre destinataire, décision attendue, preuve, argument et parcours. Les deux se complètent. Je modifie cependant leur ordre de priorité : les collisions numériques et les faux blocages linguistiques passent avant l’enrichissement du copywriting.

Ce document remplace **l’ordre de mise en œuvre** du [plan précédent](plan-copywriting-pro-2026-10-29.md). Le [rapport de recherche initial](recherche-marketing-psychologie-email-2026-10-29.md) reste une référence documentaire. Aucune promesse de hausse de conversion n’est déduite de ces travaux : il n’existe actuellement ni utilisateurs ni données d’envoi permettant de la mesurer.

## 2. Périmètre et niveau de vérification

Corpus confronté : le rapport [Psychologie des emails marketing](../../reports/Psychologie%20des%20emails%20marketing.md), ses huit notes de recherche, mes deux documents précédents et les composants actuels du dépôt. Les synthèses et recommandations des huit notes ont été examinées, avec des lectures ciblées des développements, limites et sources. Il ne s’agit pas d’une réplication exhaustive de toutes les références citées par Claude.

J’ai revérifié des sources primaires lorsque leur interprétation changeait une décision produit : persuasion politique, nudges, jugement de textes générés, préférence des juges pour leurs propres productions, réplication de techniques de persuasion, pixels, prix et accessibilité. Les références sont données au fil du texte.

J’ai également exécuté des sondes sur les fonctions de production : extraction et licence des affirmations, clarté, acronymes et nombre d’emails demandé. [Script reproductible](verification-recherche-claude-2026-10-29/probe.py) et [résultats avec empreintes des fichiers contrôlés](verification-recherche-claude-2026-10-29/results.json). Ces sondes n’appellent aucun modèle, n’ouvrent aucune session de base de données et ne lancent aucune campagne. Elles reproduisent des défauts de fonctions ; elles ne prouvent pas qu’une campagne réelle a effectivement livré chaque erreur.

## 3. Ce qu’il faut retenir des huit notes

| Note de Claude | Apport à conserver | Limite ou correction nécessaire |
|---|---|---|
| `marketingos_pipeline_map.md` | Relier chaque recommandation aux vrais composants ; préserver la machine à états ; chercher des améliorations sans nouvel appel. | Certaines descriptions simplifient le comportement actuel. Les jugements influencent aussi le classement et la qualification éditoriale ; la compréhension n’est pas leur seul effet. |
| `email_empirical_evidence.md` | Séparer ouverture, clic et achat ; distinguer expérimentation et corrélation ; traiter les recettes universelles avec prudence. | Un résultat moyen dans un autre canal ou une autre population ne fixe pas le rendement attendu d’un email MarketingOS. |
| `persuasion_psychology.md` | Réactance, confiance, pertinence des preuves, limites des techniques populaires. | Une absence de preuve robuste ne démontre pas une inefficacité universelle et ne justifie pas une interdiction stylistique. |
| `audience_differences.md` | Adapter au contexte, à la relation, au risque et aux connaissances du destinataire. | Ne pas inférer une personnalité ou une vulnérabilité à partir d’un secteur ou d’un prénom. Les typologies restent des hypothèses. |
| `copywriting_craft.md` | Langage client, objections réelles, mécanisme compréhensible, proposition concrète et continuité du CTA. | Schwartz, AIDA, PAS et autres cadres sont des outils de conception ; pas des lois imposant une longueur ou un ordre fixe. Plusieurs références sont des commentaires de praticiens, pas les ouvrages originaux. |
| `offer_pricing_trust.md` | Conditions de prix, engagement, essai, garantie et crédibilité de la preuve. | Les mots « gratuit » ou « garantie » ne suffisent pas à décider si une phrase est fausse. Il faut connaître le sujet, les conditions et la négation éventuelle. |
| `ai_generated_copy.md` | Risque d’auto-préférence, uniformisation du style, importance d’évaluations indépendantes et d’exemples humains. | Les résultats sur des articles anglais et certains modèles ne valident pas un détecteur universel de « style IA » dans les emails français. |
| `pitfalls_deliverability_legal.md` | Pied de page, distinction des finalités, accessibilité, export et séparation entre contenu et infrastructure d’envoi. | Un générateur ne peut certifier le consentement, la réputation d’un domaine ou toutes les obligations juridiques à partir du texte seul. |

Il faut aussi résoudre les tensions internes du corpus. La note de copywriting présente parfois les niveaux de conscience comme une progression prescriptive ; celle sur les audiences invite à contextualiser. Retenir la seconde approche : utiliser la grille seulement si les informations disponibles permettent de la renseigner, avec une valeur « inconnu » explicite.

## 4. Corrections factuelles et méthodologiques importantes

### 4.1 La densité factuelle n’est pas une formule universelle de vente

L’étude sur les leviers de persuasion citée par Claude porte sur des conversations politiques, avec 19 modèles et 707 sujets. Elle apporte une hypothèse intéressante sur l’information persuasive, mais ne démontre pas qu’accumuler des faits augmente les achats dans un email. Elle observe également une dégradation de l’exactitude dans certaines conditions plus persuasives. [Étude primaire](https://arxiv.org/abs/2507.13919).

**Décision :** mesurer si une preuve répond à l’objection décisive, pas le nombre de faits par cent mots. Un email de marque peut vendre par une image, un désir, une démonstration ou une histoire vraie ; il ne doit pas devenir un dossier administratif.

### 4.2 Les effets moyens des nudges ne donnent pas un plafond au copywriting

Le résultat d’environ 1,4 point de pourcentage chez des unités publiques provient de 126 essais de nudges. Il ne permet ni de prédire le gain de nos emails, ni d’affirmer que leurs effets seront toujours de 1 à 2 points. [DellaVigna et Linos](https://www.nber.org/papers/w27594.pdf).

**Décision :** retirer toute estimation de rendement commercial tirée d’une moyenne hors contexte. Définir des critères observables hors ligne aujourd’hui ; réserver les effets commerciaux aux futurs essais d’envoi.

### 4.3 Une technique mal étayée n’est pas une phrase interdite

La méta-analyse du « vous êtes libre de refuser » trouve un effet groupé, mais les études à faible risque de biais donnent une estimation incertaine dont l’intervalle inclut zéro. Cela fragilise la recette ; cela ne démontre pas qu’une formulation respectueuse de l’autonomie est toujours inutile. [Méta-analyse](https://open.lnu.se/index.php/metapsychology/article/view/2640).

**Décision :** aucune « astuce » ne devient obligatoire. Une formulation peut rester pertinente pour le ton et la relation, sans lui attribuer un gain causal non établi.

### 4.4 Les limites des juges justifient leur évaluation, pas leur abandon

Les difficultés observées sur WritingQuality et l’auto-préférence sont des raisons de construire des contre-exemples et de tester les juges. Elles ne démontrent pas que tout jugement automatique est inutile. [WritingQuality](https://arxiv.org/abs/2504.07532), [auto-préférence](https://arxiv.org/abs/2404.13076).

De même, la détection experte d’articles générés étudiée sur un corpus anglais ne signifie pas que tous les acheteurs détectent nos emails, ni que des seuils de ponctuation permettraient de les améliorer. [Étude de détection](https://arxiv.org/abs/2501.15654).

**Décision :** conserver le lecteur aveugle ; tester séparément sa compréhension, ses préférences et ses angles morts. Comparer éventuellement des familles de modèles, sans prétendre éliminer tous les biais par ce seul changement.

### 4.5 Les règles de conformité doivent être contextualisées

- La CNIL distingue des pixels nécessitant un consentement et des cas d’exemption. « Tout pixel est toujours interdit sans consentement » serait trop absolu. [Recommandation du 14 avril 2026](https://www.cnil.fr/fr/recommandation-pixel-suivi-courriels).
- La règle européenne de référence du prix antérieur sur trente jours visée par l’article 6 bis concerne les biens dans le champ de cette directive ; on ne peut pas l’appliquer automatiquement à tous les services SaaS. Des règles nationales peuvent ajouter des obligations. [Communication de la Commission](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX%3A52021XC1229%2806%29).
- Un email transactionnel peut contenir un prix : une facture en est un exemple évident. La finalité et le contenu promotionnel comptent davantage qu’un filtre « contient un montant ». [CNIL, questions sur les pixels et les courriels](https://www.cnil.fr/fr/faq-recommandation-pixels-courriers-electroniques).
- WCAG 2.4.4 accepte un objet de lien compréhensible par son texte ou son contexte déterminable. « En savoir plus » n’est donc pas automatiquement une violation, même si un libellé précis est souvent préférable. [W3C](https://www.w3.org/WAI/WCAG21/Understanding/link-purpose-in-context).

**Décision :** contrôler les éléments connus, demander les éléments manquants lorsque nécessaires, et présenter les inconnues. Un pied de page n’est pas un certificat de conformité globale.

## 5. Défauts reproduits : nouvelle priorité immédiate

| Sonde | Résultat actuel observé | Conséquence |
|---|---|---|
| Nom correctement présent : `Élan` ou `Café Crème` | Blocage de clarté ; le témoin `Elan` passe ce contrôle. | Le système peut rejeter une bonne copie française. |
| `9 € par mois` | Aucune affirmation extraite. | Un petit prix peut échapper au contrôle numérique concerné. |
| `29 € par mois` | `29` extrait comme quantité ; refusé sans preuve. | Nuance importante : tous les prix français ne passent pas librement. |
| Source `29 modèles disponibles`, copie `29 € par mois` | Aucune affirmation non étayée signalée par le contrôle. | Un nombre présent dans une source peut licencier un prix sans rapport. |
| Source `29,90 euros par mois`, copie `2990 euros par mois` | Aucune affirmation non étayée signalée. | Collision de normalisation décimale particulièrement importante. |
| `en 3 jours` / `en 3 minutes` | La première durée n’est pas extraite ; la seconde l’est. | Couverture linguistique partielle, plutôt qu’absence totale de français. |
| Citation en `« … »` / même citation entre guillemets ASCII | Seule la seconde est extraite dans la sonde. | Trou de contrôle lié à la typographie française. |
| `RGPD`, `CNIL`, `SIRET` | Blocages du contrôle « spam » ; `HTTP` passe. | Faux positifs sur des acronymes légitimes. |
| « Écris cinq emails » | Trois emails par défaut, nombre non reconnu comme explicite. | Non-respect d’une demande française simple. |

Ces constats justifient des tests de régression ciblés. Ils ne justifient pas une réécriture complète de la pipeline. Les empreintes enregistrées dans les résultats permettent de savoir si le code a changé depuis la vérification.

## 6. Architecture cible : enrichir les contrats, préserver le déroulement

```text
Sources de marque et marché
        ↓
Faits typés, provenance, conditions, validité, locale
        ↓
Contrat de communication + décision attendue
        ↓
Options d’argument → brief contextualisé
        ↓
Rédaction → contrôles → lecture aveugle → correction ciblée
        ↓
Objet + aperçu + corps + action + destination + export versionnés
```

Les changements structurants portent sur les données transmises et les responsabilités des contrôles. `ModelSession`, la machine à états, l’émetteur d’événements et le rôle de persistance de l’orchestrateur restent en place. Le web reste réservé aux composants de marché.

Réutiliser les structures présentes : `ArgumentOption`, les champs `next_step_decision/value/evidence_ids/limit`, les références d’action et `destination_kind`, ainsi que les catégories de problème du critique. Créer une seconde ontologie d’arguments ou un nouveau routeur « intelligent » ajouterait surtout des incohérences.

## 7. Nouveau plan de réalisation, par ordre de dépendance

### Lot 0 — Construire une référence bilingue avant de modifier les critères

**But :** savoir si l’on améliore réellement les emails, sans calibrer le système sur un utilisateur inexistant.

Reprendre les 24 cas proposés précédemment, répartis en 16 cas de développement et 8 réservés. Couvrir français et anglais, prospection, activation, client existant, produit émotionnel, achat coûteux, action par réponse et action par lien. Ajouter des cas où la bonne réponse consiste à signaler un manque de matière.

Séparer les fixtures déterministes des emails de référence éditoriaux. Les premières établissent ce qui doit passer ou échouer. Les seconds servent aux comparaisons à l’aveugle ; deux références humaines anglaises ne suffisent pas à définir le style français. Ne pas présenter des exemples rédigés par un modèle comme humains. Si de nouvelles références humaines ne sont pas disponibles, indiquer cette limite et commencer par les invariants vérifiables.

**Acceptation :** chaque cas a un contexte, une décision attendue et des erreurs interdites ; aucun score de clic simulé n’est présenté comme une conversion mesurée. Aucun appel facturé n’est nécessaire pour constituer les fixtures et les mutations.

### Lot 1 — Réparer le français et la licence des affirmations

**Cibles :** `knowledge/ledger.py`, `marketing/gates.py`, `marketing/contract.py` et leurs tests.

1. Normaliser Unicode et typographie de façon cohérente entre extraction et comparaison. Conserver le texte original et éviter qu’une normalisation trop agressive confonde deux entités.
2. Parser les montants avec une locale explicite et une représentation décimale exacte : symbole avant/après, virgule décimale, espaces de milliers et espaces insécables. Refuser une interprétation silencieuse lorsque le format est ambigu.
3. Conserver le type, la devise, l’unité, la période, le produit ou plan et les conditions. Un nombre de modèles ne peut jamais justifier un abonnement de même montant.
4. Couvrir les durées et guillemets français ; reconnaître les nombres écrits dans la demande et les limites raisonnables de nombre d’emails.
5. Corriger les faux positifs d’acronymes. Transformer les jugements généraux sur les majuscules en conseils de forme, sans prétendre reproduire les filtres antispam.

**Acceptation :** tous les défauts du tableau précédent deviennent des régressions explicites ; les témoins anglais et les citations typographiquement équivalentes restent corrects. Ajouter notamment les cas `29,90`, `2 990`, montant annuel/mensuel et preuve portant sur un autre produit.

**Coût :** aucun nouvel appel modèle. Effort limité sur les accents et les nombres écrits, plus significatif sur les montants typés. Le retour immédiat est double : moins de faux rejets et moins d’affirmations faussement autorisées.

### Lot 2 — Étendre le contrat de communication et l’offre vérifiable

**Cibles :** requête, intention, briefs, schémas, compilation de connaissances et miroir frontend.

Utiliser les objectifs et relations déjà présents. Ajouter seulement les informations manquantes : locale, registre souhaité, décision visée, finalité de communication, niveau de connaissance documenté, effort demandé et conditions de l’offre. Distinguer une information fournie, observée dans une source et supposée par le système.

Créer une vue de l’offre réutilisable : produit concerné, montant, devise, facturation, taxes si connues, engagement, essai, conditions de garantie, période de validité et source. Une affirmation « gratuit » doit conserver ce qui est gratuit, pendant combien de temps et avec quelles conditions connues. Une date collectée hier n’atteste pas automatiquement qu’un stock est encore disponible demain.

La finalité commerciale, transactionnelle ou relationnelle est une information à traiter ; elle ne déclenche pas une interdiction générale des prix. Les règles dépendant du pays ou du secteur restent explicitement conditionnelles.

**Acceptation :** impossible de transformer un essai en offre gratuite permanente, une réduction expirée en urgence actuelle ou un prix annuel en prix mensuel. Les faits inconnus restent inconnus ; ils ne sont pas complétés par le rédacteur.

**Coût :** enrichir les sorties des appels existants et le stockage, avec invalidation des caches concernés. Pas de nouveau rôle. Vérifier le surcoût de tokens et les migrations plutôt que déclarer le changement « gratuit ».

### Lot 3 — Donner au rédacteur une vraie décision à faire avancer

**Cibles :** stratégie, `ArgumentOption`, briefs et prompts de rédaction.

Chaque email doit répondre à cinq questions : quelle situation reconnue, quelle décision raisonnable maintenant, quelle objection freine cette décision, quelle preuve pertinente peut la lever et pourquoi l’action proposée vaut son effort ? Une inconnue reste visible au lieu de devenir une psychologie inventée du destinataire.

Les variantes doivent différer par leur argument : démonstration d’usage, réduction d’un risque, désir concret, comparaison étayée, changement de perspective. Trois formulations du même bénéfice ne sont pas trois stratégies. Utiliser les options existantes dans l’appel de stratégie, sans tripler mécaniquement les campagnes.

La preuve retenue doit soutenir la promesse effectivement écrite. Une citation enthousiaste mais sans rapport n’est pas supérieure à une description précise du mécanisme. Ne pas récompenser le nombre brut de références utilisées. Préserver les protections existantes contre la perte d’appui explicite, puis évaluer la pertinence sémantique séparément.

**Acceptation :** sur les cas de développement, un évaluateur aveugle peut reformuler le produit, l’intérêt de l’action et la raison d’y croire ; le système distingue manque de preuve et mauvaise rédaction.

**Coût :** réutilisation des appels stratégie/rédaction. Une recherche complémentaire n’intervient que si une lacune précise bloque un argument utile et que le budget l’autorise.

### Lot 4 — Remplacer les recettes générales par une rédaction contextualisée

**Cibles :** prompts writer/reader/duel/inbox, profil de voix et politique de réécriture.

Remplacer le scénario systématique des centaines d’emails non lus et de la réunion imminente par un contexte de lecture compatible avec la relation. Ne transmettre au lecteur aveugle que ce qu’un destinataire réel saurait ; garder le brief et l’argument attendu hors de son contexte.

Modulariser le prompt : invariants factuels, contexte, intention, voix et critères propres au cas. Réexaminer les règles universelles de longueur, nombre de paragraphes et position de l’offre. Un email de suivi bref et une explication d’un achat engageant n’ont pas besoin du même format.

La voix utilise des exemples authentiques et leur provenance. Les `avoid_words` déjà présents ne doivent pas devenir automatiquement des interdictions dures lorsqu’ils sont inférés par un modèle. Les préférences explicites de marque peuvent être contractuelles ; les déductions stylistiques restent révisables. Une alternance tu/vous déclenche une analyse de contexte, car une citation ou un pluriel peut l’expliquer.

Préserver l’émotion, l’humour, le rythme et la surprise lorsqu’ils servent la marque. Éviter de remplacer la copie générique par une copie uniformément sèche. Le bon critère est la pertinence et la singularité, pas l’absence de toute expression fréquente.

**Acceptation :** la personnalisation change la pertinence de l’argument, pas seulement le prénom ; les emails restent distinctifs quand on retire le nom de marque ; aucune émotion personnelle n’est affirmée sans fondement.

### Lot 5 — Séparer intégrité, qualité éditoriale et incertitude

**Cibles :** gates, reader, critic, craft, report et évaluation.

| Niveau | Exemples | Conséquence prévue |
|---|---|---|
| Intégrité déterministe | Prix non étayé, citation inventée, URL interdite, condition commerciale contradictoire. | Bloquer ou corriger l’affirmation concernée. |
| Contrat explicite | Mauvais nombre d’emails, mauvaise langue, action incompatible avec la demande. | Corriger ; signaler si impossible. |
| Qualité éditoriale | Argument banal, effort disproportionné, mauvaise transition, preuve peu convaincante. | Comparer et réviser dans une enveloppe bornée. |
| Incertitude externe | Consentement inconnu, état réel du stock, réputation d’envoi, effet sur l’achat. | Montrer l’inconnue et son propriétaire ; ne pas inventer une validation. |

Réutiliser les catégories actuelles du critique : problème de copie, d’argument ou de matière. Une phrase faible appelle une réécriture locale ; un argument faible appelle un pivot ; une preuve absente appelle une recherche ciblée ou une proposition moins ambitieuse. Fixer des limites et conserver la meilleure version valide.

La compréhension reste prioritaire dans la sélection. Mais un score de « pull » n’est pas une probabilité d’achat. Présenter séparément admissibilité factuelle, compréhension, qualité éditoriale et limites. Documenter les conditions actuelles de `ships`/`landed` avant de les changer : le dépôt contient déjà plusieurs effets de jugement au-delà de la seule compréhension.

Commencer l’évaluation des juges par les contrôles et mutations gratuits. Préparer les mutations difficiles en français : preuve vidée de son contenu, deuxième demande concurrente, bénéfice remplaçant l’explication, condition déplacée ou supprimée. Ensuite seulement lancer une campagne de mesure bornée du bench difficile. Le chiffre historique d’environ 128 appels est un ordre de grandeur à recalculer selon les cas et options.

**Acceptation :** lire la matrice des erreurs par mutation et contrôle ; ne pas remplacer cette analyse par un taux global. Tester des juges de familles différentes sur les mêmes exemples, avec ordre inversé, uniquement si la mesure initiale révèle un biais que cette expérience peut éclairer.

### Lot 6 — Garantir la cohérence de l’email livré et de la séquence

**Cibles :** objets, aperçus, rendu HTML/texte, export, rapport et interface.

Versionner l’ensemble objet–aperçu–corps–CTA–destination. Toute modification tardive doit invalider les vérifications concernées. Un objet plus attractif ne peut introduire une promesse absente du corps. L’action doit correspondre à la destination réelle, y compris réponse ou action hors ligne.

Unifier l’enveloppe d’export selon la finalité et les données disponibles : identité, mentions applicables, désinscription lorsque requise, variantes HTML et texte. La lecture du renderer montre que le chemin de footer du rendu branded n’est pas partagé par le rendu plain ; traiter cet écart sans imposer une enveloppe promotionnelle identique à une facture. Ne jamais inventer une adresse ou un lien de désinscription manquant.

Contrôler le rendu : langue, direction lorsque pertinente, lisibilité, liens compréhensibles, contraste et alternatives textuelles. Les headers de désinscription, l’authentification et les politiques de fréquence relèvent du système d’envoi ; les afficher comme prérequis d’intégration, sans simuler leur vérification.

Chaque email d’une séquence doit apporter une raison nouvelle de poursuivre. Aucune relance ne prétend que le destinataire a lu, cliqué ou hésité sans événement réel. Prévoir les conditions d’arrêt et de branchement dans le contrat d’intégration, même si le générateur ne les exécute pas encore.

**Acceptation :** aucune exportation silencieuse d’une version différente de celle évaluée ; parité des informations nécessaires entre formats ; pas de progression fictive du destinataire dans la séquence.

## 8. Arbitrage des propositions de Claude

| Proposition | Décision consolidée |
|---|---|
| Unicode, prix, durées, citations et acronymes français | **Faire immédiatement**, avec les collisions décimales et de type en plus. |
| Dates, urgence, gratuité, garanties et popularité | **Faire par étapes**, avec faits typés et portée ; éviter le moteur à mots-clés prétendument exhaustif. |
| Attribution des témoignages | **Retenir** : texte, auteur, contexte et permission connue doivent rester liés ; une citation exacte ne prouve pas une permission d’utilisation. |
| Footer du rendu plain | **Retenir**, dans une enveloppe d’export contextualisée. |
| Faux `Re:` / `Fwd:` / `TR:` | **Retenir contre la tromperie**, en conservant le contexte d’une véritable réponse ou d’un transfert. |
| Majuscules, emojis, longueur, ordre preuve/CTA | **Conseils contextuels**, pas interdictions universelles. |
| Interdire les prix hors promotion | **Rejeter** : faux positifs évidents sur les communications de service. |
| Tu/vous et niveaux de conscience | **Reformuler** : données de contexte et diagnostics, pas règles aveugles. |
| Score anti-IA et seuil de densité factuelle | **Reporter/écarter comme gate** : validité insuffisante et risque d’uniformisation. |
| Bloquer tous les mots à éviter inférés | **Rejeter** ; distinguer instruction explicite et hypothèse de voix. |
| Accessibilité du rendu | **Retenir**, avec des contrôles conformes au critère réellement applicable. |
| Checklist délivrabilité | **Retenir à l’intégration d’envoi**, sans la confondre avec la qualité du texte. |
| Bench difficile et références françaises | **Retenir**, après préparation gratuite et budget explicite. |
| Toujours employer un juge d’une autre famille | **Expérimenter**, sans en faire un prérequis architectural. |

## 9. Ce que je corrige dans mon propre plan

1. **La fiabilité française devient le premier chantier.** L’architecture de décision ne suffit pas si les montants sont mal normalisés ou si un nom accentué déclenche un refus.
2. **Le contrat d’offre devient plus structuré.** La provenance d’un nombre seule ne protège ni sa signification ni ses conditions d’utilisation.
3. **L’évaluation devient bilingue dès le départ.** Les références anglaises existantes ne suffisent pas pour juger le produit visé ici.
4. **L’export est une responsabilité à part entière.** Une copie correcte dans l’éditeur peut devenir incohérente dans sa forme réellement livrée.
5. **La recherche psychologique reste une bibliothèque conditionnelle.** Chaque règle doit indiquer contexte, type de preuve, limites et conséquences autorisées ; aucune étude isolée ne devient un interdit de génération.

Je conserve la priorité donnée à la décision attendue, aux preuves pertinentes, à la singularité de marque, aux variantes d’argument et à la révision guidée par la cause. Ces éléments empêchent le plan consolidé de se réduire à un projet de validation syntaxique.

## 10. Coût, validation et première livraison recommandée

La première livraison doit couvrir **lot 0 + lot 1**, avec un inventaire des champs du lot 2. Elle produit un résultat utile et vérifiable sans dépendre de données commerciales futures. Les lots 2 à 6 viennent ensuite par incréments ; éviter une migration générale qui modifierait simultanément les faits, les prompts, les juges et les exports.

« Aucun nouvel appel » ne veut pas dire aucun coût. Des prompts plus longs consomment des tokens ; des gates différents modifient le nombre de réécritures. Vérifier les prévisions de coût et les tests de forecast même lorsque le nombre théorique de rôles ne change pas. Toute expérience facturée doit préciser la question, les cas, le nombre maximal d’appels et le critère d’arrêt.

Pour chaque future modification de code : tests ciblés significatifs, puis checks requis du dépôt ; schémas frontend synchronisés si contrat modifié ; contrôle des migrations lorsqu’un stockage change. Les exécutions réelles sont réservées aux questions de comportement du modèle et ne remplacent jamais les tests scriptés.

Pas de fine-tuning, pas de multiplication d’agents, pas de dépendance initiale à de la télémétrie inexistante. Pas non plus de nouvelle promesse « copywriter PRO » fondée uniquement sur un juge automatique. Le résultat défendable est un générateur qui respecte la demande, affirme des choses justifiables, choisit un argument pertinent, écrit avec une voix reconnaissable et montre honnêtement ce qu’il n’a pas pu vérifier.

### Livrables de cette analyse

- Le présent plan consolidé et son arbitrage des recherches.
- Le script de sondes et les résultats reproductibles liés en section 2.
- Aucune correction applicative, campagne réelle, migration ou dépense de quota modèle effectuée dans cette intervention.
