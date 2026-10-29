# Recherche marketing, psychologie et email — applications à MarketingOS

Date : 29 octobre 2026. Rapport de recherche et de conception ; aucune modification du générateur dans ce travail.

## 1. Ce que MarketingOS devrait apprendre de cette recherche

**Un bon email aide une personne donnée à prendre une décision pertinente, avec suffisamment de compréhension et de confiance, pour un effort acceptable.** Cette proposition est une synthèse de conception, pas une formule scientifique de conversion.

Le système doit d'abord comprendre l'offre, le destinataire, leur relation et la décision à faciliter. La qualité de la formulation vient ensuite. Une offre inadaptée, un besoin inventé ou un rendez-vous disproportionné ne se réparent pas avec un meilleur objet.

Les priorités proposées sont :

1. Adapter la rédaction et l'évaluation au type de message et à la relation réelle.
2. Vérifier que la preuve répond précisément à la promesse et au doute du lecteur.
3. Expliquer l'intérêt et le coût de la prochaine action, sans exagérer ce qu'elle permettra de vérifier.
4. Traiter la rareté, le storytelling, les promotions et la personnalisation comme des options conditionnelles.
5. Remplacer les règles éditoriales prétendument universelles par des choix explicites, testables et contextualisés.
6. Mesurer hors ligne les défauts de raisonnement et de communication, sans présenter les préférences d'un modèle comme des ventes prédites.

### Méthode et niveau de confiance

Cette revue ciblée croise des expériences de terrain, des méta-analyses, des recherches d'utilisabilité, des recommandations officielles et une lecture du code actuel. Elle n'est pas une revue systématique exhaustive : pas de protocole préenregistré, de recherche exhaustive dans toutes les bases ni de réanalyse des données originales. Certaines conclusions reposent sur les résumés et extraits accessibles des publications ; elles restent limitées à ce qui y est indiqué.

Les sources ne sont pas interchangeables :

| Type | Ce qu'il permet de dire | Ce qu'il ne permet pas de dire |
|---|---|---|
| Expérience randomisée sur un véritable email | Une intervention a causé une différence dans ce contexte | Le même gain se reproduira pour MarketingOS |
| Méta-analyse | Plusieurs études convergent, ou leurs résultats varient | Chaque public réagira comme la moyenne |
| Étude observationnelle | Deux phénomènes sont associés | L'un provoque nécessairement l'autre |
| Recherche d'utilisabilité | Des obstacles de lecture ou de navigation existent | Leur correction produira un gain de vente déterminé |
| Documentation officielle | Une exigence technique ou réglementaire est publiée | Le message est persuasif |
| Proposition de ce rapport | Une adaptation cohérente à tester dans le système | Un résultat expérimental déjà acquis |

