# Rejeu de Bannerbear et Canny à partir des archives

Le comparatif d’origine a bloqué les deux premiers emails. Le rejeu charge la base SQLite en lecture seule, reprend le brief et le dossier de pertinence historiques ainsi que les sources déjà compilées, et conserve les modèles du run d’origine. Il lance la stratégie et la rédaction en mode Fast, avec relecture indépendante. Il ne relance ni le crawl ni les analyses de marché. [Comparatif initial](scorecard.md).

## Correction

La stratégie reçoit des extraits liés au besoin du lecteur. Elle vérifie que le bénéfice, l’opération et l’action proposée tiennent ensemble avant de rédiger. Les extraits sur le produit, le mécanisme et le CTA sont sélectionnés à partir du brief, puis transmis à la rédaction, aux réécritures et au relecteur indépendant. Le relecteur peut aussi chercher des extraits propres à chaque version. Il doit citer des passages littéraux et juge chaque nouvelle version. Les conditions du brief et les exclusions restent prioritaires.

Le premier rejeu de Bannerbear a livré un HTML et a conservé le bénéfice principal après une réécriture. Le premier rejeu de Canny a encore bloqué sur des détails de quota et de facturation, puis sur une description trop large de la catégorie. La seconde correction distingue les conditions de l’action proposée de celles qui n’interviennent qu’à un stade ultérieur, et demande de nommer la catégorie minimale attestée par les sources. [Rejeu Bannerbear](bannerbear/proposition-replay/replay.json), [rejeu Canny](canny/proposition-replay/replay.json).

Les passages suivants ont montré que le relecteur pouvait encore confondre une suggestion du plan avec une exigence de l’utilisateur. Le contexte de relecture sépare désormais la demande originale du plan et écarte les conditions proposées par la stratégie. Le relecteur vérifie les conditions nécessaires directement dans les citations. Les exclusions et les consignes de personnalisation restent visibles. [Deuxième passage Bannerbear](bannerbear/proposition-replay-v2/replay.json), [deuxième passage Canny](canny/proposition-replay-v2/replay.json).

## Résultat final

Le dernier passage reprend des brouillons exacts des passages précédents avec leur plan et relance la relecture et, au besoin, la réécriture de production. Chaque marque a utilisé cinq appels. Aucun verdict antérieur n’a été repris.

| Marque | Résultat | Texte retenu |
| --- | --- | --- |
| Bannerbear | Vérification des sources passée, texte et HTML exportés après une réécriture. | Un même modèle produit des variantes à partir des données fournies. Le bouton mène à l’inscription à l’essai. |
| Canny | Vérification des sources passée, texte et HTML exportés. | Autopilot extrait et regroupe les demandes. L’inscription gratuite est proposée sans prix, quota ni cycle de facturation. Une autre réécriture a réintroduit le cycle annuel et a été rejetée. |

Les deux emails restent à relire sur le plan éditorial selon le lecteur simulé. Le rejeu valide les deux régressions ciblées sur les archives et ne mesure pas une nouvelle marque, un nouveau parcours depuis l’accueil, ni le temps de travail économisé face à ChatGPT. [Bannerbear texte](bannerbear/proposition-final-replay/email.txt), [Bannerbear HTML](bannerbear/proposition-final-replay/email.html), [trace Bannerbear](bannerbear/proposition-final-replay/replay.json), [Canny texte](canny/proposition-final-replay/email.txt), [Canny HTML](canny/proposition-final-replay/email.html), [trace Canny](canny/proposition-final-replay/replay.json).

Vérifications du dépôt après les rejeux : 2 294 tests backend réussis, deux avertissements de dépréciation. Ruff, le lint frontend et le contrôle TypeScript sont passés.
