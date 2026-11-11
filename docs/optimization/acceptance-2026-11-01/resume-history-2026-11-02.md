# État de reprise au 2 novembre 2026

**Réouvert le 2 novembre au soir à la demande de l’utilisateur.** Le seuil5/6
ci-dessous est un bilan historique, pas une instruction d’arrêt actuelle.
Correction en cours : préservation du périmètre des preuves lors de la récupération
(E138 frais des tunnels ne doit pas devenir E156 frais du lien en bio malgré leur
citation identique).24 tests ciblés et2167 tests complets passent. La séquence
`b04aad5f-e9c3-4dab-9a8a-6e487018e658` est en cours ; la collecter, ne pas en
lancer une autre en parallèle pour le même cas. Le backend utilise toujours la
copie SQLite d’audit. Les anciens horaires de quota sont dépassés : seul un
nouveau refus établit l’indisponibilité actuelle.

**Audit terminé : seuil technique atteint, 5/6 cas utilisables après retouches mineures.**
Lire le verdict final dans `../../reviews/acceptance-2026-11-01.md` et `state.json`.
Loops Knowledge v2 et dossier v3/interprétation18 qualifient Supabase uniquement,
sans override. Les deux emails sont générés, retouchés avec un appel chacun,
acceptés et exportés dans l’interface. Quatre propositions réelles et trois témoins
directs sont terminés. Les originaux et échecs restent archivés.

La séquence systeme.io livre maintenant 3/3 ; elle reste le cas de qualité non
validé, car son troisième argument repose sur le 0% du lien en bio sans mécanisme
d’achat étayé. La réussite 5/6 ne transforme pas ce cas en résultat prêt à envoyer.
Le minimum connu est395 appels pour l’audit complet, corrections et échecs inclus ;
un ancien compteur de carte reste inconnu. Vérifications finales :2156 backend,
135 ciblés après prompts,37 frontend, lint/types/schema verts. La clôture vient
du seuil atteint, pas d’un épuisement général de quota. Aucun appel supplémentaire
n’est à lancer automatiquement. Conserver la copie SQLite séparée.

La couverture Loops, la qualification de sa branche documentée et les retouches
ont été corrigées et vérifiées. Ne pas réexécuter les instructions historiques
ci-dessous comme une file de tâches encore en attente. Les limites actuelles et
les artefacts choisis figurent dans le rapport final.

---

# Reprise de l'audit fixé

Lire d'abord `protocol.md`, `state.json`, `journal.md` et `../../reviews/acceptance-2026-11-01.md`. Le verdict est incomplet pour quota, pas refusé. Ne pas repartir de zéro et ne pas changer l'échantillon.

## Environnement à préserver

- Branche `master`, arbre déjà modifié avant l'audit ; aucun commit, branche ou worktree créé.
- Base d'audit : `C:/Users/oussa/AppData/Local/Temp/marketingos-acceptance-2026-11-01.sqlite`, migrée de `c53a9f27d401` à `9cc72045ff9a`.
- **Réutiliser cette copie ; ne pas la remplacer par la base originale.** Définir `DATABASE_URL=sqlite:///C:/Users/oussa/AppData/Local/Temp/marketingos-acceptance-2026-11-01.sqlite` uniquement dans l'environnement du serveur d'audit.
- Démarrer backend et frontend avec les configurations de `.claude/launch.json` (8000 et 3000). Vérifier `/api/health` et `/api/executions/running` avant toute mutation.
- Compteurs des jobs précédents sauvegardés : `knowledge-jobs-final.json`, `market-jobs-final.json`, `metrics.json` et snapshots `loops-acquisition/steps/*poll.json`. Les registres des jobs ne survivent pas au redémarrage ; les artefacts et la base, oui.

## Blocage externe

Dernier refus GPT : quota épuisé, reprise annoncée à « 7:55 AM », fuseau non précisé par le CLI. Claude installé via SDK mais non connecté. Aucun achat, connexion forcée, changement de fournisseur global ou nouvelle tentative inchangée.

Après rétablissement plausible du quota, reprendre **une étape utile** : la carte Loops. Si le même refus revient, conserver le snapshot et ne pas lancer les autres opérations. Si elle réussit, poursuivre les étapes dépendantes normalement. Le protocole autorise la reprise d'une interruption externe avec conservation de l'essai initial ; pas de régénération supplémentaire pour améliorer une note.

## Loops

La marque `bf6613ea-71b1-45ac-8331-f09a42dc9f86` a déjà 12 documents, Knowledge v1 et un scan terminé. Ne pas refaire import, compilation ou scan.

Depuis la racine :

```powershell
backend/.venv/Scripts/python.exe -X utf8 scripts/audit_brand_flow.py map --case docs/optimization/acceptance-2026-11-01/loops-acquisition/case.json --revision quota-resume-2
backend/.venv/Scripts/python.exe -X utf8 scripts/audit_brand_flow.py poll --case docs/optimization/acceptance-2026-11-01/loops-acquisition/case.json --wait 45
```

