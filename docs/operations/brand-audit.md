# Audit réel depuis une URL principale

Procédure de référence pour tester MarketingOS sans constituer les sources à sa
place. Utiliser le skill `.agents/skills/campaign-optimization/SKILL.md` et les
fichiers `case.json`, `state.json`, `journal.md` du cas. Ne jamais confondre une
évaluation indépendante des pages publiques avec des données fournies au générateur.

Les commandes suivantes partent de la racine du dépôt, sur Windows. Le serveur
doit répondre à `GET http://localhost:8000/api/health`. Utiliser les configurations
`backend` et `frontend` de `.claude/launch.json` pour le démarrer. Un éventuel jeton
vient de `MARKETINGOS_TOKEN`, jamais d'un fichier de traces.

## Créer le cas et lire le site

Créer un dossier `docs/optimization/<cas>/` avec ce `case.json` :

```json
{"name":"Nom officiel de la marque","website_url":"https://site-principal.example/","api_base":"http://localhost:8000"}
```

```powershell
backend/.venv/Scripts/python.exe scripts/audit_brand_flow.py create --case docs/optimization/<cas>/case.json
backend/.venv/Scripts/python.exe scripts/audit_brand_flow.py ingest --case docs/optimization/<cas>/case.json
backend/.venv/Scripts/python.exe scripts/audit_brand_flow.py compile --case docs/optimization/<cas>/case.json
backend/.venv/Scripts/python.exe scripts/audit_brand_flow.py poll --case docs/optimization/<cas>/case.json --wait 45
backend/.venv/Scripts/python.exe scripts/audit_brand_flow.py capture --case docs/optimization/<cas>/case.json
```

Le nom de marque sert aussi au rendu HTML de l'email. Utiliser son nom officiel ;
garder les labels « audit » dans le dossier du cas et le nom de campagne.
La création de la marque **n'importe pas son site**. Il faut ensuite appeler
`POST /api/knowledge` avec `brand_id` et **uniquement l'URL principale**. Les valeurs
par défaut sont `crawl=true`, `max_pages=12`. Le crawl suit maintenant les liens
découverts jusqu'à deux niveaux, sur le site et ses sous-domaines de documentation
liés (docs, help, support, developers), avec un budget de pages borné.
Il ne garantit ni une lecture exhaustive ni la lecture d'une documentation sur un
autre domaine. Un échec ou un contenu vide peut réduire le nombre de documents.
Contrôler les URL effectivement importées ; la présence d'un index `/docs` ne prouve
pas la lecture des guides. Les métadonnées indiquent profondeur et page d'origine.

`POST /brands/{brand_id}/knowledge/compile` nécessite des sources déjà importées.
`GET /brands/{brand_id}/knowledge/compile` ne rend que l'état et le message.
`GET /knowledge/jobs` contient les appels, jetons et journaux de compilation.
Les jobs acceptent aussi un modèle explicite, limité au job : `compile_model`
dans le cas pour Knowledge, `market_scan_options.model` pour le scan,
`audience_map_options.model` pour la carte, puis `research_model` et
`dossier_model`. Sans ces champs, les choix habituels restent utilisés.
Une valeur est un nom de modèle, jamais un tier. Ces sélections sont refusées
en facturation par crédits. Archiver la configuration précédente et nommer la
révision si l'on compare deux fournisseurs ; ne pas présenter des conditions
différentes comme un A/B strict.

La découverte de concurrents cherche des URL ; le profilage lit les pages
avec le crawler Python et vérifie les citations. La carte d'audiences utilise
également recherche puis fetch Python. Ces rôles peuvent donc utiliser un
modèle OpenAI disposant de la recherche, sans lui annoncer un outil web_fetch.
Proof et la recherche de prospects qui demandent encore web_fetch doivent
continuer de refuser un modèle qui ne le fournit pas. La lecture d'images
reste un chemin distinct ; ce parcours homepage-only ne la valide pas.

