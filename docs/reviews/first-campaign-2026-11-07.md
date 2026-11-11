# Première campagne — vérification du 7 novembre 2026

Les appels réels ont repris avec les abonnements configurés. Les essais utilisent des bases SQLite isolées, la branche `master` et des brouillons uniquement. Aucun envoi, déploiement ou paiement API. Les essais historiques du 6 novembre restent conservés.

## Résultats examinés

| Cas | Préparation du dernier passage | Génération | Résultat |
| --- | --- | --- | --- |
| Buttondown, sources et recherche déjà sauvegardées | 4 appels, 6 min 47 s | 3 appels, 1 min 24 s | Un email terminé, sans demande de revue ; ajustement facultatif ensuite accepté |
| Papier, sources et recherche déjà sauvegardées | 2 appels, 2 min 48 s | 5 appels, 2 min 19 s | Un email terminé, sans demande de revue |
| Simple Analytics, dossier agence corrigé sur les sources sauvegardées | 2 lectures de dossier fermées sur GPT ; puis préparation réutilisée, 0 appel | 3 appels, 1 min 41 s sur le dernier essai | Un email terminé, sans demande de revue ; les versions précédentes restent conservées |

Ces durées sont celles des passages indiqués. Elles excluent les préparations précédentes, les interruptions de quota et le temps de consultation. Ce ne sont pas des durées de premier démarrage. Le parcours vierge Buttondown fait l’objet d’une piste séparée.

