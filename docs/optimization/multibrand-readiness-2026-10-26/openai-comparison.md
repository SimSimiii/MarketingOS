> Mise à jour du 29 octobre : voir [le bilan actuel](checkpoint-2026-10-29.md). Un parcours systeme.io est désormais validé avec un email88/100. Le bilan ci-dessous conserve les résultats historiques ; A25 est testé sur disque mais son activation réelle a été refusée automatiquement.

# Faut-il utiliser OpenAI partout ?

Évaluation terminée sur ce lot de quatre marques ; aucune migration globale des préférences n’a été faite. Recommandation : conserver le choix par étape. OpenAI fonctionne sur le parcours textuel testé, mais les quatre cas ne valident pas la fiabilité commerciale autonome.

## Configuration de départ

Les presets de campagne utilisent déjà `gpt-5.6-sol` pour tous les rôles de stratégie/rédaction/critique/lecture. Les compilations Knowledge autonomes et les jobs de marché emploient leur propre routeur, dont les tiers par défaut sont Claude. Modifier le fournisseur par défaut ne suffit donc pas à déplacer ces jobs.

L'adaptateur OpenAI de ce dépôt annonce la recherche Web, pas un outil indépendant `web_fetch`. La documentation officielle confirme la recherche en direct via `codex --search` : [Web search](https://learn.chatgpt.com/docs/web-search). Le support effectif d'un rôle doit toutefois être déterminé par le code et les outils réellement passés, pas par une supposition sur le modèle.

## Deux essais ciblés, mêmes textes de profil

| Profil Knowledge | OpenAI testé | Observation |
|---|---:|---|
| systeme.io | 30,3 s, un appel GPT-5.6 Sol | Offre gratuite et ses limites conservées, aucun tarif payant inventé ; une offre structurée renseignée contre aucune dans le profil Claude |
| CABAIA | 37,6 s, un appel GPT-5.6 Sol | Sept produits/prix renseignés contre une liste vide dans le profil Claude ; les sept montants se trouvent près du titre du produit dans sa propre page importée |

Ce sont des diagnostics de **profil uniquement**, pas des compilations complètes ni un A/B strict de deux systèmes. Le profil Claude disponible est passé par le post-traitement du compilateur ; son temps par template n'est pas isolé dans les journaux. Comparer ces 30–38 secondes avec les 7–13 minutes des compilations complètes serait trompeur.

Les deux fournisseurs reformulent ou assemblent certaines citations au lieu de les recopier exactement. Les identifiants sémantiques produits dans un profil ne sont pas des identifiants du registre de preuves. Le profil OpenAI CABAIA résume aussi une garantie à « Garantie 2 ans » sans sa restriction de collection. Le rejeu gratuit du contrôle existant `ground_guarantees`, contre le registre Claude, rétablit bien la portée de la collaboration en édition limitée. Cela montre l'utilité du contrôle ; cela ne constitue pas une compilation OpenAI complète réussie.

Les compteurs de jetons et les coûts théoriques enregistrés ne mesurent ni un débit sur carte, ni le quota d'abonnement restant. Aucun changement vers une facturation API n'a été effectué.

## Compatibilité corrigée pour permettre l'essai

- Knowledge : modèle optionnel propre à une compilation, sans modifier le prochain job.
- Concurrents : le scout cherche des URL ; le crawler Python lit ensuite les pages et le profilage vérifie les citations contre ces pages. Le profilage reste fermé au Web.
- Carte d'audiences : la recherche est déjà suivie de lectures Python et d'une évaluation des sources. La déclaration des outils et l'admission sont alignées sur ce fonctionnement.
- Recherche d'audience et dossier : sélection locale du modèle déjà présente, conservée.
- Emails : chemin OpenAI déjà utilisé par défaut, à vérifier dans les nouveaux journaux de runs.
- **Hors périmètre** : Proof et la recherche de prospects demandant encore `web_fetch` continuent de refuser GPT. La lecture d'images reste liée à Claude et n'est pas testée par ces quatre homepages.

Les choix explicites sont refusés avec la facturation par crédits ; les contrôles de capacités restent en place. Validation gratuite avant essais : 1 966 tests backend, Ruff, lint/typecheck frontend et 29 tests frontend réussis.

## Continuation réelle et limites

Après un nouvel épuisement de Claude, les échecs scan CABAIA et carte systeme.io sont conservés (zéro appel terminé). Les étapes restantes sont relancées explicitement sur GPT. CABAIA/systeme.io conservent leur Knowledge Claude réussie, et systeme.io son scan Claude réussi : ces deux parcours seront donc mixtes. Papier/RTINGS ont ensuite exécuté Knowledge et leurs jobs sur OpenAI depuis leurs sources déjà importées, jusqu’à un email réel chacun.

