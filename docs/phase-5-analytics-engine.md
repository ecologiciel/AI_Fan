# Phase 5 — Analytics Engine

## Livré

- Migration `0005_analytics_engine` avec `metric_definitions` et `insight_candidates` en PostgreSQL.
- Registre central, seedé et modifiable en base, des métriques équipe/joueur : unités, poids, seuil d’anomalie, plancher numérique et taille minimale d’échantillon.
- `AnalyticsEngine` déterministe : valeur actuelle, baseline pertinente, différence absolue/relative, score de déviation, confiance, contexte, nouveauté et score final sont tous calculés en Python.
- Sélection de baseline contextualisée : domicile/extérieur en priorité, puis forme récente, saison et compétition ; les échantillons sous le minimum sont explicitement exclus.
- Candidats persistés et idempotents par match, équipe, type de contenu et clé de calcul. Un métrique absent crée un candidat non éligible avec `MISSING_METRIC` au lieu de casser le pipeline.
- Règles composées factuelles : `FLATTERING_WIN`, `UNLUCKY_DEFEAT`, `DOMINANT_WIN`, `POSSESSION_WITHOUT_THREAT` et `LOW_POSSESSION_HIGH_THREAT` lorsque toutes les preuves requises existent.
- Règle `PLAYER_OUTLIER` sur la base de `LAST_5_PER_90` et `SEASON_PER_90`. Les apparitions de moins de 20 minutes sont rejetées explicitement, sans comparaison naïve.
- `InsightRanker` sélectionne au plus trois candidats éligibles, de confiance suffisante, avec diversité de type et de métrique.
- Endpoints : `GET /fixtures/{id}/insights?team_id=...` et `POST /fixtures/{id}/recalculate-insights?team_id=...`. L’admin affiche les candidats, scores, motifs d’exclusion et sélection.

## Décisions

Une `claim` de candidat est une phrase technique interne, entièrement dérivée de sa preuve et de sa baseline. Elle n’est pas une formulation éditoriale : le Script Engine de la Phase 7 recevra uniquement ces candidats sélectionnés et leurs preuves.

Les poids de la formule sont centralisés dans `app/analytics/config.py`; les paramètres propres aux métriques sont dans le registre DB. Aucun calcul n’utilise le LLM, Sportmonks ou une règle spécifique au Barça.

## Vérifications exécutées

- Tests d’anomalie, de sélection de baseline domicile, de données manquantes, de Scoreline Truth Check, de classement diversifié, de normalisation joueur par 90 et des endpoints analytics.
- Lint/type-check API et génération SQL Alembic jusqu’à `0005_analytics_engine`.

Le test Docker Compose reste différé : Docker CLI n’est pas disponible dans l’environnement courant.
