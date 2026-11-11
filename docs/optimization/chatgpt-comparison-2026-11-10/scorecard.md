# Résultats du comparatif

[Protocole](protocol.md) · [Brouillons ChatGPT](chatgpt-drafts.md)

## ChatGPT

Quatre brouillons au premier passage, en deux demandes par marque. Les premiers ont été constatés disponibles moins de 16 secondes après l’envoi pour Canny et moins de 19 secondes pour Bannerbear. La durée exacte des deux réponses suivantes n’a pas été instrumentée. Aucun prompt de correction n’a été nécessaire pour obtenir les quatre brouillons.

| Email | Évaluation à la relecture | Travail restant avant export |
| --- | --- | --- |
| Canny — introduction | Exploitable. La préparation de la roadmap donne un contexte pertinent. Les quatre fonctionnalités en liste diluent le motif principal, la valeur de chaque demande pour le chiffre d’affaires. | Raccourcir si le format l’exige. Régler le champ de personnalisation du destinataire. |
| Canny — objection | Exploitable avec une précision locale. L’import CSV et le choix du portail répondent concrètement au coût de migration. La mention Jira est plus large que l’intégration Jira Cloud annoncée. | Préciser « Jira Cloud » ou retirer Jira de la liste. Le CTA vers les intégrations tient sa promesse. |
| Bannerbear — introduction | Exploitable. La déclinaison des visuels par produit et canal donne une application claire. L’essai et le lien direct sont confirmés. | Le chiffre de 100 rendus est exact selon la page e-commerce, mais la phrase mélange un bénéfice pour le marketeur et un détail d’API. Coupe éditoriale facultative. |
| Bannerbear — objection | Exploitable avec une retouche. Le chemin boutique, champs, modèles répond à la difficulté de mise en place. Le bouton d’essai mène aux prix. | Utiliser l’inscription directe ou adapter le libellé. La page de prix permet aussi de démarrer l’essai en un clic supplémentaire. |

