# Architecture fonctionnelle

Ce document décrit le système **tel qu'il tourne aujourd'hui**, lu dans le code, et pas tel
qu'il a été conçu — [ai-architecture-redesign.md](ai-architecture-redesign.md) est la
proposition d'origine et a dérivé depuis (elle annonce cinq rôles ; il y en a plus, et la
moitié du produit qu'elle décrit n'existait pas encore).

Cible : comprendre le fonctionnement assez précisément pour proposer des optimisations.
Le *pourquoi* de chaque décision est dans [README.md](../README.md) et dans les docstrings
de tête de chaque module, qui sont la vraie documentation de conception.

---

## 0. La règle qui explique presque tout le reste

**Le modèle propose, le code dispose.** Partout où un modèle produit quelque chose de
vérifiable — une citation, une URL, un identifiant d'évidence, un prix — Python le
recontrôle avant persistance. Ce qui ne passe pas est **jeté**, pas corrigé.

**Aucun appel modèle ne décide de la suite.** L'ordre des étapes est écrit dans
`app/marketing/pipeline.py`. Budgets, deadlines, annulation, seuils, retries sont du code
ordinaire, vérifiés *entre* les étapes, jamais pendant un appel. C'est ce qui rend le coût
d'un run calculable avant de l'acheter (`app/marketing/forecast.py`).

**Seul le déterministe bloque.** Un lecteur froid peut renvoyer un brouillon en réécriture ;
il ne peut pas l'empêcher de partir. Seules les gates de `app/marketing/gates.py` bloquent.

Deux marques utilisées dans les schémas de tout ce document :

| Marque | Sens |
|---|---|
| **[M]** | un appel modèle — coûte du quota d'abonnement, peut mentir |
| **[C]** | une vérification Python — gratuite, rejouable, c'est elle qui décide |

---

## 1. Vue d'ensemble

Deux mondes séparés. L'atelier marché appartient à la **marque** et survit aux campagnes ;
le run de campagne le **lit** et ne l'écrit jamais.

```
┌─ ATELIER MARCHÉ · par marque · construit une fois ───────────────────────┐
│                                                                          │
│   Knowledge ──────► Demand Map ──────► Audience Research ─────┐          │
│   6 artefacts       audiences          1 audience admise,     │          │
│   + Evidence        candidates du      sourcée et vérifiée    ▼          │
│     Ledger          marché                            ┌──────────────┐   │
│        │                                              │  RELEVANCE   │   │
│        └──────────────────────────────────────────────►   DOSSIER    │   │
│                     Positioning Map ──────────────────►              │   │
│                     (scan des rivaux)                 └──────────────┘   │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │ lecture seule
┌────────────────────────────────────▼─────────────────────────────────────┐
│ RUN DE CAMPAGNE · machine à états · ordre fixé en Python                 │
│                                                                          │
│   Contrat ──► Stratège ──► Craft × N ──► Séquence ──► Rapport            │
│   combien     1 brief      écrire ·      lue d'un      pull, coût,       │
│   d'emails    par email    mesurer ·     bloc          receipts          │
│                            réécrire                                      │
└──────────────────────────────────────────────────────────────────────────┘
```

Conséquence économique à connaître avant toute proposition : **une deuxième campagne pour
la même marque ne repaie rien de la bande du haut.** Elle ne paie que la bande du bas.

Un arrêt (budget, deadline, annulation, provider muet) qui arrive avec des emails finis
derrière lui produit un run `degraded`, jamais `failed`.

---

## 2. Comment la knowledge base est analysée

`app/knowledge/compiler.py` · `app/knowledge/artifacts.py` · `app/knowledge/ledger.py`

Entrée : un *corpus* — site crawlé (12 pages par défaut), documents, images.
Sortie : six documents structurés assez courts pour être injectés **en entier** dans chaque
prompt en aval. Plus jamais de markdown brut tronqué devant un modèle.

```
                   ┌─ [M] Profil + Offre ─── 1 appel, 40k car. ──┐
   Corpus ─────────┼─ [M] Évidences ──────── N appels, 14k car. ─┼──┐
   site, docs,     └─ [M] Voix ───────────── 1 appel, 20k car. ──┘  │
   images                    (les trois en parallèle)               │
                                                                    ▼
                                                    ┌─ [C] La citation est-elle
                                                    │      vraiment dans la source ?
                                                    │      ≥ 12 caractères
                                                    └──┬────────────┬──
                                                  oui  │            │  non → jeté
                                                       ▼
                        [M] Audience ──────────► EvidenceLedger  E1…En
                        1 appel, après le reste
```

