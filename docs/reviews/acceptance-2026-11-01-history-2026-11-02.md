# Audit d’acceptation MarketingOS — bilan du 2 novembre 2026

**Reprise du 2 novembre au soir : décision globale rouverte à la demande explicite
de l’utilisateur. Le bilan 5/6 ci-dessous reste historique et ne clôt plus le
travail.** Une confusion déterministe entre deux lignes tarifaires ayant la même
citation a été reproduite et corrigée ; 2167 tests backend passent. La même
séquence est régénérée pour juger le service complet et rendre un verdict binaire
de valeur estimée à l’achat. Voir `state.json` et `journal.md` pour l’état courant.

**Verdict final : seuil technique atteint, avec cinq cas utilisables sur six après retouches mineures. MarketingOS est suffisamment utile pour proposer une offre payante assistée de préparation, rédaction et ajustement d’emails fondés sur les sources, avec revue normale de la marque avant usage.**

Ce verdict est un jugement d’utilité technique sur l’échantillon fixé. Il ne mesure ni volonté de payer, ni conversion, ni marge. La séquence systeme.io reste le sixième cas non validé : les trois emails sont livrés, mais le troisième demande un changement substantiel d’argument. Une promesse de séquences toujours prêtes sans relecture dépasserait les résultats observés.

Les six cas ordinaires, les deux cas limites et le seuil de cinq réussites restent identiques. L’utilisateur a rouvert les essais après le bilan initial ; les plafonds initiaux de générations et de retouches sont historiques, comme l’explicite l’amendement du [protocole](../optimization/acceptance-2026-11-01/protocol.md). Les échecs sont conservés. Aucune audience plus facile, preuve ajoutée manuellement ou dérogation au précontrôle n’a remplacé le cas Loops.

L’arrêt final vient de l’atteinte du seuil, alors qu’OpenAI répond encore. Le quota Claude a été épuisé pendant la reprise ; les rôles compatibles ont continué sur l’abonnement OpenAI. Aucun solde API, achat de crédits, envoi ou déploiement n’a été utilisé.

## Résultats finaux du même échantillon

Les notes /100 sont des jugements éditoriaux selon la grille fixée, sans prédiction de conversion.

| Cas | Livraison finale | Note | Décision |
| --- | --- | --- | --- |
| Papier, acquisition | 1/1 | 88 | Utilisable après retouches locales de formulation. |
| Papier, considération | 1/1 | 87 | Utilisable après suppression de répétitions. |
| systeme.io, acquisition affiliée | 1/1 | 83 | Utilisable après précision du périmètre des sites et allègement des réserves. |
| systeme.io, séquence affiliée | 3/3 | 71 | Non validée : le troisième argument économique doit changer. |
| Loops, acquisition | 1/1 | 89 | Version ajustée utilisable ; même argument, mêmes fonctions et même guide. |
| Loops, considération | 1/1 | 88 | Version ajustée utilisable ; attribution du guide et sujet corrigés. |

Les trois premiers verdicts portent sur les livrables précédemment examinés ; ils ne deviennent pas de nouvelles générations. Les deux nouveaux cas Loops ont été inspectés sur leur texte, leurs preuves et leur rendu. Les avis simulés demandant toutes les réponses techniques dans l’email ne sont pas automatiquement des veto : une invitation documentée à évaluer l’architecture peut rester utile.

### Ce qui a réellement changé

Le crawler ne suivait pas le manifeste documentaire officiel lié par Loops et s’arrêtait trop tôt dans l’arborescence. Il découvre maintenant ce manifeste, déduplique les représentations HTML/Markdown et privilégie les guides d’intégration, tout en conservant le budget de douze pages. La homepage seule a ainsi conduit aux guides Supabase/Clerk et aux tarifs. Le contexte des audiences déjà choisies guide le recrawl de leur propre marque, sans URL ajoutée par l’opérateur ; la recherche de marché conserve son comportement de ciblage distinct.

Le dossier confondait ensuite une alternative explicite « Supabase ou Clerk » avec l’obligation de satisfaire les deux plateformes. Il peut maintenant qualifier la branche documentée Supabase, rendre cette restriction visible et transmettre les conditions de configuration à la stratégie et aux réécritures. Une conjonction de besoins reste entière ; sélectionner une information ne la vérifie pas. Clerk ne devient pas compatible avec la migration d’authentification par cette correction. Les anciens dossiers sont conservés et invalidés normalement par la version d’interprétation 18.

