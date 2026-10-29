# Buffer — audit depuis la seule URL principale

## 2026-10-18 — protocole

Demande utilisateur : une nouvelle marque, parcours complet, noter chaque étape.
Entrée système unique : https://buffer.com/. Pas de sous-page ni de faits fournis manuellement.
La consultation indépendante de la page principale sert uniquement à choisir la marque.
Première audience de la carte retenue sans substitution. Un email d'acquisition en anglais,
stratégie automatique, preset balanced, aucun envoi.

Chaque étape : note éditoriale sur 10 (couverture, fidélité, utilité), éléments vérifiés,
limites. Email : grille stable 25/20/20/15/10/10, jugement humain de revue,
sans prétention de conversion mesurée. Aucun score avant inspection des résultats.

Instance existante 8006 : santé OK, aucune campagne active. Les dernières corrections
du filtre DPIA et du prompt de stratégie sont dans les fichiers mais pas dans ce processus.
Les étapes de recherche utilisent cette instance ; la génération finale utilisera le même
CampaignService dans un worker autonome lisant le code courant, sans redémarrer de serveur,
sans court-circuiter le précontrôle. Les résultats historiques sont conservés.

## Import — 7/10
12 pages, 17 148 mots. Prix et /pricing.md trouvés sans intervention ; quatre études de cas détaillées. Trois pages de liste/pagination consomment le budget ; aucune documentation des sous-domaines support/developers. Bonne couverture commerciale, couverture technique incomplète. Le crawl borné ne vaut pas lecture exhaustive.

## Compilation — 6,5/10
19 appels terminés, 284 031 jetons entrants / 299 181 sortants rapportés, environ 16,4 min. 501 citations sur 501 retrouvées par normalisation dans leur document ; 10 candidats rejetés. Tarifs mensuels/annuels et limite de file Free correctement extraits. Défaut de synthèse : garantie « Keep your three free channels if you upgrade from the Free plan » ambiguë/trompeuse, contredite par E238 : chaque canal est facturé au passage au payant. Ledger correct, résumé non fiable sur ce point. Ne pas corriger ce résultat à la main ; suivre sa propagation éventuelle. La longue latence et le bruit company (45 faits) dégradent le parcours.

## Marché — concurrents 7,5/10 ; positionnement 3,5/10
Six alternatives crédibles ; quatre sites lus, 127 citations vérifiées ; Meta illisible et le statu quo tableur sans site restent non vérifiés. Les rationales acceptées citent les deux côtés. Réserve : Sprout résumé à 199–399 USD/siège, omettant son niveau Essentials dans la même capture. Positionnement trop lexical : 147 lignes, 143 inconnues et 4 différences potentielles ; revenus de WriteStack classés prix, ventes historiques AJ&Smart comparées aux tarifs logiciels. Les avertissements sont présents, mais le classement et les labels open/exposed ne constituent pas une différence concurrentielle exploitable. Scan : 5 appels, 141 402 entrées / 71 318 sorties rapportées, 5 min 18 s.

Note opératoire : le snapshot capture et le lancement map ont brièvement chevauché leurs écritures locales. L entrée map a été restaurée depuis sa réponse de lancement immuable ; aucun job relancé et aucun résultat produit modifié. Attendre désormais la fin effective du processus helper avant toute mutation suivante.

## Catalogue de capacités — 3/10
276 entrées dérivées, références existantes. Mais 20 entrées company et 21 de scope unknown entrent encore dans les capacités vérifiées. E1 recrutement, E4 identité du CEO et E22 fonctions de WriteStack sont conservés ; le sujet/propriétaire doit être filtré indépendamment de la présence de la citation. La dérivation automatique se déclenche au mapping. Avant ce mapping, GET capability-profile répondait 404 avec une consigne erronée de recompiler alors que v1 était déjà compilée. Aucun produit ou résultat modifié pour contourner le test.

