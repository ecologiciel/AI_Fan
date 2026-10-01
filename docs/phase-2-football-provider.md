# Phase 2 — Football Provider

## Livré

- Contrat asynchrone `FootballDataProvider`, modèles normalisés et `ProviderCapabilities`.
- Adaptateur isolé `SportmonksProvider` pour l'API Football v3 : authentification par variable d'environnement, pagination, timeout, retry limité des erreurs réseau/429/5xx et mapping des payloads.
- Enum interne de statuts : `SCHEDULED`, `LIVE`, `HALF_TIME`, `FINISHED`, `POSTPONED`, `CANCELLED`, `ABANDONED`, `UNKNOWN`. Aucun service métier ne dépend d'un code Sportmonks.
- `MatchSyncService` : récupère J-7 à J+30, upsert les compétitions et fixtures, associe chaque fixture à l'équipe synchronisée, enregistre le payload brut et l'horodatage de synchronisation.
- API : `POST /api/v1/teams/{id}/sync`, `GET /api/v1/fixtures`, `GET /api/v1/fixtures/{id}` et `POST /api/v1/fixtures/{id}/refresh`.
- Admin : bouton de synchronisation par équipe configurée et liste des matchs mis en cache.
- Fixtures JSON synthétiques locales, dont match terminé, reporté et sans xG.

## Décisions

Le service de synchronisation dépend uniquement du registre de providers et de `FootballDataProvider`. Sportmonks n'est importé que par le registre/adapter, jamais par le service ou les routes métier.

L'absence de xG renvoie `None` : elle ne fait échouer ni l'adaptateur ni la synchronisation. La normalisation détaillée des statistiques sera volontairement traitée en Phase 4.

Un profil sans `external_team_id` retourne une synchronisation sans écriture et avec un avertissement explicite. Une panne ou une mauvaise configuration provider donne une erreur HTTP 502, sans altérer les fixtures déjà stockées.

## Configuration

Renseignez dans `.env` :

```env
SPORTMONKS_API_TOKEN=
SPORTMONKS_BASE_URL=https://api.sportmonks.com/v3/football
```

Puis définissez l'identifiant externe de l'équipe dans son profil. FC Barcelona le lit aussi depuis `BARCELONA_EXTERNAL_TEAM_ID` lors du premier seed.

## Vérifications exécutées

- `pytest` : 20 tests réussis.
- `ruff` et `mypy` : succès pour l'API et le worker.
- `npm run lint`, `npm run type-check` et `npm run build` : succès pour le frontend.
- Les tests provider utilisent exclusivement `httpx.MockTransport` et les JSON locaux ; aucune clé ni requête réelle n'est requise.

Le test Docker Compose reste différé, conformément à la décision précédente.
