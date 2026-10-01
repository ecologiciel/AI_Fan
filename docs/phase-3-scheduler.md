# Phase 3 — Scheduler

## Livré

- Table `generation_jobs` et migration `0003_generation_jobs`, avec clé d'idempotence unique, statut, dates d'exécution, tentatives, erreur et payload persistant.
- `SchedulerService` : création des jobs PRE_MATCH à `kickoff - prematch_offset_minutes`, jobs POST_MATCH après détection de `FINISHED` puis délai profil, replanification sur changement de kickoff et annulation lorsque le match/profil n'est plus éligible.
- Clé automatique stable : `{team_profile_id}:{fixture_id}:{content_type}:v{profile_version}`. Une nouvelle version de profil annule le job `PENDING` obsolète et crée le nouveau job.
- Réservation atomique des jobs dus au moyen de `FOR UPDATE SKIP LOCKED`, avec incrément de tentative avant exécution. Deux dispatchs ne peuvent pas exécuter le même job déjà réservé.
- Worker Python distinct : synchronisation des équipes actives toutes les 6 heures par défaut, dispatch toutes les 60 secondes ; ces valeurs sont configurables par environnement.
- Endpoints `GET /api/v1/jobs` et `POST /api/v1/jobs/{id}/retry`, ainsi qu'une liste des jobs dans l'admin.

## Décisions

Le scheduler exécute un contrat `GenerationJobExecutor`. Le véritable exécuteur sera branché au Script Engine en Phase 7. Avant cela, le worker marque explicitement un job dû `SKIPPED` avec son motif, plutôt que de simuler une génération ou de dupliquer des contenus.

La planification POST_MATCH utilise le premier job créé après que le provider a signalé `FINISHED`. Les refresh ultérieurs ne repoussent pas un job `PENDING`, ce qui évite de différer indéfiniment la génération finale.

## Vérifications exécutées

- `pytest` : 26 tests réussis, incluant idempotence, report, finalisation, versionnement, dispatch double et API de retry.
- `ruff` et `mypy` : succès pour l'API et le worker.
- `npm run lint`, `npm run type-check` et `npm run build` : succès pour le frontend.

Le test Docker Compose reste différé, Docker CLI n'étant pas disponible dans l'environnement courant.