Les six artefacts : `BusinessProfile`, `OfferSheet`, `EvidenceLedger`, `VoiceProfile`,
`AudienceModel`, `GapReport`.

| Point | Détail |
|---|---|
| **Réutilisation** | Les artefacts sont indexés par une **empreinte de la matière**. Corpus inchangé = rechargement, zéro appel. C'est la plus grosse économie du produit. |
| **Plafonds** | Lots de 14 000 caractères, 4 lectures en vol, plafond global 240 000 caractères. Ce qui dépasse est *signalé*, pas coupé en silence. |
| **Grounding** | Chaque fait porte `grounded` / `inferred` / `user_stated` / `vendor_claim`. Le dernier existe parce qu'une page produit citée pour *la douleur du client* est une affirmation du vendeur, pas une observation. |
| **Robustesse** | Une lecture d'évidences qui échoue coûte les faits de ces pages-là, pas le compile entier. |

Le compile est **le seul rôle autorisé à lire librement la matière**. Tout ce qui vient
après ne voit plus jamais les pages d'origine — d'où la vérification mot pour mot : un
témoignage halluciné ici empoisonnerait invisiblement toutes les campagnes futures.

Conséquence directe : un fait absent du ledger ne peut **jamais** apparaître dans un email.
`evidence_gate` relit chaque brouillon et licencie chiffre, prix, citation et URL contre le
ledger.

---

## 3. Comment l'audience est trouvée

Deux étapes distinctes, qui ont exactement la même forme : un appel qui a le droit de
chercher sur le web, un fetch Python borné, puis un appel **enfermé dans le corpus
rapporté**. Le fetch au milieu est ce qui empêche la boucle de se refermer sur elle-même :
le modèle ne peut pas décider de ce qu'il a lu.

### 3.1 La carte — qui pourrait acheter ça ?

`app/market/demand.py` (`AudienceCartographer`) · `app/market/audience_discovery.py`

```
  [M] Découverte ──URLs──► [C] Fetch borné ──► [M] Validation ──► Demand Map
  tier deep                 URLs exactes,       corpus fermé,      segments classés,
  web search + fetch        6k car./page        aucun outil web    compatibilité produit
```

Le point central : la carte lit **le marché du produit**, pas le discours de l'entreprise.
La matière d'une entreprise ne peut retourner que l'audience qu'elle croit déjà avoir —
l'industrie adjacente avec le même problème et un autre vocabulaire, la personne d'un siège
à côté, le revendeur qui le mettrait devant quarante comptes, n'y sont jamais. L'audience
déclarée est donnée au cartographe **uniquement pour qu'il puisse s'en écarter
délibérément**.

La validation sépare les observations du jugement : une preuve faible reste visible comme
**hypothèse**, et une capacité inconnue ne devient jamais supportée par omission. La
priorité de recherche n'est pas un taux de réponse prédit.

### 3.2 La recherche profonde — une audience, sans parler du produit

`app/market/audience_research.py`

```
  [M] Localiser ──► [C] Fetch exact ──► [M] Synthèse ──► [C] Vérification ──► Audience
  ≤ 10 URLs          ces URLs-là,        corpus fermé     chaque citation       Research
  proposées          pas de crawl,       uniquement       dans la source
                     ≤ 4 redirects,                       qu'elle nomme
                     IP publiques
```

Chaque source fetchée est classée par **niveau d'observation** :

1. `BUYER_VOICE` — l'acheteur parle lui-même
2. `BEHAVIOURAL` — offres d'emploi, documentation, forums : ce qu'il *fait*
3. `INTERPRETATION` — un tiers qui commente

Ce que la recherche produit sur une audience : sa situation, ses **problèmes** (chacun avec
un id, qui sert de clé plus tard), ce qu'elle fait déjà à la place, ses déclencheurs, ses
résultats voulus, son niveau de sophistication, et ses **phrases textuelles**. Zéro mention
du produit : c'est une description du monde de l'acheteur, pas un argumentaire.

Le niveau de la source voyage avec chaque observation jusque dans le brief.

---

## 4. Le dossier de relevance

`app/market/relevance.py` · prompt : `backend/prompts/relevance_dossier.md`

### 4.1 Ce que c'est

Commençons par ce que ce n'est **pas** : pas une stratégie, pas un angle, pas un plan de
campagne. Le prompt le dit en une ligne : *« le dossier sélectionne et licencie. Il ne
génère pas. »*

