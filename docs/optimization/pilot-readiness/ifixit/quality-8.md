# iFixit — première séquence complète, 6 octobre 2026

Run `22f5e0eb-591f-40be-b453-a1369b1c23fd`, piste recovered-source-v4 → v5.
Même brief, public, destination produit, preset balanced et GPT `gpt-5.6-sol`.
914 faits avant récupération, 920 après ; ce résultat n'est pas comparable à une
séquence complète sur le corpus initial de 901 faits. Les anciens runs incomplets
restent sans note.

## Résultat brut : 74/100, correction obligatoire

3/3 livrés, revue de séquence passée, aucun manque matériel signalé par le pipeline.
60 étapes, 23 min 32 s, 3 459 736 tokens en entrée + 169 204 en sortie ; estimation
$31.3811. Ce statut technique ne garantit pas l'exactitude des emails.

| Critère constant | Note | Observation |
| --- | --- | --- |
| Faits | 15/25 | Prix, outils et exemple Polaroid étayés ; l'exhaustivité des exclusions de garantie est fausse dans l'email 3 |
| Public et offre | 19/20 | Offre identifiable dans les trois emails ; pas de possession de caméra ni de réparation ratée présumée |
| Argument | 15/20 | Choix de kit, usage concret, garantie ; le deuxième email reste moins convaincant pour un premier kit général |
| Continuité | 13/15 | Trois raisons distinctes, emails indépendants ; signatures à harmoniser |
| Rendu | 9/10 | HTML inspecté, trois boutons vers la page produit, résumé à 375 px sans débordement ; marque de test à renommer |
| Absence de promesses non étayées / répétitions | 3/10 | Preview et corps 3 disent que tout sauf trois outils est couvert, malgré R15–R18 |
| Total | **74/100** | **Ne pas utiliser la séquence brute sans corriger l'email 3** |

Le guide Polaroid autorise une extension flexible **ou un tournevis très court**,
alternative conservée. Aucune garantie de résultat de réparation. Les conditions de
garantie proviennent de la page US et doivent être revues pour le marché réel.

## Cause et correction

Le rédacteur et le critique recevaient R5, R14 et R19, mais pas les autres exclusions
R15–R18 de la même page officielle. Une règle générale sur les non-consommables plus
un seul exemple est devenue une liste complète. La sélection conserve maintenant
les limites de garantie de ces mêmes sources dans l'enveloppe existante de 15 faits.
Les prompts interdisent d'interpréter des exemples comme des exclusions exhaustives.

40 tests ciblés passent. Le probe réel `warranty-probe.json` fait trois appels GPT :
le critique repère les lignes fausses, le rédacteur les réécrit, puis le critique
valide le brouillon révisé. Coût estimé $0.809583. Aucun appel API payant à la carte,
aucune modification de la base par ce probe. Il ne rejoue ni lecteurs à froid ni
revue de séquence, et ne remplace pas les assets du run original.

La révision liste des exemples de consommables sans les présenter comme exhaustifs.
Lors de la revue de marque, préférer les noms précis Spudger et Halberd Spudger au
pluriel générique « spudgers », et vérifier les conditions régionales. Aucun nouveau
score de campagne n'est attribué à ce probe.

## Décision

Correction ciblée démontrée, mais pas de nouvelle séquence complète validée après elle.
Arrêter les générations répétées sur ce cas volumineux. Commencer les pilotes avec
les cas SaaS simples déjà validés et des sources ciblées. Conserver ce cas comme
régression de contexte de garantie ; rejouer une séquence complète si un pilote
réel de produit physique le nécessite, après chargement du code corrigé.

Consommation estimée iFixit : $107.9878 sur huit runs, plus $0.809583 pour le probe,
soit $108.797383. Inclut essais annulés et échecs ; ce n'est pas une facture.
