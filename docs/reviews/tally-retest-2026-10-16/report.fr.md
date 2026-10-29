# Contre-vérification du cas Tally — 16 octobre 2026

Ce document conserve le diagnostic initial. Voir [les corrections du 17 octobre et
l'essai qualitatif](../tally-reliability-followup-2026-10-17.md) pour l'état actuel.
Les scripts de ce dossier ont été rejoués après correction ; leurs sorties JSON
peuvent donc refléter ce dernier rejeu. Les exports sources et le manifeste initial
restent inchangés.

## Conclusion

**Les corrections sont partielles.** La suite de régression passe, mais la reprise des données exactes de Tally retrouve encore des défauts importants. Le précédent bilan d'implémentation ne démontrait pas la résolution de tous les symptômes de cette analyse externe.

Ce contrôle ne modifie pas le code produit. Il sépare les garanties des tests scriptés, les défauts reproduits avec le code actuel et les questions qui nécessiteraient une nouvelle génération ou une évaluation qualitative.

## Périmètre et méthode

- Branche conservée : `master`. Aucune branche Git nommée Tally n'a été trouvée ; la marque locale correspondante est **Tally--Test**.
- Retrouvé l'email exact **« Put Tally before your automation »**, son brief, sa recherche d'audience, son dossier et son scan concurrentiel.
- Copie en lecture seule des lignes propres à cette marque : 380 faits, 11 documents sources / 107 174 caractères, un scan, une carte d'audiences, une recherche approfondie, un dossier, une campagne, une exécution et huit candidats Proof.
- Rejoué les fonctions déterministes actuelles sur ces données et sur des cas synthétiques explicitement identifiés. Les scripts et résultats sont conservés dans ce dossier.
- Aucun appel modèle, campagne réelle, recherche web, migration de la base utilisateur ou réécriture de l'email historique.

La suite générale a été relancée : **1 608 tests backend réussis**, deux avertissements de dépréciation de dépendances, environ **177 secondes**. Côté frontend : **24 tests réussis**, ESLint, TypeScript et compilation statique réussis. Ruff, contrat API généré et migrations sur base temporaire réussis.

Ces résultats ne signifient pas que tous les critères de l'analyse Tally sont satisfaits. Les tests d'acceptation supplémentaires restent hors de la suite normale pour conserver leurs échecs visibles et reproductibles sans modifier artificiellement les anciens tests.

## Résultats par problème

| Point de l'analyse | Résultat du contre-test | Statut |
| --- | --- | --- |
| Témoignages différents assimilés à la même preuve | Les sept propositions de preuve propres à Tally ne sont plus toutes ramenées au même territoire commun ; les exemples synthétiques contrastés ne sont plus équivalents par catégorie. | Corrigé sur les cas testés |
| Absence capturée présentée comme une avance concurrente | La formulation « Where the field is ahead » disparaît ; les limites de capture et l'absence de conclusion sur les capacités sont explicites. | Corrigé dans la présentation |
| Domaines personnalisés et retrait de marque mal représentés | E296/E297 sont toujours classés `other` et écartés par la sélection globale des 30 faits ; E126 est classé `breadth`. La reconstruction n'a aucun argument propre à Tally dans `control`. | Non corrigé |
| Prix de concurrents traités comme nos propres arguments | Neuf prix de concurrents issus de la page comparative Tally occupent les propositions propres à Tally. Même un contexte explicite `vendor_comparison` ne suffit pas à les retirer de cette sélection. | Non corrigé |
| Devises, périodes, unités et conditions tarifaires | Les cas simples de devise/période/unité passent. Certaines formulations comme `billed yearly` ou `annual payment required` restent ignorées. Les citations à plusieurs prix, présentes dans le vrai corpus, restent problématiques. | Partiel |
| Vocabulaire normal du produit pénalisé | Le contre-test avec form/submissions/data/integrations ne provoque pas d'avis de réécriture. | Corrigé sur le cas testé |
| Une citation présente considérée comme une interprétation correcte | La recherche enregistrée affirme que la simplification du module natif complique le traitement ; sa citation dit qu'elle le rend plus facile. Le rapprochement textuel ne détecte pas cette inversion. | Non corrigé |
| Audience « automatisation sans responsable » reliée à « webhook gratuit » | La substitution mécanique par le premier problème est corrigée. Mais le rejeu du vrai dossier devenu périmé conserve le problème de redirection sans lien avec le webhook gratuit. Un dossier synthétique marqué courant efface ce problème non relié, sans modifier l'idée principale ni le mécanisme. | Partiel, échec reproduit sur l'historique |
| Nouveauté non étayée | Le contrôle prévu pour « new feature/just launched » fonctionne, mais la formulation exacte « Tally is now available… » passe sans signalement. | Non corrigé pour cet email |
| Résultat client généralisé ou transplanté | Avec les vraies sources complètes, « Tally gets you 30%+ response rates with Make, Zapier or n8n » passe sans avertissement. Un contexte client synthétique ajouté au vrai résultat permet de signaler certaines formulations, mais pas celle-ci. | Partiel, contre-exemple non couvert |
| Affichage des estimations de réaction | Les cartes affichent des évaluations simulées, mais le pipeline émet encore « % of them are estimated to bite ». Le calcul interne du score à partir de clics fictifs demeure. | Partiel |
| Proof avec statuts plutôt qu'un pourcentage | Le nouveau contrôle de citation et les statuts sont couverts par des tests. Les huit anciennes lignes restent historiques et non certifiées rétroactivement. | Corrigé pour les nouvelles recherches, historique conservé |
| Proof réunissant les faits connus et les trouvailles selon l'argument | Les preuves approuvées sont fusionnées dans les connaissances d'une campagne, mais la vue Proof ne réunit pas les preuves du corpus et les nouvelles avec un classement par argument. La recherche reste générique à la marque. | Non corrigé dans ce parcours |
| Campagne fonctionnelle sans témoignage | Les tests de preflight et de pipeline autorisent une fonctionnalité documentée sans inventer de résultat client. | Corrigé sur les tests scriptés |
| Données inconnues et contre-indications d'audience | Compatibilité inconnue, preuve du problème, usage/achat et accès sont séparés ; les contre-indications portent une conséquence visible. Cela ne valide ni l'achat ni l'adéquation sémantique de chaque segment. | Corrigé mécaniquement, portée limitée |
| Temps gagné et meilleure campagne face à une génération simple | Aucun comparatif aveugle à informations égales ni mesure de retouches/temps humain n'a été effectué dans ce contre-test. | Non mesuré |

## Ce que révèle le cas original

Le rapport enregistré avait déjà `run_status=degraded`, `clean=true` et `landed=false`. Il signalait explicitement que créer le formulaire ne suffisait pas à résoudre le problème opérationnel de l'audience. Il serait donc inexact de présenter cette campagne comme ayant été validée sans réserve par tous les contrôles.

Cependant, signaler ce problème n'a pas produit un meilleur email dans l'artefact livré. La stratégie, la citation mal interprétée et la confusion de parcours restent des sujets distincts de la propreté formelle.

La citation sauvegardée explique que les données simplifiées du module natif sont **plus faciles** à traiter dans Make. L'observation structurée affirme qu'elles **compliquent** ce traitement et conseille le webhook générique. La vérification actuelle des citations conserve cette inversion : elle confirme la présence des mots cités, pas la conclusion. Le statut `grounded` ne suffit donc toujours pas à démontrer l'interprétation.

Dans un autre contre-exemple synthétique, supprimer un état antérieur inventé ne supprime pas l'explication `why_it_fails` qui s'appuyait sur cet état. Les vérifications déterministes ne signalent pas non plus une phrase qui mélange connexion native et endpoint personnalisé. Cela ne prouve pas qu'un modèle de critique la laisserait passer : aucun modèle n'a été interrogé.

Les **380 faits historiques n'ont aucun contexte structuré**. Les nouvelles structures ne reconstituent pas automatiquement les sujets, conditions et dates absents. Les vieux dossiers doivent rester identifiables comme historiques ; leur invalidation n'est pas une réparation de leur contenu.

Le nouveau positionnement reconstruit aussi **158 propositions contre 10 lignes auparavant**. Sa section de stratégie passe de **5 459 à 47 623 caractères**, soit environ **8,7 fois plus**, et reste transmise sans borne dédiée au Strategist. Le nombre d'étapes modèle ne monte pas, mais le volume de contexte augmente réellement ; aucune mesure de quota ou de latence d'un modèle réel n'a été effectuée.

Enfin, la base locale consultée est encore à la révision `2f7c2f4d9817` : les colonnes Proof `context` et `verification_status` y sont absentes. Les migrations temporaires passent, mais cela ne prouve pas que cette base locale a été mise à niveau. Elle n'a pas été modifiée pendant la vérification.

## Pièces reproductibles

- `manifest.json` : branche, révision, empreintes des fichiers de code et snapshots.
- `inputs/` : copies en lecture seule des artefacts exacts et des documents sources Tally.
- `positioning_probe.py`, `positioning-probe.xml`, `positioning-replay.json`, `positioning-findings.md` : **7 assertions réussies, 8 échouées**, plus 89 tests ciblés existants réussis.
- `facts_proof_probes.py`, `facts-proof-retest.json` : **3 protections présentes, 5 absentes sur 8 vérifications d'acceptation** ; 61 tests existants ciblés réussis. Le rejeu inclut la totalité des sources, pas seulement le ledger.
- `audience-chain-probe.py`, `audience-chain-results.json` : normalisation réelle, contre-exemples synthétiques, inversion du sens de la citation, évaluation des audiences et visibilité du fallback.

Les échecs ci-dessus sont des reproductions, pas une estimation statistique de la qualité générale de MarketingOS. Une nouvelle génération comparative serait nécessaire pour affirmer que l'email final est devenu plus convaincant ; elle n'a pas été lancée pour cette demande de vérification.
