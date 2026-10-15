# Préparation du test avec Mehdi — 13–14 octobre 2026

La plateforme peut faire l'objet d'un test privé accompagné. Cette vérification ne démontre ni une absence totale de bugs, ni la qualité de tous les secteurs, ni une rentabilité commerciale. Le résultat le plus utile maintenant est un essai de Mehdi sur une offre qu'il connaît vraiment.

## Compte de test

- Application : https://app.orqagent.com
- Identifiant : `mehdi-test@marketing.com` ; mot de passe choisi par le fondateur, non recopié dans ce rapport.
- Compte utilisateur normal, propriétaire de son propre espace, formule gratuite, quota de **50 exécutions mensuelles**, partagé avec les traitements de fond (compilation/recherche), compteur à zéro après nos vérifications.
- Connexion et lecture du profil : HTTP 200. Marques et campagnes : listes vides. Le jeton utilisateur est refusé par l'API administrateur : HTTP 401. Déconnexion : HTTP 204.
- Parcours API en production : création d'une marque, ajout d'une source texte et création d'un brouillon (HTTP 201), estimation et conseil de génération (HTTP 200), refus de lecture sans authentification (HTTP 401). Suppression des seuls objets de test (HTTP 204), espace à nouveau vide et compteur toujours à zéro. Aucune génération payante lancée avec ce compte.
- Inscription publique toujours fermée. Aucun email envoyé ; aucun service de messagerie ou boîte email créé.
- Création via une fonction Lambda temporaire accessible uniquement par IAM, avec écriture d'une trace d'audit dans la même transaction. Fonction supprimée après utilisation. Aucun mot de passe dans les fichiers de preuve.

## Corrections réalisées

**Analyse concurrentielle.** Des statistiques de croissance des inscriptions à un essai étaient classées comme des arguments de prix, uniquement à cause du mot `trial`. Le classement conserve les offres gratuites, les durées d'essai explicites et les catégories d'évidence, mais ne range plus ces statistiques dans le prix. Sept cas de régression ajoutés. Les analyses historiques sauvegardées restent historiques : elles ne sont pas automatiquement recalculées par cette correction.

**Interface de campagne.** Une campagne en cours affichait encore un bouton actif « Run campaign ». Le bouton affiche désormais « Campaign running » et reste désactivé tant que la page connaît une exécution en cours ou en attente. Vérification dans le navigateur avec une exécution locale synthétique, supprimée ensuite, sans appel de modèle. La protection serveur contre les lancements concurrents reste nécessaire lorsque la page n'est plus à jour.

**Export texte.** Le téléchargement fonctionnait, mais la version texte omettait l'URL du bouton présent dans le HTML. La persistance utilise maintenant la même destination validée pour les deux formats. Les copies et téléchargements des nouveaux emails conservent donc ce lien ; les checkpoints récupérés conservent le lien explicitement renseigné dans la campagne. La correction est déterministe, sans nouvel appel de modèle. L'exemple corrigé est `email.fr.corrected.txt`. Les anciens résultats ne sont pas réécrits silencieusement.

Commits : `cc822a607af2395660b457e0063f7b95c5100c18` (classement/bouton) et `16553a18e3345c59cfaf19ff21f52b3208ae9a16` (export), sur `master`. Seuls ces changements ont été inclus ; les autres modifications locales de l'interface ont été conservées. État du déploiement : voir `deployment-builds.json`, `export-deployment-build.json` et la note finale ci-dessous.

## Qualité de l'email français

Cas : un email pour des amateurs d'électronique francophones qui envisagent un premier kit et consultent l'offre américaine iFixit. Sources compilées existantes réutilisées ; aucune nouvelle recherche commerciale facturée. Exécution locale `b361b5d4-0808-4838-9b4f-2327f7843472`.

Un email livré en **7 min 20 s**, après deux réécritures. Estimation de traitement : **4,2364 USD**, pour 727 868 jetons d'entrée et 54 328 de sortie. Il s'agit d'un fonctionnement local sur abonnement CLI et d'une estimation, pas d'une facture fournisseur ni d'une mesure du coût de la même campagne sur les API de production.

**84/100 selon ma grille de relecture interne**, distincte du score simulé de lecteur de 6/10 affiché par la plateforme. Le rapport automatique conserve un avertissement sur les critères d'évaluation non satisfaits : il n'affirme pas que cet email est prêt à envoyer.

| Critère | Score | Observation |
|---|---:|---|
| Exactitude et sources | 25/25 | Composition du kit R2/R3 ; garantie US et exclusions R14–R19 ; lien vers les conditions R5 |
| Audience et clarté de l'offre | 18/20 | Produit et besoin de premier équipement compréhensibles |
| Argument et spécificité | 14/20 | Compare les embouts seuls aux outils d'ouverture et de manipulation ; reste descriptif |
| Objet, corps et action | 11/15 | Un lien clair vers la fiche ; préheader trop centré sur les restrictions |
| Rédaction et rendu | 7/10 | Français lisible et aperçu mobile correct ; paragraphe de garantie dense ; langue HTML déclarée en anglais |
| Promesses et répétitions | 9/10 | Pas de remise, urgence ou résultat de réparation inventé |

La liste d'exclusions est explicitement non exhaustive (« Parmi ceux documentés »), contrairement au défaut précédemment constaté. La portée américaine est nommée. Aucun tarif ni condition de livraison française n'a été inventé. Une simulation de lecteur suppose néanmoins un achat depuis la France, ce que la seule langue française ne permet pas de conclure : cette objection doit être traitée comme une hypothèse du lecteur, pas comme une information client.