Ces jobs sont locaux au processus : capturer leurs statistiques **avant** un
redémarrage. Les artefacts et les documents restent persistants.
Attendre `completed` pour la compilation et `done` pour les jobs de marché avant
de lancer l'étape suivante. Un `poll --wait 45` peut encore rendre `running` :
répéter alors seulement `poll`. Un état `failed` demande un diagnostic, pas une
répétition automatique du POST.
Pour une instance d'audit sur un autre port, renseigner `api_base` dans le cas.
Le runner de campagne utilise séparément `--base-url` : lui passer la même origine
à chaque lancement ou reprise. Ne pas mélanger les registres de jobs de deux processus.

Évaluer : couverture des pages utiles, prix et conditions, nature de l'offre,
fonctionnalités et limites, verbatims/provenance, omissions et contradictions.
L'outil `capture` conserve les artefacts via `GET /brands/{id}/knowledge` et les
métadonnées des documents via `GET /knowledge?brand_id=...`. Le texte complet est
dans le snapshot d'import ou via `GET /knowledge/{document_id}`.

## Scanner le marché et choisir l'audience

```powershell
backend/.venv/Scripts/python.exe scripts/audit_brand_flow.py scan --case docs/optimization/<cas>/case.json
backend/.venv/Scripts/python.exe scripts/audit_brand_flow.py poll --case docs/optimization/<cas>/case.json --wait 45
backend/.venv/Scripts/python.exe scripts/audit_brand_flow.py capture --case docs/optimization/<cas>/case.json
backend/.venv/Scripts/python.exe scripts/audit_brand_flow.py map --case docs/optimization/<cas>/case.json
```

Les boutons New market scan de Positioning et Competitors déclenchent le **même**
`POST /market/{brand_id}/scan` avec `discover=true` par défaut : découverte et
profilage des concurrents, puis carte de positionnement. Ne pas le facturer deux
fois pour tester deux onglets. `discover=false` relit la liste existante.

`POST /market/{brand_id}/audience/map` accepte `{}` pour les options normales.
Attendre chaque étape puis capturer. `GET /market/{brand_id}/job` rend le dernier
job ; `GET /market/jobs` contient les jobs connus du processus. Ne pas lancer une
autre opération de marché pour la même marque avant l'état terminal.

Lire `audiences.map.segments`, puis exécuter `select-first` avec le même `--case`
lorsque le protocole impose la première audience. Le script conserve l'index et
l'objet sélectionné et écrit son **nom exact** dans `case.json` sous
`audience_segment`. Ne pas choisir silencieusement une audience
mieux notée après avoir vu la liste. Si la première n'est pas admise à la recherche,
conserver l'échec et sa cause avant toute autre sélection.

Évaluer les concurrents comme des alternatives réelles, et les différences comme
des observations sourcées ; « pas vu » ne signifie pas « n'existe pas ». Évaluer
les audiences sur leur situation concrète, adéquation produit, décision d'achat,
preuve d'existence et possibilité de recherche. Un score de classement est une
hypothèse, pas une mesure de demande ni un taux de conversion.

Contrôler aussi le passage dossier → campagne : un fit ADDRESSED d’un dossier v2
avec recommandation et preuves encore licenciées doit atteindre la stratégie.
Les anciens dossiers sans catalogue ne l’autorisent pas. Les réserves des fits
ADDRESSED, PARTIAL ou SOLVED doivent suivre les preuves sélectionnées dans les
contraintes du brief et du rédacteur. Une fonction de collecte ne garantit pas
une hausse des réponses : conserver cette réserve même si le fit est ADDRESSED.

Contrôler aussi la différence entre classement éditorial et licence factuelle.
Un fait absent du top LEAD/SUPPORT peut expliquer un mécanisme ou une condition
de plan. Le contrat admet ces détails uniquement comme faits atomiques exacts
de capacités vérifiées, ou conditions commerciales officielles fortes ; il
n'ouvre pas les résultats clients non classés. Les WITHHOLD explicites, références
absentes, capacités non vérifiées, frontières et visibilités internes restent
prioritaires. Si un lecteur demande une information déjà dans Knowledge mais
absente du contrat, diagnostiquer cette transmission avant d'acheter une nouvelle
recherche. Après une modification de ces règles, versionner l'interprétation et
reconstruire le dossier normalement, sans corriger l'asset ou le ledger en base.

