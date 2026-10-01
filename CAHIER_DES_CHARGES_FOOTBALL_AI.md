# Cahier des charges — Football AI Fan Intelligence Platform
## Version 1.0 — Spécification maître pour développement avec Codex

**Statut :** prêt pour implémentation  
**Approche :** MVP simple, multi-équipe dès l’origine, extensible sans sur-ingénierie  
**Équipe pilote :** FC Barcelona  
**Langue du personnage Barça :** espagnol d’Espagne (`es-ES`)  
**Identité du personnage Barça :** supporter catalan natif, passionné du FC Barcelona  
**Validation éditoriale V1 :** humaine obligatoire par défaut  
**Publication automatique V1 :** hors périmètre, mais architecture préparée  
**Fournisseur de données V1 :** Sportmonks via une abstraction `FootballDataProvider`  
**LLM V1 :** OpenAI via une abstraction `LLMProvider`

---

# 1. Vision du produit

Le produit est une plateforme capable de générer automatiquement du contenu éditorial football autour de plusieurs équipes.

Chaque équipe est représentée par un **profil configurable** comprenant :

- son identité ;
- ses identifiants chez le fournisseur de données ;
- ses compétitions ;
- sa langue de script ;
- son contexte culturel ;
- son personnage de supporter ;
- son niveau d’émotion ;
- ses rivaux ;
- son style d’analyse ;
- ses paramètres de génération ;
- ses règles éditoriales ;
- ses horaires de génération.

La plateforme détecte automatiquement les matchs à venir et terminés, collecte les données football nécessaires, calcule les anomalies et tendances, sélectionne les informations les plus intéressantes, puis confie **uniquement ces informations vérifiées** au LLM chargé d’écrire le contenu.

Le LLM ne doit pas être la source des statistiques et ne doit pas effectuer seul l’analyse numérique.

Le principe fondamental est :

> **Données → calculs déterministes → insights vérifiés → narration → personnage → Content Pack**

Le premier profil sera celui du FC Barcelona, mais aucune partie essentielle du moteur ne doit être codée spécifiquement pour le Barça.

---

# 2. Objectifs de la V1

La V1 doit permettre de :

1. créer, modifier, activer et désactiver plusieurs profils d’équipes ;
2. synchroniser automatiquement leur calendrier ;
3. détecter le prochain match ;
4. produire automatiquement un contenu `PRE_MATCH` avant le match ;
5. produire automatiquement un contenu `POST_MATCH` après le match ;
6. collecter et normaliser les statistiques nécessaires ;
7. conserver un historique statistique équipe/joueur ;
8. calculer automatiquement des tendances et anomalies ;
9. produire des `InsightCandidate` factuels et traçables ;
10. sélectionner les meilleurs insights ;
11. construire le contexte émotionnel du personnage ;
12. choisir une durée adaptée au contenu ;
13. produire plusieurs hooks ;
14. produire un script final adapté à la durée ;
15. produire un Content Pack complet ;
16. afficher les preuves et sources de chaque affirmation analytique ;
17. permettre une validation humaine ;
18. permettre une régénération manuelle ;
19. conserver l’historique des versions ;
20. préparer la future collecte de performance des vidéos ;
21. permettre ultérieurement de changer de fournisseur football ou de LLM sans réécriture globale.

---

# 3. Hors périmètre de la V1

Ne pas développer dans la première version :

- génération d’avatar ;
- génération vidéo ;
- synthèse vocale ;
- publication automatique TikTok/Instagram/YouTube ;
- analyse vidéo du match ;
- computer vision ;
- tracking physique propriétaire ;
- prédictions sophistiquées par machine learning ;
- apprentissage automatique sur la performance des vidéos ;
- génération live pendant le match ;
- réaction automatique à la composition officielle ;
- gestion commerciale des sponsors ;
- application mobile ;
- système multi-tenant SaaS ;
- système de paiement ;
- Redis ;
- RabbitMQ ;
- Celery ;
- Kubernetes.

L’architecture doit toutefois permettre d’ajouter ultérieurement :

- `LINEUP_REACTION` ;
- `HALF_TIME` ;
- `LIVE_EVENT` ;
- `TRANSFER` ;
- `WEEKLY_RECAP` ;
- publication sociale ;
- analyse des performances de contenu ;
- données Opta/Sportradar ;
- tracking spatial/physique ;
- plusieurs personnages pour une même équipe.

---

# 4. Principes d’architecture obligatoires

## 4.1 Séparation des responsabilités

Créer les interfaces/services suivants :

```text
FootballDataProvider
MatchSyncService
StatsNormalizationService
BaselineEngine
AnalyticsEngine
InsightRanker
NarrativeAngleEngine
CharacterEngine
DurationEngine
LLMProvider
ScriptEngine
ContentPackService
SchedulerService
```

Aucun de ces services ne doit dépendre directement du FC Barcelona.

## 4.2 Architecture fournisseur football interchangeable

Le code métier ne doit jamais appeler directement Sportmonks.

Il doit appeler une interface :

```python
class FootballDataProvider(Protocol):
    async def get_team(self, external_team_id: str): ...
    async def get_fixtures(self, external_team_id: str, start, end): ...
    async def get_fixture(self, external_fixture_id: str): ...
    async def get_fixture_statistics(self, external_fixture_id: str): ...
    async def get_lineups(self, external_fixture_id: str): ...
    async def get_events(self, external_fixture_id: str): ...
    async def get_xg(self, external_fixture_id: str): ...
```

Implémentation V1 :

```text
SportmonksProvider
```

Implémentations futures possibles :

```text
OptaProvider
SportradarProvider
```

## 4.3 Architecture LLM interchangeable

Créer :

```python
class LLMProvider(Protocol):
    async def generate_structured(self, request, response_schema): ...
```

Implémentation V1 :

```text
OpenAIProvider
```

Le reste du système ne doit connaître ni nom de modèle ni syntaxe spécifique au fournisseur.

## 4.4 Pas de logique métier critique dans le prompt

Les opérations suivantes doivent être faites par du code Python :

- moyennes ;
- différences ;
- pourcentages ;
- tendances ;
- baselines ;
- scores ;
- rankings ;
- contrôle de disponibilité d’une statistique ;
- sélection de fenêtre temporelle ;
- validation des preuves ;
- contrôle de durée.

Le LLM sert à :

- transformer des insights validés en narration ;
- produire des hooks ;
- adapter le ton au personnage ;
- produire une formulation naturelle ;
- découper le script ;
- produire titre/caption/question.

---

# 5. Stack technique retenue

## Backend

- Python, version stable supportée ;
- FastAPI ;
- Pydantic ;
- SQLAlchemy ;
- Alembic ;
- PostgreSQL ;
- `httpx` pour les appels HTTP ;
- scheduler/worker Python séparé ;
- tests avec `pytest`.

## Frontend administration

- Next.js, version stable ;
- React ;
- TypeScript ;
- App Router ;
- UI simple et responsive ;
- appels exclusivement au backend FastAPI.

## Infrastructure

Docker Compose avec au minimum :

```text
frontend
api
worker
postgres
```

Pas de Redis en V1.

## Déploiement

Le projet doit pouvoir être lancé :

```bash
docker compose up
```

et déployé sur n’importe quel VPS compatible Docker.

---

# 6. Structure recommandée du repository