C'est **le croisement vérifié entre ce qui est vrai du produit et ce qui compte pour cette
audience** — et surtout le verdict sur ce qu'on a *le droit* d'en dire. Il est indépendant
de toute campagne : le même dossier sert dix campagnes différentes.

Un seul appel modèle, tier `deep`, avec **`tools=[]` en dur** — aucun accès web, même si le
catalogue de rôles change. Il ne voit que trois snapshots déjà persistés et ne peut répondre
qu'avec des identifiants issus de ces snapshots.

```
  Evidence Ledger ───┐
  autorité produit   │
                     │    ┌───────────────────┐    ┌────────────────────┐
  Audience Research ─┼───►│ [M] Relevance     │ids │ [C] Normalisation  │
  autorité acheteur  │    │     Analyst       ├───►│ chaque id résolu   │──► Dossier
                     │    │  tier deep        │    │ contre le snapshot │
  Positioning Map ───┘    │  tools = []       │    │ exact ; verdicts   │
  autorité terrain        │  monde fermé      │    │ imposés en code    │
                          └───────────────────┘    └────────────────────┘
```

### 4.2 Ce qu'il contient

- **orientation** — une phrase neutre, non promotionnelle : ce que ce produit *est* pour cet
  acheteur. Pas de la copy, pas de CTA.
- **ranked_relevance** — chaque fait du ledger classé en quatre bandes.
- **problem_fits** — pour chaque problème researché, un verdict en six valeurs.
- **segment_objections** — avec des réponses licenciées par des ids d'évidence, ou vides.
- **silences** — les problèmes réels que la matière actuelle **ne peut pas** adresser.
- **claim_contract** — quatre ensembles, dont un seul atteint le rédacteur.

Les deux échelles :

| Bande | Sens |
|---|---|
| `LEAD` | porte l'email |
| `SUPPORT` | renforce le lead |
| `CONTEXT` | utile en arrière-plan |
| `WITHHOLD` | vrai et licencié, mais mauvais choix pour cette audience |

| Verdict | Sens |
|---|---|
| `SOLVED` | preuve d'un résultat réel, pas une formulation persuasive |
| `ADDRESSED` | une capacité du catalogue traite le problème |
| `PARTIAL` | traite en partie, avec un caveat concret |
| `UNSUPPORTED` | aucune référence produit positive |
| `IMMATERIAL` | réel, mais sans coût ni fréquence pour cet acheteur |
| `OFF_LIMITS` | une contrainte du catalogue l'interdit |

### 4.3 Le contrat de claims

```
  verified_product_claims   l'inventaire complet de ce qui est vrai (interne)
       │
       ├──► campaign_allowed_claims   ◄── le SEUL ensemble remis au rédacteur
       ├──► forbidden_claims              « ce n'est pas vrai de nous » — un mensonge
       └──► withheld_claims               vrai, et volontairement pas dépensé ici
```

La distinction qui porte tout : `forbidden` et `withheld` ne sont **pas** la même chose.
Les confondre — ce que faisait l'ancienne liste unique — perd la différence entre un
mensonge et une décision éditoriale, et rend le receipt illisible pour l'opérateur.

### 4.4 Fraîcheur : des pointeurs de version, pas une date

Le dossier stocke l'`id` + la `version` de chacune de ses entrées.
`MarketService.relevance_status` compare et retourne `current`, `stale` ou `missing`.
Un dossier périmé reste lisible mais devient **consultatif** pour la campagne, avec la
raison nommée : `knowledge_changed`, `audience_research_changed`, `market_scan_changed`,
`capability_profile_changed`, `company_qualification_changed`.

Dans le run, si l'audience sélectionnée ne matche aucune recherche (ou en matche
plusieurs), la campagne bascule sur le fallback historique — l'audience compilée depuis le
site de l'entreprise — et le dit dans le flux d'événements. Rien n'échoue en silence.
Voir `app/marketing/intelligence.py`.

---

## 5. La pipeline de génération d'emails

`app/marketing/pipeline.py` · `app/marketing/craft.py`

### 5.1 Avant d'écrire : trois décisions en Python

1. **Le contrat** — combien d'emails, lu dans la phrase de l'utilisateur
   (`app/marketing/contract.py`). Le run est vérifié contre ce contrat à la fin.
