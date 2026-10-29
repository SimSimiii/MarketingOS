# Faut-il utiliser OpenAI partout ?

Évaluation en cours ; aucune migration globale des préférences n'a été faite.

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

## Comparaison réelle à terminer

Après un nouvel épuisement de Claude, les échecs scan CABAIA et carte systeme.io sont conservés (zéro appel terminé). Les étapes restantes sont relancées explicitement sur GPT. CABAIA/systeme.io conservent leur Knowledge Claude réussie, et systeme.io son scan Claude réussi : ces deux parcours seront donc mixtes. Papier/RTINGS doivent tester le parcours courant sur OpenAI depuis leurs sources déjà importées.

Le code courant est exercé par les vraies routes de l'application dans des workers d'audit ASGI sans listener ni lifespan. Le serveur existant n'a pas été arrêté ni rechargé après le refus automatique de son redémarrage. Les résultats ne doivent pas être présentés comme la preuve qu'il a chargé les changements.

**Conclusion provisoire :** OpenAI semble prometteur pour structurer les offres, et peut exécuter le parcours courant avec les adaptations ci-dessus. Sa supériorité générale et la prise en charge de toutes les fonctions du produit restent à établir. Changer de modèle ne répare pas les pages RTINGS mal collectées.

## Résultats supplémentaires du 27 octobre

Les compilations OpenAI de Papier (492 faits, 10 appels) et RTINGS (79 faits, 5 appels) ont terminé. Les cartes des quatre marques ont terminé sur GPT, sans présenter leurs hypothèses comme une priorité commerciale établie. Le scan RTINGS sélectionne aussi des pages automobiles de Consumer Reports : ce défaut de pertinence du crawl ne disparaît pas avec le fournisseur.

Contrôle CABAIA, audience exacte inchangée : la recherche GPT avait échoué après dix URL sans texte exploitable ; Sonnet a obtenu trois pages et quatre problèmes. Les quatre problèmes reposent sur une seule page de 2021, et sont correctement déclassés comme historiques et non corroborés. Les recherches en direct variant avec le temps et les requêtes, ce n’est pas un A/B strict. C’est néanmoins une raison concrète de conserver une possibilité Claude pour cette étape.

Un sous-processus Codex héritait aussi du catalogue de skills de la machine. Des options locales au sous-processus désactivent désormais ce contexte et les outils inutiles ; recherche live explicite pour les rôles autorisés, Web désactivé sinon. Contrôle CLI et sonde réelle conservés ; aucune préférence globale changée. Validation après correction des prompts d’audience : 1 967 tests backend et Ruff passent.

Recommandation actuelle : OpenAI convient au parcours textuel testé et structure mieux les prix dans les deux diagnostics limités. Garder le routage par capacité et le choix local par job ; ne pas migrer aveuglément toutes les fonctions. Les rôles qui exigent encore fetch et la lecture d’images restent hors de cette conclusion. Les emails et l’utilité commerciale sont évalués séparément.