```text
/
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   ├── db/
│   │   │   ├── domain/
│   │   │   ├── providers/
│   │   │   │   ├── football/
│   │   │   │   └── llm/
│   │   │   ├── services/
│   │   │   ├── analytics/
│   │   │   ├── prompts/
│   │   │   └── schemas/
│   │   └── tests/
│   ├── worker/
│   │   ├── app/
│   │   └── tests/
│   └── web/
│       ├── app/
│       ├── components/
│       └── lib/
├── migrations/
├── docker/
├── docs/
├── fixtures/
├── .env.example
├── docker-compose.yml
├── README.md
└── Makefile
```

Le backend et le worker peuvent partager un package Python commun.

---

# 7. Concept central : Team Profile

Une équipe ne doit jamais être une constante dans le code.

Elle est représentée par une entité `TeamProfile`.

## 7.1 Champs principaux

```text
id
slug
display_name
short_name
active
football_provider
external_team_id
country
city
timezone
primary_script_language
locale
cultural_context
fan_identity
character_name
character_description
speech_style
speech_rate_wpm
default_duration_mode
forced_duration_seconds nullable
prematch_offset_minutes
postmatch_delay_minutes
validation_mode
created_at
updated_at
profile_version
```

## 7.2 Paramètres éditoriaux

```text
emotion_base_level
provocation_level
humor_level
technical_depth
rivalry_boost
optimism_bias
self_criticism_level
allowed_slang
forbidden_phrases
favorite_expressions
editorial_rules
```

Les niveaux numériques sont compris entre 0 et 100.

## 7.3 Rivalités

Table séparée :

```text
team_rivalries
- id
- team_profile_id
- opponent_external_team_id
- opponent_name
- intensity 0..100
- rivalry_label
- custom_character_rules JSONB
```

Exemple Barça :

```json
{
  "opponent_name": "Real Madrid",
  "intensity": 100,
  "rivalry_label": "El Clásico",
  "custom_character_rules": {
    "provocation_boost": 25,
    "emotion_boost": 20
  }
}
```

## 7.4 Versionnement

Toute modification significative d’un profil doit incrémenter `profile_version`.

Chaque contenu généré conserve :

```text
team_profile_id
team_profile_version
```

Ainsi un script historique peut toujours être relié à la configuration utilisée lors de sa génération.

---

# 8. Profil pilote : FC Barcelona

Seed initial obligatoire.

```yaml
slug: barcelona
display_name: FC Barcelona
short_name: Barça
active: true

primary_script_language: es
locale: es-ES
timezone: Europe/Madrid

cultural_context:
  region: Catalunya
  fan_identity: native_catalan_barca_supporter
  script_language: Spanish
  note: >
    Le personnage est catalan natif mais s'adresse à une audience football
    en espagnol. Il peut ponctuellement utiliser une expression catalane
    uniquement si elle semble naturelle et si le profil l'autorise.

character:
  supporter_type: passionate
  emotion_base_level: 75
  humor_level: 55
  provocation_level: 55
  technical_depth: 80
  optimism_bias: 60
  self_criticism_level: 70

editorial_rules:
  - Le personnage aime le Barça mais ne falsifie jamais une statistique.
  - Il peut critiquer l'équipe quand les données le justifient.
  - Il peut taquiner un rival mais pas insulter des personnes.
  - L'émotion peut être subjective ; les affirmations statistiques doivent rester factuelles.
  - Pas de salutations longues en début de Short.
  - Le hook doit commencer immédiatement.
```

Le `external_team_id` doit être configuré via l’interface ou un seed d’environnement et ne doit pas être supposé par le code.

---

# 9. Modèle de données

## 9.1 `team_profiles`

Contient la configuration principale de chaque équipe.

## 9.2 `team_rivalries`

Rivalités configurées.

## 9.3 `competitions`

```text
id
provider
external_competition_id
name
country
active
```

## 9.4 `team_competitions`

Relation N-N entre profils et compétitions.

## 9.5 `fixtures`

```text
id UUID
provider
external_fixture_id
competition_id
season_id
home_external_team_id
away_external_team_id
home_name
away_name
kickoff_at UTC
status
home_score
away_score
result_info
last_provider_sync_at
raw_payload JSONB
created_at
updated_at
```

Contrainte unique :

```text
(provider, external_fixture_id)
```

## 9.6 `team_fixture_links`

Permet à un match d’être associé à plusieurs profils.

```text
fixture_id
team_profile_id
team_side home|away
```

## 9.7 `team_match_stats`

Format normalisé.

```text
id
fixture_id
team_external_id
metric_code
metric_value
metric_unit
period
provider_type_id nullable
source
confidence
created_at
```

Contrainte de déduplication appropriée par match/équipe/métrique/période.

## 9.8 `player_match_stats`

```text
id
fixture_id
player_external_id
player_name
team_external_id
minutes
metric_code
metric_value
metric_unit
source
confidence
```

## 9.9 `match_events`

Pour les événements nécessaires aux analyses :

```text
fixture_id
provider_event_id
minute
extra_minute
event_type
team_external_id
player_external_id
related_player_external_id
x nullable
y nullable
payload JSONB
```

## 9.10 `metric_definitions`

Catalogue central.

```text
code
display_name
scope team|player
unit
higher_is_better nullable
importance_weight
editorial_weight
default_anomaly_threshold
min_sample_size
enabled
provider_mapping JSONB
```

Exemples :

```text
goals
xg
shots
shots_on_target
possession_pct
passes
pass_accuracy_pct
corners
fouls
yellow_cards
red_cards
player_xg
player_shots
player_key_passes
player_tackles
player_interceptions
```

Une métrique indisponible chez le fournisseur ne doit jamais bloquer le pipeline.

## 9.11 `baselines`

Cache des références calculées.

```text
entity_type team|player
entity_external_id
competition_id nullable
metric_code
window_type
window_size
context
sample_size
mean
median
stddev nullable
min_value
max_value
calculated_at
```

Exemples de `window_type` :

```text
LAST_5
LAST_10
SEASON
HOME_LAST_5
AWAY_LAST_5
COMPETITION_LAST_5
```

## 9.12 `insight_candidates`

```text
id
fixture_id
team_profile_id
content_type
insight_type
headline_internal
claim
evidence JSONB
baseline JSONB
metric_codes JSONB
deviation_score
importance_score
confidence_score
context_score
novelty_score
final_score
direction
eligible
rejection_reason nullable
created_at
```

## 9.13 `generation_jobs`

```text
id
team_profile_id
fixture_id
content_type
status
scheduled_for
started_at
finished_at
attempt_count
max_attempts
idempotency_key UNIQUE
last_error
payload JSONB
```

Statuses :

```text
PENDING
RUNNING
SUCCEEDED
FAILED
CANCELLED
SKIPPED
```

## 9.14 `content_packs`

```text
id
team_profile_id
team_profile_version
fixture_id
content_type
generation_job_id
language
target_duration_seconds
estimated_duration_seconds
status
emotion_profile JSONB
selected_insights JSONB
narrative_angle JSONB
hooks JSONB
recommended_hook
script
script_segments JSONB
title
first_screen_text
caption
comment_question
hashtags JSONB
evidence_manifest JSONB
llm_provider
llm_model
prompt_version
created_at
approved_at nullable
approved_by nullable
```

Statuses :

```text
DRAFT
NEEDS_REVIEW
APPROVED
REJECTED
PUBLISHED
ARCHIVED
```