Pour les questions soulevées par les lecteurs, la critique dispose d'un index
compact des seuls faits autorisés. Elle peut choisir jusqu'à six
`supporting_evidence_ids` dans son appel existant ; le code résout ces références
dans le ledger, ignore les références inconnues/interdites et transmet leurs
citations et conditions complètes à la réécriture. Contrôler la sélection dans
l'événement `critique` et sa présence dans l'entrée du rédacteur. Le lecteur froid
ne doit jamais recevoir l'index ou les sources. Cette recherche de faits existants
n'ajoute pas d'appel ; elle augmente seulement le contexte de la critique.

Le reçu de la version retenue conserve une demande de révision du critique, même
si les lecteurs dépassent leur seuil. Elle déclenche le signal de revue sans
bloquer la livraison d'un brouillon passant les gates. Une critique `ship` sur
une nouvelle version retenue ne doit pas hériter d'une ancienne réserve.

Pour les prix, rejouer aussi la phrase entière : un alias de plan vérifié reste
valide après une virgule ou un tiret de clause suivi de « and »/« et ». Une bonne
phrase telle que « … — and Starter is $29/month » ne doit pas devenir un autre
plan à cause du séparateur. Les noms composés inconnus et mauvaises périodes
doivent toujours échouer ; ne pas retoucher le prix ou l'asset pour passer.

Une critique `argument` peut nommer une `research_question` factuelle précise
sans déclarer une promesse fausse. Le pipeline réutilise alors la recherche de
matériau officiel existante, une seule fois. Sans question, il n’achète pas de
recherche pour un simple avis éditorial. Les réponses ne sont admises qu’après
fetch et validation des citations. Contrôler après une récupération la nouvelle
version de Knowledge et la fraîcheur des dossiers qui en dépendent.

Pour changer explicitement les modèles d’une campagne déjà créée, enregistrer
`model_overrides` dans `case.json`, puis utiliser `audit_brand_flow.py policy`
(ou `audit_session.py audit policy`). Ce helper appelle le PUT `/campaigns/{id}/policy`,
conserve un snapshot et ne modifie que les pins de modèles. Modifier le cas seul
ne change pas la campagne persistée. Les noms doivent respecter les capacités du
rôle ; `material_researcher` utilise web_search puis un fetch Python contrôlé.

## Recherche et dossier

```powershell
backend/.venv/Scripts/python.exe scripts/audit_brand_flow.py research --case docs/optimization/<cas>/case.json
backend/.venv/Scripts/python.exe scripts/audit_brand_flow.py poll --case docs/optimization/<cas>/case.json --wait 45
backend/.venv/Scripts/python.exe scripts/audit_brand_flow.py capture --case docs/optimization/<cas>/case.json
backend/.venv/Scripts/python.exe scripts/audit_brand_flow.py dossier --case docs/optimization/<cas>/case.json
```

La recherche appelle `POST /market/{id}/audience/research`, et le dossier appelle
`POST /market/{id}/audience/relevance`, tous deux avec `{"segment":"nom exact"}`.
Les lectures sont `/audience/research/latest?segment=...` et
`/audience/relevance/status?segment=...` ; encoder le paramètre de requête.

Si toutes les pages du premier lot de recherche sont illisibles, le système
effectue une seule recherche supplémentaire sur d'autres hôtes. Les hôtes en
échec et leurs sous-domaines sont exclus du second lot ; aucun contrôle d'accès
n'est contourné. Budget maximal : deux lots de dix URL, deux appels de recherche
et un de synthèse. Un premier lot lisible garde le coût habituel. Les échecs et
la couverture partielle restent dans le journal ; un problème d'authentification
ou de quota n'est pas relancé par ce mécanisme.