Une synthèse de **1 149 études et 30 variations de messages** conclut que les différences moyennes de persuasion sont généralement petites et que l'option gagnante en moyenne ne gagne pas systématiquement. Cela n'annule pas le travail de rédaction : cela interdit de transformer une recette en garantie. [O'Keefe et Hoeken, 2021](https://pubmed.ncbi.nlm.nih.gov/34267703/).

## 2. Ce qui intervient réellement dans une décision d'achat

Le modèle de travail suivant sert à diagnostiquer un message. Ce n'est ni une équation ni une description obligatoire du chemin de tous les acheteurs.

| Question du destinataire | Ce que le message doit rendre possible | Erreur fréquente |
|---|---|---|
| Pourquoi me parlez-vous de cela ? | Reconnaître une situation ou un intérêt plausible | Une introduction interchangeable ou une douleur inventée |
| Qu'est-ce que c'est ? | Identifier le produit, le service ou l'offre | Décrire un problème sans nommer la solution |
| Qu'est-ce que cela change pour moi ? | Relier une capacité à une conséquence utile | Empiler des fonctionnalités ou des adjectifs |
| Pourquoi le croire ? | Examiner un fait, un mécanisme, une démonstration ou un résultat attribué | Une affirmation enthousiaste sans support |
| Est-ce adapté à mon cas ? | Voir le périmètre, les conditions et les limites importantes | Transformer un cas client en promesse générale |
| Qu'est-ce que cela me demande ? | Comprendre l'effort, le prix, les dépendances ou l'engagement | Un bouton facile derrière lequel se cache un projet |
| Pourquoi maintenant ? | Voir une raison réelle de considérer l'offre | Inventer une urgence parce que le modèle veut un clic immédiat |
| Que se passe-t-il ensuite ? | Anticiper le résultat de l'action proposée | « En savoir plus » vers une page sans rapport précis |

Les motivations possibles dépassent la douleur : accomplissement, plaisir, confort, autonomie, sécurité, appartenance, reconnaissance, découverte, maîtrise d'un travail, réduction d'une incertitude. **Ce sont des hypothèses de motivation à relier à l'offre et au contexte, pas des traits à attribuer automatiquement aux gens.**

Un acheteur B2B peut chercher un résultat pour son entreprise et vouloir pouvoir défendre sa décision auprès de collègues. Un acheteur d'un produit de loisir peut surtout vouloir une expérience agréable. Un utilisateur déjà inscrit peut avoir besoin d'une instruction, sans avoir besoin d'être convaincu d'acheter à nouveau. Ces distinctions sont des scénarios de conception, pas des stéréotypes démographiques.

Une expérience de courrier commercial dans le crédit montre que le contenu peut modifier une véritable décision, tout en soulignant la difficulté de prévoir quelle présentation sera efficace. Le prix et l'offre restent aussi déterminants. Le domaine du crédit ne justifie aucune promesse chiffrée pour l'email SaaS. [Bertrand et collègues](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1332007).

## 3. Les leviers utiles, leurs limites et leur application

### 3.1 Pertinence et personnalisation

Des expériences randomisées avec trois entreprises ont trouvé des bénéfices à une personnalisation même peu informative. Dans l'expérience principale rapportée par les auteurs, le prénom dans l'objet augmente les ouvertures de 20 % et les leads de 31 %, en relatif. **Ce ne sont pas 20 ou 31 points de pourcentage, ni une prévision pour un nouvel envoi.** [Résumé des auteurs à Stanford](https://www.gsb.stanford.edu/faculty-research/working-papers/personalization-email-marketing-role-non-informative-advertising) ; [publication de 2018](https://pubsonline.informs.org/doi/abs/10.1287/mksc.2017.1066).

À l'inverse, des recherches sur la publicité personnalisée montrent que la collecte perçue comme dissimulée peut provoquer un sentiment de vulnérabilité et dégrader la réaction. Le contexte étudié est publicitaire, pas un essai de tous les types d'emails. [Aguirre et collègues, 2015](https://openaccess.city.ac.uk/id/eprint/15747/).

**Application proposée :** privilégier une pertinence explicable : rôle professionnel, objectif déclaré, contenu auquel la personne s'est inscrite, usage confirmé. Le prénom reste une option. Un fait public sur une entreprise ne prouve ni les difficultés ni les émotions d'une personne.

À éviter : « J'ai remarqué que votre équipe perd du temps à… » quand seule l'activité de l'entreprise est connue. Préférer une formulation conditionnelle ou une présentation de capacité qui ne présuppose pas ce vécu.

### 3.2 Concret, compréhension et mécanisme

Des travaux sur les échanges de service client relient un langage concret à la satisfaction et aux achats ; leurs expériences soutiennent notamment le rôle de l'impression d'être compris. La transposition à l'acquisition par email est plausible, mais indirecte. [Packard et Berger, 2021](https://academic.oup.com/jcr/article/47/5/787/5873524).

**Application proposée :** exprimer une action observable avant un bénéfice abstrait. « Rassembler les commentaires sur une version du document » aide à imaginer l'usage ; « révolutionner votre collaboration » ne permet pas de vérifier ce qui sera différent.

Un mécanisme explique comment une capacité pourrait produire un bénéfice. Il ne prouve pas à lui seul un résultat chiffré. Une bonne démonstration peut être plus utile qu'un témoignage général, selon le doute à résoudre.

### 3.3 Preuve sociale et crédibilité

Une méta-analyse de 96 études trouve une association positive moyenne entre bouche-à-oreille électronique et ventes, avec des différences selon les produits, plateformes et mesures. Il ne s'agit pas d'une preuve que coller un témoignage dans n'importe quel email fera acheter. [Babić Rosario et collègues, 2016](https://pure.rug.nl/ws/files/81643765/The_effect_of_electronic_word_of_mouth_on_sales_a_meta.pdf).

**Application proposée :** choisir la preuve selon la question :

| Doute | Support pertinent si disponible | Support insuffisant à lui seul |
|---|---|---|
| Le produit fait-il cette action ? | Démonstration ou documentation de la capacité exacte | Nombre total de clients |
| Le résultat est-il plausible ? | Cas attribué avec situation, résultat et conditions | Slogan de marque |
| Cela convient-il à notre fonctionnement ? | Exemple comparable et prérequis vérifiés | Logo célèbre sans détail |
| Puis-je l'essayer sans projet lourd ? | Conditions réelles de l'essai et étapes nécessaires | « Simple » ou « sans friction » |
| Puis-je faire confiance au vendeur ? | Identité claire, sources vérifiables, engagements précis | Série de superlatifs |

Ne pas inventer de preuve lorsque la marque est jeune. Présenter une démonstration limitée, une caractéristique vérifiable ou une invitation à examiner l'offre.

### 3.4 Effort, risque et réversibilité

Une méta-analyse de 21 articles sur les politiques de retour montre que leur souplesse peut favoriser les achats, avec des effets différents selon l'argent, le délai, l'effort et le périmètre. Une politique commerciale réelle n'est pas équivalente à écrire « sans risque ». [Janakiraman, Syrdal et Freling, 2016](https://www.sciencedirect.com/science/article/pii/S0022435915000822).

**Application proposée :** distinguer le coût du clic du coût de l'action : inscription, carte bancaire, import de données, installation, décision d'équipe, appel commercial. N'annoncer « sans carte », « remboursable » ou une durée de mise en route que si les sources l'établissent.

Le petit pas n'est utile que s'il aide une décision réelle. Un test sur un document peut éclairer un usage ; il ne valide pas une migration complète ou toutes les contraintes de sécurité.

### 3.5 Choix et appel à l'action

La surcharge de choix n'est pas une loi générale : une méta-analyse de 2010 trouve un effet moyen proche de zéro et une forte variabilité. Celle de 2015 identifie notamment la complexité, la difficulté et l'incertitude des préférences comme modérateurs. Ces travaux portent sur des choix, pas directement sur le nombre de boutons d'un email. [Scheibehenne et collègues, 2010](https://scheibehenne.de/ScheibehenneGreifenederTodd2010.pdf) ; [Chernev et collègues, 2015](https://myscp.onlinelibrary.wiley.com/doi/full/10.1016/j.jcps.2014.08.002).

**Application proposée :** un objectif principal est un bon réglage initial pour une sollicitation ciblée. Une newsletter de sélection peut légitimement proposer plusieurs contenus. Deux liens vers la même action ne constituent pas nécessairement deux décisions concurrentes. La désinscription n'est pas un CTA commercial concurrent.

### 3.6 Autonomie et pression

Une méta-analyse publiée en 2025 relie le langage qui menace la liberté de choix à davantage de colère, de pensées négatives et de réactance. Elle ne prouve pas qu'un bouton direct comme « Voir les modèles » soit nuisible. [Message effects on psychological reactance](https://academic.oup.com/hcr/article/52/1/38/8178818?searchresult=1).

**Application proposée :** demander clairement, sans culpabiliser. Éviter « vous ne pouvez pas vous permettre de rater cela » ou une relance qui reproche au destinataire de ne pas répondre. Ne pas confondre respect de l'autonomie et formulation interminable ou timide.

### 3.7 Rareté et urgence

Une méta-analyse de 131 études constate des effets de la rareté sur l'intention d'achat, variables selon la source de rareté et la catégorie de produit. Une intention déclarée n'est pas une vente observée. [Barton, Zlatevska et Oppewal, 2022](https://doi.org/10.1016/j.jretai.2022.06.003).

**Application proposée :** utiliser une date, un stock ou une capacité uniquement s'ils sont attestés et encore valides. Distinguer une échéance de l'offre d'une urgence supposée chez le lecteur. Lorsque rien ne presse, le message peut apporter une information utile sans exiger une action aujourd'hui.

### 3.8 Gains, pertes et émotions

Une méta-analyse portant sur 165 tailles d'effet ne trouve pas de supériorité générale des messages centrés sur les pertes. Les domaines et comportements étudiés limitent toute extrapolation commerciale. [O'Keefe et Jensen, 2006](https://academic.oup.com/anncom/article-abstract/30/1/1/7850835).

**Application proposée :** comparer un bénéfice attendu et un risque évité seulement lorsque les deux sont légitimes. Ne pas appliquer « la perte persuade deux fois plus » à la rédaction. Ne pas transformer un lancement ou un onboarding en récit d'échec. Une émotion doit venir d'un enjeu intelligible, pas d'une dramatisation ajoutée.

### 3.9 Histoires et identification

Une méta-analyse de 14 études trouve des avantages persuasifs aux récits dans les contextes étudiés, y compris à distance de l'exposition. Elle ne démontre pas qu'une histoire améliore chaque email court. [Oschatz et Marker, 2020](https://academic.oup.com/joc/article/70/4/473/5880130).

**Application proposée :** un cas réel peut illustrer une situation, une action et un résultat. Pour une instruction d'activation, le détour narratif peut être inutile. Séparer strictement cas client vérifié, exemple hypothétique et résultat promis. Ne jamais transformer un exemple inventé en témoignage.

### 3.10 Prix et promotions

Une méta-analyse de 51 études ne trouve pas de dégradation moyenne systématique de la préférence de marque après promotion ; les résultats changent selon les promotions et produits. L'affirmation « les réductions détruisent toujours la marque » est donc trop forte. [DelVecchio, Henard et Freling, 2006](https://www.sciencedirect.com/science/article/pii/S0022435906000388).

**Application proposée :** employer une promotion autorisée lorsqu'elle sert l'objectif commercial. Rendre visibles la période, le périmètre, la facturation et les conditions essentielles. Un meilleur texte ne suffit pas à décider si une remise est rentable. Ne pas inventer un prix de référence pour fabriquer une bonne affaire.

### 3.11 Ce que l'on peut apprendre des différences individuelles

Des expériences de publicité numérique ont trouvé des effets à l'adaptation de messages à des caractéristiques psychologiques. Elles n'établissent pas qu'un LLM puisse déduire correctement la personnalité d'un prospect à partir de sa page publique. [Matz et collègues, 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5715760/).

**Application proposée :** commencer par les différences observables et utiles : relation, tâche, expertise, conditions de décision, intérêt déclaré. Ne pas créer des profils imaginaires du type « dirigeant donc dominant », « jeune donc impulsif » ou « ingénieur donc insensible aux émotions ».

### 3.12 Fréquence et fatigue

Le nombre d'emails et leur cadence sont deux décisions différentes. Le corpus examiné ne permet pas de recommander une fréquence universelle. Une newsletter attendue, une relance après demande et une prospection inconnue ne donnent pas la même permission implicite de solliciter l'attention.

**Application proposée :** définir une raison propre à chaque message : explication, exemple, objection, rappel d'une échéance réelle. Si aucun contenu utile nouveau n'existe, ne pas ajouter une relance pour remplir une séquence. Ne pas supposer qu'un silence signifie une objection donnée, ni qu'une ouverture prouve l'intérêt.

## 4. Ce qui change selon les personnes et les situations

La matrice suivante est une proposition de stratégie à tester. Elle n'annonce pas que tous les membres d'un segment se ressemblent.

| Situation établie | Question probablement utile | Message à privilégier | Erreur à éviter |
|---|---|---|---|
| Prospect inconnu, problème non établi | Pourquoi examiner cette offre ? | Usage précis, pertinence conditionnelle, étape proportionnée | Lui raconter sa souffrance comme un fait |
| Prospect ayant demandé des informations | L'offre répond-elle à ma question ? | Réponse directe, preuves utiles, conditions | Recommencer une introduction à froid |
| Personne comparant des solutions | Quels compromis et prérequis ? | Différence vérifiée, périmètre, modalités | Comparaison avec un concurrent imaginaire |
| Client ou utilisateur inscrit | Que puis-je faire ensuite ? | Action concrète, aide, bénéfice de l'étape | Lui vendre à nouveau la catégorie entière |
| Acheteur satisfait de son outil actuel | Quelle valeur additionnelle justifie un examen ? | Cas précis, complément éventuel, coût du changement | Déclarer son outil actuel défaillant |
| Utilisateur opérationnel B2B | Que change cela dans mon travail ? | Usage et effort pratique | Seulement du ROI de direction |
| Décideur économique B2B | Quelle décision et quel engagement ? | Coût, périmètre, preuve pertinente | Une démo technique sans lien avec son arbitrage |
| Expert du domaine | Qu'apporte réellement cette solution ? | Terminologie exacte, limites, mécanisme | Supprimer les mots techniques nécessaires |
| Débutant | Qu'est-ce que c'est et comment commencer ? | Explication simple, repères concrets | Accumuler acronymes et prérequis implicites |
| Achat de loisir ou d'expression personnelle | Quelle expérience ou quel style ? | Usage, plaisir, caractéristiques sensibles | Forcer une justification de productivité |
| Abonné venu lire une sélection | Qu'est-ce qui mérite mon attention ? | Sélection lisible, liens descriptifs | Interdire plusieurs choix par principe |

La langue, la culture de communication et les conventions de politesse comptent comme paramètres de localisation. Sans données spécifiques, ne pas assigner de règles psychologiques nationales. Adapter le vocabulaire, les unités, la monnaie et le registre à la demande et aux exemples de marque.

## 5. Les éléments à avoir dans un email marketing

Il s'agit de fonctions à remplir, pas d'un ordre obligatoire de paragraphes.

| Élément | Fonction | Vérification proposée |
|---|---|---|
| Expéditeur identifiable | Comprendre qui parle | Nom et organisation réels ; relation non simulée |
| Objet fidèle | Donner une attente utile | La promesse de l'objet est tenue dans le corps |
| Pré-en-tête complémentaire | Préciser l'intérêt avant ouverture | Ne répète pas mécaniquement l'objet |
| Entrée pertinente | Expliquer pourquoi lire | Ne présuppose pas une biographie inconnue |
| Offre identifiable | Comprendre ce qui est proposé | Un lecteur peut la reformuler sans le brief |
| Conséquence utile | Relier l'offre à une décision | Le bénéfice découle d'une capacité réelle |
| Support adapté | Donner une raison de croire | La preuve porte sur cette affirmation précise |
| Conditions déterminantes | Éviter une fausse attente | Prix, périmètre et prérequis utiles sont préservés |
| Action explicite, si demandée | Savoir quoi faire et pourquoi | Libellé, destination et résultat sont cohérents |
| Identité et opposition | Permettre une relation transparente | Mentions et désinscription adaptées au contexte |

L'objet doit rester intelligible hors du corps et commencer par les mots utiles. Le pré-en-tête peut préciser la promesse. Les travaux d'utilisabilité de Nielsen Norman Group soutiennent cette priorité à l'information lisible dans la boîte de réception ; ce ne sont pas des expériences garantissant un taux de conversion. [Microcontent](https://www.nngroup.com/articles/microcontent-how-to-write-headlines-page-titles-and-subject-lines/) ; [recherche email, sixième édition](https://www.nngroup.com/reports/email-newsletter-design/).

Pour le rendu, conserver le contenu essentiel en texte, des liens compréhensibles, une hiérarchie simple et une lecture mobile correcte. Une image informative doit avoir une alternative qui transmet son sens ; une image décorative ne doit pas ajouter de bruit de lecture. [W3C, images informatives](https://www.w3.org/WAI/tutorials/images/informative/). Ces choix d'accessibilité ne prouvent pas à eux seuls un gain commercial.

Il n'est pas nécessaire d'avoir systématiquement un témoignage, un prix, une histoire, une promotion, une objection et un P.S. dans le même email. Une confirmation d'étape n'a pas besoin d'un argumentaire d'acquisition. Une newsletter peut livrer sa valeur dans le message même.

### Exemple pédagogique original

Les capacités de l'outil fictif ci-dessous sont supposées vérifiées pour l'exemple. Elles ne constituent pas des faits sur MarketingOS.

**Version faible :**

> Objet : Révolutionnez votre productivité !
>
> Votre équipe perd des heures chaque semaine. Notre solution innovante vous permet de collaborer plus efficacement. Profitez de cette opportunité unique et réservez une démo dès aujourd'hui.

**Version plus précise pour une audience qui examine des outils de relecture :**

> Objet : Les commentaires au même endroit que le document
>
> Pour faire relire un document à plusieurs personnes, Filigrane rassemble leurs commentaires sur sa version partagée.
>
> Vous pouvez voir qui a commenté chaque passage et répondre dans le même échange. L'exemple montre ce fonctionnement sur un document de démonstration.
>
> Voir l'exemple de relecture

Ce que cette réécriture améliore : une capacité identifiable, une utilité explicable, une destination précise, aucune histoire inventée sur le lecteur. Elle ne prouve pas que la version obtiendra davantage de ventes. Pour un client existant qui veut savoir comment inviter un collègue, il faudrait encore un autre message.

## 6. Les choses à éviter — et les faux remèdes

| À éviter | Pourquoi | Remplacement proposé |
|---|---|---|
| Faux « Re: », faux suivi de conversation | Crée une relation trompeuse | Objet commercial honnête |
| Urgence non documentée | Introduit un fait inventé | Date réelle ou absence d'urgence |
| Diagnostic imaginaire du prospect | Confond ciblage et observation | Usage conditionnel ou besoin déclaré |
| Témoignage généré | Fabrique une preuve | Cas sourcé ou démonstration limitée |
| Citation vraie mais hors sujet | Le fait ne soutient pas la promesse | Preuve attachée au doute précis |
| Bénéfice sans mécanisme ni appui | Demande de croire sans comprendre | Capacité précise et conséquence bornée |
| « Simple », « rapide », « sans risque » non qualifiés | Cache des prérequis possibles | Conditions vérifiées |
| Cinq raisons et cinq demandes dans un petit message | Rend l'arbitrage difficile | Priorité explicite selon l'objectif |
| CTA modeste vers un engagement lourd | Rompt l'attente créée | Annoncer ce qui arrive réellement |
| Relance culpabilisante | Menace l'autonomie et détériore la relation | Nouvelle information utile ou arrêt |
| Preuve recopiée partout | Allonge sans répondre à un doute nouveau | Réemploi uniquement lorsqu'il sert la décision |
| Benchmark fournisseur présenté comme causal | Mélange sélection des clients et effet du texte | Usage descriptif, périmètre indiqué |
| Persona inventée par le modèle | Produit de la précision sans fondement | Faits, hypothèses et inconnues distincts |

Ne pas remplacer ces erreurs par d'autres dogmes :

- « Toujours moins de 100 mots » : aucune longueur universelle n'est établie ici.
- « Toujours une seule URL » : le nombre de décisions et le type de message comptent davantage.
- « Toujours ouvrir sur la douleur » : l'aide, l'annonce et le plaisir sont aussi des usages légitimes.
- « Ajouter le prénom rend pertinent » : l'attention n'est pas l'adéquation de l'offre.
- « Une émotion forte fait acheter » : elle peut aussi détourner du produit ou provoquer un refus.
- « Le bouton rouge gagne » : ne pas transformer une convention graphique en mécanisme universel.
- « La meilleure heure est le mardi à 10 h » : aucune preuve générale applicable à toutes les audiences n'a été établie dans cette recherche.
- « AIDA ou PAS est une loi psychologique » : ce sont des structures de travail possibles, pas une obligation.
- « Plus de score IA signifie plus de ventes » : il manque une validation comportementale.

## 7. Délivrabilité, consentement et mesure

### Ce que la rédaction peut et ne peut pas garantir

Les consignes de Gmail portent notamment sur l'authentification, le transport, la réputation, les plaintes et la désinscription. Pour les expéditeurs de masse concernés, SPF, DKIM, DMARC et la désinscription en un clic font partie des exigences décrites. Une liste de mots interdits ne constitue donc pas une garantie d'arrivée en boîte principale. Cela ne signifie pas que le contenu n'intervient jamais dans le filtrage. [Google, exigences des expéditeurs](https://support.google.com/mail/answer/81126?hl=en).

**Proposition MarketingOS :** séparer « texte vérifié » et « configuration d'envoi vérifiée ». Le système actuel prépare des messages ; il ne peut certifier à partir du texte seul la réputation d'un domaine ou le fonctionnement des en-têtes de désinscription.

### Cadre français et international

En France, la CNIL distingue notamment le consentement préalable en B2C, sous exceptions encadrées, et la prospection professionnelle pertinente pour la profession avec information et opposition. La simple création d'un compte ne vaut pas automatiquement relation client pour l'exception B2C. Chaque message doit identifier l'annonceur et permettre l'opposition. Trouver une adresse sur une page publique ne règle donc pas à lui seul la question de l'utilisation commerciale. [CNIL](https://www.cnil.fr/la-prospection-commerciale-par-courrier-electronique).

Aux États-Unis, CAN-SPAM impose notamment des en-têtes et objets non trompeurs, une adresse postale valide et un mécanisme d'opposition ; le B2B n'est pas exclu. Ces règles ne doivent pas être appliquées comme si elles étaient identiques au cadre français. [FTC, guide CAN-SPAM](https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business?view=Schedule).

**Proposition :** attacher au contexte d'export le marché, la relation, les informations d'expéditeur et le mécanisme d'opposition disponibles. Signaler ce qui manque sans fabriquer de lien de désinscription ni prétendre certifier la conformité complète.

### Ce que l'on mesure

Apple indique que Mail Privacy Protection empêche les expéditeurs de savoir si l'utilisateur a ouvert leur message. Les ouvertures mesurées ne sont donc pas un reflet fiable et uniforme de l'attention humaine. [Apple](https://support.apple.com/en-ie/guide/iphone/iphf084865c7/27/ios/27).

Lorsqu'il existera des envois réels, l'indicateur utile dépendra de l'objectif : réponse qualifiée, activation accomplie, achat, contribution à la marge, rétention. Les désinscriptions et plaintes servent de contre-indicateurs. Cette perspective ne doit pas devenir une condition préalable à l'amélioration du générateur aujourd'hui.

## 8. Ce que MarketingOS fait déjà et ce qu'il reste à examiner

Constats issus de la lecture du code présent le 29 octobre 2026, comprenant les modifications locales en cours. Il ne s'agit pas d'un audit exhaustif d'exécution. Les chemins sont relatifs à la racine du dépôt.

| Sujet | Déjà présent dans le code lu | Conséquence pour les propositions |
|---|---|---|
| Objectif et relation | `backend/app/marketing/intent.py` distingue acquisition, activation, annonce, etc. | Étendre leur usage, ne pas recréer un modèle d'intention |
| Argument et alternative actuelle | `briefs.py` contient besoin, situation actuelle, mécanisme, objection | Ne pas imposer ces éléments lorsque le message ne les exige pas |
| Valeur du prochain pas | `next_step_decision`, `next_step_value`, `next_step_evidence_ids`, `next_step_limit` existent | Tester leur efficacité de bout en bout avant d'ajouter des champs |
| Séparation fait/hypothèse | Les prompts insistent déjà sur les frontières de preuve et la biographie inconnue | Préserver ce travail et vérifier ses régressions |
| Compréhension à froid | `reader.py` et `reader.md` demandent ce que le message vend | Conserver le lecteur privé du brief et de la documentation |
| Scores non prédictifs | `ReaderAssessment.pull` et `inbox.md` parlent d'évaluation éditoriale non calibrée | La correction des faux taux est déjà engagée ; ne pas la proposer comme absente |
| Situation de lecture | `reader.md`, `duel.md`, `inbox.md` imposent une boîte surchargée et une réunion proche | Tester l'effet de ce scénario constant selon le type d'email |
| Finalité du jugement | Le duel demande encore quelle version obtient le clic ; `would_act` est décrit comme cliquer aujourd'hui | Examiner les réponses, les actions d'activation et la valeur de lecture |
| Longueur | `email_copy.py` fixe notamment 60–220 mots, au moins trois paragraphes et 65 caractères d'objet | Ce sont des politiques éditoriales ; leur généralité mérite d'être testée |
| Filtre lexical | `gates.py` bloque notamment « buy now » et « money back guarantee » au titre du spam | Distinguer style indésirable, garantie réellement documentée et délivrabilité |

**Deux précautions de conception :** rendre une heuristique déterministe ne prouve pas sa validité ; ajouter une règle à un prompt déjà très long peut créer des contradictions. Une modification devrait remplacer ou préciser la règle existante, puis être évaluée sur des contre-exemples.

## 9. Plan d'intégration priorisé

Les coûts ci-dessous sont des estimations qualitatives, pas des devis. « Aucun nouvel appel » signifie aucun appel modèle supplémentaire par campagne ; l'allongement des entrées consomme tout de même davantage de tokens. Une évaluation des modèles sur banc reste facturée en quota.

| Priorité | Proposition | Point d'intégration | Coût marginal visé | Vérification disponible sans utilisateurs |
|---|---|---|---|---|
| P0 | Aligner le jugement sur la décision demandée | Intention, lecteur, duel, rapport | Aucun nouvel appel ; effort moyen si schéma modifié | Réponse par email, activation, lecture et clic correctement distingués |
| P0 | Contextualiser le lecteur pressé | Construction du profil et prompts lecteur/inbox/duel | Aucun nouvel appel ; effort faible à moyen | Même produit évalué comme prospection, newsletter attendue et onboarding |
| P0 | Requalifier les interdits de style et les longueurs | `gates.py`, `email_copy.py`, contrat et tests | Aucun nouvel appel ; effort moyen | Cas légitimes acceptés sans laisser passer tromperie ou contenu non fondé |
| P1 | Renforcer la correspondance promesse–preuve–doute | Sélection des preuves, critique et banc | Réutiliser les appels existants ; effort moyen | Une preuve exacte mais non pertinente ne masque pas le défaut |
| P1 | Vérifier la promesse de la prochaine action | Champs `next_step_*`, offre et destination connue | Aucun nouvel appel ; effort moyen | Pas de démonstration prétendue complète à partir d'un exemple limité |
| P1 | Enregistrer les conditions des tactiques | Brief, sources, critique | Aucun nouvel appel ; effort faible à moyen | Urgence expirée, garantie absente, remise hors périmètre détectées |
| P2 | Préparer un contrôle d'export distinct | Rendu et interface de livraison | Aucun nouvel appel ; effort moyen | Identité, opposition, liens et lisibilité contrôlés sur l'artefact |

### Précision sur P0 : préserver la lecture à froid

Ne pas donner au lecteur le brief stratégique pour qu'il « comprenne l'objectif ». Le lecteur doit rester capable de détecter ce que l'email n'explique pas. Le contexte légitime comprend la relation établie et une situation de lecture explicitement choisie ; il n'inclut pas la conclusion désirée par le vendeur.

Une approche possible : le lecteur décrit l'action qu'il comprend et l'obstacle qu'il perçoit ; le critique, déjà informé de la demande, vérifie si cela sert l'objectif. Le duel juge la clarté et la valeur de l'action exprimée, sans imposer que toute bonne décision soit un clic immédiat.

### Précision sur P0 : règles bloquantes ou avis

Conserver les contrôles d'intégrité : champs manquants, chiffres ou citations non autorisés, incohérences vérifiables, destination interdite. Les préférences de longueur, de ton ou de nombre de liens devraient dépendre d'un contrat éditorial explicite. Une politique de marque peut être stricte sans être présentée comme une loi scientifique.

Ne pas supprimer le filtre actuel en bloc. Construire d'abord des cas contradictoires : une garantie réelle, un nom technique en majuscules, un message d'activation très court, une newsletter utile plus longue. Identifier ce que chaque règle protège réellement et ce qu'elle rejette à tort.

### Représenter une règle issue de la recherche

Exemple de fiche de conception, sans exiger une nouvelle base de données :

```yaml
id: urgency_requires_current_evidence
decision: utiliser une urgence uniquement si elle est réelle et applicable
conditions:
  - échéance ou capacité attestée pour cette offre
  - validité temporelle contrôlable
  - périmètre conservé dans la copie
unknown_behavior: ne pas affirmer l'urgence
source_kind: méta-analyse pour l'effet ; source produit pour le fait
enforcement: contrôle de cohérence lorsqu'il est déterministe
editorial_review: examiner le caractère proportionné de la formulation
expected_conversion_gain: inconnu
```

Séparer deux preuves : **la littérature peut soutenir l'intérêt d'une tactique ; seule une source sur l'offre peut autoriser les faits employés dans l'email.** Un article sur la rareté ne prouve jamais que le produit est presque épuisé.

## 10. Évaluer les progrès sans envois et sans multiplier les appels

Les simulations de personnes par LLM peuvent reproduire certains résultats et présenter des distorsions sur d'autres tâches. Elles ne constituent pas un échantillon humain représentatif par défaut. [Aher, Arriaga et Kalai, ICML 2023](https://proceedings.mlr.press/v202/aher23a.html).

### Première couche : tests gratuits

Utiliser les fournisseurs scriptés existants pour vérifier les contrats, le routage, les champs, les décisions de conservation des versions et les conditions de tactiques. Construire des fixtures où la bonne décision dépend de faits explicites, pas d'une préférence de style.

### Deuxième couche : jeu de cas éditoriaux

Proposition de départ : douze scénarios documentés, chacun avec une version cohérente, une dégradation plausible et un contrôle neutre. Ce nombre est une taille de travail proposée, pas un minimum statistique.

| Cas | Dégradation étudiée | Résultat attendu hors ligne |
|---|---|---|
| Acquisition à froid | Douleur personnelle ajoutée sans source | Identifier l'hypothèse présentée comme fait |
| Réponse demandée | CTA de réponse remplacé par un clic sans utilité | Préserver l'action réellement demandée |
| Onboarding | Instruction remplacée par une promesse abstraite | Reconnaître la perte d'aide pratique |
| Annonce à des clients | Relation client remplacée par une présentation à froid | Détecter l'incohérence relationnelle |
| Comparaison technique | Suppression d'un prérequis déterminant | Identifier la fausse impression de compatibilité |
| Cas client | Résultat attribué transformé en garantie | Refuser la généralisation |
| Preuve sociale | Citation exacte mais sans rapport avec le doute | Distinguer présence et pertinence de la preuve |
| Démonstration limitée | Présentée comme validation d'un déploiement complet | Signaler le saut de portée |
| Promotion réelle | Condition déterminante retirée | Détecter l'offre devenue trompeuse |
| Échéance | Date passée présentée comme future | Échec déterministe selon date de référence |
| Newsletter | Plusieurs liens utiles pénalisés par principe | Ne pas appliquer aveuglément la règle du CTA unique |
| Message clair très court | Texte allongé seulement pour le quota de mots | Éviter de récompenser le remplissage |

Pour les cas de préférence contextuelle, admettre une égalité et conserver une justification. Une suppression de preuve n'est pas toujours une dégradation si la preuve était redondante : chaque paire doit être inspectée avant de devenir un test.

### Troisième couche : banc modèle limité

Après les vérifications gratuites, employer le banc existant sur un sous-ensemble pertinent. Alterner A/B, préserver des paires identiques et des variations neutres, analyser les résultats par défaut et par scénario. Ne pas utiliser le banc grossier déjà saturé pour revendiquer un progrès subtil.

Mesures proposées :

- détection de chaque défaut ciblé et faux positifs sur les contrôles ;
- reformulation correcte de l'offre et de l'action ;
- préservation des conditions et des preuves utiles après réécriture ;
- différences entre types de campagnes ;
- nombre d'appels et coût par email livré ;
- sensibilité à l'ordre A/B et aux variantes de formulation sans changement de sens.

La vérification automatique de la présence d'un fait n'établit pas sa compréhension. Les jugements sémantiques restent des évaluations de modèle ou de revue humaine, à rapporter comme tels. Garder une partie des cas hors du travail d'ajustement évite d'optimiser exclusivement pour les exemples connus.

**Ce que ce protocole permet d'affirmer :** moins de défauts ciblés, meilleure cohérence avec les contraintes, coût maîtrisé. **Ce qu'il ne permet pas d'affirmer :** hausse des ventes, taux d'ouverture attendu ou supériorité sur toute audience réelle.

## 11. Bibliographie de travail et limites de transfert

Les liens ci-dessous complètent les références placées auprès des conclusions. Les recommandations de conception non directement étudiées dans ces sources sont explicitement présentées comme propositions dans le rapport.

| Source | Nature et portée | Utilité principale |
|---|---|---|
| [O'Keefe & Hoeken, 2021](https://pubmed.ncbi.nlm.nih.gov/34267703/) | Synthèse de recherches sur les variations de messages | Limiter les recettes universelles |
| [Sahni, Wheeler & Chintagunta, 2018](https://pubsonline.informs.org/doi/abs/10.1287/mksc.2017.1066) | Expériences de terrain par email | Personnalisation ; effets contextualisés |
| [Aguirre et al., 2015](https://openaccess.city.ac.uk/id/eprint/15747/) | Publicité personnalisée et collecte d'information | Pertinence, transparence et vulnérabilité |
| [Packard & Berger, 2021](https://academic.oup.com/jcr/article/47/5/787/5873524) | Service client, données et expériences | Langage concret ; transfert indirect à l'acquisition |
| [Babić Rosario et al., 2016](https://pure.rug.nl/ws/files/81643765/The_effect_of_electronic_word_of_mouth_on_sales_a_meta.pdf) | Méta-analyse, association avis/ventes | Preuve sociale sans causalité universelle |
| [Janakiraman et al., 2016](https://www.sciencedirect.com/science/article/pii/S0022435915000822) | Méta-analyse des retours produits | Réduction du risque par conditions réelles |
| [Scheibehenne et al., 2010](https://scheibehenne.de/ScheibehenneGreifenederTodd2010.pdf) | Méta-analyse du choix | Variabilité de la surcharge |
| [Chernev et al., 2015](https://myscp.onlinelibrary.wiley.com/doi/full/10.1016/j.jcps.2014.08.002) | Méta-analyse avec modérateurs | Complexité et incertitude |
| [Réactance, 2025](https://academic.oup.com/hcr/article/52/1/38/8178818?searchresult=1) | Méta-analyses de communication persuasive | Coût potentiel du langage coercitif |
| [Barton et al., 2022](https://doi.org/10.1016/j.jretai.2022.06.003) | Méta-analyse de rareté | Intention d'achat ; différences de contexte |
| [O'Keefe & Jensen, 2006](https://academic.oup.com/anncom/article-abstract/30/1/1/7850835) | Méta-analyse gains/pertes | Absence de supériorité générale des pertes |
| [Oschatz & Marker, 2020](https://academic.oup.com/joc/article/70/4/473/5880130) | Méta-analyse de communication narrative | Histoires sous conditions |
| [DelVecchio et al., 2006](https://www.sciencedirect.com/science/article/pii/S0022435906000388) | Méta-analyse des promotions | Éviter les dogmes sur les remises |
| [Matz et al., 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5715760/) | Expériences de publicité numérique | Hétérogénéité sans validation des personas LLM |
| [Bertrand et al., 2009, version de travail](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1332007) | Courrier commercial, crédit | Importance du contenu et imprévisibilité des effets |
| [NN/g, microcontent](https://www.nngroup.com/articles/microcontent-how-to-write-headlines-page-titles-and-subject-lines/) | Recommandations d'utilisabilité | Objet et information compréhensible hors contexte |
| [NN/g, email et newsletters](https://www.nngroup.com/reports/email-newsletter-design/) | Programme de recherche d'utilisabilité | Lecture, navigation et attentes |
| [W3C WAI](https://www.w3.org/WAI/tutorials/images/informative/) | Référence d'accessibilité | Alternatives textuelles |
| [Google](https://support.google.com/mail/answer/81126?hl=en) | Exigences d'expédition | Séparer copie et infrastructure |
| [CNIL](https://www.cnil.fr/la-prospection-commerciale-par-courrier-electronique) | Cadre de prospection en France | Relation, information, consentement/opposition |
| [FTC](https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business?view=Schedule) | Cadre commercial américain | Objet fidèle, identité, opposition |
| [Apple](https://support.apple.com/en-ie/guide/iphone/iphf084865c7/27/ios/27) | Documentation Mail Privacy Protection | Limites des ouvertures mesurées |
| [Aher et al., 2023](https://proceedings.mlr.press/v202/aher23a.html) | Recherche sur les simulations humaines par LLM | Séparer jugement simulé et comportement observé |

## 12. Décision recommandée pour la suite

Commencer par un lot cohérent : **adapter les évaluateurs à la relation et à l'action attendue, puis tester les exceptions aux règles de longueur et de vocabulaire**. Cela utilise des informations déjà disponibles et peut améliorer la pertinence sans ajouter de rôle ni d'appel par campagne.

Le lot suivant devrait vérifier la chaîne **promesse → preuve utile → prochaine action → destination**, en réutilisant les champs existants. Les tactiques psychologiques viennent ensuite comme options documentées.

Le résultat recherché est un générateur qui explique mieux une offre réelle à une audience plausible, sait reconnaître ce qu'il ignore et propose une action utile. La conversion commerciale demeure une hypothèse tant qu'elle n'est pas observée.