2. **Le preflight preuve** (`app/marketing/preflight.py`) — si la matière ne contient aucun
   client nommé, aucune citation, aucun résultat attribué, le run **s'arrête avant le
   stratège** et rend les questions qui répareraient ça. Parce qu'aucune réécriture n'a
   jamais ajouté une preuve que la matière ne contenait pas.
3. **L'audience** — celle qui décidera à qui chaque brouillon est écrit *et par qui il sera
   noté*. Annoncée explicitement, jamais échangée en silence par un champ de formulaire.

### 5.2 Une seule synthèse stratégique

`app/marketing/strategist.py` — un appel pour toute la séquence, qui produit un
`EmailBrief` par email :

- le **job** de cet email et son **idée unique** (deux briefs ne doivent jamais pouvoir
  échanger la leur) ;
- **l'argument en quatre temps** : `felt_need` → `status_quo` → `why_it_fails` →
  ce que le produit fait à la place. C'est `why_it_fails` qui transforme une vantardise en
  argument, et il porte sur le *mécanisme de la catégorie*, jamais sur un concurrent nommé ;
- au plus **3 faits assignés** (`MAX_EVIDENCE_PER_EMAIL`) — un brief qui en assigne six
  demande une page produit ;
- jusqu'à **3 propositions alternatives complètes** (`MAX_ALTERNATIVE_IDEAS`) pour le
  bake-off : besoin, claim, preuve, limite, objection et CTA qui bougent ensemble.

### 5.3 La boucle de craft, par email

```
ÉTAPE 1 · BAKE-OFF — plusieurs paris, un seul survivant

  [M] N candidats ──► [C] 13 gates ──► [M] Lecture froide ──► Champion
  écrits en parallèle  gratuites ;      panel de 3             critique et
  arguments différents, un candidat     dispositions           réécritures
  pas des phrases       bloqué ne sera                         dépensées sur
  différentes           même pas lu                            lui seul

ÉTAPE 2 · LA BOUCLE — au plus `max_revisions` tours

      ┌──────────────────────────────────────────────┐
      │                                              │
      ▼                                              │
  [M] Duel ──► [M] Critique ──► [M] Réécriture ──────┘
  les 2 versions  dérive vs     gardée seulement    re-mesurée :
  côte à côte,    brief,        si elle revient     gates, lecture
  le lecteur      évidence non  meilleure           froide, duel
  en choisit une  dépensée

SORTIES

  Il passe          0 gate bloquante + pull ≥ 7/10 → expédié
  Ça stagne         pivot vers un AUTRE argument, depuis zéro — une seule fois
  Matière manquante le critique signale un trou → recovery, puis re-stratégie
  Plafond atteint   meilleure version gardée, sous-seuil signalé au rapport

PUIS

  Bake-off d'objets (≤ 8 variantes) · lecture de la séquence entière ·
  reworks ciblés, bornés séparément
```

La boucle commence large puis rétrécit. Écrire un deuxième candidat achète un **argument
différent** ; écrire une deuxième réécriture n'achète que le même argument poncé. C'est
pour ça que le bake-off est le levier qualité le moins cher du système.

Le pivot existe parce que quand la copy arrête de bouger, ce qui ne marche pas est
généralement le *claim* — et aucune réécriture n'a le droit de changer le claim.

### 5.4 Le lecteur froid est l'instrument, pas un avis

`app/marketing/reader.py`

Il n'a jamais vu le brief, la demande, le positionnement, la doc produit ni l'intention.
C'est le mécanisme entier : un modèle qui a lu le brief répond *depuis* le brief et bouche
les trous de la copy avec un contexte qu'aucun destinataire réel n'aura.

Il rend deux choses :

