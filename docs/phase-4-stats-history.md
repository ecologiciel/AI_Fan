# Phase 4 — Stats & History

## Livré

- Migration `0004_statistics_history` et tables PostgreSQL `team_match_stats`, `player_match_stats`, `match_events` et `baselines`.
- `StatisticsService` normalise une liste contrôlée de métriques équipe/joueur (buts, xG, tirs, possession, passes, cartons, minutes, etc.) depuis le contrat `FootballDataProvider`. Les payloads Sportmonks ne remontent jamais au moteur métier.
- Les données xG, lineups et événements sont facultatives : une indisponibilité est enregistrée comme avertissement et les données disponibles sont tout de même persistées.
- Upserts idempotents par match, entité, métrique et période. La valeur reste accompagnée de sa source et de son niveau de confiance.
- `BaselineService` calcule des agrégats déterministes uniquement sur les matchs `FINISHED` précédant le match cible : `LAST_5`, `LAST_10`, `SEASON`, `HOME_LAST_5`, `AWAY_LAST_5` et `COMPETITION_LAST_5`.
- Endpoints admin : `POST /fixtures/{id}/stats/refresh`, `GET /fixtures/{id}/stats` et `GET /fixtures/{id}/baselines?team_id=...`.
- L’admin permet d’ouvrir un match, de rafraîchir les statistiques fournisseur et d’afficher valeur courante + baselines. Le worker normalise les statistiques des matchs terminés déjà synchronisés.

## Décisions

Les baselines sont calculées avant le match cible : elles ne peuvent donc pas inclure le match analysé ni produire une fuite de données. Les statistiques joueurs conservent les minutes jouées ; toute normalisation par 90 minutes sera dérivée par l’Analytics Engine, jamais approximée à partir d’une simple apparition.

Un `context_key` complète la table de baselines afin de conserver l’instant et le match de référence utilisés pour le calcul. Cela rend le résultat affiché ré-auditable sans confondre deux demandes de baseline pour une même équipe.

## Vérifications exécutées

- Tests ciblés du stockage normalisé, de l’xG disponible, des données joueur et des fenêtres historiques déterministes.
- `ruff` et `mypy` pour l’API et le worker.
- Génération SQL Alembic jusqu’à `0004_statistics_history`.

Le test Docker Compose reste différé : Docker CLI n’est pas installé dans cet environnement.
