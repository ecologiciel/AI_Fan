# Phase 0 — Bootstrap

## Livré

- Monorepo avec `apps/api`, `apps/worker` et `apps/web`.
- FastAPI exposant `GET /api/v1/health`.
- Next.js avec une page d'accueil minimale.
- PostgreSQL, API, worker et frontend déclarés dans Docker Compose.
- Alembic initialisé avec une révision de bootstrap sans schéma métier.
- Worker séparé, volontairement passif jusqu'à la Phase 3 où les jobs persistés seront ajoutés.
- Test API, lint Python, type-check Python et contrôles frontend configurés.

## Décisions

Le schéma de domaine n'était pas anticipé dans cette phase : les tables de profils, rivalités, compétitions et fixtures ont ensuite été ajoutées par la migration versionnée de Phase 1. Ainsi, FC Barcelona n'est jamais devenu une constante technique avant l'existence de `TeamProfile`.

Le healthcheck API est un test de vivacité sans dépendance externe afin que l'orchestration distingue un processus démarré d'un incident PostgreSQL. Les futurs endpoints de readiness/provider seront ajoutés avec leurs services respectifs.

## Limite de vérification

L'environnement courant ne dispose pas de Docker CLI ; la commande `docker compose up --build` est documentée et sa validation finale doit être exécutée sur une machine avec Docker installé.

## Vérifications exécutées

- `alembic upgrade head --sql` : succès, avec création attendue de la table Alembic uniquement.
- `pytest` : 1 test réussi.
- `ruff` et `mypy` : succès pour l'API et le worker.
- `npm run lint`, `npm run type-check` et `npm run build` : succès pour le frontend.
