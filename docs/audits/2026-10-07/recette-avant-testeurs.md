# Recette de sortie — MarketingOS

À exécuter **après les corrections**, sur une révision candidate identifiée. Cette liste est un plan de validation, pas une liste de tests déjà réussis. Les vérifications réellement exécutées le 7 octobre 2026 sont consignées dans [preuves.json](./preuves.json). Les tickets cités sont détaillés dans [le rapport](./rapport-global.md).

Le [bilan des corrections du 9 octobre](corrections.md) et [leurs preuves](preuves-corrections.json) décrivent l’état courant. Les contrôles automatisés n’ont pas coché les scénarios nécessitant navigateur, cloud, PostgreSQL ou Stripe. La migration `b7a109c4e2f8` doit être appliquée à une base correctement versionnée et sauvegardée avant déploiement des deux APIs.

## Règle de validation

Pour chaque scénario, conserver : révision et configuration non sensible, environnement, date, résultat, capture ou journal, anomalie restante et responsable. Ne jamais joindre de clé, de cookie, de donnée client ou de document confidentiel. Une case cochée exige une preuve sur la version livrée. Un scénario hors périmètre doit être explicitement exclu de l'offre et de l'interface ; il ne devient pas « réussi ».

Commencer avec données fictives, provider simulé et moyens de paiement de test. Les campagnes réelles sont réservées aux questions de qualité du modèle, avec budget défini. Les interruptions destructives et restaurations se font en environnement isolé.

Fiche de campagne de recette :

| Champ | À remplir |
| --- | --- |
| Révision candidate et date | |
| URL de préproduction et mode d'hébergement | |
| Mode fournisseur et facturation activée ou non | |
| Base, version de migration, versions des dépendances | |
| Périmètre : langues, types d'offre, nombre d'emails | |
| Budget maximal de recette et du pilote | |
| Responsable et lien vers les preuves | |

## A. Prérequis techniques — avant tout testeur distant

- [ ] **A01 — Installation propre (BE-01/02, SEC-01, OPS-05).** Depuis les fichiers livrés, installer backend et deux frontends dans un environnement neuf. Imports, migration, lint, suites, génération du schéma et builds réussissent. Aucun paquet indispensable fourni seulement par le venv du développeur. Dépendances signalées traitées et nouvelle analyse conservée.
- [ ] **A02 — Trajet distant (BE-03/06, OPS-01).** Dans le navigateur, se connecter sur le vrai domaine HTTPS et terminer une campagne simulée. Vérifier API, cookies, CORS/proxy, liens profonds et rechargement d'une URL de marque/campagne/run. Le résultat doit être visible sans console développeur.
- [ ] **A03 — Base de production (OPS-02).** Monter les migrations depuis une version précédente représentative sur PostgreSQL si c'est la base livrée. Exécuter les cas de contraintes et transactions concurrentes. Vérifier la procédure de rollback compatible avec les données, sans se contenter d'une base vide.
- [ ] **A04 — Sauvegarde et incident (OPS-03).** Restaurer une sauvegarde dans une base isolée, retrouver sources et résultats. Simuler DB indisponible : readiness échoue, l'alerte arrive au bon destinataire, le client voit un message exploitable. Documenter délai et perte maximale acceptés.
- [ ] **A05 — Voie Step Functions, seulement si livrée (BE-03 à BE-06).** Prouver le dispatch depuis l'API, les accès réseau, la conservation de l'identifiant après erreur, l'état terminal en DB et l'idempotence de plan/craft/finish. Rejouer une étape sans perte des résultats ni double dépense. Sinon marquer cette voie non supportée.

## B. Comptes, isolation et données — avant tout testeur distant

- [ ] **B01 — Invitation et récupération (PROD-02).** Un nouveau testeur reçoit son accès, se connecte et récupère un accès perdu avec la procédure annoncée. L'UI ne lui demande pas d'exécuter un script. Les états invitation invalide/expirée sont compréhensibles.
- [ ] **B02 — Deux comptes (SEC-02, OPS-01).** Avec A et B, essayer lecture, modification, suppression, téléchargement et lancement sur les identifiants de l'autre : marques, sources, campagnes, exécutions, journaux et crédits. Refus sans fuite de contenu. Vérifier aussi accès anonyme et séparation admin/client.
- [ ] **B03 — Sessions (SEC-03/04, UX-04).** Tester expiration, refresh, nouvel onglet, révocation globale et logout en réseau normal puis coupé. Une déconnexion échouée ne doit pas afficher un succès trompeur ; un 401 ne doit pas devenir une page vide ou « compte local ».
- [ ] **B04 — Abus et entrées (SEC-02, BE-09, OPS-04).** Tester rafales de connexion, limites de taille, chaîne très longue et `limit` excessif. Rejet borné et explicite ; les contrôles couvrent le point d'entrée réellement déployé, sans exposer un accès alternatif non protégé.
- [ ] **B05 — Suppressions (BE-10/11, SEC-06).** Créer une campagne avec état de run et la supprimer ; traiter une marque avec dépendances selon la politique annoncée. Pour compte crédité, vérifier conservation financière et traitement des données personnelles. Aucun 500 par clé étrangère ni données rendues accessibles à un autre compte.
- [ ] **B06 — Information et assistance (SEC-06/07, PROD-02/03).** Le testeur trouve quelles données sont utilisées, par quels services, pour quelle durée et comment demander export/suppression. Le support reste joignable après blocage ou suspension. Les conditions correspondent au fonctionnement réel.