Les principaux faits et les destinations ci-dessus ont été vérifiés après la génération. [Canny Product Management](https://canny.io/team/product-management), [Canny Autopilot](https://canny.io/features/autopilot), [démo Canny](https://canny.io/request-demo), [intégrations Canny](https://canny.io/integrations), [import CSV Canny](https://help.canny.io/en/articles/3635951-importing-feedback), [options de mise en œuvre Canny](https://help.canny.io/en/articles/12310866-options-for-implementing-canny), [Bannerbear e-commerce](https://www.bannerbear.com/v5/solutions/ecommerce/), [intégrations Bannerbear](https://www.bannerbear.com/v5/products/integrations/), [prix Bannerbear](https://www.bannerbear.com/pricing/), [inscription Bannerbear](https://app.bannerbear.com/users/sign_up?trial=automate).

## Diagnostic Bannerbear au premier passage

La préparation a duré 6 min 43 s et a pris 12 appels modèles. Elle a proposé un premier essai à partir des données du lecteur. La rédaction, la relecture et la réécriture ont ajouté 5 min 09 s et 7 appels. Le run s’est soldé par zéro email livré. Le relecteur a rejeté la promesse centrale, faute d’une citation admissible qui établisse le lien entre données entrantes, modèle et variantes générées.

Le registre initial compte 24 entrées. Le périmètre autorisé pour ce brief cite l’essai, le quota, les intégrations et l’existence de l’API. Ces pièces, séparément, laissent sans preuve la chaîne de travail que le dossier présente comme vérifiée. La page d’accueil importée mentionne déjà les modèles et leurs variantes. La page e-commerce liée expose directement les publicités issues du catalogue. Elle est absente des neuf pages importées. La page actuelle d’intégrations donne aussi le mécanisme qui relie un champ d’entrée au modèle. Le cas révèle un écart entre la recherche, la sélection des preuves et la décision de lancer la rédaction. [Capture du parcours](bannerbear/steps/20261110T055825862815Z-capture.json), [résultat brut](bannerbear/runs/f3a3b5c0-c8c1-47c9-8fc9-bedd8b37244d/result.json), [page d’accueil](https://www.bannerbear.com/), [solution e-commerce](https://www.bannerbear.com/v5/solutions/ecommerce/), [intégrations](https://www.bannerbear.com/v5/products/integrations/).

## Diagnostic Canny au premier passage

La préparation a duré 8 min 56 s et a pris 16 appels modèles, dont une récupération de faits dans les pages officielles. La génération a pris 5 min 50 s et 7 appels sans livrer d’email. Le premier brouillon ajoutait « product roadmapping software » avec des citations admissibles centrées sur la collecte de feedback. La réécriture a introduit « $0/month billed yearly », une nouvelle phrase que l’extrait E19 ne suffit pas à justifier. Le dossier amont avait introduit cette formulation alors que le brief laissait les prix hors de l’email. La page officielle juxtapose un libellé annuel dans son comparateur et une carte Free à 0 $. L’aide officielle explique ce que le lecteur peut utiliser gratuitement. L’email pouvait présenter Autopilot et la limite du plan sans ajouter un cycle de facturation. [Capture du parcours](canny/steps/20261110T060042588426Z-capture.json), [résultat brut](canny/runs/bcf8b28a-8629-42d4-97a2-960d88a1826b/result.json), [prix Canny](https://canny.io/pricing), [aide sur le plan Free](https://help.canny.io/en/articles/10446585-is-the-free-plan-really-free).

## Réutilisation des connaissances

Les deux campagnes suivantes ont réutilisé la compilation existante et conservé le segment initial. Dans les deux cas, le dossier courant demandait un contournement pour le nouveau brief. La préparation guidée a levé ce blocage après deux appels modèles par marque, en 1 min 41 s pour Bannerbear et 1 min 50 s pour Canny. [Préparation Bannerbear](bannerbear/warm/prepare-final.json), [préparation Canny](canny/warm/prepare-final.json), [refus initial Bannerbear](bannerbear/warm/direct-advice.json), [refus initial Canny](canny/warm/direct-advice.json).

Le deuxième passage Bannerbear a pris 6 min 28 s et 8 appels modèles pour la génération. Il n’a livré aucun email. Après une réécriture, la description de la catégorie n’était toujours pas établie par les citations fournies. Le texte n’indiquait pas non plus le prérequis de conception du modèle demandé dans le brief interne. Les neuf pages importées et le registre de 24 faits ont été réutilisés tels quels. [Résultat brut](bannerbear/warm/runs/9f5c1078-d6af-439c-89b2-daa1ad1b9009/result.json).

Le deuxième passage Canny a pris 4 min 35 s et 7 appels modèles pour la génération. Il a livré un email signalé « à relire ». Il explique clairement le passage de la conversation à la demande produit, propose d’essayer avec une seule source, et le bouton mène à la bonne page d’inscription. L’email traite la charge de tri manuel, mais laisse ouverte la question du contrôle humain sur les résultats. La documentation explique comment approuver les suggestions et revoir les fusions. C’est une phrase concrète qui aurait mieux répondu à l’objection. Le HTML a été rendu à 390 et 1 280 pixels, sans débordement. [Email texte](canny/warm/runs/4bda4dec-15cd-4e40-b674-30b5f8875e16/email-1.txt), [email HTML](canny/warm/runs/4bda4dec-15cd-4e40-b674-30b5f8875e16/email-1.html), [résultat brut](canny/warm/runs/4bda4dec-15cd-4e40-b674-30b5f8875e16/result.json), [inscription Canny](https://canny.io/register), [contrôles Autopilot](https://help.canny.io/en/articles/8202451-autopilot).

## Verdict

| Marque et tâche | ChatGPT | MarketingOS | Durée machine MarketingOS | Appels MarketingOS |
| --- | --- | --- | --- | ---: |
| Canny — introduction | Exploitable | Aucun email | 14 min 46 s | 23 |
| Canny — objection | Exploitable avec une précision locale | Livré, à relire, HTML disponible | 6 min 25 s | 9 |
| Bannerbear — introduction | Exploitable | Aucun email | 11 min 52 s | 19 |
| Bannerbear — objection | Exploitable avec une retouche de CTA | Aucun email | 8 min 09 s | 10 |

La durée MarketingOS additionne les étapes actives de préparation et de génération, hors délai entre les deux. Les 61 appels correspondent aux appels observés dans la préparation et la génération. Ils utilisent les routes d’abonnement configurées. Le nombre d’appels internes de ChatGPT n’est pas visible. Son effort opérateur observé se résume à deux demandes par marque avant relecture. Côté MarketingOS, les deux seconds briefs ont nécessité une préparation supplémentaire et trois briefs se sont terminés sans livrable. Aucun temps humain n’a été chronométré. La relecture est effectuée avec l’origine des textes connue et le comparateur ChatGPT réutilise le chat en mode invité, sans projet. Aucune modification du produit et aucun envoi.

Pour cet usage, je garderais ChatGPT. L’export et la validation indépendante apportent une valeur concrète sur l’email Canny livré. Pour justifier l’abonnement, il faut que cette validation facilite la production récurrente. Sur ces deux marques, les preuves manquantes arrivent trop tard dans le parcours. Le changement prioritaire est de faire vérifier, avant la rédaction, que les citations retenues établissent le bénéfice central. En cas de manque, le système doit récupérer la preuve dans les sources officielles ou choisir un angle déjà documenté, puis garder les mêmes contraintes pendant la réécriture.