Les prompts demandent de partir de la fonction prouvée lorsque la cause d’un problème n’est pas résolue par les sources, et de proposer l’inspection du guide avant une configuration lourde. Le nom de l’éditeur du guide doit également être exact. La répétition fermée d’une identité ou d’une mention d’affiliation ne bloque plus la séquence ; la répétition d’une promesse marketing reste contrôlée. Aucun appel modèle supplémentaire n’a été ajouté à la boucle pour ces changements.

### Loops : preuves, retouches et parcours réel

La même première audience demeure sélectionnée, avec qualification **Supabase uniquement**, dossier courant et aucun forçage. La Knowledge v2 contient notamment E1 (hook, Edge Function et template par type), E37/E380 (synchronisation de contacts distincte), E42 (domaine vérifié) et E378 (deux voies d’intégration). Le texte explique comment envoyer l’authentification et alimenter l’onboarding sans prétendre modifier les limites propres à Supabase.

La retouche d’acquisition clarifie les deux intégrations, précise leurs conditions existantes et enlève une digression sur le contrôle de débit. La retouche de considération corrige « documentation Supabase » en « guide Supabase publié par Loops », recentre le sujet et réduit les répétitions. Ni l’argument, ni l’offre, ni la destination ne sont remplacés. Chaque proposition utilise **un seul appel GPT**, repasse les contrôles et ne reprend pas l’ancien verdict de lecture comme une validation.

Acceptation, différence affichée, conservation de l’original et de l’historique, copie et téléchargement exacts de la version choisie ont été vérifiés dans la véritable interface. Une alerte consultative compare littéralement le libellé du CTA aux actions cataloguées ; la destination officielle correcte reste accessible et aucun contrôle bloquant n’est ignoré. Les retouches Papier et systeme.io précédentes restent conservées : accepter/restaurer et refuser/demander un autre ajustement ont aussi été observés.

- Acquisition : [texte choisi](../optimization/acceptance-2026-11-01/loops-acquisition/selected/email-1.txt), [HTML](../optimization/acceptance-2026-11-01/loops-acquisition/selected/email-1.html), [mobile](../optimization/acceptance-2026-11-01/loops-acquisition/selected/email-1-390.png), [export UI](../optimization/acceptance-2026-11-01/loops-acquisition/revision-scope-export.txt), [contrôle copie/export](../optimization/acceptance-2026-11-01/loops-acquisition/revision-scope-ui-check.json).
- Considération : [texte choisi](../optimization/acceptance-2026-11-01/loops-consideration/selected/email-1.txt), [HTML](../optimization/acceptance-2026-11-01/loops-consideration/selected/email-1.html), [ordinateur](../optimization/acceptance-2026-11-01/loops-consideration/selected/email-1-1280.png), [export UI](../optimization/acceptance-2026-11-01/loops-consideration/revision-scope-export.txt), [contrôle copie/export](../optimization/acceptance-2026-11-01/loops-consideration/revision-scope-ui-check.json).

Les rendus à 1280/390 pixels sont lisibles sans débordement. Les destinations ont été examinées séparément : la page officielle présente les deux voies, et le clic réel « Auth Hook » ouvre le guide d’envoi. Ces vérifications n’ont pas enrichi les entrées de génération. Il s’agit d’une inspection navigateur, sans matrice complète de clients email.

### Préparation Loops complète

| Étape | Note /10 | Utilité et limite observées |
| --- | --- | --- |
| Ingestion | 9 | Guides utiles et tarifs trouvés depuis la homepage, dans le budget ; vingt documents cumulés après recrawl, anciens conservés. |
| Compilation | 9 | 541 faits avec citations et conditions ; aucune mesure de résultats clients déduite. |
| Capacités | 8 | Auth Supabase et contact sync distingués ; incompatibilité Clerk Auth conservée. |
| Concurrents | 7 | Six concurrents lus ; absence de proposition équivalente capturée distinguée d’une absence de capacité. |
| Positionnement | 7 | Aucun avantage exclusif inventé ; les propositions non comparées restent inconnues. |
| Carte d’audiences | 7 | Les sept audiences sont conservées et réévaluées sur le catalogue courant ; le dossier réduit explicitement le premier segment trop large à sa branche documentée. |
| Recherche | 7 | Dix sources récupérées, six problèmes et quatre éléments écartés ; limites de date et de corroboration maintenues. Les problèmes observés ne sont pas attribués personnellement au destinataire. |
| Dossier | 8 | Branche Supabase, conditions et limites transportées, aucun override. |
| Livraison / consultation | 8 | Emails utilisables, versions et export vérifiés ; autonomie novice non mesurée. |