## 9.15 `content_performance`

Prévu dès V1, saisie manuelle possible.

```text
content_pack_id
platform
published_at
views
engaged_views nullable
average_watch_seconds nullable
average_percentage_viewed nullable
likes
comments
shares
saves nullable
followers_gained nullable
measured_at
source manual|api
```

Aucun moteur d’apprentissage n’est requis en V1.

---

# 10. Synchronisation calendrier

## 10.1 Worker

Le worker tourne indépendamment de l’API.

Il exécute plusieurs tâches périodiques.

### Job A — `sync_active_teams`

Fréquence par défaut :

```text
toutes les 6 heures
```

Pour chaque `TeamProfile.active = true` :

1. récupérer les fixtures de J-7 à J+30 ;
2. upsert les fixtures ;
3. associer les fixtures au profil ;
4. détecter les nouvelles dates ou reports ;
5. recalculer les futurs jobs de contenu.

### Job B — `dispatch_due_generation_jobs`

Fréquence :

```text
toutes les 60 secondes
```

Recherche :

```text
status = PENDING
scheduled_for <= now()
```

Réserve atomiquement le job puis exécute le pipeline.

## 10.2 Idempotence

Un même contenu ne doit jamais être généré deux fois par accident.

Exemple de clé :

```text
{team_profile_id}:{fixture_id}:{content_type}:v{profile_version}
```

Utiliser une contrainte UNIQUE en base.

Pour une régénération manuelle, créer une révision ou un `generation_run` distinct, mais ne pas contourner silencieusement l’idempotence automatique.

---

# 11. Déclenchement PRE_MATCH

Par défaut :

```text
kickoff - 360 minutes
```

Paramètre configurable par profil :

```text
prematch_offset_minutes
```

Avant exécution :

- fixture non annulée ;
- fixture future ;
- profil actif ;
- suffisamment de données historiques ;
- job non déjà réussi.

Si la date du match change, la tâche doit être replanifiée.

---

# 12. Déclenchement POST_MATCH

Ne pas supposer qu’une heure de fin calculée suffit.

Le système doit lire le statut du fournisseur.

Déclenchement lorsque le fournisseur indique un état final compatible :

```text
FT
AET
PEN
ou équivalent normalisé
```

Ajouter ensuite :

```text
postmatch_delay_minutes = 10
```

par défaut, configurable.

Objectif : laisser le temps aux statistiques finales de se stabiliser.

Le worker peut augmenter temporairement la fréquence de synchronisation autour des matchs d’une équipe active.

---

# 13. Normalisation des statuts de match

Créer un enum interne :

```text
SCHEDULED
LIVE
HALF_TIME
FINISHED
POSTPONED
CANCELLED
ABANDONED
UNKNOWN
```

Le provider Sportmonks mappe ses statuts vers cet enum.

Aucune logique métier ne doit dépendre directement d’un code Sportmonks.

---

# 14. Pipeline PRE_MATCH

```text
Fixture détectée
    ↓
Vérification fraîcheur des données
    ↓
Historique équipe
    ↓
Historique adversaire
    ↓
Historique joueurs disponibles
    ↓
Baselines
    ↓
Analyses de tendances
    ↓
Insight candidates
    ↓
Insight ranker
    ↓
Contexte du match
    ↓
Emotion Engine
    ↓
Narrative Angle Engine
    ↓
Duration Engine
    ↓
LLM Script Engine
    ↓
Validator
    ↓
Content Pack
    ↓
NEEDS_REVIEW
```

---

# 15. Données PRE_MATCH à utiliser

Priorité 1 :

- cinq derniers matchs ;
- dix derniers matchs ;
- saison ;
- domicile/extérieur ;
- buts marqués ;
- buts encaissés ;
- xG si disponible ;
- xGA si disponible ou dérivable ;
- tirs ;
- tirs cadrés ;
- possession ;
- passes / précision ;
- statistiques défensives disponibles ;
- forme récente des joueurs ;
- minutes jouées ;
- blessures/indisponibilités uniquement si une source fiable est intégrée.

Priorité 2 :

- confrontations directes récentes ;
- tendances par compétition ;
- performance contre profils d’adversaires similaires ;
- line-up attendu si disponible.

Les confrontations historiques doivent avoir un poids éditorial inférieur à la forme récente.

---

# 16. Pipeline POST_MATCH

```text
Fixture FINISHED
    ↓
Attente configurable
    ↓
Refresh données finales
    ↓
Stats équipe
    ↓
Stats joueur
    ↓
Events
    ↓
xG si disponible
    ↓
Baselines pré-match
    ↓
Comparaison match vs normalité
    ↓
Insights simples
    ↓
Insights composés
    ↓
Insight ranker
    ↓
Scoreline Truth Check
    ↓
Character Emotion
    ↓
Narrative Angle
    ↓
Duration
    ↓
LLM Script
    ↓
Fact Validator
    ↓
Content Pack
```

---

# 17. Analytics Engine

Le moteur analytique doit être déterministe.

## 17.1 Objectifs

Pour chaque statistique, répondre à :

1. quelle est la valeur actuelle ?
2. quelle est la référence pertinente ?
3. quelle est la différence absolue ?
4. quelle est la différence relative ?
5. l’échantillon est-il suffisant ?
6. la donnée est-elle fiable ?
7. cette différence est-elle éditorialement intéressante ?
8. cette information est-elle redondante avec une autre ?

## 17.2 Baselines

Calculer plusieurs références.

### Équipe

```text
LAST_5
LAST_10
SEASON
HOME_LAST_5
AWAY_LAST_5
COMPETITION_LAST_5
```

### Joueur

```text
LAST_5_APPEARANCES
LAST_10_APPEARANCES
SEASON_PER_90
LAST_5_PER_90
```

Ne pas comparer naïvement un joueur ayant joué 15 minutes à une moyenne par match.

Quand cela est pertinent, normaliser en `per_90`.

---

# 18. Sélection de la baseline pertinente

Chaque anomalie peut être testée contre plusieurs baselines.

La baseline sélectionnée doit maximiser un `baseline_quality_score` basé sur :

```text
sample_size
recency
context_relevance
metric_compatibility
```

Règles :

- ne jamais utiliser une baseline sous `min_sample_size` sauf mention explicite ;
- préférer `HOME_LAST_5` pour un match à domicile si l’échantillon est suffisant ;
- sinon `LAST_5` ;
- utiliser la saison comme référence stable ;
- conserver les autres comparaisons comme contexte secondaire.

---

# 19. Anomaly Score

Le score doit rester simple et explicable.

Pour chaque métrique :

```text
relative_deviation =
    abs(current_value - baseline_value)
    / max(abs(baseline_value), metric_floor)
```

Chaque métrique possède :

```text
default_anomaly_threshold
```

Exemple :

```text
xG: 0.20
shots: 0.25
possession_pct: 0.10
```

Puis :

```text
deviation_score =
    clamp(relative_deviation / default_anomaly_threshold, 0, 1)
```

Autres composantes entre 0 et 1 :

```text
importance_score
confidence_score
context_score
novelty_score
```

Formule initiale :

```text
final_score_0_1 =
      0.35 * deviation_score
    + 0.25 * importance_score
    + 0.15 * confidence_score
    + 0.15 * context_score
    + 0.10 * novelty_score

final_score = round(final_score_0_1 * 100)
```

