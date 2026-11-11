# Scribe — rejeu de la réécriture après une erreur factuelle

La correction ciblée passe. Le nouveau texte retire la capture en direct insuffisamment étayée sur Basic et conserve le partage du guide pour qu’un collègue puisse suivre la procédure. La revue IA a réévalué les affirmations du nouveau texte puis confirmé ce bénéfice en citant les deux passages.

Le rejeu reprend le premier brouillon de l’exécution Scribe v32c, le brief, les huit documents importés, la base de connaissances et le verdict de ce brouillon. Le corps et les champs de diffusion viennent de la chronologie. Les deux titres de mise en page viennent du verdict archivé. Les champs internes de rôle et de langue du brouillon rejeté étaient absents de la chronologie. Toutes les affirmations ancrées dans le verdict figurent dans le texte visible reconstitué. Aucun fait, lien, exemple ou consigne propre à Scribe n’a été ajouté au générateur.

| Mesure | Résultat |
|---|---|
| Réécriture avec le code de production | Une réécriture, une revue IA des sources et une lecture à froid. Trois appels GPT-5.6 Sol via abonnement, en 99 secondes. |
| Contrôle factuel | Le brouillon initial est bloqué dans le verdict archivé. Le texte corrigé passe sa nouvelle revue et l’application sélectionne la deuxième version. |
| Bénéfice | Le guide reste partageable et le texte dit à quoi il sert à l’équipe. La nouvelle revue cite le passage avant et après. |
| Contrôle négatif | La réécriture archivée sans partage est factuellement approuvée avec une réserve éditoriale sur le bénéfice perdu. |
| Limite du résultat | Le lecteur simulé reste à 6/10 et demande plus de détails sur le déroulement de l’essai. Ce rejeu vérifie une correction du parcours existant. Il ne mesure pas la vendabilité sur une nouvelle marque. |

Le premier contrôle négatif avait pris la simple production d’un guide comme preuve de conservation du bénéfice. Le contrôle corrigé identifie d’abord le passage qui décrit l’usage concret, puis cherche le passage équivalent dans la version réécrite. Le code vérifie la présence littérale des passages et des citations. Le modèle juge si leur sens est équivalent. L’absence de bénéfice reste une réserve éditoriale et ne peut ni approuver ni bloquer un fait à elle seule.

Les deux contrôles finaux ont pris un appel chacun sur des textes déjà produits. Ils n’ajoutent aucune étape au parcours de production. Avec le premier contrôle négatif qui a révélé le défaut, l’ensemble du rejeu a consommé six appels. L’estimateur a compté environ 1,20 USD sur ces appels via abonnement.

- [Email corrigé](../optimization/scribe-cold-v32-validation-2026-11-09/replay-v33/email.txt)
- [Brouillon, verdict et réécriture](../optimization/scribe-cold-v32-validation-2026-11-09/replay-v33/replay.json)
- [Contrôle final positif](../optimization/scribe-cold-v32-validation-2026-11-09/replay-v33b-positive/replay.json) · [Contrôle final négatif](../optimization/scribe-cold-v32-validation-2026-11-09/replay-v33b-negative/replay.json)
