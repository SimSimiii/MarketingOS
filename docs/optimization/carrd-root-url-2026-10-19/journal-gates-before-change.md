# Diagnostic pendant le run initial, avant correction

Le run 7f217580-283d-4294-a617-e701d691f7d7 rejette le premier brouillon malgré
« Pro Standard costs $19 per year » et un essai Pro documenté de sept jours.
Le brouillon stocké et les événements restent inchangés. Ce journal séparé évite
de concurrencer les écritures du runner dans state.json et journal.md.

Causes confirmées dans ledger.py : le normaliseur conserve le trait d'union dans
l'unité de 7-day au lieu de canoniser days ; le parseur de prix ne capture que
le dernier mot Standard alors que la provenance nomme Pro Standard.

Correction attendue : comparer les mêmes durées singulier/pluriel/trait d'union ;
reconnaître un nom complet de plan connu du prix dans la phrase qui le tarifie.
Ne pas confondre deux plans partageant Standard, ni une durée différente, ni un
montant mensuel avec un montant annuel. Tests et rejeu gratuits des brouillons
capturés, aucune modification du dossier ou d'un asset. Le run en cours garde
le code qu'il a chargé ; collecter son état terminal avant arrêt de la session.