Ces poids doivent être dans la configuration et non dispersés dans le code.

---

# 20. Confidence Score

Éléments :

- donnée officiellement disponible ;
- échantillon suffisant ;
- donnée non partielle ;
- période complète ;
- source unique clairement identifiée ;
- pas de contradiction entre champs.

Exemple :

```text
HIGH >= 0.80
MEDIUM >= 0.60
LOW < 0.60
```

Par défaut, seuls les insights `HIGH` et `MEDIUM` peuvent entrer dans un script.

Les `LOW` sont visibles dans l’admin mais exclus de la génération.

---

# 21. Context Score

Le contexte augmente ou réduit l’intérêt éditorial.

Facteurs :

- rivalité ;
- importance de compétition ;
- match éliminatoire ;
- finale ;
- retour de blessure si données fiables ;
- série de victoires/défaites ;
- très gros écart entre performance récente et saison ;
- joueur vedette configuré dans le profil.

Ne jamais transformer le `context_score` en donnée sportive.

Il sert uniquement à classer ce qui mérite d’être raconté.

---

# 22. Novelty Score

Objectif : éviter 10 vidéos consécutives racontant la même chose.

Le système compare un insight aux derniers contenus du profil.

Exemple :

si les trois derniers scripts ont déjà parlé de :

```text
low_xg
```

alors réduire légèrement son `novelty_score`, sauf si l’anomalie actuelle est exceptionnelle.

---

# 23. Insights composés

La valeur du produit ne doit pas dépendre uniquement de métriques isolées.

Créer un petit moteur de règles composées.

## 23.1 Scoreline Truth Check

POST_MATCH :

```text
scoreline vs xG
scoreline vs shots_on_target
scoreline vs big_chances si disponible
```

Exemples de concepts internes :

```text
FLATTERING_WIN
UNLUCKY_DEFEAT
DOMINANT_WIN
CLINICAL_FINISHING
WASTEFUL_ATTACK
```

Ne pas utiliser ces labels comme vérité éditoriale brute ; générer une affirmation quantitative soutenue par les chiffres.

## 23.2 Possession Without Threat

Candidat lorsque :

```text
possession élevée
ET
xG ou tirs dangereux faibles
```

## 23.3 Low Possession High Threat

Inverse.

## 23.4 Player Outlier

Exemple :

```text
player_metric_current
vs
player_last_5_per90
```

## 23.5 Trend Break

Exemple :

```text
équipe produisait > 2.0 xG/match
puis match actuel < 1.0
```

## 23.6 Defensive Warning

Exemple :

```text
xGA ou tirs cadrés concédés significativement supérieurs à la baseline
```

Chaque règle doit :

- être testable ;
- fournir un `claim`;
- fournir son `evidence`;
- fournir son `confidence`;
- ne jamais dépendre d’une interprétation opaque du LLM.

---

# 24. Insight Candidate — contrat

Exemple :

```json
{
  "type": "POSSESSION_WITHOUT_THREAT",
  "claim": "El Barça tuvo mucho balón, pero generó bastante menos peligro de lo habitual.",
  "evidence": [
    {
      "metric": "possession_pct",
      "current": 68.2,
      "baseline": 64.5,
      "baseline_window": "LAST_5"
    },
    {
      "metric": "xg",
      "current": 1.08,
      "baseline": 1.91,
      "baseline_window": "LAST_5"
    }
  ],
  "confidence": 0.94,
  "final_score": 88
}
```

Le champ `claim` peut être produit initialement sous forme neutre/interne, puis traduit stylistiquement par le LLM.

---

# 25. Insight Ranker

Objectif :

sélectionner peu d’insights mais très forts.

## PRE_MATCH

Par défaut :

```text
2 à 3 insights
```

## POST_MATCH

Par défaut :

```text
2 à 3 insights
```

Un quatrième insight n’est autorisé que pour un format long ou match exceptionnel.

## Règles de diversité

Éviter :

- trois insights basés sur la même métrique ;
- trois variantes du même problème ;
- deux insights identiques équipe/joueur.

Favoriser :

```text
1 insight équipe
+
1 insight tactique/statistique
+
1 insight joueur ou adversaire
```

quand disponible.

---

# 26. Emotion Engine

L’émotion ne doit pas être tirée au hasard.

Sortie normalisée :

```json
{
  "primary": "euphoric",
  "secondary": "analytical",
  "intensity": 87,
  "confidence": 75,
  "rivalry": 100,
  "arc": ["euphoric", "suspicious", "analytical", "confident"]
}
```

## Entrées

- résultat ;
- performance ;
- rivalité ;
- importance ;
- scénario du match ;
- attentes pré-match ;
- paramètres personnage.

## Exemple

Victoire 4–0 contre grand rival :

```text
emotion_intensity très élevé
```

Victoire 1–0 avec mauvaise performance :

```text
primary = relieved
secondary = critical
```

Défaite malgré très forte performance :

```text
primary = frustrated
secondary = defiant
```

---

# 27. Narrative Angle Engine

Après sélection des insights, choisir un angle éditorial.

Angles V1 :

```text
HIDDEN_STAT
SCORE_DOES_NOT_TELL_STORY
GOOD_NEWS_BAD_NEWS
ONE_NUMBER_CHANGES_EVERYTHING
PLAYER_SPOTLIGHT
TACTICAL_WARNING
RIVALRY_PROVOCATION
UNEXPECTED_POSITIVE
UNEXPECTED_NEGATIVE
```

Le moteur peut utiliser des règles simples.

Exemple :

si `Scoreline Truth Check` est fort :

```text
SCORE_DOES_NOT_TELL_STORY
```

si un joueur possède le meilleur insight :

```text
PLAYER_SPOTLIGHT
```

L’angle est ensuite transmis au LLM.

---

# 28. Duration Engine

Modes :

```text
AUTO
30
45
60
90
```

Par défaut :

```text
AUTO
```

## Règles AUTO initiales

### 30–35 s

- 1 insight très fort ;
- peu de contexte secondaire.

### 45 s

- 2 insights forts ;
- format par défaut recommandé pour MVP.

### 60 s

- 3 insights forts ;
- contexte nécessitant une explication.

### 90 s

- uniquement si :
  - forçage manuel ;
  - match exceptionnel ;
  - au moins 4 éléments significatifs ;
  - ou futur format long.

## Calcul mots

Chaque profil contient :

```text
speech_rate_wpm
```

Valeur initiale Barça :

```text
150
```

Calcul :

```text
target_word_count =
round(target_duration_seconds * speech_rate_wpm / 60)
```

Tolérance V1 :

```text
± 8 %
```

Le Validator doit demander une régénération ou une réduction automatique si la longueur dépasse cette tolérance.

---

# 29. Character Engine

Le Character Engine construit un `CharacterContext`.

Il ne génère pas les statistiques.

Sortie :

```json
{
  "language": "es",
  "locale": "es-ES",
  "identity": "native Catalan FC Barcelona supporter",
  "tone": {
    "emotion": 85,
    "humor": 55,
    "provocation": 70,
    "technical_depth": 80
  },
  "speech_rules": [
    "Hablar como un aficionado real, no como un periodista corporativo.",
    "No inventar cifras.",
    "Puede criticar al Barça.",
    "La provocación al rival debe ser deportiva, no insultante.",
    "Evitar introducciones genéricas."
  ]
}
```

---

# 30. Langue et localisation

