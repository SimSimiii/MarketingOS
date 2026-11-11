# Validation commerciale multi-marques — 31 octobre 2026

## Conclusion

MarketingOS produit des brouillons factuellement prudents et modifiables, mais la qualité commerciale n'est pas assez régulière pour promettre des campagnes autonomes prêtes à envoyer. Cette validation soutient un pilote accompagné avec relecture. Elle ne démontre ni conversion ni volonté de payer.

Sur les trois marques effectivement générées, Papier est utilisable après une petite retouche. La séquence systeme.io est cohérente mais trop descriptive; CABAIA ne répond pas suffisamment au besoin choisi. Deux autres dossiers, Fathom et Senja, sont périmés et demandent une actualisation avant génération normale. Ils sont comptés comme réserves de préparation, pas comme tests de rédaction réussis ou ratés.

## Conditions et limites

- Copie SQLite cohérente par `sqlite3.backup`, migrée séparément. Base de développement non migrée et non utilisée pour ces générations.
- Sources, offres et audiences déjà présentes; pas de faits ajoutés à la main, pas de nouvelle compilation. Évaluation des sources sauvegardées, pas de leur actualité sur le web aujourd'hui.
- Modèle du preset existant `gpt-5.6-sol`, abonnement CLI. Preset **fast**, stratégie planifiée, plafond 400000 tokens et 900secondes par campagne. systeme.io ajoute la revue de séquence et au maximum une reprise de séquence.
- Les résultats ne mesurent pas le preset balanced par défaut. Les coûts sont les estimations enregistrées par MarketingOS, pas une facture d'abonnement.
- CABAIA a une réserve de support produit; génération en mode découverte explicitement consignée. Papier et systeme.io sont GO_NARROW et gardent leur sous-audience qualifiée.
- Grille interne de revue: faits25, audience/offre20, argument20, continuité15, finition10, absence de promesses indues/répétitions10. Notes de jugement, sans calibration commerciale.

## Résultats

| Cas | Livré | Durée | Appels modèle terminés | Verdict humain |
|---|---:|---:|---:|---|
| Papier, email anglais | 1/1 | 69s | 3 | Utilisable, ouverture un peu abstraite; 83/100 |
| Papier, retouche plus directe | 1 proposition | 21s | 1 | Amélioration concrète, 109→99 mots de corps; 85/100 |
| CABAIA, email français | 1/1, dégradé | 94s | 5 | Ne résout pas le besoin choisi; 62/100 |
| systeme.io, séquence française initiale | 1/3, dégradé | 175s | 9 | Incomplète, non scorée comme séquence |
| systeme.io, même séquence après premier correctif | 3/3, dégradé | 236s | 16 | Cohérente mais pas assez persuasive; 76/100 |
| systeme.io, retouche du deuxième email | 1 proposition | 15s | 1 | 125→91 mots; consigne et affiliation conservées |

Total: **35 appels modèle terminés**, échec initial et reprises inclus. Aucun retry transport enregistré pour les campagnes. Les quatre campagnes représentent environ **6,00USD d'estimation interne**, hors les deux retouches. Le détail tokens/durées est dans `metrics.json`.

## Ce que montrent réellement les textes

### Papier: un cas exploitable

L'email explique le planner physique, les16semaines non datées, les découpages d'objectifs et les vues mensuelle/hebdomadaire/quotidienne. E73/E74 documentent la structure; E464 documente les vues du produit. L'action Look inside dispose d'une provenance explicite vers le bon produit.

L'ouverture initiale « If a substantial client project needs a defined place away from screens… » est lourde. La retouche demandée sans ajouter de faits donne « A client project can take shape on paper across 16 undated weeks. » Le produit devient plus immédiat et les contrôles repassent sans problème. Le texte reste sobre plutôt qu'irrésistible; la recherche d'audience actuelle contient des observations périphériques sur Obsidian, donc ne pas surinterpréter le ciblage.

Preuves: `papier/email-1.txt`, `papier/revision.txt`, `papier/knowledge.json`, `papier/advice.json`.

### CABAIA: prudence correcte, adéquation insuffisante

Le besoin est de réunir ordinateur, repas et gourde dans un sac quotidien. Le dossier signale une preuve produit manquante. L'email propose de commencer par vérifier la poche rembourrée jusqu'à14pouces d'un sac de voyage Duffle Adventurer (E703), puis de poursuivre l'examen.