La considération réutilise cette préparation sans recompilation. Ces notes évaluent la préparation actuelle, séparément du premier essai insuffisant archivé ci-dessous.

### Le cas qui reste insuffisant

La [séquence finale systeme.io](../optimization/acceptance-2026-11-01/systeme-sequence/runs/c5516539-fc3e-4bdd-9e3e-8b4e2620fb10/result.json) livre trois emails en 78 appels, dans les plafonds existants. Le premier explique la vente physique, le second l’inscription volontaire reliée à la liste, au tag et à la séquence. Le troisième isole un « 0 % » de la rubrique « Lien en bio » sans établir son rôle dans l’achat du livre. Le critique le détecte, mais les réécritures conservent cet argument faible. Le nombre est cité dans son périmètre, mais sa conséquence économique n’est pas suffisamment fondée. Il faudrait choisir une autre preuve et un autre argument : ce n’est pas une retouche mineure. Ce cas reste dans le dénominateur des six et ne compte pas comme une réussite.

Les deux cas limites restent inchangés : CABAIA expose le besoin insuffisamment prouvé avec une action vers les sources ; une marque sans connaissances demande du matériel et n’invente pas d’email. Le parcours minimal sans personnalisation demeure disponible.

### Comparaison directe et coût observé

Les trois témoins donnent au même modèle de rédaction la même demande et les connaissances déjà compilées, avec le contexte de campagne. Ils sont utiles et peuvent être plus directs ; le témoin Loops explique lui aussi les deux intégrations. **Aucune supériorité générale de rédaction n’est démontrée.** L’avantage observable du produit est la préparation depuis les sources, sa réutilisation, les preuves et restrictions conservées, les contrôles, les versions et l’export. Le témoin reçoit gratuitement cette préparation dans la comparaison : aucun gain humain de préparation ou nombre de minutes économisées n’en est déduit.

Le [décompte final](../optimization/acceptance-2026-11-01/metrics-final.json) donne **au moins 395 appels terminés** pour l’audit entier, échecs et itérations correctives compris : 340 en campagnes, 48 en préparation capturée, trois témoins et quatre propositions. Un ancien compteur de carte d’audiences a été perdu avec un processus ; le total exact reste inconnu. Les derniers runs Loops utilisent 28 et 26 appels, puis un appel par retouche ; la séquence en utilise 78. Ces chiffres d’investigation ne sont pas un coût par client. Les montants USD sont des estimations de catalogue, pas une facture ; marge et temps humain restent non mesurés.

### Vérifications et activation

**2 156 tests backend** passent, puis **135 tests ciblés** de prompts/contrats/stratégie/forecast après les derniers changements textuels. Les **37 tests frontend**, Ruff `app tests`, ESLint, TypeScript, schéma API et `git diff --check` passent. Deux avertissements de dépréciation de dépendances sont conservés dans le journal complet. Voir [validation](../optimization/acceptance-2026-11-01/validation.json).

Les changements restent sur `master`, sans commit ni changement de branche. Le SQLite d’audit est une copie séparée ; la base locale d’origine reste intacte. Aucun job actif à la clôture ; les serveurs temporaires sont arrêtés après capture des résultats. Les changements ne sont pas déployés. Les dossiers préexistants demanderont une reconstruction normale à cause de la nouvelle interprétation ; aucun historique n’est effacé.

L’acceptation s’arrête ici selon la règle fixée avant les résultats. Le sixième cas et l’efficacité économique restent des limites explicites ; ils ne sont ni masqués ni transformés en nouvelles exigences pour refuser indéfiniment l’offre assistée validée.

## Archive : observations des premiers essais et bilan initial

Les sections ci-dessous sont historiques. Leurs verdicts, compteurs et étapes « à tester » décrivent leur date d’écriture ; le verdict final et les données courantes sont ceux des sections précédentes.

## Livrables réellement examinés