## C. Sources et création de campagne — avant tout testeur distant

- [ ] **C01 — Imports nominal et vide (BE-08/09).** Importer URL pertinente, texte et document supporté. Afficher ce qui a réellement été lu. Une page vide, trop courte, uniquement JavaScript ou un document illisible ne doit pas produire « ajouté » sans source exploitable.
- [ ] **C02 — Imports difficiles (BE-08/09, UX-03/04).** Simuler lenteur, timeout, URL refusée, page secondaire inaccessible, fichier trop gros et échec partiel multi-sources. Montrer résultat par source et possibilité de reprise ; conserver le brief et les sources déjà importées. Ne pas dépendre d'une requête plus longue que le proxy ne l'autorise.
- [ ] **C03 — Premier brief (UX-01/02, IA-03).** Sans formation, choisir le type de campagne, renseigner les éléments obligatoires et comprendre ce qui manque. Les champs indiqués facultatifs le sont réellement. L'offre, la langue, le CTA et la quantité sont confirmés avant lancement.
- [ ] **C04 — Conservation et remise à zéro (UX-02/03).** Quitter vers la gestion des sources, revenir, fermer/rouvrir et rafraîchir selon le contrat annoncé : aucune perte silencieuse du brouillon. Créer une deuxième campagne : aucun objectif de la première n'est repris par erreur.
- [ ] **C05 — Modifier avant relance (UX-02).** Corriger le brief, le nom, la destination ou la source et lancer une nouvelle version ; l'ancien résultat reste consultable avec son contexte. Le client n'a pas à recréer tout son espace pour corriger un champ.
- [ ] **C06 — API indisponible (UX-04, PAY-07).** Couper successivement les routes marque, connaissances, compte et crédits. Afficher erreur/retry distincts des états « aucun élément ». Aucune recompilation ni dépense décidée simplement parce qu'une lecture a échoué.

## D. Exécution et qualité — avant tout testeur distant

- [ ] **D01 — Coût et quantité (PAY-01, IA-03).** Afficher sources, nombre d'emails, compilation éventuelle, quota et plafond avant lancement. Refuser une demande structurellement incompatible avec le budget proposé ou permettre une réduction explicite. Aucun nombre fictif présenté comme coût garanti.
- [ ] **D02 — Double clic et concurrence (BE-03/07, OPS-01).** Double clic, deux onglets et quelques comptes simultanés ne créent pas deux dépenses involontaires. Admission/attente/rejet sont expliqués. Le déploiement respecte la contrainte de processus unique tant que le registre n'est pas partagé.
- [ ] **D03 — Navigation et suivi (UX-05).** Quitter le run, revenir et recharger. Le suivi affiche la phase et la fraîcheur des données ; il ne promet pas du temps réel si une actualisation manuelle est nécessaire. Les résultats terminés sont retrouvables depuis la liste.
- [ ] **D04 — Annulation et panne (BE-07).** Simuler annulation entre deux étapes, erreur provider, dépassement de budget puis arrêt brutal du processus. Les emails déjà acceptés sont préservés selon le contrat annoncé ; l'état final et le coût sont expliqués. Aucun run indéfiniment « en cours ».
- [ ] **D05 — Tâches annexes (BE-11).** Lancer compilation/recherche, fermer la page puis redémarrer le service de test. Retrouver résultat ou diagnostic explicite, sans réception de job définitivement perdue. La reprise ne double pas la dépense.
- [ ] **D06 — Source insuffisante (IA-01/02, UX-06).** Fixtures sans prix/preuve, conditions contradictoires, garantie avec exceptions et CTA absent : obtenir questions ou brouillon prudent. Aucun bénéfice universel inventé ; le message sur la dépense reflète les appels déjà effectués.
- [ ] **D07 — Qualification modèle (IA-01 à IA-04).** Sur les usages réellement proposés, relire les résultats bruts et noter exactitude, compréhension, spécificité, progression, action et retouches. Traiter séparément chaque erreur factuelle matérielle. Le probe iFixit ne remplace pas une validation de séquence si cette catégorie est vendue.
- [ ] **D08 — Livraison et export (IA-05, UX-11).** Copie objet/preview/texte/HTML et export produisent exactement le contenu sélectionné. Vérifier liens, accents, placeholders et signature. Si édition sauvegardée livrée, conserver l'original et distinguer la version humaine.

