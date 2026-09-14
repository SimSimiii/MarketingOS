# Correctifs de la revue globale — septembre 2026

Ce document accompagne la revue du 12 septembre. Les modifications LinkedIn déjà présentes
dans le répertoire ont été conservées. Aucun appel réel à un modèle, aucune modification de
la base de travail et aucun déploiement ne font partie des validations décrites ici.

## Sécurité et intégrité

- Les permissions des fournisseurs restent confinées aux outils explicitement autorisés.
  Les tests existants vérifient aussi la suppression des clés API de l'environnement des CLI.
- Le texte collé ne devient plus un chemin de fichier. Les uploads restent bornés à 20 Mo.
- Documents autonomes avec propriétaire ; filtrage SQL des documents, exécutions actives et
  jobs marché. Une campagne sans marque ne récupère que la bibliothèque de son propriétaire.
  Un couple marque/campagne incohérent est refusé. Les clones conservent leur propriétaire.
- Téléchargement HTTP partagé : uniquement destinations publiques, résolution DNS contrôlée,
  connexion à l'IP vérifiée avec Host/SNI conservés, validation des redirections, durée et
  volume bornés. Les réponses compressées sont refusées pour éviter les bombes de décompression.
- Clés étrangères SQLite actives. Suppression d'une marque utilisée : HTTP 409, sans suppression
  implicite des campagnes, connaissances ou recherches associées.
- Access tokens vérifiés contre une version en base ; déconnexion globale, changement de mot
  de passe, suspension et action administrateur invalident les anciens jetons. Les comptes
  administrateur disposent aussi de cette révocation après logout et réinitialisation.
- Rotation du refresh token atomique. Renouvellement frontend mutualisé par onglet et par
  verrou navigateur entre onglets. Les erreurs temporaires permettent une nouvelle tentative.
- Aucun jeton dans les URL SSE/CSV. Proxy de téléchargement limité aux routes prévues.
  Les mutations API nécessitent un en-tête Bearer ; le cookie seul n'autorise que les lectures.

## Quota et fonctionnement

- Les overrides de politique sont revalidés après fusion, avec bornes serveur. Les anciennes
  clés retirées restent ignorées pour relire les campagnes historiques.
- Chaque job réserve atomiquement une unité du quota mensuel UTC : campagne, compilation,
  recherche marché/LinkedIn ou analyse d'image. `0` signifie illimité. Une admission sans
  tentative de modèle est remboursée ; une tentative consomme l'unité même si elle échoue.
- `MAX_CONCURRENT_JOBS=4`, `MAX_JOBS_PER_ACCOUNT=2` par défaut. Plafonds supplémentaires par
  job : 500 tentatives, 4 millions de tokens, une heure, contrôlés entre les appels. Un appel
  commencé peut dépasser le dernier seuil de tokens ; aucun appel n'est interrompu au milieu.
- L'admission refuse les jobs modèle sur Lambda avec HTTP 503. Le code actuel nécessite un
  processus durable unique pour exécuter les campagnes ; les API Lambda restent utilisables
  pour les lectures et CRUD. L'administration démarre avec ses seuls secrets propres.
- Les compteurs de concurrence restent locaux au processus, comme le broker SSE. Déployer
  avec un seul worker. Une file durable et un broker partagé seront nécessaires si le mode
  multi-worker est demandé. Après un crash, une réservation déjà débitée n'est pas remboursée
  automatiquement, car le système ne peut pas prouver qu'aucun appel n'a été envoyé.

## Ingestion, qualité et performances

- PDF et DOCX extraits dans un processus séparé, tué sur annulation/dépassement de durée :
  deux extractions simultanées, 30 secondes, 768 Mio de mémoire, 200 pages PDF, un million de
  caractères. DOCX : 2 000 entrées ZIP et 50 Mo décompressés maximum ; tableaux conservés.
  Windows utilise une limite de mémoire de Job Object, Unix `RLIMIT_AS`.
  Référence : [limites mémoire Win32](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information).
- Images : 20 mégapixels maximum ; OCR hors de la boucle HTTP avec timeout Tesseract.
  Une extraction vision structurée remplace cinq appels. Elle traverse ModelSession, conserve
  l'usage dans les métadonnées persistées et alimente le corpus avec texte/provenance/observation.
  Si l'OCR manque, la transcription vision prend le relais. Pas de nouvel appel juge.
- Les paraphrases du compilateur ne peuvent plus inventer un chiffre autorisé. Les citations
  exactes fondent les licences. Des changements identifiables de métrique et de sujet nommé
  sont bloqués ; la critique existante vérifie les autres erreurs de sens. Cette gate ne
  prétend pas prouver la vérité de toute affirmation ni comprendre toutes les paraphrases.