La langue appartient au profil équipe.

Exemples futurs :

```text
Barcelona      → es-ES
Real Madrid    → es-ES
Liverpool      → en-GB
PSG            → fr-FR
Bayern         → de-DE
```

La localisation ne consiste pas uniquement à traduire.

Le profil doit permettre :

```text
dialect
football_vocabulary
allowed_local_expressions
cultural_references
forbidden_stereotypes
```

Le Barça doit produire un espagnol naturel.

Le fait que le personnage soit catalan doit influencer son identité et certaines expressions, mais le script principal reste espagnol tant que `primary_script_language = es`.

---

# 31. Script Engine

Le LLM reçoit uniquement :

1. contexte du match ;
2. profil personnage ;
3. émotion ;
4. angle narratif ;
5. insights sélectionnés ;
6. evidence manifest ;
7. durée/mots ;
8. contraintes éditoriales.

Il ne reçoit pas une base brute de centaines de statistiques.

---

# 32. Règles de prompt obligatoires

Le prompt système doit inclure au minimum :

```text
- Tu es scénariste, pas source statistique.
- Utilise uniquement les affirmations et chiffres fournis dans EVIDENCE.
- Ne crée jamais une statistique.
- Ne transforme pas une corrélation en certitude causale.
- Si une preuve est insuffisante, n'utilise pas l'affirmation.
- N'ajoute pas de blessure, citation, rumeur ou information absente.
- Le supporter peut être émotionnel ; les faits restent exacts.
- Commence par un hook immédiat.
- Respecte le nombre de mots cible.
- Écris dans la langue et le registre du profil.
```

---

# 33. Structure du script

Format cible Short/Reel/TikTok.

## 0–3 secondes

Hook.

Pas de :

```text
Hola chicos...
Bienvenidos...
Hoy vamos a hablar...
```

## 3–10 secondes

Réaction/personnalité/contexte.

## Milieu

Preuve principale.

## Ensuite

Deuxième insight ou twist.

## Fin

Conclusion émotionnelle + question naturelle.

Pas de CTA artificiel systématique du type :

```text
LIKE Y SUSCRÍBETE
```

Le CTA doit rester configurable et peu fréquent.

---

# 34. Hook Generator

Produire au minimum :

```text
3 hooks
```

Catégories différentes si possible :

```text
curiosity
emotion
contrarian
```

Exemple de structure, sans chiffres inventés :

```text
HOOK 1 — curiosité
Hay un dato de este partido que cambia completamente la historia.

HOOK 2 — émotion
Sí, hemos ganado. Pero hay una cosa que me preocupa muchísimo.

HOOK 3 — contradiction
El marcador dice una cosa. Los números dicen otra.
```

Le système doit choisir `recommended_hook` et conserver les alternatives.

---

# 35. Content Pack — sortie finale

Chaque génération produit un objet structuré.

Schéma conceptuel :

```json
{
  "content_type": "POST_MATCH",
  "team": "FC Barcelona",
  "fixture": {
    "opponent": "Real Madrid",
    "competition": "LaLiga",
    "kickoff_at": "..."
  },
  "language": "es",
  "target_duration_seconds": 45,
  "target_word_count": 113,
  "emotion": {
    "primary": "euphoric",
    "secondary": "analytical",
    "intensity": 90
  },
  "narrative_angle": "SCORE_DOES_NOT_TELL_STORY",
  "hooks": [
    "...",
    "...",
    "..."
  ],
  "recommended_hook": "...",
  "title": "...",
  "first_screen_text": "...",
  "script": "...",
  "segments": [
    {
      "start": 0,
      "end": 3,
      "purpose": "hook",
      "text": "..."
    },
    {
      "start": 3,
      "end": 12,
      "purpose": "emotion",
      "text": "..."
    },
    {
      "start": 12,
      "end": 30,
      "purpose": "insight_1",
      "text": "..."
    }
  ],
  "caption": "...",
  "comment_question": "...",
  "hashtags": [],
  "evidence_manifest": [],
  "quality_checks": {
    "facts_validated": true,
    "word_count_valid": true,
    "language_valid": true,
    "duplicate_content_check": true
  }
}
```

---

# 36. Evidence Manifest

Chaque affirmation numérique du script doit être reliée à une preuve.

Exemple :

```json
[
  {
    "evidence_id": "EV-001",
    "claim": "El Barça produjo menos xG de lo habitual.",
    "metric": "xg",
    "current_value": 1.08,
    "baseline_value": 1.91,
    "baseline_window": "LAST_5",
    "source_provider": "sportmonks",
    "fixture_id": "...",
    "confidence": "HIGH"
  }
]
```

L’interface doit permettre de cliquer sur un insight et voir sa preuve.

---

# 37. Fact Validator

Après génération du LLM :

1. extraire/relire les nombres présents ;
2. vérifier qu’ils sont présents dans `evidence_manifest` ;
3. vérifier les noms joueur/équipe ;
4. vérifier langue ;
5. vérifier longueur ;
6. vérifier qu’aucune statistique supplémentaire n’est apparue.

Si validation échoue :

```text
une seule tentative automatique de correction
```

Si elle échoue encore :

```text
status = NEEDS_REVIEW
quality_warning = true
```

Ne pas boucler indéfiniment.

---

# 38. PRE_MATCH : règles éditoriales

Le script doit répondre à une question du type :

> Qu’est-ce qu’un supporter devrait surveiller dans ce match que les statistiques récentes permettent réellement d’identifier ?

Priorités :

1. forme récente ;
2. différences vs normalité ;
3. matchup adversaire ;
4. joueurs en tendance ;
5. rivalité/contexte.

Les pronostics numériques sont **désactivés par défaut en V1**.

Le personnage peut exprimer un sentiment qualitatif :

```text
Tengo buenas sensaciones.
Este partido me preocupa.
Hay una oportunidad clara aquí.
```

mais pas inventer une probabilité.

Prévoir plus tard :

```text
prediction_mode:
  DISABLED
  QUALITATIVE
  PROVIDER_PROBABILITY
```

V1 par défaut :

```text
QUALITATIVE
```

---

# 39. POST_MATCH : règle éditoriale centrale

Question principale :

> **Qu’est-ce que le score ne raconte pas ?**

Même en cas de match évident, le moteur doit chercher :

- performance vs résultat ;
- efficacité ;
- anomalie individuelle ;
- tendance confirmée ou cassée ;
- faiblesse masquée ;
- amélioration masquée.

Ne pas forcer artificiellement un “secret” si aucun insight n’est assez fort.

Dans ce cas :

```text
narrative_angle = STRAIGHT_ANALYSIS
```

La crédibilité prime sur la recherche artificielle de surprise.

---

# 40. Interface d’administration

## 40.1 Dashboard

Afficher :

- équipes actives ;
- prochains matchs ;
- jobs planifiés ;
- scripts à valider ;
- erreurs récentes ;
- état fournisseur de données ;
- dernière synchronisation.

## 40.2 Teams

Liste des profils.

Actions :

```text
Créer
Modifier
Dupliquer
Activer
Désactiver
```

## 40.3 Team Editor

Sections :

```text
Identity
Data Provider
Competitions
Language & Culture
Character
Rivalries
Analytics
Generation
Editorial Rules
```

## 40.4 Matches

Filtres :

```text
team
date
competition
status
```

Détail match :