Il n'invente pas que le repas et la gourde rentreront. Mais il ne donne donc pas une raison suffisamment forte d'acheter pour ce besoin, insiste sur ce qu'on ignore et termine par une personnification maladroite du sac. Le statut dégradé et le doute du lecteur concordent avec cette revue. Une autre réécriture ne prouverait pas les dimensions utiles ou le rangement manquant: il faut documenter l'adéquation produit ou choisir un besoin mieux couvert.

Preuves: `cabaia/email-1.txt`, E703 dans `cabaia/knowledge.json`, `cabaia/advice.json`.

### systeme.io: une séquence distincte, encore trop « fiche de comparaison »

Les trois axes sont distincts: petite gamme de produits physiques, inscription→contacts→séquence automatisée, puis distinction frais plateforme/frais processeur. Les affirmations examinées concordent avec E72/E101/E102, E49/E13 et E138/E144. Le texte ne transforme pas0% de frais plateforme en gratuité de tous les paiements.

Les corps font140,125 et127mots. La mention d'affiliation est présente dans chaque email. La phrase « Est-ce adapté à votre prochain livre ? » n'apparaît qu'à la fin du corps du deuxième; elle reste présente après sa retouche à91mots.

Le défaut commercial est visible: « comparer », « vérifier », « examiner » occupent la place du bénéfice. E101 établit pourtant fiches produits, variantes, stocks, frais de livraison, commandes et paiement. Le premier email utilise surtout le périmètre et les exclusions, alors que des mécanismes opérationnels déjà sourcés pourraient expliquer son intérêt. Les trois lectures restent à6/10, mesure simulée et non calibrée; mon jugement ne repose pas sur cette note seule.

Preuves: `systeme-retest/email-1.txt`, `email-2.txt`, `email-3.txt`, `revision.txt`, `knowledge.json` et `execution.json`.

## Défaut technique trouvé et corrigé

Le contrôle de répétition rejetait « affilié indépendant de systeme.io », alors que la transparence de l'affiliation est obligatoire dans chaque email. Le premier essai échoue à email2 et ne livre qu'un email sur3.

Le premier correctif exclut de la comparaison de variété des clauses de déclaration reconnues, liées au nom exact de la marque. Il ne supprime pas le paragraphe entier et ne modifie pas les contrôles factuels, les objets ou le reste des arguments. Le rejeu livre les3emails mais met en évidence un deuxième appel au même contrôle dans la revue de séquence, qui ne recevait pas le nom de marque.

Le correctif final propage cette identité à `SequenceReviewer` depuis le pipeline. Les mêmes trois textes passent ensuite le contrôle déterministe complet (`systeme-retest/corrected-sequence-check.json`, résultat vide). **Pas de troisième campagne payante après cette dernière propagation**: vérification par rejeu déterministe des vrais textes et tests du pipeline. Le snapshot du deuxième run conserve honnêtement son statut et ses alertes historiques. Sa faiblesse persuasive reste réelle, indépendamment du faux positif corrigé.

## Rendu et vérifications

Les HTML des cinq emails finaux ont été ouverts dans Chromium à390 et1280px: pas de débordement horizontal, CTA présents et URL cohérentes avec les destinations sourcées. Captures conservées; revue visuelle des emails représentatifs. Cela ne remplace pas une campagne de compatibilité Outlook/Gmail.

La retouche Papier passe tous les contrôles. Celle de systeme.io conserve un avertissement non bloquant sur le libellé du CTA, absent de la liste fermée des actions de l'offre; la destination reste la page officielle de fonctionnalités. Aucun verdict de lecture de l'ancienne version n'est présenté comme validation de la nouvelle.

Validation automatisée finale: voir `validation.json` (suite backend, Ruff, frontend lint/types/tests, contrat API).

## Priorités avant une promesse de libre-service autonome

1. Faire réellement utiliser au plan et au rédacteur les mécanismes opérationnels disponibles, au lieu de transformer chaque email en invitation à vérifier une fiche.
2. Mieux traiter les besoins insuffisamment documentés et les dossiers périmés avant génération; davantage de réécritures ne fournit pas les preuves manquantes.
3. Conserver la relecture humaine des affirmations et du ciblage. Cet essai ne lève pas la limite connue du contrôle sémantique des affirmations reformulées sans chiffre.

La prochaine validation commerciale utile serait une livraison accompagnée à des utilisateurs cibles, mesurant le travail de correction et l'acceptation des textes. Aucun résultat de vente, d'ouverture ou de conversion n'est revendiqué ici.
