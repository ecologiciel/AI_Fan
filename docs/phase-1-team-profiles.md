# Phase 1 — Domain + Team Profiles

## Livré

- Migration `0002_team_profiles` pour les profils, rivalités, compétitions, fixtures et leurs tables de liaison.
- Modèles SQLAlchemy et contraintes PostgreSQL : identifiants UUID, données configurables JSONB, unicité des slugs et des identifiants externes par provider, bornes 0–100 pour les niveaux éditoriaux.
- API `/api/v1/teams` : liste, création, lecture, modification, activation, désactivation, duplication et CRUD des rivalités.
- Versionnement : chaque modification de profil ou de rivalité incrémente `profile_version`.
- Seed idempotent de FC Barcelona : langue `es`, locale `es-ES`, identité de supporter catalan natif et rivalité El Clásico. Son `external_team_id` est lu depuis `BARCELONA_EXTERNAL_TEAM_ID` et n'est pas supposé par le code.
- Interface d'administration minimaliste : consultation des profils et création d'une seconde équipe, dont Real Madrid, via le backend.
- CORS limité à `WEB_URL` afin que l'interface web puisse joindre l'API sans ouvrir l'accès à toutes les origines.

## Décisions

Les fixtures sont persistables dès cette phase mais ne sont ni récupérées ni affichées : la synchronisation relève exclusivement de la Phase 2 et du provider `FootballDataProvider`.

L'API utilise SQLAlchemy synchrone avec PostgreSQL/psycopg. Cela garde le CRUD simple et permet des tests SQLite isolés ; les providers resteront asynchrones lorsque leurs appels HTTP seront introduits.

## Vérifications exécutées

- `alembic upgrade head --sql` : succès ; la migration génère les tables PostgreSQL et les champs JSONB attendus.
- `pytest` : 5 tests réussis à la clôture de la phase.
- `ruff` et `mypy` : succès pour l'API et le worker.
- `npm run lint`, `npm run type-check` et `npm run build` : succès pour le frontend.

La validation Docker Compose reste différée comme convenu, Docker CLI n'étant pas disponible dans cet environnement.