- score ;
- statut ;
- données brutes résumées ;
- stats normalisées ;
- joueurs ;
- insights calculés ;
- contenus générés.

## 40.5 Content

Liste :

```text
NEEDS_REVIEW
APPROVED
REJECTED
PUBLISHED
```

Fiche contenu :

- hooks ;
- script ;
- segments ;
- insights utilisés ;
- preuves ;
- durée ;
- avertissements ;
- bouton approuver ;
- bouton rejeter ;
- bouton régénérer ;
- édition manuelle.

Toute édition manuelle doit créer une nouvelle révision ou au minimum conserver l’original généré.

## 40.6 Manual Generate

Depuis un match :

```text
Generate PRE_MATCH
Generate POST_MATCH
```

Le système doit signaler si les données nécessaires ne sont pas disponibles.

---

# 41. Authentification

V1 :

- un compte administrateur ;
- authentification email/mot de passe ou username/mot de passe ;
- mot de passe hashé ;
- session sécurisée ;
- cookies HTTP-only recommandés ;
- aucune clé API exposée au navigateur.

Préparer une table `users` extensible sans développer RBAC avancé.

---

# 42. API backend

Préfixe :

```text
/api/v1
```

## Auth

```text
POST /auth/login
POST /auth/logout
GET  /auth/me
```

## Teams

```text
GET    /teams
POST   /teams
GET    /teams/{id}
PATCH  /teams/{id}
POST   /teams/{id}/activate
POST   /teams/{id}/deactivate
POST   /teams/{id}/sync
POST   /teams/{id}/duplicate
```

## Rivalries

```text
GET    /teams/{id}/rivalries
POST   /teams/{id}/rivalries
PATCH  /teams/{id}/rivalries/{rivalry_id}
DELETE /teams/{id}/rivalries/{rivalry_id}
```

## Fixtures

```text
GET /fixtures
GET /fixtures/{id}
POST /fixtures/{id}/refresh
```

## Analytics

```text
GET  /fixtures/{id}/insights
POST /fixtures/{id}/recalculate-insights
GET  /fixtures/{id}/baselines
```

## Content

```text
GET   /contents
GET   /contents/{id}
POST  /fixtures/{id}/generate/pre-match
POST  /fixtures/{id}/generate/post-match
POST  /contents/{id}/regenerate
POST  /contents/{id}/approve
POST  /contents/{id}/reject
PATCH /contents/{id}
```

## Performance

```text
POST /contents/{id}/performance
GET  /contents/{id}/performance
```

## System

```text
GET /health
GET /health/providers
GET /jobs
POST /jobs/{id}/retry
```

---

# 43. Sportmonks Adapter V1

L’adapter doit être isolé dans :

```text
providers/football/sportmonks/
```

Responsabilités :

- authentification ;
- pagination ;
- retry ;
- rate-limit handling ;
- mapping identifiants ;
- mapping statuts ;
- mapping métriques ;
- parsing ;
- journalisation ;
- stockage optionnel du payload brut.

Utiliser les capacités disponibles pour récupérer selon couverture :

- fixtures ;
- participants ;
- scores ;
- statistics ;
- lineups ;
- events ;
- xG.

Le système doit fonctionner même si xG n’est pas disponible pour une compétition ou un abonnement donné.

Créer :

```text
ProviderCapabilities
```

Exemple :

```json
{
  "fixture_stats": true,
  "player_stats": true,
  "events": true,
  "xg_team": true,
  "xg_player": false,
  "tracking": false
}
```

---

# 44. Gestion des données manquantes

Principe obligatoire :

> une statistique manquante réduit les possibilités d’analyse mais ne casse pas le match.

Le pipeline doit pouvoir produire un script avec :

```text
shots
possession
passes
score
```

même si :

```text
xG
```

est absent.

Un insight dépendant d’une donnée absente doit être :

```text
eligible = false
rejection_reason = MISSING_METRIC
```

---

# 45. Cache et maîtrise des coûts

## Football API

Ne pas appeler l’API à chaque affichage frontend.

Stocker les réponses normalisées.

Politique suggérée :

### Match futur loin du kickoff

refresh toutes les 6 h.

### Jour de match

refresh plus fréquent.

### Match live

si la V1 doit seulement attendre la fin :

```text
toutes les 5 minutes
```

autour de la fenêtre probable de fin.

### Match terminé

un refresh final puis gel de la majorité des données.

## LLM

Le LLM ne doit être appelé que lorsque :

- un job de contenu est dû ;
- régénération manuelle ;
- correction après validation.

Aucun LLM nécessaire pour :

- calculer baselines ;
- calculer scores ;
- classer statistiques simples ;
- synchroniser fixtures.

---

# 46. Gestion d’erreurs

## API football indisponible

Retry exponentiel avec limite.

Exemple :

```text
3 tentatives
```

Puis job `FAILED`.

## Données incomplètes POST_MATCH

Replanifier automatiquement une fois :

```text
+ 10 minutes
```

si le match vient de finir et que les statistiques critiques sont absentes.

## LLM indisponible

Retry limité.

Ne jamais dupliquer le job.

## Mauvais JSON LLM

Utiliser structured output si disponible.

Sinon :

- validation Pydantic ;
- une tentative de réparation ;
- échec propre.

---

# 47. Observabilité

Logs structurés JSON.

Chaque job doit avoir :

```text
job_id
team_profile_id
fixture_id
content_type
provider
duration_ms
status
```

Journaliser :

- appels provider ;
- nombre de données récupérées ;
- nombre d’insights candidats ;
- insights sélectionnés ;
- appels LLM ;
- coût/tokens si fournisseur le retourne ;
- erreurs.

Prévoir table ou vue simple `system_events` uniquement si nécessaire.

---

# 48. Sécurité

Obligatoire :

- secrets uniquement en variables d’environnement ;
- `.env` non commité ;
- `.env.example` sans secrets ;
- API provider appelée uniquement backend ;
- clés LLM uniquement backend ;
- validation stricte Pydantic ;
- protection CORS limitée ;
- mots de passe hashés ;
- pas de raw SQL non paramétré ;
- logs sans clés API ;
- timeout HTTP ;
- taille maximale payload raisonnable.

---

# 49. Variables d’environnement

Exemple :

```env
APP_ENV=development
APP_SECRET_KEY=
DATABASE_URL=

SPORTMONKS_API_TOKEN=
FOOTBALL_PROVIDER=sportmonks

OPENAI_API_KEY=
LLM_PROVIDER=openai
LLM_MODEL=

ADMIN_EMAIL=
ADMIN_PASSWORD=

DEFAULT_TIMEZONE=UTC
WEB_URL=http://localhost:3000
API_URL=http://localhost:8000
```

Le nom de modèle ne doit pas être codé en dur.

---

# 50. Prompt versioning

Chaque template possède un identifiant :

```text
prematch_script_v1
postmatch_script_v1
hook_v1
fact_repair_v1
```

Stocker dans `content_packs` :

```text
prompt_version
```

Ne jamais modifier silencieusement un prompt historique sans incrémenter sa version.

---

# 51. Performance future du contenu

Bien que la V1 n’apprenne pas automatiquement, préparer les données permettant plus tard de répondre à :

```text
Quels hooks retiennent le mieux ?
Quelle durée fonctionne le mieux ?
Quel type d’insight est le plus partagé ?
Quel niveau émotionnel fonctionne le mieux ?
Quels joueurs génèrent le plus d’engagement ?
```