Attendre le statut terminal, capturer les métriques, inspecter la carte. Puis `capture`, `select-first`, `research`, `poll`, `capture`, `dossier`, `poll`, `capture` avec le même `--case`. Ne pas changer la première audience exacte. Rediriger les grandes captures vers un fichier si nécessaire. Lancer `campaign` puis `advice` seulement après préparation ; conserver tout refus, sans `generate_anyway`.

Lancer la campagne avec `scripts/optimize_campaign.py run --case ...`, puis `summary` et inspecter les assets. Pour une commande d'affichage interrompue, utiliser `resume` : il collecte le run existant, il ne relance pas la campagne.

Créer ensuite `loops-consideration/case.json` à partir de la même marque et de l'audience exacte retenue, sans réutiliser un `campaign_id`. Demande arrêtée : un email de considération en anglais, lecteur connaissant Loops mais n'ayant pas acheté ; expliquer un aspect utile et prouvé, proposer un prochain pas documenté, ne pas inventer de visite, contact, résultat, urgence ou remise. Preset balanced, stratégie auto, objectif nurture, relation prospect. Aucune recompilation inchangée.

## Séquence systeme.io

Campagne `30292ca6-8932-4dcc-99bf-35d827c5507e`, premier run interrompu `954dad32-5531-44fb-a808-3d7f0a036fdd`, 1/3 livré. La machine ne reprend pas le craft au milieu : une reprise exige un nouveau run, à compter et conserver séparément.

Après disponibilité réelle du fournisseur, noter la reprise externe dans le journal, puis une seule commande :

```powershell
backend/.venv/Scripts/python.exe -X utf8 scripts/optimize_campaign.py run --case docs/optimization/acceptance-2026-11-01/systeme-sequence/case.json
```

Ne pas changer la demande, l'audience, les modèles, les contraintes d'affiliation ou les faits. Comparer la livraison complète et la cohérence des trois emails ; ne pas compter le premier email comme validation d'une séquence.

## Retouches réelles, maximum deux jobs

1. Papier considération : campagne `ba9a3f45-b4d3-4eca-9464-7b058a889b93`, exécution `bf614ad8-8467-4094-b553-a28b5d296ab8`. Dans Adjust : « Too long. Make it more direct in three short paragraphs while keeping the product, its 16-week undated structure, the planning views and the same link. » Examiner la proposition et ses nouveaux contrôles, accepter, copier et télécharger, puis restaurer l'original et vérifier l'historique. Capturer les textes et réponses réelles.
2. systeme.io acquisition : campagne `03aced27-19e9-4bd8-8787-448c1853a4b2`, exécution `a1e13681-a98e-4f04-8fd1-9a9b46d080fd`. Demander plus direct, préciser les sites/tunnels de systeme.io, garder l'affiliation et les limites utiles. Examiner les différences et nouveaux contrôles ; refuser la proposition et vérifier que copie/export restent sur la version choisie. L'ouverture d'Adjust further peut être observée sans soumettre un troisième job.

Les deux jobs sont encore disponibles : aucun n'a été soumis dans cet audit. Ne jamais considérer les anciens verdicts comme validation des nouvelles versions. Si une proposition échoue aux contrôles, conserver cet échec et vérifier le comportement prévu plutôt que le contourner.

## Comparaisons directes, maximum trois appels de rédaction

Le script `scripts/acceptance_direct_baseline.py` utilise ModelSession, le modèle du rédacteur, la même demande, les connaissances complètes, la recherche et le dossier d'audience, le positionnement et les choix utilisateur. Il ne lit pas la stratégie de la campagne générée et n'appelle aucun outil web. Le dossier de sortie refuse les doublons. Aucun témoin n'a encore été exécuté.

Depuis `backend/`, une fois par acquisition :

```powershell
.venv/Scripts/python.exe -X utf8 ../scripts/acceptance_direct_baseline.py ../docs/optimization/acceptance-2026-11-01/papier-acquisition/case.json
.venv/Scripts/python.exe -X utf8 ../scripts/acceptance_direct_baseline.py ../docs/optimization/acceptance-2026-11-01/systeme-acquisition/case.json
.venv/Scripts/python.exe -X utf8 ../scripts/acceptance_direct_baseline.py ../docs/optimization/acceptance-2026-11-01/loops-acquisition/case.json
```

Comparer les textes sur les critères fixés et les mêmes preuves ; ne pas inventer un avantage si le témoin est équivalent ou meilleur. Donner les analyses déjà préparées au témoin isole la rédaction ; cela ne mesure pas un temps humain de préparation économisé. Comptabiliser les retries internes enregistrés par le script.

## Clôture

Actualiser métriques, grille commerciale, états, journaux et rapport sans effacer les premiers essais. Rendre accepté, refusé sur défauts précis ou incomplet sur preuve manquante selon les critères déjà fixés. Les contrôles après le correctif de présentation sont enregistrés dans `validation.json` ; aucun appel réel n'est nécessaire pour ce correctif. Confirmer tous les jobs terminaux avant l'arrêt des serveurs d'audit.