- **`pull`** sur 10, calibré en arithmétique d'email froid. `PULL_THRESHOLD = 7` signifie
  « au moins 6 personnes sur 100 comme moi cliqueraient », ce qui est un très bon cold
  email. L'échelle a été refaite parce que l'ancienne (« cette personne, interrogée à
  brûle-pourpoint, cliquerait-elle aujourd'hui ») mesurait un événement à 3 % : tous les
  brouillons revenaient à 1 ou 2 et l'instrument ne pouvait plus les distinguer.
- **`understood`** — a-t-il pu dire ce qu'on lui vendait sans deviner. C'est un **veto, pas
  un terme** : un brouillon que le panel n'a pas décodé perd contre un brouillon décodé à
  n'importe quel score, parce qu'un score de clic sur un email que personne n'a compris
  répond à une autre question. Voir `EmailVersion.measured`.

Le panel varie la **disposition** du lecteur, jamais son identité. Un panel qui couvrirait
plusieurs segments ne pourrait être satisfait que par une copy assez vague pour marcher sur
tous, et la boucle dépenserait son budget à poncer un email spécifique en email général.

### 5.5 Les 13 checks déterministes

`gates.run_all`, dans cet ordre : structure du brouillon, puis honnêteté, puis
délivrabilité, puis « un inconnu peut-il dire ce que c'est », puis variété.

| Gate | Ce qu'elle attrape |
|---|---|
| `structure` | brouillon malformé |
| `placeholder` | un `[Nom]` resté là |
| `stock_phrase` | formules creuses |
| `evidence` | chiffre / prix / citation / URL non licenciés par le ledger |
| `capability_scope` | une capacité interdite revendiquée |
| `spam` | délivrabilité |
| `overlap` | répète l'email précédent |
| `repeated_call_to_action` | plusieurs demandes concurrentes |
| `call_to_action` | un CTA absent de l'offre réelle |
| `clarity` | ne nomme jamais l'offre là où l'œil regarde (la signature ne compte pas) |
| `substantiation` | l'évidence assignée n'a pas été dépensée |
| `sameness` | un cadre d'argument que tous les concurrents utilisent aussi |
| `copy_review` | relecture ligne à ligne contre le ledger |

Deux détails à ne pas casser :

- Les comparaisons sont **aveugles à la typographie** : un CMS met des apostrophes courbes,
  un modèle recite en ASCII, et un test de sous-chaîne exact jetterait silencieusement une
  preuve correctement citée.
- Chaque issue est formulée **comme le correctif** (« le bloc 2 fait 71 mots en un
  paragraphe — coupe-le »), parce qu'elle est rendue telle quelle au rédacteur comme tour de
  correction.

---

## 6. Leviers et contraintes

`app/marketing/policy.py`

Les presets `fast` / `balanced` / `maximum` n'échangent pas des modèles moins chers contre
des modèles meilleurs. Ils échangent des **jugements par email**.

| Levier | Ce que ça coûte | Ce que ça achète |
|---|---|---|
| `draft_candidates` 1–4 | +1 écriture et +1 panel par candidat | un **pari différent**. Le meilleur rapport du système : quel argument fait réagir n'est pas déductible du brief |
| `reader_panel` | ×3 sur l'appel le moins cher du run | la médiane de 3 transforme « cette réécriture est meilleure » d'un tirage en **mesure** |
| `tournament` | quelques votes par comparaison | évite de comparer deux scores absolus saturés — ce qui rendait une réécriture qui change tout indistinguable d'une qui ne change rien |
| `critic_enabled` | 1 appel deep par tour | les deux échecs qui *ont l'air finis* : la dérive vis-à-vis du brief, et l'évidence assignée jamais dépensée |
| `subject_variants` 0–8 | 1 tour d'écriture + 1 réaction par lecteur | la seule phrase que la plupart des destinataires liront jamais |
| `max_revisions` 0–4 | 1 écriture + re-mesure complète par tour | le moins rentable des cinq : au-delà de 2, une réécriture arrête de réparer et commence à poncer |

### Contraintes à garder en tête avant de proposer quoi que ce soit

- **Ajouter un appel modèle = mettre à jour le forecast.** Le coût d'un run est affiché
  avant achat, et `tests/marketing/test_forecast.py` exécute la pipeline à chaque preset,
  compte les appels réellement faits et vérifie que le forecast les contenait. Ce n'est
  possible que parce qu'aucun appel ne route.
- **Zéro utilisateur, zéro donnée d'envoi réelle.** Toute idée dont la première étape est
  « collecter de la télémétrie » ou « calibrer sur l'opérateur » est morte à l'arrivée.
  Voir [external-review-brief.md](external-review-brief.md).
- **Chaque appel coûte du quota d'un abonnement personnel.** Une proposition qui augmente
  la dépense doit dire ce qu'elle achète.
- **Ne jamais lancer une vraie campagne pour vérifier un changement de code.** Le provider
  scripté des tests répond *par rôle*, donc un test dit « le lecteur froid a détesté ce
  brouillon » et reste vrai quel que soit le nombre d'appels autour.
- **Le goût ne bloque jamais.** Une proposition qui donne à un modèle le pouvoir d'arrêter
  un envoi sort de l'architecture.
- **Développeur solo.** Après le quota, l'effort d'implémentation est la ressource la plus
  rare.
