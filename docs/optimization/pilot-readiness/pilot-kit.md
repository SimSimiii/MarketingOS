# Pilote accompagné MarketingOS

## Périmètre proposé

Tester la création de brouillons d'emails à partir des propres sources du participant,
avec validation humaine avant utilisation. Commencer avec 3 à 5 participants et un
cas concret chacun. Le recrutement et les contacts restent à la charge du fondateur.
Le produit ne doit promettre ni hausse des ventes ni taux d'ouverture mesuré.

Le mode local actuel permet une séance sur le poste de l'opérateur. Un accès public,
un déploiement, une facturation et une autonomie sans accompagnement ne sont pas
validés par cet audit. Aucun environnement de production n'a été modifié.

## Séance testeur — 30 à 45 minutes de parcours et de relecture

Ce créneau exclut l’attente variable de compilation et de génération. Recueillir si possible
le brief et les sources avant la séance ; prévoir une reprise quand les brouillons sont
prêts si la génération déborde. Ne pas promettre un résultat dans ce délai.

1. Apporter une offre réelle, son public, l'action attendue, l'URL de destination,
   et 1 à 3 sources officielles utiles. Éviter d'importer des informations privées
   de clients. Choisir une offre sans claims médicaux ou financiers pour ce pilote.
2. Créer une marque. L'adresse du site enregistrée est un repère ; ajouter ensuite
   les pages utiles dans **Sources**. Contrôler les titres et les documents importés.
3. Créer une campagne. Décrire le public, remplir le brief **Custom emails**, choisir
   le nombre, le ton et le lien. Enregistrer le brief.
4. Lire le brief sauvegardé et l'estimation d'appels avant **Run campaign**.
   La première compilation coûte plus ; les runs suivants réutilisent les sources.
5. Observer le suivi. Quitter puis rouvrir la page pour vérifier la reprise.
   Si le fournisseur refuse une requête, lire le motif au lieu de recréer la campagne.
6. Relire chaque email avec les sources : offre, faits, limites, prix, lien, prénom
   et signature. Une séquence doit donner des raisons distinctes de continuer.
7. Examiner l'aperçu à largeur mobile puis copier le texte ou le HTML depuis **Design**.
   Les liens et la signature doivent être finalisés dans l'outil d'envoi du participant.
8. Donner le retour ci-dessous. Aucun envoi à des destinataires n'est nécessaire
   pour terminer ce test.

## Guide opérateur

- Avant la séance : backend et frontend locaux disponibles, abonnement Codex connecté,
  quota disponible, modèle par défaut OpenAI. Ne jamais ajouter de clé API pour
  contourner un problème d'abonnement. Rôles de recherche marché : Claude si web-fetch requis.
- Faire un seul run à la fois pendant une séance ; les limites personnelles sont
  partagées. Une erreur de capacité n'est pas une preuve de quota épuisé.
- Choisir des sources ciblées. L'import Website peut lire plusieurs pages liées :
  vérifier le nombre importé avant compilation. Une vaste bibliothèque produit
  augmente la première compilation sans nécessairement améliorer le brief.
- Si une livraison est `degraded`, compter les emails effectivement livrés avant
  de parler d'une campagne terminée. Conserver les traces de l'échec ou de l'annulation.
- La copie doit rester un brouillon jusqu'à relecture de la marque. Vérifier les
  conditions commerciales actuelles dans ses documents originaux.
- Archiver : brief, sources, run, résultat, durée, coût estimé, corrections humaines
  et feedback. Séparer les simulations IA des retours du participant.
- Arrêter si aucune source ne permet d'affirmer le bénéfice demandé ; demander
  le document manquant ou changer le brief sans inventer une preuve.

## Accès et limites avant un pilote distant

Les tests couvrent l'authentification, la rotation des sessions et l'isolation des
marques/campagnes entre comptes. Le serveur de ce poste est en mode local sans
authentification obligatoire : ne pas l'exposer au réseau pour accueillir des testeurs.
Pour une future ouverture, activer l'authentification dans un environnement dédié,
préparer les comptes invités, vérifier l'accès réel avec deux comptes et fixer une
enveloppe de générations. Cela exige une préparation distincte de l'accès distant ;
aucune de ces opérations n'a été effectuée en production ici.

## Invitation à adapter par le fondateur

« Je cherche quelques personnes pour tester MarketingOS sur une vraie offre :
vous apportez vos sources et votre besoin, nous créons puis relisons les emails
ensemble. Prévoir 30 à 45 minutes de parcours et de retour, avec une génération
préparée en amont si nécessaire. Aucun envoi d’email n’est demandé. Le but est
de voir si le résultat vous serait utile et quelles retouches vous feriez. »

## Retour par participant

| Question | Réponse à consigner |
| --- | --- |
| Offre, public, objectif | Le besoin réel avant de voir le résultat |
| Parcours | Étape où une aide a été nécessaire ; temps pour arriver au brief |
| Faits | Claims incorrects ou conditions manquantes, avec source |
| Compréhension | Ce que le lecteur pense être vendu et l'action proposée |
| Utilisation | Utilisable tel quel / petites retouches / réécriture / inutilisable |
| Retouches | Texte exact changé et minutes passées |
| Valeur | Aurait utilisé ce résultat dans son travail ? Pourquoi ? |
| Achat | Paierait pour un prochain résultat similaire ? Montant et conditions libres |
| Incident | Run, étape, erreur, récupération et temps perdu |

## Critères de passage proposés

Pour décider d'élargir après les premiers retours : aucun fait matériel non soutenu,
aucun problème d'accès entre comptes, majorité des participants capables d'enregistrer
leur brief et de récupérer le résultat avec au plus une aide, et au moins 3 participants
sur 5 qui utiliseraient le résultat après de petites retouches. Consigner séparément
les réponses d'achat : une bonne note éditoriale ne démontre pas la volonté de payer.
Ces seuils sont des critères de pilote proposés, pas des résultats déjà obtenus.

## Temps restant

Les contacts peuvent commencer pendant la préparation. Une séance locale accompagnée
peut se tenir après validation des cas et préparation des sources du participant.
Réserver environ une demi-journée pour organiser les 3 à 5 premières séances ; les
retours et éventuelles corrections prendront ensuite 2 à 5 jours de travail selon
les problèmes rencontrés. Un lancement public n'a pas de date fiable avant ces retours
et la vérification d'un accès distant dédié.