Évaluer séparément : citations réellement présentes, source vendor ou utilisateur,
date et indépendance, problème observé ou inféré, portée du produit compatible,
lien problème/preuve/action et avis de lancement. Un dossier stale n'est pas courant.
Une modification des connaissances peut imposer une nouvelle recherche de pertinence.
La route `/audience/relevance/rebuild` force un nouveau dossier : ne l'utiliser
qu'après diagnostic, jamais comme simple bouton de rafraîchissement.

Un dossier courant qui énumère des exigences produit encore non vérifiées peut
recevoir `verify_product_gaps=true` sur son lancement/rebuild. Le bouton
**Verify product gaps** effectue alors la récupération officielle déjà utilisée
par le moteur : recherche, fetch contrôlé et vérification des citations, puis
enregistrement de Knowledge et réévaluation. Jusqu'à trois appels ; aucun email
n'est lancé. Sans fait vérifié, le dossier précédent reste intact. Si ses
références de capacités doivent être réévaluées, le job le signale avant
d'acheter une nouvelle analyse : utiliser le recheck normal sur la même audience.
Pour l'audit, `dossier_options: {"verify_product_gaps": true}` dans le cas porte
cette option ; la retirer après l'essai de récupération. Aucune URL ou preuve
supplémentaire n'est transmise par l'opérateur.

## Campagne d'un email

Créer via `POST /campaigns`, avec `brand_id`, `audience_segment` exact, une demande
contenant explicitement **one email** et l'intention correspondant à la demande.
Ne pas injecter les problèmes, témoignages ou liens découverts par l'évaluateur.
Laisser le système choisir une action documentée lorsque le test l'exige.
Enregistrer l'ID retourné sous `campaign_id` dans `case.json`.
Le helper réalise cette création avec l'action `campaign`, après avoir renseigné
`campaign_request` et éventuellement `intent` dans le cas. L'action `advice`
conserve le devis et le précontrôle avant génération.

Avant le lancement, lire `/campaigns/{id}/forecast` et
`/campaigns/{id}/generation-advice`. Conserver les raisons d'un éventuel refus ;
un contournement `generate_anyway=true` exige une justification enregistrée.

```powershell
backend/.venv/Scripts/python.exe scripts/optimize_campaign.py inspect --case docs/optimization/<cas>/case.json
backend/.venv/Scripts/python.exe scripts/optimize_campaign.py run --case docs/optimization/<cas>/case.json
backend/.venv/Scripts/python.exe scripts/optimize_campaign.py summary --case docs/optimization/<cas>/case.json
```

`resume` collecte une exécution interrompue sans la relancer. Ne pas acheter un
second run tant que le premier n'a pas de `result_dir`. Les fichiers de résultat
contiennent les assets ; conserver le texte, le HTML, les lectures, le rapport et
les erreurs. Inspecter le rendu ordinateur/mobile et la destination du CTA.
Un brouillon n'est jamais envoyé par ce protocole.
Sur une console Windows qui refuse un caractère Unicode dans les sorties,
ajouter `-X utf8` après `python.exe` ; ne pas relancer une génération simplement
parce que l'affichage de sa sortie a échoué.

Évaluer avec la grille stable 25/20/20/15/10/10 du skill, en distinguant les lacunes
des sources des défauts du générateur. Les réserves d'un lecteur simulé restent
visibles ; ni son score ni celui du coordinateur ne prédit une conversion.