Verdict : ce cas fournit une base utilisable après relecture de marque et retouches légères. Il ne valide pas une séquence entière, l'affiliation, tous les produits e-commerce ou une volonté de payer. Pour une vente réelle, vérifier à nouveau les sources commerciales à jour. Les fichiers `email.fr.txt`, `email.fr.html`, `knowledge.json` et le dossier `runs/` permettent de relire le résultat et ses preuves.

## Vérifications techniques et AWS

- Backend : **1 483 tests réussis**, deux avertissements de dépréciation existants ; Ruff propre. Le parcours d'authentification et l'isolation entre comptes font partie de cette suite.
- Frontend : lint et typecheck réussis ; **17 tests réussis**, après modification du bouton.
- Navigateur local : tableau de bord, brief, progression, résultat, aperçu HTML mobile et téléchargement texte vérifiés. Aperçu lisible sans débordement horizontal ; le cadre HTML défile. Ce n'est pas un test de rendu dans Outlook/Gmail ni un audit d'accessibilité complet.
- API Lambda : aucun événement d'erreur dans les points CloudWatch retournés sur les 24 dernières heures, avec très peu d'activité. Ce constat ne mesure pas une fiabilité en charge.
- Step Functions : seule l'exécution synthétique de récupération est visible au moment du contrôle. **Une campagne réelle complète par les API et Lambdas de production reste à valider.** La génération locale réussie ne remplace pas cette preuve.
- Cost Explorer : environ **11,07 USD estimés au niveau du compte AWS du 1er au 12 octobre inclus** ; principal poste WAF, environ 9,29 USD. Données différées, non isolées au projet, et période qui ne représente pas le fonctionnement futur de la nouvelle NAT Gateway. Ce montant n'est pas un budget mensuel.

## Ordre des prochaines actions

1. **Test accompagné de Mehdi**, sur un seul produit, une audience et un seul email. Le laisser découvrir l'interface avant de démontrer ; utiliser `tester-guide.en.md`. Faire ce premier lancement ensemble pour observer aussi le parcours de production et traiter immédiatement un éventuel échec.
2. **Corriger les blocages observés**, surtout accès, ajout de sources, compréhension du résultat, erreurs factuelles et récupération après échec. Refaire la même mission avec lui après correction.
3. **Mesurer et réduire attente/coût sur ce parcours précis.** Un email local en plus de sept minutes mérite une attention prioritaire. Examiner la taille du contexte utile et le nombre de lectures/réécritures avant d'ajouter des appels. Comparer une correction à qualité constante ; ne pas confondre estimation CLI et dépenses API.
4. **Corriger les détails déjà identifiés** : langue HTML correspondant au contenu ; concision des paragraphes de conditions ; ne pas déduire un pays de résidence de la langue du brief. Revoir aussi l'expérience du premier accès après pause d'Aurora.
5. **Choisir ensuite une seule amélioration produit** à partir de son travail réel : retouche ciblée d'un passage si la majorité du temps part en édition, meilleure préparation du brief si les sources manquent, ou export adapté si le transfert vers son outil d'emailing est le blocage.

Ne pas lancer maintenant un nouvel ensemble de fonctionnalités : davantage de canaux, un outil d'envoi, une automatisation d'affiliation ou un nouveau tableau de bord ne répondraient à aucun problème utilisateur encore observé. Pour l'affiliation, demander d'abord l'offre réelle, les sources autorisées et les contraintes de l'annonceur.

## Déploiement final — 14 octobre 2026

Les trois builds ont réussi : les corrections de classement, de bouton et d’export sont en production. Console : `cc822a6` ; API : `16553a1`. Après déploiement, application, santé API, disponibilité de la base et santé admin répondent HTTP 200 ; les campagnes sans authentification restent refusées (401). La vérification de disponibilité de la base a pris 0,25 s sur cet accès à chaud ; ce chiffre ne remplace pas un test de démarrage à froid. Preuves : `production-http-final.json`, `deployment-builds.json`, `export-deployment-build.json`.


## Mise à jour — session et test anglais
Le défaut de déconnexion immédiate a été reproduit dans le navigateur de production puis corrigé : l'URL API absolue du build console empêchait le parcours d'authentification sur le même domaine. La console utilise maintenant /api ; login, navigation et rechargement conservent la session. Commit 7cff914, build console 6445b7f5-4a36-45c2-a1de-6942185b4553 réussi. Capture : session-fixed-production.jpg.
Le compte de Mehdi dispose maintenant de 50 exécutions mensuelles, compteur conservé à zéro lors de la modification. Le guide anglais est tester-guide.en.md ; le budget détaillé est api-test-budget.fr.md. Le test local du produit actuel est documenté dans ../marketingos-self/report.fr.md. La correction d'admission des outils de recherche est déployée dans 3c16ee0 ; la dernière suite backend compte 1 488 tests réussis. Ces nouveaux constats remplacent les chiffres de quota et de suite précédente ci-dessus, sans réécrire les résultats historiques.

## Test anglais terminé — 15 octobre
Le rapport d'auto-marketing est ../marketingos-self/report.fr.md. Deux emails GPT ont été livrés en 8m45s ; relecture interne 84/100, avec une petite condition ajoutée séparément au second pour un compte sans résultat. Le rapport automatique conserve sa réserve d'audience. Versions relues : ../marketingos-self/gpt-enriched/email-1.reviewed.en.txt et email-2.reviewed.en.txt. Équivalent des jetons API : 2,71–5,04 USD pour les deux emails, hors préparation, AWS et taxes ; ce n'est pas une facture. API 53c2ba2 et console 748274b déployées avec succès. Les avertissements de source sont maintenant présentés comme une détection incertaine, non une certitude d'absence de preuve. Le premier parcours réel Lambda reste à observer avec Mehdi.
