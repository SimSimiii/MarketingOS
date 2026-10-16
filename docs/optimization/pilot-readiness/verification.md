# Vérifications locales finales

6 octobre 2026, branche master, fichiers du workspace sans commit.

| Vérification | Commande | Résultat |
| --- | --- | --- |
| Régression public / pipeline | `backend/.venv/Scripts/python.exe -m pytest tests/marketing/test_audience_context.py tests/marketing/test_reader.py tests/marketing/test_pipeline.py -q` depuis backend (chemin Python relatif `.venv/Scripts/python.exe`) | 90 passent |
| Rapport de preuves manquantes | `.venv/Scripts/python.exe -m pytest tests/marketing/test_pipeline.py::test_persistent_missing_material_is_not_delivered -q` depuis backend | 1 passe |
| Références récupérées / arrêt de récupération | `.venv/Scripts/python.exe -m pytest tests/marketing/test_pipeline.py::test_failed_recovery_keeps_only_emails_without_missing_material tests/market/test_material_research.py -q` depuis backend | 8 passent |
| Public, critiques et arrêts de pipeline | `.venv/Scripts/python.exe -m pytest tests/marketing/test_pipeline.py tests/marketing/test_audience_context.py tests/marketing/test_critic.py -q` depuis backend | 77 passent |
| Backend final complet | `.venv/Scripts/python.exe -m pytest tests -q` depuis backend | 1403 passent, 2 avertissements de dépendances, 119,33s |
| Lint backend | `.venv/Scripts/python.exe -m ruff check app tests` depuis backend | Propre |
| Frontend | `npm run lint`, `npm run typecheck`, `npm test`, `npm run build` depuis frontend | Lint/typage propres ; 12 tests passent ; build réussi |
| Diff | `git -c core.safecrlf=false diff --check` | Propre |

Les tests scriptés valident le code sans appel modèle. Les verdicts sur les textes réels
restent dans les dossiers de cas ; les tests ne font pas monter leur note de qualité.
Les captures de navigateur et leurs limites figurent dans `ui-audit.md`.