Pendant les tests, le code courant a été exercé par les vraies routes de l’application dans des workers d’audit ASGI sans listener ni lifespan. Après terminaison, arrêt propre des quatre workers et sauvegarde SQLite, le serveur principal a été rechargé sur le même port par arrêt du seul PID vérifié. Santé, schémas et résultats persistés vérifiés ; le refus automatique antérieur est résolu. Voir server-activation.json.

**Observation des premiers essais :** OpenAI semble prometteur pour structurer les offres, et peut exécuter le parcours courant avec les adaptations ci-dessus. Sa supériorité générale et la prise en charge de toutes les fonctions du produit restent à établir. Changer de modèle ne répare pas les pages RTINGS mal collectées.

## Résultats supplémentaires du 27 octobre

Les compilations OpenAI de Papier (492 faits, 10 appels) et RTINGS (79 faits, 5 appels) ont terminé. Les cartes des quatre marques ont terminé sur GPT, sans présenter leurs hypothèses comme une priorité commerciale établie. Le scan RTINGS sélectionne aussi des pages automobiles de Consumer Reports : ce défaut de pertinence du crawl ne disparaît pas avec le fournisseur.

Contrôle CABAIA, audience exacte inchangée : la recherche GPT avait échoué après dix URL sans texte exploitable ; Sonnet a obtenu trois pages et quatre problèmes. Les quatre problèmes reposent sur une seule page de 2021, et sont correctement déclassés comme historiques et non corroborés. Les recherches en direct variant avec le temps et les requêtes, ce n’est pas un A/B strict. C’est néanmoins une raison concrète de conserver une possibilité Claude pour cette étape.

Un sous-processus Codex héritait aussi du catalogue de skills de la machine. Des options locales au sous-processus désactivent désormais ce contexte et les outils inutiles ; recherche live explicite pour les rôles autorisés, Web désactivé sinon. Contrôle CLI et sonde réelle conservés ; aucune préférence globale changée. Validation après correction des prompts d’audience : 1 967 tests backend et Ruff passent.

Recommandation actuelle : OpenAI convient au parcours textuel testé et structure mieux les prix dans les deux diagnostics limités. Garder le routage par capacité et le choix local par job ; ne pas migrer aveuglément toutes les fonctions. Les rôles qui exigent encore fetch et la lecture d’images restent hors de cette conclusion. Les emails et l’utilité commerciale sont évalués séparément.

## Conclusion du lot terminé

Quatre marques ont produit un vrai email ; huit tentatives de campagne, sept emails livrés, 225 appels terminés. Meilleurs scores de revue : CABAIA71, Papier84, systeme.io84, RTINGS86/100. Tous les derniers runs restent degraded/needs_review. RTINGS était un diagnostic malgré DISCOVERY_ONLY et ne valide pas son amont ; le seuil de trois cas complets utiles n’est pas atteint. OpenAI n’a donc pas démontré ici une qualité commerciale autonome supérieure.

La révision des consignes a ramené livres/auteurs dans systeme.io (79→83), puis apporté un gain limité après clarification du CTA (84). Papier82→84 garde du langage interne de vérification. Le choix d’inscription/personnalisation reste difficile à faire évoluer par les seules consignes. CABAIA nécessite une vraie preuve de capacité ou une autre proposition admise sur la même audience ; le fournisseur ne peut créer ce fait.

Les contrôles gratuits restent déterminants : exception exacte du nom canonique en capitales et conservation d’une destination choisie sourcée lorsqu’une action n’a pas d’URL. Dernière suite :1972 tests backend et Ruff passent. Ce dernier correctif déterministe est chargé ; aucune nouvelle campagne payante ne justifie encore une amélioration du score historique CABAIA.

Un appel de recherche officielle CABAIA a été refusé par une limite d’usage («6:08 AM», zone non précisée), tandis que d’autres appels ont continué ensuite. Ne pas interpréter cet incident comme une mesure du quota global ou une panne de tous les rôles. Les durées de profils, compilations et campagnes restent des tâches différentes, sans comparaison de vitesse entre fournisseurs à corpus/conditions variables.

Garder OpenAI pour les fonctions textuelles validées et Claude comme option de recherche, puis choisir sur des essais identiques par rôle si une migration est envisagée. Les outils et la couverture des sources doivent rester les critères d’admission ; ne pas désactiver les contrôles fetch ou de preuves pour obtenir un routage uniforme. Aucun changement de préférences globales ni facturation API/crédits.