## Interruption fournisseur — 2026-10-18 17:50 UTC
La découverte de la carte échoue : quota Claude de session épuisé, remise à zéro annoncée à 22 h 50 Europe/Paris. Aucun appel terminé sur ce job ; consommation de la tentative refusée inconnue. 24 appels terminés connus au total, 425 433 entrées / 370 499 sorties rapportées. Les étapes suivantes ne sont ni exécutées ni notées. Aucun email, aucun envoi. Aucun correctif manuel des artefacts ni changement de production dans ce test. Le calcul brut estimait 17 lots ; le compilateur rapporte 16 lectures effectivement utilisées.

### Note de qualité à ce point
Email : non noté, aucun résultat généré ; aucun meilleur score dans ce nouveau cas. Forces : import autonome des prix et citations vérifiées, concurrents plausibles et sourcés. Défauts majeurs : synthèse de garantie contradictoire, capacités hors produit, comparaisons lexicales. Le parcours complet reste non validé. Reprise uniquement du mapping après quota, révision quota-reset ; aucune nouvelle compilation ni aucun nouveau scan requis. Aucun réveil automatique programmé.

Vérification finale des traces : la note import (7/10), déjà conservée dans le journal et le rapport, a aussi été restaurée dans state.json après détection de son écrasement par le premier poll. L intégrité est maintenant vérifiée : six revues d étapes, cinq lancements enregistrés, aucune campagne ni score email.

## Correction demandée — diagnostic avant modifications

Causes : garanties libres du profil non reliées aux citations ; capacités dérivées
acceptant scopes unknown et sujets tiers ; comparaison price autorisant tout montant
avec une période ; classification par mots avant le sujet ; crawl excluant les
sous-domaines de documentation et donnant trop de priorité aux paginations.
Hypothèse : des garde-fous déterministes sur la provenance verbatim, le type/sujet
produit et le sens des mesures élimineront ces erreurs sans nouvel appel modèle.
Attendus observables sur le replay Buffer sauvegardé : garantie trois canaux omise,
E1/E4/E22 retirés des capacités positives, ventes/revenus classés preuve plutôt que
prix et jamais rapprochés de tarifs, limites API hors speed. L'histoire brute reste
inchangée. Tests HTTP simulés pour docs liées, frontière de domaine et pagination.
Le message 404 du catalogue doit distinguer absence de dérivation et de compilation.
Validation ciblée puis suite complète, Ruff et contrôles frontend applicables.
Aucune nouvelle note email avant génération et revue effective après quota.

## Correction 1 — validation finale, sans nouveau modèle
Mécanismes modifiés : garanties reprises du verbatim avec conditions avant audience et à la lecture ; catalogue v3 strict sur portée/type/propriétaire, également pour les attachements maintenus ; revenus client classés proof et non prix ; quotas API classés capacité ; comparaison de preuve sur mêmes sujets/conditions ; résumé de positionnement sans inférence de terrain libre ; fourchettes concurrentes non citées écartées ; crawl des sous-domaines documentaires liés, pagination ignorée, déduplication tracking et suppression de partage ; message catalogue clarifié.
Rejeu Buffer : 3 garanties valides conservées, mauvaise garantie écartée ; 276 vers 186 capacités positives ; recrutement/CEO/WriteStack exclus ; hypothèse Sprout à fourchette fabriquée non vérifiée. Snapshot initial inchangé SHA256 76bcb4cd098fb7287b4ea5466bc6cc4f695d89dd2d8ce60eb339683b42c64d14. Crawl HTTP seul : 11 documents, dont index support et article ; 16 lots planifiés, aucune économie de modèle mesurée.
Qualité email : non notée, aucun email généré ; aucun meilleur score. Les notes originales ne sont pas modifiées par des tests de code. Validation : 1746 tests backend, Ruff, lint/typecheck frontend et 28 tests frontend passent ; deux avertissements backend de dépendances. Aucun appel modèle ajouté. Rapport : docs/reviews/buffer-corrections-2026-10-18.md.
Suite : charger le code au prochain redémarrage normal du serveur existant puis reprendre le mapping après disponibilité du quota. Pas de réécriture manuelle du résultat en base, aucun serveur arrêté et aucun envoi.