Contrôles issus du parcours Plausible : comparer `status` API à
`result.run_status`, `needs_review` et `report.emails[].landed` ; un fichier livré
peut encore être `degraded`. Un compteur de problèmes ne mesure pas le nombre de
sources indépendantes. Vérifier les dates originales, le sujet réel des capacités
(une intégration tierce ne devient pas une fonction du produit) et les omissions
de sélection. Le dossier reçoit un extrait borné, pas nécessairement tout le ledger.
Après une correction de sélection ou de normalisation, conserver l'ancien dossier,
augmenter sa version d'interprétation si nécessaire, puis le régénérer avec une
révision explicite avant l'email. Ne pas recompiler ni refaire tous les scans sans
raison. Inspecter le CTA réel et le rendu ; les captures navigateur ne valent pas
un test dans chaque client email.

Contrôles de fiabilité ajoutés après cet audit :

- Le catalogue automatique est constitué de faits atomiques du ledger, avec
  `origin=derived` et une `derivation_version`. Les identifiants `fact_…` ne sont
  pas une liste universelle de fonctions. Une capacité maintenue par l'utilisateur
  conserve son origine et doit toujours être justifiée par ses preuves. Lire
  `/market/{id}/capability-profile` ; `POST …/derive` reconstruit le catalogue sans
  appel modèle. Une ancienne version peut être revalidée à la lecture sans que
  son historique en base soit réécrit.
- Les prix complétés à la lecture des anciens artifacts proviennent uniquement
  de faits tarifaires non ambigus, attribués à une offre et accompagnés de leurs
  conditions. Un conflit reste vide. Comparer le montant **et** le palier,
  la période et la provenance ; ne pas forcer une recompilation pour tester cela.
- Les dates de publication viennent des pages récupérées, puis de leur URL datée,
  jamais de la date de collecte. `publication_date_basis` distingue ces cas et
  `unknown`. `source_count` compte les contenus cités distincts ; `corroboration`
  est borné par les domaines et contenus distincts, sans garantir leur indépendance
  éditoriale. Lire `review_notes` et `interpretation_warnings` avant d'interpréter
  cinq problèmes comme cinq confirmations actuelles.
- Une justification concurrentielle acceptée porte
  `rationale_status=source_linked_hypothesis` et cite les deux côtés :
  `rationale_sources` et `our_evidence_ids`. Elle reste une hypothèse. Le récit
  initial est conservé dans `discovery_reason` et ne devient pas une différence
  prouvée. Une page d'application illisible peut utiliser une page publique
  réellement trouvée lors de la découverte, sans ajout manuel d'URL.
- Un scan relit les pages HTTP mais réutilise l'extraction si leur capture, le
  contexte produit, le lead et le prompt sont identiques. `reused=true` doit
  correspondre à zéro nouvel appel d'extraction pour ce profil. Des pages modifiées
  ou un prompt modifié invalident le cache ; ne pas annoncer une économie avant
  d'avoir lu les compteurs de l'opération.
- `status` indique la fin du processus. `outcome_status`, `needs_review` et
  `review_reasons` indiquent l'état des brouillons. Un processus `completed` peut
  donc afficher « Drafts need review ». Les statistiques de lecteurs simulés
  restent des signaux éditoriaux, jamais des résultats commerciaux.

## Reprise et mémoire

`audit_brand_flow.py` conserve chaque réponse sous `steps/<horodatage>-<action>.json`
et refuse un lancement déjà enregistré. Après un diagnostic et une correction
consignés au journal, `--revision nom-correction` autorise un nouvel essai explicite
en conservant l'initial. `poll` et `capture` sont toujours en lecture seule.
Un timeout HTTP de lancement a une issue incertaine : inspecter l'état serveur et
les objets persistés avant toute nouvelle mutation. Ne jamais imprimer de secrets.

Après chaque étape, enregistrer appréciation, faits vérifiés, limites et statistiques.
Mettre à jour `state.json` et `journal.md`, puis produire un rapport par étape avec
des liens vers les snapshots. Le cas `docs/optimization/plausible-root-url/` sert
de trace réelle de cette procédure, sans transformer ses conclusions en règle générale.