Les notes sont des jugements éditoriaux du coordinateur, selon la grille préexistante : faits /25, audience et offre /20, argument /20, continuité /15, rendu /10, absence de promesses abusives ou répétitions /10. Elles ne mesurent aucune conversion et ne remplacent pas les critères d'acceptation.

| Cas | Livraison | Revue /100 | Conclusion sur le livrable |
| --- | --- | --- | --- |
| Papier, acquisition | 1/1 | 88 (25/18/16/13/9/7) | Utilisable ; rendre la dernière phrase plus directe et relier le clic aux vues mensuelle, hebdomadaire et quotidienne. |
| Papier, considération | 1/1 | 87 (25/18/15/13/9/7) | Utilisable ; supprimer une répétition du cadre de 16 semaines et simplifier « planning cadence ». L'argument et les preuves restent identiques. |
| systeme.io, acquisition affiliée | 1/1 | 83 (23/18/15/12/9/6) | Utilisable après précision « dans les tunnels et sites créés avec systeme.io ». Alléger les réserves générales sans supprimer la limite sur les grandes boutiques. |
| systeme.io, séquence affiliée | 1/3 | Non notée comme séquence | Quota interrompu. Premier email conservé ; préciser le calcul des frais de livraison et le périmètre des sites. Deux emails manquants, aucune cohérence de séquence validée. |
| Loops, acquisition | 0/1, non lancé | Non noté | Préparation interrompue à la carte d'audiences. |
| Loops, considération | 0/1, non lancé | Non noté | Dépend de la même préparation ; aucune substitution d'audience. |

Les trois runs complets sont marqués `degraded` avec revue éditoriale dans l'application. Ces réserves ont été examinées sur le texte, sans transformer automatiquement un jugement de lecteur en veto commercial. Aucune erreur factuelle majeure observée dans ces trois livrables ; la formulation des sites systeme.io reste une correction nécessaire avant usage.

