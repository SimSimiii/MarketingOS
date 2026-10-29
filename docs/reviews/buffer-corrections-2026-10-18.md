# Corrections des mécanismes révélés par Buffer — 18 octobre 2026

Les corrections portent sur le code qui produit et interprète les résultats.
Les snapshots de l'audit, les preuves brutes et les anciennes notes sont conservés.
Un rejeu des données enregistrées vérifie les nouveaux contrôles, sans modèle,
sans réécriture du résultat en base et sans modifier le brief d'une campagne.

## Garanties et conditions d'offre

Le résumé libre du profil n'est plus une preuve. Chaque garantie doit retrouver
une citation du ledger sous une portée d'offre ou de capacité appropriée.
La recherche peut reconnaître une paraphrase courante, mais le texte conservé
est toujours celui de la source, avec ses conditions et limites. Le résumé du
ledger ne peut pas servir à valider un autre résumé. Les nombres et négations
d'une proposition ne sont pas ignorés lors de cette recherche.

Le contrôle intervient avant la synthèse des audiences du compilateur et aussi
à la lecture des anciens artefacts. Une omission est signalée par une note.
Le prompt demande également de copier les garanties avec leurs exceptions.

**Rejeu Buffer : quatre garanties deviennent trois.** L'essai gratuit de 14 jours,
l'absence de carte pour Free et la remise nonprofit restent présents sous leurs
formulations sources. La garantie trompeuse sur les trois canaux gratuits après
upgrade disparaît ; la règle correcte E238 reste dans le ledger. Aucun patch de
texte propre à Buffer n'est utilisé.

## Capacités : périmètre et propriétaire

La dérivation v3 exige une portée capability explicite, un sujet documenté et
une catégorie compatible avec une fonction du produit. Elle exclut faits
d'entreprise, marché, marque, résultats clients et conditions commerciales.
Quand le nom du produit est connu, le sujet doit désigner ce produit ; une
mention de Buffer à l'intérieur d'un workflow WriteStack ne suffit pas.
Les capacités maintenues ne peuvent pas contourner ce contrôle par un autre ID.

Les anciens attachements sont revalidés à la lecture, sans écrire leur historique.
Le fingerprint versionné impose une nouvelle dérivation lors de la prochaine
opération qui en a besoin. Les frontières explicites unsupported sont préservées.
Les faits retirés du catalogue restent disponibles dans leurs sections du ledger.

**Rejeu Buffer : 276 entrées initiales, 186 capacités positives après contrôle.**
Les 186 ont une portée capability ; E1 recrutement, E4 identité du CEO et E22
fonctions WriteStack n'en font plus partie. Le contrôle en lecture retrouve le
même nombre de capacités positives sur le profil ancien.

## Positionnement et justifications concurrentielles

Les résultats clients, notamment les revenus, sont classés proof avant les
indices lexicaux de prix. Même un ancien objet mal étiqueté price ne peut pas
devenir comparable à un abonnement. Les comparaisons de preuve conservent les
sujets et conditions ; des clients différents ne sont pas rendus équivalents.
Les limites API relèvent de la capacité et non d'une vitesse d'exécution mesurée.
Les fonctions explicitement attribuées à un autre produit et les faits d'entreprise
ne deviennent plus nos promesses de positionnement.

Le résumé annonce les différences documentées et les propositions non appariées
à vérifier, plutôt qu'un potentiel open ground déduit d'une capture incomplète.
Les identifiants historiques open/exposed restent compatibles ; leur présence
ne prouve toujours ni exclusivité ni faiblesse concurrente.

Une fourchette de prix fabriquée à partir de plusieurs tarifs n'est plus acceptée
dans une justification présentée comme sourcée, sauf si la source énonce cette
fourchette. Cela vaut pour les profils nouveaux, les lectures d'anciens scans
et les résultats réutilisés du cache. Le prompt exige des plans et une base de
facturation explicites.

**Rejeu Buffer :** les propositions de prix ne contiennent plus les revenus de
WriteStack ou les ventes AJ&Smart. La justification Sprout à fourchette incomplète
est désormais non vérifiée, avec une raison visible ; ses prix détaillés ne sont
pas supprimés. Les données capturées ne suffisent toujours pas à démontrer un
avantage commercial : aucune note de qualité artificiellement relevée.

## Crawl et diagnostic du catalogue

Depuis la seule homepage, le crawler suit les liens réellement découverts vers
les sous-domaines docs, help, support et developers de la source. Il ne devine
aucun chemin et n'accepte ni domaine ressemblant ni sous-domaine arbitraire.
Les contrôles public_http restent en place sur toutes les requêtes.

Les paginations sont ignorées ; les variantes d'URL de tracking sont dédupliquées.
Le budget est réparti entre documentation, prix, preuves et produit. Les guides
de démarrage gardent leur priorité. Les liens de partage et prompts de partage
vers un assistant ne gonflent plus le texte destiné au compilateur.

**Contrôle HTTP réel : onze documents utilisables**, dont l'index support Buffer
et un article d'aide, au lieu d'aucune page de ce sous-domaine. Le budget reste
douze tentatives ; ce n'est pas une lecture exhaustive. Seize lots d'extraction
sont planifiés sur ce nouveau corpus. Aucune recompilation réelle n'a été achetée,
donc aucun gain de durée ou de quota modèle n'est établi.

L'erreur 404 d'un catalogue absent indique maintenant qu'après compilation il faut
le dériver ou lancer le mapping, sans conseiller uniquement de recompiler.

## Vérification et limites

Les régressions couvrent les garanties inversées, les exceptions, l'idempotence,
les mauvais propriétaires, le périmètre inconnu, les mesures incomparables, les
fourchettes non citées, les liens de documentation, les domaines ressemblants,
les liens malformés, les paginations, la déduplication et le message API.

Résultats finaux : **1 746 tests backend passés**, deux avertissements de dépendances
déjà présents ; **Ruff propre** ; **lint et typecheck frontend propres**, **28 tests
frontend passés**. Quatorze scénarios de régression ajoutés, et des fixtures positives
précisent désormais leur portée capability. Un fait non qualifié ne doit plus être
promu automatiquement. Le contrôle Git des espaces passe également.
Les logs et les replays sont sous docs/optimization/buffer-root-url/ :
correction-replay.json, crawl-after-fix.json, full-tests-final.txt,
ruff-fixes.txt et frontend-*-fixes.txt.

**Aucun nouvel appel modèle pour ces corrections.** L'audit jusqu'à l'email reste
à reprendre après la disponibilité du quota Claude. Les serveurs déjà ouverts
doivent charger le code courant à leur prochain redémarrage normal. Aucun serveur
n'a été arrêté et aucun résultat brut n'a été corrigé manuellement dans cette tâche.