Compter les appels terminés avec les événements `model_call_finished` des logs ou
du timeline. `agent_executions` regroupe plusieurs appels (panel de lecteurs,
candidats, duels) : sa longueur n'est pas un compteur d'appels. Le helper `summary`
expose maintenant `model_calls` et `agent_groups` séparément ; un ancien historique
sans événements d'appel reste inconnu. Les erreurs transport et les tours internes
des CLI ne sont pas une quantité qu'on peut reconstruire avec ces groupes.

Si un bon plan produit un mauvais email, consulter le `plan_history` (brut et
normalisé), les brouillons de chaque candidat, puis les contrôles avant de modifier
le planificateur. Un candidat bloqué n'est pas lu lorsque l'autre passe : dans ce
cas, l'avis du lecteur sur le gagnant n'explique pas le rejet du premier. Le cas
Plausible a reproduit un faux positif sur l'acronyme DPIA ; son brouillon correct
était éliminé avant lecture. Le rejeu gratuit `run_all` sur le brouillon enregistré
a isolé le filtre, et la correction a été validée par une nouvelle génération.

Le cas garde actuellement `api_base=http://127.0.0.1:8006` pour ses captures.
Le proxy frontend a été rétabli à sa configuration locale initiale (8000 par
défaut), après les tests sur 8006. Si l'environnement est arrêté, mettre à jour
le cas pour l'instance configurée réellement démarrée. Les refus du
contrôle automatique de redémarrer/créer un serveur restent consignés ; ne pas
réessayer la même action par un autre moyen. Pour ce dernier test seulement, le
service `CampaignService.start_execution` a été exécuté dans un worker ponctuel
sans serveur ni lifespan, avec ID durable et collecte par `resume`. Ce worker
ne modifie pas le code chargé par les serveurs déjà en place : leur rechargement
normal reste nécessaire pour activer les dernières règles dans les prochains
lancements depuis l'interface. Aucun nouveau serveur ne doit démarrer pendant
une campagne en cours, car le lifespan traite les exécutions orphelines.

Consulter le rapport et `state.json` pour connaître les étapes effectivement
réalisées. Une commande documentée depuis le code ne prouve pas qu'un test réel
a pu la terminer. En cas de limite fournisseur, conserver l'erreur, l'heure de
réinitialisation et la prochaine commande, puis reprendre cette étape uniquement.

Contrôles issus de Buffer (18 octobre 2026, audit arrêté au quota) :

- Vérifier les résumés d'offre séparément du ledger : une citation correcte dans
  le ledger ne garantit pas que la synthèse ne contredise pas une condition tarifaire.
- Une capacité atomique avec référence valide peut encore décrire l'entreprise ou
  un outil tiers. Contrôler le propriétaire et le type du fait, y compris lorsque
  claim_scope est unknown ou capability. Ne pas modifier les résultats à la main.
- Sur Positioning, contrôler la comparabilité sémantique avant de lire open/exposed :
  chiffre d'affaires client, ventes historiques et prix d'abonnement ne sont pas
  des objets interchangeables sur un axe price.
- Après refus du quota, capturer le job failed, conserver les étapes achevées et
  utiliser une révision explicite uniquement sur l'étape refusée après remise à zéro.
  Aucun résultat en aval ne doit être inventé ou noté ; les personas du compilateur
  ne remplacent pas une carte d'audiences absente. Ne pas programmer une reprise
  automatique sans demande de suivi de l'utilisateur.
- Un helper qui rend un session_id continue de tourner : attendre sa fin avant
  une autre mutation du même cas. Même capture écrit son état local et peut sinon
  écraser l'entrée de lancement d'un autre helper.

Contrôle issu de SavvyCal (19 octobre 2026) : une réserve `missing_material` du
critique peut lancer une recherche officielle et un replan bornés, mais ne doit
pas supprimer un brouillon passant les gates. Après récupération infructueuse,
vérifier l'asset, `report.emails[].unresolved`, `landed=false` et `needs_review`.
Un aperçu avant inscription souhaité par le lecteur n'est pas une ressource
promise par une simple invitation à essayer un outil. Les refus de préflight
sans contenu exploitable et les gates bloquantes restent indépendants de cet
avis éditorial. Conserver le résultat initial sans asset pour la comparaison.

