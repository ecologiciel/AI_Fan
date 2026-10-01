# Football AI Fan Intelligence Platform

Plateforme multi-équipe de génération de contenu football factuel. Le développement suit les phases du cahier des charges et s'arrête à la fin de chaque phase validée.

## État d'avancement

- [x] Phase 0 — Bootstrap
- [x] Phase 1 — Domain + Team Profiles
- [x] Phase 2 — Football Provider
- [x] Phase 3 — Scheduler
- [x] Phase 4 — Stats & History
- [x] Phase 5 — Analytics Engine
- [x] Phase 6 — Character/Narrative/Duration
- [x] Phase 7 — LLM
- [x] Phase 8 — Review UI
- [x] Phase 9 — Performance preparation
- [x] Phase 10 — Hardening

## Démarrage

1. Copiez `.env.example` vers `.env`, puis définissez `APP_SECRET_KEY` (32 caractères minimum) et `ADMIN_PASSWORD`.
2. Lancez `docker compose up --build`.
3. Ouvrez `http://localhost:3000` et `http://localhost:8000/api/v1/health`.

Les migrations Alembic sont appliquées au démarrage de l'API. La migration de bootstrap est volontairement vide : le premier schéma métier sera ajouté en Phase 1.

> Vérification locale : les tests, lint, type-check, build frontend et génération SQL des migrations ont été validés. Le démarrage réel de Docker Compose reste à exécuter sur une machine disposant de Docker Desktop/CLI ; l’exécutable Docker n’est pas installé dans cet environnement.

## Vérifications locales

```powershell
python -m pip install -r apps/api/requirements-dev.txt
cd apps/api; python -m pytest tests; python -m ruff check app tests; python -m mypy app; cd ../..
python -m ruff check apps/worker
$env:MYPYPATH = "$PWD/apps/api"; python -m mypy apps/worker/worker

cd apps/web
npm ci
npm run lint
npm run type-check
npm run build
```

Voir la documentation de [bootstrap](docs/phase-0-bootstrap.md), des [profils équipes](docs/phase-1-team-profiles.md), du [provider football](docs/phase-2-football-provider.md), du [scheduler](docs/phase-3-scheduler.md), des [statistiques et baselines](docs/phase-4-stats-history.md), du [moteur analytique](docs/phase-5-analytics-engine.md), du [contexte éditorial](docs/phase-6-editorial-context.md), du [Script Engine](docs/phase-7-llm.md), de la [revue humaine](docs/phase-8-review-ui.md) et des [performances](docs/phase-9-performance.md).

La [documentation d’exploitation](docs/operations.md) décrit les variables d’environnement, les healthchecks, les retries persistants, les logs JSON et la procédure de sauvegarde/restauration PostgreSQL.
