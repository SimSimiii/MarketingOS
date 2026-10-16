# Préparation du pilote — 6 octobre 2026

## Cadre

Travail local sur `master`, changements de Claude conservés et revus. Aucun commit,
push, merge, déploiement, contact de prospect ou envoi d’email. La configuration versionnée, le fichier .env.example et les modèles de campagne
par défaut sont OpenAI (`gpt-5.6-sol`) ; les rôles nécessitant web-fetch gardent Claude.
Les nouveaux cas conservent cette allocation. Les notes ci-dessous sont des jugements
éditoriaux internes, pas des mesures de conversion ni une preuve de volonté de payer.

## Parcours et corrections vérifiés

Création de marque et import, brief libre avec 1–12 emails, sauvegarde avant consultation
de l’estimation puis lancement, suivi et historique, copie texte/HTML, rendu mobile.
Les noms blancs sont refusés. Les doublons finaux exacts de CTA/signature sont retirés
sans désactiver les contrôles factuels. Le public personnalisé est transmis aux lecteurs
de contrôle. Les livraisons partielles affichent leur compte exact et un statut d’attention.
Voir `ui-audit.md` pour la preuve et les limites de chaque parcours.

Vérification finale du code corrigé : **1403 tests backend passent**, Ruff `app tests`
propre ; frontend lint et typecheck propres, **12 tests passent**, build réussi.
Deux avertissements backend existants concernent les dépendances. Aucune colonne
SQL ajoutée, donc pas de migration requise. Le backend local a chargé les corrections
avant les runs de validation définitifs.

## Validation des campagnes

| Cas | Périmètre | Livraison et verdict |
| --- | --- | --- |
| Plausible | 1 email, SaaS, sources et dossier de pertinence | 85/100, utilisable après revue normale de marque ; cas vérifié lors de la reprise OpenAI |
| Buffer | 1 email, planification de posts d’un commerce | 87/100, utilisable après revue normale de marque ; cas vérifié lors de la reprise OpenAI |
| National Trust | 1 email, adhésion, une seule page officielle | 0/1, `needs_input` ; non vendable pour ce brief. La couverture des lieux et restrictions manque ; aucun score inventé |
| iFixit | 3 emails, produit physique, 12 pages officielles | Validation en cours ; la première livraison 1/3 ne valide pas une séquence |

La grille constante répartit 100 points : faits 25, public/offre 20, argument 20,
continuité 15, rendu 10, absence de promesses non étayées/répétitions 10. Chaque score
nécessite la lecture des assets, des preuves et du rendu. Les conditions différentes
et les anciens runs Claude sont conservés sur des pistes séparées.

## Fiabilité et consommation

Les échecs et annulations restent dans les dossiers de cas. Le premier iFixit a atteint
la limite de durée et livré 1/3 ; son enveloppe a été étendue pour ce seul cas à
3600 secondes / 4M tokens. Le deuxième National Trust était bloqué par
la limite d’abonnement, explicitement attestée par la trace CLI ; le quatrième s’est
arrêté sur des preuves manquantes. Ce dernier résultat précède les nouvelles consignes
de critique et de destination du bouton, et n’a pas été rejoué avec elles. Le quota est
disponible à la reprise. Deux essais ont été annulés car lancés avant le rechargement vérifié du
backend ; ils sont conservés comme erreurs d’opérateur, sans score produit.
Les montants affichés sont des estimations de consommation et ne sont pas des factures.

## Pilote et prochaine décision

Le protocole, le guide opérateur et le formulaire de retour sont dans `pilot-kit.md`.
Prévoir 3–5 participants, un besoin réel chacun, et une relecture de marque avant usage.
Le recrutement appartient au fondateur. Une séance locale accompagnée est le premier
périmètre visé ; un accès public autonome et une facturation ne sont pas validés ici.

Après les générations en cours : examiner les textes complets et leur evidence ledger,
consigner les verdicts et rendre le kit au fondateur. Les contacts peuvent commencer
pendant la préparation. Estimation de préparation des premières séances : une demi-journée,
puis 2–5 jours de travail pour exploiter les retours et corriger les problèmes rencontrés.
Un lancement public nécessite encore un accès distant dédié vérifié et les retours réels.

## Limites explicites

Campagnes évaluées en anglais ; aucune conclusion générale sur les autres langues.
Pas de vrais utilisateurs, d’envoi, de mesure d’ouverture/clic/achat ou de test réel
Outlook/Gmail. Authentification et isolation testées automatiquement ; navigateur local
sans authentification obligatoire. Rendu mobile examiné dans le navigateur. Le temps
et la consommation varient avec les sources, la première compilation et les réponses
fournisseur ; ne pas promettre une séance complète de génération en 30 minutes.