## E. UI, responsive et clients email — avant tout testeur distant

- [ ] **E01 — Captures actuelles (UX-08/09).** Vérifier compte vide, compte rempli, import, brief, run actif, résultat partiel, erreur et paramètres à 360, 390, 768 et 1440 px. Aucun CTA masqué, défilement horizontal involontaire ou modal impossible à terminer. Conserver les captures de la version candidate.
- [ ] **E02 — Clavier et lisibilité (UX-08/09).** Parcours sans souris, focus visible et correctement géré dans les dialogues, labels et messages d'erreur lisibles par lecteur d'écran, zoom 200 %, contrastes mesurés. Les statuts ne reposent pas uniquement sur la couleur.
- [ ] **E03 — Langue et terminologie (UX-10, PROD-01).** Langue du brief, de la génération et du produit conforme au périmètre annoncé. Expliquer crédit, quota et livraison partielle. Pas de jargon opérateur ni de promesse « tout est vérifié » qui excède les contrôles réels.
- [ ] **E04 — Rendu email (IA-05).** Envoyer seulement vers des boîtes de recette autorisées : Gmail, Outlook et Apple Mail retenus dans la matrice de support, desktop/mobile, images bloquées et modes clair/sombre. Vérifier CTA et merge tags après passage dans l'outil d'envoi choisi. L'aperçu navigateur seul ne valide pas ce scénario.

## F. Paiements — obligatoires seulement avant activation des achats

- [ ] **F01 — Réservation et tarif (PAY-02/04).** Pour chaque modèle autorisé, vérifier nom demandé/résolu, tokens cache, règles d'arrondi et prix datés. La réserve est réaliste et compatible avec les packs pour l'usage vendu. Montrer séparément disponible, réservé et consommé.
- [ ] **F02 — Contrôle des options (PAY-05).** Envoyer les overrides directs et imbriqués via toutes les routes de création/modification/lancement : aucun contournement du catalogue payant. Les mêmes règles s'appliquent au frontend et aux appels API.
- [ ] **F03 — Plafond effectif (PAY-01/03).** Avec un solde limité et deux jobs concurrents, aucune dépense ne dépasse le plafond accepté. Refus avant appel : réserve libérée. Appel au statut fournisseur ambigu : retenue expliquée et réconciliable, sans double facturation.
- [ ] **F04 — Achat nominal et retard (PAY-06/07).** Stripe test : succès, annulation, retour avant webhook, retour absent, webhook retardé et deux onglets. Crédit attribué exactement une fois et statut visible jusqu'à résolution, même après vingt secondes.
- [ ] **F05 — Webhooks désordonnés (PAY-06, OPS-02).** Rejouer doublons, concurrence et ordre inversé sur la base de production choisie. Vérifier signature invalide refusée et rapprochement montant/devise/compte ; aucune attribution supplémentaire.
- [ ] **F06 — Remboursement et litige (PAY-06, PROD-03).** Remboursement partiel/complet, crédits déjà consommés, suspension et résolution du litige : état comptable cohérent, actions opérateur tracées et aide toujours accessible. Ne pas effectuer ces essais avec de vrais paiements pendant la recette technique.
- [ ] **F07 — Quotas et historique (PAY-07/08).** Le client distingue quota d'exécution et crédit acheté avant de payer. L'historique permet d'identifier date, run, achat, réserve, règlement et remboursement. Aucun achat rendu inutilisable par une limite cachée.
- [ ] **F08 — Prix périmés et justificatifs (PAY-09, PROD-03).** Simuler expiration de la revue des prix : préserver accès au compte, historique et support, bloquer proprement les seules nouvelles dépenses concernées. Retrouver reçu et conditions applicables à l'achat.

## Décision de lancement à consigner

**Pilote privé :** A à E validés sur le chemin retenu, exclusions visibles, aucun P0 ouvert sur ce chemin, assistance et budget définis. Une fonctionnalité payante désactivée permet de différer F ; elle ne permet pas d'ignorer la maîtrise de la consommation fournisseur.

**Vente :** recette privée + F validées, aucun P0/P1 financier ouvert, conditions et traitement des données adaptés au marché.

**Après les premiers retours :** consigner séparément bugs, difficultés de compréhension, qualité des emails et volonté de payer. Les testeurs doivent juger l'utilité du produit ; la recette technique ci-dessus doit avoir été faite avant leur arrivée.