Contrôle de continuité du besoin issu de Senja : comparer `map.segments[].need`,
le job du segment adapté et le brief réel. La recherche peut trouver des désirs plus
généraux ; elle ne doit pas effacer le besoin qui définit la cible choisie. Ce besoin
reste une hypothèse de ciblage, séparée de la situation et des problèmes sourcés.
Il ne prouve ni l'historique ni l'échéance du destinataire. Une fonction documentée
d'export ou de publication, une fois le contenu reçu, ne promet pas de réponse, de
qualité persuasive ou de ventes. Garder ses prérequis et limites sans interdire
cette fonction au seul motif que ces résultats humains ne sont pas mesurés.
Rechercher une contradiction entre critiques successives avant d'ajouter du budget
ou des recherches : une obéissance au brief peut annuler une correction pertinente.
Le champ `EmailBrief.target_audience` est fixé depuis le nom exact sélectionné,
et conservé lors d'un changement d'argument. Le besoin détaillé de la carte peut
mélanger un but et une méthode proposée ; il reste une hypothèse de stratégie,
sans devenir une obligation dans le brief ni une biographie du lecteur.
Vérifier aussi la frontière de faits
dans les résumés : retirer un ID du ledger ne suffit pas si free_entry, les plans
ou une réponse d'objection en répètent la promesse. La vue de prompt fermée conserve
identité/actions et faits autorisés, sans modifier la Knowledge persistée.
Si la critique demande un nouvel argument avec des faits déjà connus, contrôler
`supporting_evidence_ids` et l'événement de reprise fermée. Les IDs structurés
validés doivent atteindre le replan, même s'ils ne sont pas écrits dans strategy_gap.
Cette reprise unique utilise le budget déjà prévu ; aucune recherche supplémentaire
n'est nécessaire. Une interruption de sa rédaction conserve le premier brouillon
passant encore les contrôles, avec son problème de stratégie toujours visible.

Lorsque le CTA nomme un seul plan du catalogue, contrôler aussi les conditions
canoniques transmises à la rédaction et à la critique : sujet du produit et du
plan explicites, portée offre/capacité, source documentaire officielle non faible
ou attestation utilisateur, aucun ID interdit. La vue est bornée à six faits et
n'ajoute pas d'appel. Les résumés identifient le nom du plan sans autoriser leurs
propres inclusions ; un service dit « gratuit » n'est pas une condition du plan
Free. Un CTA générique ou plusieurs plans ne permettent aucune inférence. Le
lecteur reste froid. Expliquer les limites utiles à l'essai proposé, sans imposer
une table tarifaire complète ni promettre des résultats humains.

Contrôles issus de Carrd (19–20 octobre 2026) :

- Vérifier les headers éditoriaux de la homepage : retirer la navigation ne doit
  pas retirer le résumé produit, le prix annuel ou la portée des fonctions Pro
  placés dans un header de section. Après correction d'import, laisser le crawl
  refaire la collecte depuis la même homepage et recompiler normalement.
- Examiner l'extrait reçu par le dossier, pas seulement le ledger complet.
  Rendre obligatoires les capacités requises par l'audience ; épingler toutes les
  capacités du catalogue peut remplir le budget avant la récupération des prix.
  Une absence dans l'extrait n'est pas une absence dans Knowledge. Après correction
  de sélection, versionner l'interprétation et régénérer seulement le dossier.
- Une action officielle relative, telle que `/build`, doit être résolue sur
  l'origine de la marque et correspondre au bouton et au texte livrés. Ne pas
  ajouter manuellement de cta_url au cas pour compenser un fallback incorrect.
- Compter les appels réels, y compris la correction de JSON : deux étapes logiques
  de cartographie ont consommé trois appels dans ce cas. La durée et les limites
  de couverture comptent dans la note, même lorsque le résultat est terminé.