Le Content Pack doit donc conserver des tags analytiques :

```text
hook_type
narrative_angle
insight_types
duration
emotion_intensity
rivalry_intensity
featured_players
```

---

# 52. Anti-répétition

Avant génération :

récupérer les 5 à 10 derniers contenus du profil.

Fournir au Script Engine uniquement un résumé de :

- hooks récents ;
- angles récents ;
- expressions surutilisées.

Le LLM doit éviter de répéter exactement :

```text
"El marcador miente"
```

à chaque match.

Mais ne pas empêcher un angle pertinent de réapparaître.

---

# 53. Tests obligatoires

## Unit tests

Couvrir :

- anomaly score ;
- baseline selection ;
- sample size ;
- duration engine ;
- rivalry boost ;
- missing metrics ;
- scoreline truth rules ;
- idempotency key ;
- status normalization.

## Provider tests

Utiliser des fixtures JSON locales.

Ne pas dépendre systématiquement de l’API réelle dans les tests CI.

Tester :

```text
Sportmonks payload → normalized domain model
```

## Integration tests

Scénarios :

### A — PRE_MATCH normal

- fixture future ;
- historique disponible ;
- job créé ;
- insights ;
- content pack.

### B — POST_MATCH

- fixture finished ;
- stats disponibles ;
- content generated once.

### C — xG absent

- pipeline réussit sans xG.

### D — match reporté

- job PRE_MATCH replanifié.

### E — double worker

- pas de double génération.

### F — provider failure

- retry puis état propre.

### G — LLM invente un chiffre

- validator rejette le contenu.

---

# 54. Jeux de données de test

Créer des données synthétiques.

Ne pas intégrer dans les tests unitaires des affirmations présentées comme statistiques réelles actuelles du Barça.

Fixtures :

```text
barcelona_future_match.json
barcelona_finished_match.json
missing_xg_match.json
postponed_match.json
extreme_player_outlier.json
```

---

# 55. Critères d’acceptation V1

La V1 est acceptée lorsque :

1. l’admin peut créer une deuxième équipe sans modification du code ;
2. chaque équipe peut avoir son propre provider team ID ;
3. chaque équipe possède sa propre langue ;
4. chaque équipe possède sa propre personnalité ;
5. les fixtures sont synchronisées automatiquement ;
6. un PRE_MATCH est planifié automatiquement ;
7. un POST_MATCH est planifié automatiquement après fin ;
8. aucune double génération automatique n’a lieu ;
9. le moteur calcule plusieurs baselines ;
10. le moteur produit des insights sans LLM ;
11. chaque insight possède une preuve ;
12. le LLM reçoit seulement les insights sélectionnés ;
13. un nombre absent des preuves ne peut pas apparaître sans alerte ;
14. le script respecte approximativement la durée cible ;
15. le Barça produit un script en espagnol ;
16. un nouveau profil peut produire une autre langue ;
17. les scripts sont visibles dans l’admin ;
18. approbation/rejet fonctionnent ;
19. régénération fonctionne ;
20. le système démarre avec Docker Compose ;
21. les migrations fonctionnent sur une base vide ;
22. les tests passent ;
23. aucune clé n’est commise ;
24. une panne provider n’endommage pas les données ;
25. xG manquant ne bloque pas le pipeline.

---

# 56. Phases d’implémentation Codex

## Phase 0 — Bootstrap

Créer :

- monorepo ;
- Docker Compose ;
- FastAPI ;
- Next.js ;
- PostgreSQL ;
- migrations ;
- healthcheck ;
- tests de base.

**Stop condition :**

```text
docker compose up
```

lance l’ensemble correctement.

## Phase 1 — Domain + Team Profiles

Créer :

- modèles DB ;
- TeamProfile ;
- Rivalry ;
- Competition ;
- Fixture ;
- CRUD admin ;
- seed Barcelona.

**Stop condition :**

on peut créer Madrid depuis l’interface sans modifier le code.

## Phase 2 — Football Provider

Créer :

- interface `FootballDataProvider` ;
- `SportmonksProvider` ;
- mapping statuts ;
- sync calendrier ;
- cache/raw payload ;
- tests avec fixtures locales.

**Stop condition :**

un profil peut récupérer ses matchs et les afficher.

## Phase 3 — Scheduler

Créer :

- worker ;
- `generation_jobs` ;
- sync périodique ;
- planification PRE ;
- détection FINISHED ;
- planification POST ;
- idempotence.

**Stop condition :**

un match futur crée automatiquement les bons jobs.

## Phase 4 — Stats & History

Créer :

- normalisation team stats ;
- player stats ;
- xG optionnel ;
- historiques ;
- baselines.

**Stop condition :**

l’admin affiche la valeur actuelle et plusieurs baselines.

## Phase 5 — Analytics Engine

Créer :

- Metric Registry ;
- anomaly scoring ;
- confidence ;
- context ;
- novelty ;
- compound rules ;
- InsightRanker.

**Stop condition :**

un match peut produire 2–3 insights traçables sans LLM.

## Phase 6 — Character/Narrative/Duration

Créer :

- CharacterContext ;
- rivalry boost ;
- EmotionEngine ;
- NarrativeAngleEngine ;
- DurationEngine.

**Stop condition :**

un match produit un package interne complet prêt pour le scénariste.

## Phase 7 — LLM

Créer :

- interface `LLMProvider` ;
- OpenAI adapter ;
- prompts versionnés ;
- structured response ;
- Script Engine ;
- hooks ;
- Content Pack ;
- validation.

**Stop condition :**

le Barça génère un Content Pack en espagnol avec preuves.

## Phase 8 — Review UI

Créer :

- queue `NEEDS_REVIEW` ;
- détail contenu ;
- evidence viewer ;
- approve ;
- reject ;
- edit ;
- regenerate.

## Phase 9 — Performance preparation

Créer :

- table performance ;
- saisie manuelle ;
- tags éditoriaux.

Pas de machine learning.

## Phase 10 — Hardening

- tests ;
- logs ;
- retries ;
- erreurs ;
- documentation ;
- backup ;
- seed ;
- `.env.example`.

---

# 57. Règles spécifiques pour Codex

Codex doit respecter les règles suivantes.

## Règle 1

Ne pas développer toutes les fonctionnalités dans un seul fichier.

## Règle 2

Ne pas intégrer de logique spécifique au Barça dans `AnalyticsEngine`.

## Règle 3

Le profil Barça est une donnée de configuration.

## Règle 4

Ne pas appeler Sportmonks hors du provider adapter.

## Règle 5

Ne pas appeler OpenAI hors du LLM adapter.

## Règle 6

Ne pas utiliser le LLM pour calculer une statistique.

## Règle 7

Toute migration DB doit être versionnée.

## Règle 8

Tout comportement critique doit avoir un test.

## Règle 9

Ne pas ajouter Redis/Celery “par précaution”.

## Règle 10

Ne pas ajouter de microservices inutiles.

## Règle 11

Préférer code explicite et simple à une abstraction prématurée.

## Règle 12

Avant chaque phase :

1. lire le cahier des charges ;
2. inspecter le code existant ;
3. proposer le petit plan de changement ;
4. implémenter ;
5. exécuter tests/lint ;
6. corriger ;
7. documenter ;
8. seulement ensuite passer à la phase suivante.

---

# 58. Definition of Done par fonctionnalité