- Contexte de qualification partagé pour les prospects et l'export CSV. Test SQL : quatre
  lectures pour une audience, que la liste contienne un ou cent prospects.
- Campagnes, documents et endpoint prospects : pagination SQL validée, ordre stable, maximum
  250 éléments par réponse. Navigation par pages sur les campagnes et les sources de marque.
  Les vues historiques nécessitant une collection entière parcourent explicitement les pages ;
  la réponse agrégée audience et le CSV restent des lectures groupées complètes.
- Découpage ciblé : HTTP public, admission des jobs, processus d'extraction, limites mémoire
  et renouvellement de session sont centralisés dans des modules dédiés.

## Contrats et dépendances

- Next et eslint-config-next : 16.3.5 dans les deux applications ; pypdf : 6.18.1.
  `shadcn` est un outil de développement. Les dépendances transitives concernées sont mises à jour.
- `backend/requirements.lock` verrouille l'environnement de test ; `backend/requirements.txt`
  verrouille le bundle avec PostgreSQL ; l'administration a son propre verrou et `requirements.in`.
  Les verrous incluent les empreintes des distributions. Les deux builds backend utilisent
  le verrou de test commun puis leur verrou de distribution.
- `python scripts/export_api_types.py` génère les schémas TypeScript depuis OpenAPI sans
  démarrer le serveur. `--check` bloque un contrat généré obsolète dans le build backend.
  `api-contracts.ts` vérifie les contrats essentiels des campagnes, marques et documents.
  Les types de présentation supplémentaires restent manuels ; ils ne sont pas tous couverts
  par les assertions de compatibilité. Le champ réponse `CampaignRead.channel` est maintenant typé.
- Les erreurs de lint de l'administration sont corrigées. Les buildspecs existants sont
  renforcés, sans ajouter une deuxième infrastructure de CI.

## Appliquer les migrations au déploiement

Trois migrations suivent `b1d7c9f4a20e` : propriétaire des documents (`c40a12d9e501`), version
des jetons utilisateur (`c40a12d9e502`), puis administrateur (`c40a12d9e503`).

1. Arrêter les jobs et sauvegarder la base avant toute mise à niveau.
2. Pour une base déjà gérée par Alembic : `python -m alembic upgrade head`, puis
   `python -m alembic check` depuis `backend/`, avec sa configuration de déploiement.
3. Pour une base locale créée par `create_all` sans historique Alembic : identifier d'abord
   la révision correspondant réellement à ses tables et colonnes. Si elle correspond à
   `b1d7c9f4a20e`, utiliser `alembic stamp b1d7c9f4a20e`, puis upgrade et check.
   Ne jamais utiliser `stamp head` pour contourner des colonnes manquantes.
4. Contrôler `PRAGMA foreign_key_check` sur SQLite. Les anciens orphelins doivent être examinés
   explicitement ; les contraintes actives ne réparent pas les données historiques.
5. Les documents historiques sans marque, campagne ni propriétaire ne sont pas attribués au
   hasard. Ils restent visibles en mode local partagé et masqués en mode comptes ; une reprise
   multi-compte nécessite d'établir leur propriétaire à partir de leur provenance.

## Vérifier sans toucher aux données de travail

Résultat final de cette passe : **1 175 tests backend**, **28 tests administration** et
**6 tests frontend** réussis. Ruff, lint/TypeScript des deux frontends, leurs deux builds,
le contrat OpenAPI et les migrations SQLite passent. Audits npm des deux applications et
pip-audit des trois verrous Python : aucune vulnérabilité connue signalée au moment du contrôle.
Quelques avertissements de dépréciation de dépendances subsistent dans les tests.

Depuis `backend/` :

```powershell
.venv/Scripts/python.exe -m pip install --require-hashes -r requirements.lock
.venv/Scripts/python.exe -m ruff check app tests scripts
.venv/Scripts/python.exe -m pytest tests -q
.venv/Scripts/python.exe scripts/export_api_types.py --check
.venv/Scripts/python.exe scripts/check_migrations.py
```

Depuis chacun des frontends : `npm run lint`, `npx tsc --noEmit`, `npm run build` ;
depuis le frontend principal : `npm test` également. Suite administration : depuis
`administration/backend`, `../../backend/.venv/Scripts/python.exe -m pytest tests -q`.

La vérification des migrations utilise une base SQLite temporaire et couvre création,
retour aux trois migrations précédentes, remise à niveau et absence de dérive du schéma.
PostgreSQL et AWS n'ont pas été exécutés dans cet environnement ; le moteur Docker local
était arrêté. La base de travail existante n'a pas été migrée.