- En cas de blocage d'un prix ou d'une durée, lire la phrase réelle et le motif
  du gate. Le premier email Carrd nommait correctement Pro Standard à 19/an et
  l'essai de sept jours, mais le parseur tronquait le nom du plan et distinguait
  à tort `7-day` de `7 days`. Rejouer les brouillons gratuitement avant une reprise ;
  garder les refus pour un autre plan, une autre période ou une autre durée.

Contrôle des interruptions tardives : un champion déjà passé aux gates et lu doit survivre à une panne de critique/réécriture, avec revue interrompue visible et arrêt des appels suivants. Vérifier aussi le parcours par étapes et le rapport, pas seulement la présence d’un événement email_accepted. Aucun brouillon bloqué ne devient livrable. Un quota dur Codex est non réessayable ; les incidents réseau conservent leurs retries.

Pour un audit global, le critère de réussite couvre chaque étape demandée ; un bon email ne compense pas un scan ou une carte insuffisants. Le cas peut préciser model_overrides : le helper les transmet à la campagne sans modifier les réglages globaux. Documenter toute nouvelle allocation et ne pas présenter deux marques/profiles différents comme un comparatif contrôlé. Pour la documentation sur sous-domaine et chemins plats, vérifier la sélection réelle du guide, son statut HTTP et son contenu ; une priorité correcte ne rend pas accessible une page refusée.

Avant génération, rejouer gratuitement les prix du ledger courant : un contexte « Marque Starter plan » peut nommer plus complètement le plan que le titre source. Les alias courts doivent provenir d’un titre tarifaire effectivement cité, être non ambigus pour le montant, et ne jamais faire passer Basic Starter pour Starter ni changer la période. Relire aussi le classement : un nombre clients dont la citation dit growing faster reste une preuve d’adoption, pas une mesure de vitesse ; les nombres seuls ne sont pas du vocabulaire de catégorie. build_current recalcule la carte sur les preuves persistées sans nouveau scan payant.

En abonnement local, POST audience/research et POST audience/relevance[/rebuild] acceptent model optionnel pour ce job seulement. Choisir un nom de modèle (pas fast/balanced/deep). Le catalogue valide les outils réels : audience_researcher demande web_search puis fetch Python ; relevance_analyst reste fermé au web. Ils peuvent employer GPT ; rival_profiler et les autres rôles exigeant web_fetch le refusent toujours. Le choix est refusé en billing credits. Le helper lit research_model/dossier_model depuis case.json ; les réglages globaux restent intacts. Si le modèle est changé, enregistrer la condition de comparaison et conserver l’échec avant la reprise avec révision.

## Recompilation et références de capacités

Après une nouvelle Knowledge, `audit_brand_flow.py derive` appelle normalement
`POST /market/{id}/capability-profile/derive` sans modèle. Un GET du profil ancien
ne remplace pas cette dérivation. Des IDs atomiques peuvent changer avec le
libellé ou la découpe d’une citation ; ne pas forcer des alias par ressemblance.

Le bouton **Recheck product fit** envoie `POST /market/{id}/audience/map` avec
`mode=reassess` et le même périmètre. Il conserve la liste, les noms, les situations,
les preuves et leur date de lecture. Une seule étape modèle fermée réévalue les
capacités requises ; aucun search/fetch de marché. Les IDs restent contrôlés par
le catalogue courant, y compris ses états unknown/unsupported. Une omission ne
peut établir un support. Un changement de géographie/langue/périmètre demande
une vraie nouvelle carte.

Dans l’audit, enregistrer `audience_map_options={"mode":"reassess"}` dans le cas
et lancer `map --revision product-fit-only`. Conserver la première audience
initiale exacte ; ne pas appeler select-first pour choisir une audience plus facile.
La nouvelle carte versionnée peut changer les références de sa définition : relancer
alors normalement la recherche de ce même segment, puis son dossier. Garder les
anciennes versions et leurs preuves ; ne pas réécrire leurs IDs en base.