Papier mobilise effectivement les pages non datées, les étapes de planification et les 16 semaines ; le prix de £25 est associé au bon produit (E73, E74, E456, E464). Le prix et les vues de planification ont aussi été recoupés sur la [fiche officielle](https://www.papier.com/your-plans-on-paper-57101). systeme.io explique le parcours produit, paiement et commande, et mentionne l'affiliation ; E72, E95, E101 et E102 en portent le périmètre. La [destination officielle](https://systeme.io/fr/physical-products) correspond à ce parcours. Ces consultations indépendantes n'ont pas été injectées dans les entrées des générations.

Le défaut historique de sous-utilisation des bénéfices n'a donc pas disparu uniformément : les bénéfices sont explicites dans ces sorties, mais l'acquisition systeme.io accorde encore trop de place aux réserves. Sur ce livrable, la correction nécessaire reste locale et ne demande pas de refaire l'argument.

### Assets et rendu

- Papier acquisition : [texte](../optimization/acceptance-2026-11-01/papier-acquisition/runs/10befd94-ebe9-4682-a724-d492879ebd2a/email-1.txt), [HTML](../optimization/acceptance-2026-11-01/papier-acquisition/runs/10befd94-ebe9-4682-a724-d492879ebd2a/email-1.html), [mobile](../optimization/acceptance-2026-11-01/papier-acquisition/runs/10befd94-ebe9-4682-a724-d492879ebd2a/email-1-390.png).
- Papier considération : [texte](../optimization/acceptance-2026-11-01/papier-consideration/runs/bf614ad8-8467-4094-b553-a28b5d296ab8/email-1.txt), [mobile](../optimization/acceptance-2026-11-01/papier-consideration/runs/bf614ad8-8467-4094-b553-a28b5d296ab8/email-1-390.png), [export UI](../optimization/acceptance-2026-11-01/papier-consideration/ui-original-export.txt).
- systeme.io acquisition : [texte](../optimization/acceptance-2026-11-01/systeme-acquisition/runs/a1e13681-a98e-4f04-8fd1-9a9b46d080fd/email-1.txt), [mobile](../optimization/acceptance-2026-11-01/systeme-acquisition/runs/a1e13681-a98e-4f04-8fd1-9a9b46d080fd/email-1-390.png).
- Séquence partielle : [premier email](../optimization/acceptance-2026-11-01/systeme-sequence/runs/954dad32-5531-44fb-a808-3d7f0a036fdd/email-1.txt), [ordinateur](../optimization/acceptance-2026-11-01/systeme-sequence/runs/954dad32-5531-44fb-a808-3d7f0a036fdd/email-1-1280.png).

Les quatre assets ont été rendus en 1280 et 390 pixels : pas de débordement horizontal, CTA lisibles, contenu lisible sur les captures inspectées. Il s'agit de rendu navigateur, pas d'une matrice de clients de messagerie. Aucun asset n'a été réécrit manuellement pour améliorer ce bilan.

## Parcours et cas limites

Papier considération a été créé et lancé dans la véritable interface, sans configuration de la section facultative. « Copy all » et le téléchargement contiennent exactement le texte de l'asset original. Le panneau d'ajustement s'ouvre et présente son budget ainsi que la conservation de l'original ; aucune proposition réelle n'a encore été soumise dans cet audit. Accepter, refuser, reprendre et exporter une version modifiée restent à tester avec le fournisseur disponible.

Le premier accès au résultat a rencontré une 404 Next en développement. Les types de routes générés omettaient deux routes existantes ; redémarrer le frontend avec sa configuration habituelle les a rendues accessibles, sans modification applicative ou de base. Cause initiale non prouvée ; incident conservé, sans extrapolation à la production. Une erreur du script de navigation sur la redirection 308 de création a été récupérée sans créer une campagne en double.

**CABAIA :** le précontrôle exige une dérogation ; elle n'a pas été utilisée. L'avertissement initial affichait un identifiant interne et parlait de qualification d'entreprise. Le dossier possédait pourtant déjà l'explication pertinente : la capacité simultanée ordinateur + repas + gourde dans un seul sac n'est pas établie. La projection déterministe de l'avis expose maintenant ces lacunes et un lien vers les sources. Le statut `DISCOVERY_ONLY`, les contraintes factuelles et le diagnostic conservé dans la recommandation restent inchangés. L'interface et l'ouverture du gestionnaire de sources ont été retestées sans modèle. [Avant](../optimization/acceptance-2026-11-01/limits/cabaia-ui.png), [après](../optimization/acceptance-2026-11-01/limits/cabaia-ui-after.png).

**Marque vide :** créée et lancée par l'interface, arrêt avant toute rédaction, zéro appel et zéro jeton. Le système demande un site ou un document et permet de conserver la réponse. Le résultat est `needs_input` dans le rapport, présenté comme un arrêt à compléter. L'affichage d'une appréciation à 0/10 alors qu'aucun texte n'existe est une maladresse de présentation restante ; il ne correspond pas à une évaluation réelle. [Capture](../optimization/acceptance-2026-11-01/limits/empty-run-ui.png).

## Loops : préparation disponible

Entrée unique : https://loops.so/. Douze pages ont été découvertes normalement, dont tarifs, email produit, documentation SDK/PHP et configuration DMARC/DKIM, et trois récits clients. Aucun lien d'aide n'a été fourni manuellement. Les observations suivantes sont un contrôle des sorties disponibles, pas la validation du parcours entier.

| Étape | Revue /10 | Observation |
| --- | --- | --- |
| Import | 8 | 12 pages, 11 571 mots ; documentation effective mais couverture bornée, non exhaustive. |
| Compilation | 8 | 308 entrées ; prix rattachés aux plans et quotas, exemples API séparés des prix du produit. |
| Catalogue | 7 | Faits atomiques rattachés au ledger et visibilité conservée ; adéquation à une audience non évaluée. |
| Concurrents | 7 | Six alternatives plausibles ; provenance et limites des pages lues, neuf affirmations non retrouvées écartées. |
| Positionnement | 7 | Aucune exclusivité inventée : 27 propositions sans correspondance à vérifier, zéro différence démontrée. Utilité comparative partielle. |
| Audiences, recherche, dossier | Non notés | Carte interrompue par le quota avant son premier appel terminé. |
| Génération, consultation | Non notées | Aucun email Loops disponible. |

La compilation conserve notamment la distinction entre un montant de facture fictif dans un exemple d'API (E69) et le prix du plan Growth sous ses conditions (E240). Les six profils sont Customer.io, Resend, Postmark, Mailchimp, SendGrid et une application utilisant Amazon SES. Les raisons de concurrence restent des hypothèses sourcées. Aucun dossier n'a été fabriqué pour contourner l'étape manquante.

## Appels, durée et vérifications

| Opération | Appels terminés | Durée écoulée | Estimation affichée |
| --- | --- | --- | --- |
| Papier acquisition | 26 | 140 s | 2,3961 USD |
| Papier considération | 26 | 138 s | 2,2113 USD |
| systeme.io acquisition | 26 | 174 s | 2,8510 USD |
| systeme.io séquence interrompue | 12 | 157 s | 2,4898 USD |
| Loops compilation interrompue | 8 | 133 s | Non fournie dans le compteur du job |
| Loops compilation après rétablissement | 9 | 163 s | Non fournie dans le compteur du job |
| Loops scan unique terminé | 7 | 160 s | 2,3680 USD |
| Loops carte interrompue | 0 | Voir snapshot | Aucun appel terminé |

**114 appels terminés** au total ; six appels de la séquence ont commencé sans réponse terminée, et les échecs des jobs de préparation restent dans leurs snapshots. Aucun retry transport n'est recensé dans les journaux des campagnes. La tentative de scan refusée pour concurrence HTTP 429 n'a pas créé de job ; la reprise après libération d'une place est conservée. Ces compteurs n'effacent pas le coût des tentatives de compilation échouées.

L'addition des estimations disponibles est 12,3162 USD et **exclut les deux compilations** : ce n'est pas le coût complet du parcours, ni une facture. Les appels utilisent le quota d'abonnement configuré. Les durées ne sont pas des minutes de travail humain économisées ; aucun chronométrage humain exploitable n'a été réalisé. Voir [métriques](../optimization/acceptance-2026-11-01/metrics.json).

Vérifications initiales : 2 147 tests backend et 37 tests frontend réussis ; lint backend/frontend, types et contrat API conformes. Après correction de l'avertissement : test API ciblé réussi, lint backend et frontend conformes, 37 tests frontend réussis ; **2 148 tests backend réussis, deux avertissements de dépendances**, consignés dans [son journal](../optimization/acceptance-2026-11-01/backend-tests-after-advice.log) et dans l'état d'audit. Le script de comparaison directe est préparé et compilable ; son exécution réelle est en attente.

## Décision restante et reprise

La valeur précise observée est la transformation de connaissances réutilisées en emails sourcés, lisibles et exportables. L'avantage sur une rédaction directe avec les mêmes informations reste non mesuré. Aucun prix de vente, marge, résultat client ou volonté de payer n'est déduit de ces tests.

Le fournisseur a refusé les derniers appels avec un quota épuisé et une reprise annoncée à **7:55 AM**, sans fuseau explicite. Le CLI Claude disponible n'est pas connecté. Aucun achat ni changement des réglages globaux n'a été effectué. Les données sont conservées dans une copie SQLite distincte ; la base de travail initiale n'a pas été migrée ou réécrite par cet audit.

Restent exactement : terminer la préparation et les deux cas Loops ; réexécuter la séquence interrompue après retour du quota en conservant sa première tentative ; effectuer les deux retouches réelles prévues et leurs contrôles UI ; faire les trois comparaisons directes bornées ; appliquer le verdict prévu. Les [instructions de reprise](../optimization/acceptance-2026-11-01/resume.md) conservent les identifiants et l'ordre. Aucune nouvelle génération n'est nécessaire pour valider la correction déterministe de l'avertissement.

Méthode : skill `marketingos-brand-audit`, complétée par `campaign-optimization`. L'audit s'arrête sur ce blocage externe, sans transformer une insuffisance de quota en insuffisance commerciale du produit.


## Reprise du 2 novembre 2026

La connexion Claude Pro est rétablie et vérifiée (`claude.ai`, `subscription`, aucune clé API transmise). La disponibilité GPT a également changé après l'interruption : deux témoins directs et la reprise unique de la séquence utilisent le modèle GPT original. La recherche et le dossier Loops ainsi que les retouches utilisent Claude Opus, choix explicites locaux aux essais.

**Nouveaux résultats acquis :** les deux retouches réelles sont terminées. Papier : un appel, trois paragraphes, raccourcissement modeste (139 à 134 mots avec en-têtes), proposition acceptée, copie/export exacts puis original restauré. systeme.io : un appel, formulation des tunnels/sites précisée, affiliation et limite conservées ; « Adjust further » ouvert sans troisième job, proposition refusée, copie/export de l'original vérifiés. Les nouveaux contrôles sont enregistrés sur chaque proposition, sans réutilisation du score des lecteurs. Deux avis non bloquants restent assez littéraux (emploi de E464 et dictionnaire de CTA). Voir `revision-review.json` et les captures `revision-diff.png` de chaque cas.

**Comparaison directe :** les deux appels uniques GPT produisent des textes utilisables et parfois plus concis. Ils n'établissent pas de supériorité rédactionnelle générale de MarketingOS. Le produit apporte ici un parcours réutilisable de connaissances, de contraintes, de contrôles, de versions et de HTML/export. Aucun gain de temps humain n'est mesuré. Le troisième témoin n'est pas lancé : aucun email Loops comparable n'a été livré pour l'audience retenue. Voir `direct-comparison-partial.json`.

**Loops : les deux cas ordinaires n'aboutissent pas sans apport supplémentaire de preuves.** La carte enregistrée propose sept audiences ; la première exacte porte sur la migration des emails d'authentification Supabase/Clerk avant lancement. La recherche récupère huit sources, retient cinq problèmes et écarte huit éléments invérifiables. Le dossier classe un problème ADDRESSED, un PARTIAL et trois UNSUPPORTED, avec trois questions sans réponse. Les précontrôles acquisition et considération sont `DISCOVERY_ONLY`, dérogation exigée. Aucune dérogation n'est utilisée : ces deux cas restent dans les six cas ordinaires et ne sont pas remplacés.

Le défaut est le passage d'une audience exploratoire dont les intégrations sont nommées à une campagne supposée réalisable avec la couverture documentaire importée. Le garde-fou évite de promettre une résolution du bridage ou des problèmes d'authentification sans preuve. Il reste nécessaire de vérifier le workflow critique et la couverture des guides avant de présenter cette audience comme prête. Certaines réserves portent également sur des faits absents de la sélection plutôt que du ledger entier : les limites d'envoi figurent dans les connaissances, alors que le dossier les dit non établies par ses seules preuves sélectionnées. Cela ne résout toutefois pas les lacunes sur le routage d'authentification et les limites propres à Supabase.

La première carte a survécu dans SQLite ; ses compteurs de modèle étaient locaux au processus précédent et n'ont pas été capturés à son terme. Leur coût reste inconnu et ne doit pas être compté comme zéro. Les nouveaux jobs et les retouches sont conservés séparément dans les métriques.


### Clôture du protocole

La séquence reprise `9e0c2c32-ff40-4d41-b3f7-52259240ae8e` a terminé en 798 secondes, 70 appels, estimation affichée 8,1956 USD, 1/3 email livré. Son arrêt n'est pas un échec de quota : le gate de répétition rejette « si vous passez par mes recommandations », dans une déclaration d'affiliation pourtant requise dans les emails. L'exemption existante couvrait d'autres formulations, mais pas cette clause capturée. La correction ajoute seulement cette déclaration fermée et le suffixe d'identité « sans appartenir à la marque ». Elle conserve les contrôles sur les promesses répétées, les mauvais noms de marque et les faits. Les 42 tests de gates passent ; la suite complète est enregistrée dans `backend-tests-after-overlap.log`. Aucun livrable déjà produit n'est modifié pour masquer l'échec ; aucune séquence complète après correction n'est revendiquée.

Les coûts affichés sont des estimations d'usage, et non des débits d'un solde API. Le compteur connu atteint au minimum 191 appels terminés sur l'audit, essais interrompus compris ; le compteur de la carte Claude a été perdu avec l'ancien processus, de sorte que le total exact reste inconnu. Les contrôles de code, métriques et journaux sont liés à l'état sauvegardé.

Le défaut restant à traiter pour élargir la promesse est précis : vérifier que la documentation disponible couvre le workflow décisif de l'audience avant de la présenter comme prête, ou compléter automatiquement les guides découverts sous un budget borné. Une intégration nommée ne suffit pas à prouver une migration complète. Les tarifs et limites déjà connus doivent aussi être accessibles au dossier au-delà de sa seule sélection initiale. Ces corrections devront garder la première audience du cas de régression ; choisir une audience plus facile ne démontrerait pas la réparation.


Validation finale après le correctif : **2 149 tests backend, 42 tests ciblés de gates et 37 tests frontend réussis** ; Ruff, ESLint, TypeScript et contrat API conformes. Aucun appel modèle acheté pour tester le correctif déterministe. Les serveurs temporaires sont arrêtés et la copie SQLite est conservée.