Une fonctionnalité n’est pas terminée si elle est seulement visible dans l’UI.

Elle doit avoir :

```text
DB/migration si nécessaire
domain model
service
API
validation
permissions
UI si nécessaire
tests
error handling
documentation minimale
```

---

# 59. Exemple de parcours complet

## J-1

Le worker synchronise le Barça.

Il trouve :

```text
Barcelona vs Opponent
kickoff = dimanche 21:00
```

Il crée :

```text
PRE_MATCH scheduled_for = dimanche 15:00
```

## Dimanche 15:00

Le worker prend le job.

Il récupère :

- historique Barça ;
- historique adversaire ;
- statistiques joueurs ;
- xG si disponible.

`BaselineEngine` calcule les références.

`AnalyticsEngine` produit par exemple 12 candidats.

`InsightRanker` en garde 3.

`EmotionEngine` détermine le ton.

`NarrativeAngleEngine` sélectionne l’angle.

`DurationEngine` choisit 45 s.

Le LLM produit le Content Pack espagnol.

Le Validator confirme les preuves.

Le contenu passe :

```text
NEEDS_REVIEW
```

## Après le match

Le provider passe le match à `FINISHED`.

Le système attend 10 minutes.

Il refresh les données.

Il produit le POST_MATCH de la même manière.

---

# 60. Exemple de payload envoyé au LLM

```json
{
  "task": "POST_MATCH_SCRIPT",
  "language": "es",
  "target_duration_seconds": 45,
  "target_word_count": 113,
  "character": {
    "identity": "Aficionado catalán nativo del FC Barcelona",
    "tone": "muy emocional pero analíticamente riguroso",
    "humor": 55,
    "provocation": 70
  },
  "match": {
    "team": "FC Barcelona",
    "opponent": "Example Opponent",
    "result": "..."
  },
  "emotion": {
    "primary": "frustrated",
    "secondary": "analytical",
    "intensity": 82
  },
  "narrative_angle": "SCORE_DOES_NOT_TELL_STORY",
  "insights": [
    {
      "id": "INS-1",
      "claim": "...",
      "evidence_ids": ["EV-1", "EV-2"]
    }
  ],
  "evidence": [
    {
      "id": "EV-1",
      "metric": "xg",
      "value": 1.08
    }
  ],
  "constraints": {
    "no_new_numbers": true,
    "no_unverified_facts": true,
    "hook_immediately": true
  }
}
```

---

# 61. Exemple de réponse structurée attendue du LLM

```json
{
  "hooks": [
    {
      "type": "curiosity",
      "text": "..."
    },
    {
      "type": "emotion",
      "text": "..."
    },
    {
      "type": "contrarian",
      "text": "..."
    }
  ],
  "recommended_hook_index": 1,
  "title": "...",
  "first_screen_text": "...",
  "script": "...",
  "segments": [
    {
      "purpose": "hook",
      "text": "..."
    }
  ],
  "caption": "...",
  "comment_question": "...",
  "hashtags": []
}
```

Le backend calcule lui-même les timestamps approximatifs des segments à partir du nombre de mots.

---

# 62. Qualité éditoriale

Le contenu recherché doit être :

```text
fan-first
data-backed
rapide
compréhensible
émotionnel
non corporatif
non générique
```

Éviter :

```text
Selon les statistiques...
Il est important de noter que...
En conclusion...
```

Préférer un langage oral naturel correspondant au personnage.

Le système doit toutefois éviter la vulgarité excessive, les insultes personnelles et les accusations non vérifiées.

---

# 63. Évolution future vers d’autres équipes

Création du profil Madrid :

```text
Create Team
↓
provider team id
↓
language = es
↓
culture = Madrid/Spain
↓
character = configurable
↓
rivalries
↓
activate
```

Aucun changement de code nécessaire.

Création de Liverpool :

```text
language = en
locale = en-GB
```

Le même moteur analytique continue de fonctionner.

---

# 64. Future évolution data premium

L’architecture doit permettre ultérieurement de rajouter des codes métriques comme :

```text
distance_covered
sprints
pressures
high_intensity_runs
progressive_passes
line_breaking_passes
field_tilt
ppda
average_position
zone_entries
```

sans modifier le Content Pack ou le Script Engine.

Seuls doivent changer :

```text
provider mapping
metric registry
analytics rules
```

---

# 65. Future publication sociale

Prévoir conceptuellement :

```python
class SocialPublisher(Protocol):
    async def publish(self, content, media): ...
```

Mais ne pas l’implémenter en V1.

---

# 66. Future boucle d’apprentissage éditorial

Quand suffisamment de données de performance seront disponibles :

```text
Content Pack
    ↓
Published Content
    ↓
Performance Metrics
    ↓
Editorial Performance Model
    ↓
Hook/Duration/Angle recommendations
```

Cette évolution doit être séparée du moteur de vérité statistique.

Une mauvaise performance vidéo ne doit jamais modifier les faits.

Elle peut seulement influencer :

```text
narrative angle
hook style
duration
pacing
```

---

# 67. Priorité produit

Ordre des priorités :

```text
1. Exactitude des données
2. Traçabilité
3. Multi-équipe
4. Qualité des insights
5. Qualité du personnage
6. Vitesse de génération
7. Optimisation éditoriale
8. Automatisation de publication
```

Ne jamais sacrifier les points 1–4 pour le point 7.

---

# 68. Décisions techniques finales V1

```text
Backend                 Python + FastAPI
Frontend                Next.js + TypeScript
Database                PostgreSQL
ORM                     SQLAlchemy
Migrations              Alembic
Worker                   Python séparé
Queue externe            Non
Redis                    Non
Football provider        Sportmonks adapter
LLM                      OpenAI adapter
Validation               Humaine par défaut
Pre-match                Oui
Post-match               Oui
Live                     Non
Publication sociale      Non
Multi-team               Oui dès V1
Multi-language           Oui via TeamProfile
Barcelona language       Espagnol
Barcelona identity       Supporter catalan natif
Prediction               Qualitative uniquement par défaut
Video generation         Non
```

---

# 69. Résultat attendu du MVP

À la fin de la V1, l’administrateur doit pouvoir :

1. ouvrir l’interface ;
2. voir FC Barcelona ;
3. voir le prochain match ;
4. voir quand le PRE_MATCH sera généré ;
5. récupérer automatiquement un script espagnol ;
6. voir les statistiques exactes utilisées ;
7. comprendre pourquoi chaque insight a été choisi ;
8. approuver ou modifier le script ;
9. attendre la fin du match ;
10. recevoir automatiquement un POST_MATCH ;
11. créer un profil Real Madrid ;
12. le configurer différemment ;
13. activer Madrid ;
14. obtenir ensuite les mêmes workflows sans modifier le moteur.

C’est la définition fonctionnelle fondamentale du produit.

---

# 70. Instruction maître à Codex

> Construis ce produit par phases, en privilégiant simplicité, testabilité et séparation claire des responsabilités. Ne transforme pas le MVP en infrastructure distribuée. Le cœur de la valeur est le moteur qui convertit les données football en insights factuels, puis les insights en narration adaptée à un personnage. Le LLM ne doit jamais être la source de vérité statistique. Toute équipe doit être une configuration et non une branche de code. À chaque phase, exécute les tests et assure-toi que les critères d’acceptation correspondants sont satisfaits avant de continuer.