Buttondown : le bénéfice est de conserver le blog comme lieu de publication et d’utiliser son flux RSS pour alimenter les emails. Le texte conserve la configuration initiale du modèle, la cadence par nouvel élément, l’intervalle de lecture du flux et le caractère additionnel du tarif. Les faits ont été confrontés à la [documentation RSS officielle](https://docs.buttondown.com/rss-to-email) et à la [tarification officielle](https://buttondown.com/pricing). Une demande utilisateur « Too long. Make it shorter and more direct. » a produit une proposition en un passage, sans nouvelle stratégie ni relance de campagne. L’original est conservé ; l’acceptation repasse les contrôles et retire le score de lecture de l’original de la version modifiée.

Papier : le message explique le format août–juillet, les sections de planification, les options de présentation et la personnalisation. Le bouton mène au [guide officiel de l’agenda académique](https://www.papier.com/thefold/articles/why-an-academic-year-diary-still-belongs-on-your-desk). Le prix d’un autre produit et la politique de retour d’un carnet d’adresses ne sont pas transférés à cet agenda. Aucun gain de mémoire ou de performance scolaire n’est promis.

Simple Analytics : le dossier GA4 reste `DISCOVERY_ONLY` pour la quantification spécifiquement attribuable au refus de consentement. Le cas agence peut évaluer un déploiement par site sans exiger artificiellement un forfait unique illimité. Deux lectures fermées sur GPT ont conservé cette distinction ; aucune recherche Web n’a été remplacée par une réponse sans outils. Le premier email agence affirmait des conséquences juridiques trop générales. Après correction et redémarrage du serveur, le texte décrit les champs traités, l’absence d’identifiants persistants et le stockage des IP, puis renvoie au [périmètre public du traitement](https://www.simpleanalytics.com/data-processing-agreement). Les propriétés techniques ont aussi été confrontées à la [page officielle de collecte](https://www.simpleanalytics.com/data-collection), séparément de l’entrée fournie au générateur.

Pour ces trois cas, la copie dans le presse-papiers et le téléchargement contiennent la version sélectionnée. Les rendus HTML ont été examinés à 390 et 1280 pixels, sans débordement. Le logo Papier se charge ; les deux autres messages utilisent un nom de marque textuel sans image cassée.

## Défauts corrigés

- Le dossier exigeait parfois une garantie de fonctionnement parfait ou une équivalence entre toutes les variantes. Les exigences manquantes doivent citer une condition qui impose réellement ce manque, et non simplement un sujet voisin. Une réponse contradictoire reste provisoire en code, sans acheter un appel de correction sémantique. Les véritables inconnues restent bloquantes. La documentation d’une variante ne valide pas les autres.
- Une hypothèse d’audience non adaptée ne doit pas monopoliser toute la préparation. Le parcours peut étudier une deuxième hypothèse existante, dans le budget courant, et conserve les raisons du rejet de la première. Il ne change pas ses besoins pour obtenir artificiellement un avis positif.
- La recherche officielle déjà effectuée est enregistrée avec le dossier pour éviter de la racheter à chaque reprise inchangée.
- Le logo déclaré par Buttondown renvoyait 404. L’adoption vérifie désormais l’image avec les limites réseau existantes ; la préparation vérifie aussi les anciennes images importées. Les URL choisies par le propriétaire restent conservées.
- « See the RSS workflow » était signalé à tort alors que le brief prévoyait la documentation RSS. Le contrôle reconnaît le sujet effectivement documenté à la destination ; une démo, un autre sujet ou un tarif non prévu restent signalés.
- Après acceptation d’une retouche, le bandeau global affichait encore le score de l’original. Il distingue désormais la version modifiée et renvoie à ses propres contrôles.
- Une demande de gratuité non prouvée conservait le bon prix mais produisait une retouche cosmétique sans expliquer le refus. Le nouvel essai identique a gardé le texte et renvoyé une explication explicite en un appel. La version choisie reste inchangée ; une proposition expérimentale a aussi été refusée, sans perte de l’historique.
- Une recommandation actuelle utilisable est réutilisée avant de relancer la recherche d’une hypothèse mieux classée mais encore incertaine. Une recherche terminée sans problème vérifiable est conservée ; un reçu de recherche officielle ne certifie pas que la question a été résolue et n’est réutilisé que pour les mêmes entrées.
- Un brouillon exploratoire peut porter sur un besoin opérationnel entièrement couvert et des faits licenciés, avec une demande explicitement non vérifiée. Il ne crée ni témoignage, ni problème observé, ni prospect qualifié. Une capacité manquante, des faits tous retenus hors texte ou un besoin incomplet continuent d’empêcher cet avis favorable.
- La cartographie compacte distingue le besoin opérationnel des souhaits de forfait, de permissions ou de quota ajoutés sans source. L’effort moyen est transmis aux modèles Claude compatibles durant cette préparation uniquement ; son effet sur le délai réel reste à mesurer après la réinitialisation.
- Choisir GPT pour une analyse de dossier fermée ne force plus ce choix sur le rôle de recherche Web inutilisé. La recherche Web continue d’exiger ses outils.

## Appréciation éditoriale

Jugements internes, sans mesure de conversion ou de disposition réelle à payer. Grille fixe : faits 25, audience/offre 20, argument 20, continuité objet/texte/action 15, finition/rendu 10, absence de promesses non étayées/répétitions 10.

Buttondown : original **84/100**, version acceptée **88/100**. L’argument reste une évaluation par la documentation, sans comparaison tarifaire complète ni promesse de migration. Papier : **84/100** sur cette nouvelle piste ; le résultat est concret et utilisable, plus informatif que très distinctif, et ne remplace pas une fiche produit indiquant prix et dimensions.

Simple Analytics, piste agence : **75/100** au premier essai, **82/100** après correction (+7 sur des entrées inchangées). Le résultat final est surtout utile pour une évaluation technique ; il reste moins persuasif qu’un bon email général d’acquisition. Un essai intermédiaire a encore utilisé les anciens prompts en cache : il est conservé comme expérience invalide pour mesurer la correction, sans score d’amélioration. Le redémarrage requis est documenté dans le journal.

Buttondown et Papier présentent une utilité payante plausible comme création assistée d’emails sourcés. Simple Analytics fournit maintenant un brouillon d’évaluation exploitable, avec un argument commercial encore modeste. Les lectures modèles ne prouvent ni des conversions ni un paiement réel. **Le parcours complet depuis une marque vierge n’est pas validé ; aucun verdict global de vendabilité autonome n’est déclaré.**

## Premier démarrage et quota

| Essai | Appels terminés | Durée du passage | Résultat |
| --- | --- | --- | --- |
| Buttondown vierge, plafond initial | 11 | 8 min 24 s | Arrêt avant le dossier ; sources et recherche conservées |
| Reprise de ce même cas | 10 | 9 min 48 s | Aucune recommandation utilisable pour les deux besoins détaillés proposés |
| Nouvelle marque Buttondown, avant la dernière correction de sélection | 15 | 16 min 11 s | Besoin enrichi de permissions non établies ; arrêt au budget |
| Nouveau cas v23, objectif prérempli et homepage seulement | 0 | 12 s après lancement | Quota Claude atteint pendant la compilation ; neuf pages sauvegardées |

La limite de préparation passe à quinze minutes **entre les étapes** ; un appel déjà commencé peut la dépasser. Le contrôle n’interrompt pas un modèle en cours. Le délai du premier démarrage n’est donc ni garanti sous dix minutes ni validé par ces essais. Les appels infructueux de ces passages ne sont pas masqués par les onze appels des trois générations finales.

Claude Code a annoncé une réinitialisation le **7 novembre à 15 h 20, Europe/Paris**. Les analyses fermées et les derniers emails ont pu utiliser l’abonnement ChatGPT déjà configuré. Aucun contournement sans outils de la recherche publique n’a été effectué.

Reprise : terminer le [cas v23 sauvegardé](../optimization/buttondown-cold-v3-first-campaign-2026-11-07/state.json), puis effectuer un parcours véritablement neuf, avec la seule homepage et l’objectif par défaut. Vérifier notamment la qualité des hypothèses d’audience, la compilation des bénéfices et le délai sans interruption. Une durée de reprise ne doit pas être présentée comme un premier démarrage complet.

## Contrôles techniques

Backend : **2 229 tests passent**, Ruff propre. Frontend : lint et vérification TypeScript propres, **37 tests passent**. Vérification des migrations sur une base jetable et parité des modèles réussies. Types API régénérés et types manuels synchronisés. Après le dernier changement de prompts, 31 tests ciblés supplémentaires passent et le cas Simple Analytics a été réellement régénéré après redémarrage.

La première exécution des tests a révélé des doubles de recherche incompatibles avec le nouvel argument facultatif, deux attentes structurelles devenues obsolètes et des tests comptables dépendants de la date du jour. L’horloge des fixtures de prix est stabilisée ; le refus des tarifs périmés en production reste actif et possède son test dédié. Aucun tarif de production n’a été modifié.

## Traces

- [Buttondown, original et proposition](../optimization/buttondown-first-campaign-2026-11-06/resume-2026-11-07/state.json)
- [Email Buttondown choisi](../optimization/buttondown-first-campaign-2026-11-06/resume-2026-11-07/selected-email.html)
- [Email Papier](../optimization/papier-v4-first-campaign-2026-11-06/resume-2026-11-07/email.html)
- [Email Simple Analytics retenu](../optimization/simpleanalytics-v2-first-campaign-2026-11-06/resume-2026-11-07/email.html)
- [Historique Simple Analytics et comparaison](../optimization/simpleanalytics-v2-first-campaign-2026-11-06/resume-2026-11-07/state.json)
- [Résultat final des tests backend](../optimization/buttondown-cold-v3-first-campaign-2026-11-07/backend-tests-final.txt)
- [Dernière piste depuis une marque vierge](../optimization/buttondown-cold-v3-first-campaign-2026-11-07/case.json)
