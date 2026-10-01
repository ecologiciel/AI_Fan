# Phase 9 — Préparation des performances de contenu

La V1 conserve des mesures de performance sans en déduire de recommandation et sans modifier les faits football. Aucun modèle d’apprentissage, appel LLM, publication sociale ou collecte automatique n’est ajouté.

## Données persistées

La migration `0008_content_performance` ajoute :

- `content_performance`, une série de snapshots par Content Pack, plateforme et instant de mesure ;
- `editorial_tags` sur chaque Content Pack.

Les snapshots peuvent conserver les vues, vues engagées, durée ou pourcentage de visionnage, likes, commentaires, partages, sauvegardes et abonnés gagnés. Les valeurs négatives et les pourcentages hors 0–100 sont refusés. La V1 accepte exclusivement `source=manual`.

Les tags sont capturés au moment de la génération : type de hook retenu, angle narratif, types d’insights, durée, intensité émotionnelle, intensité de rivalité et joueurs mis en avant. Ils sont conservés comme contexte historique et ne sont jamais utilisés comme preuve analytique ni transmis pour modifier des statistiques.

## API et interface

Les endpoints authentifiés sont :

- `POST /api/v1/contents/{id}/performance`
- `GET /api/v1/contents/{id}/performance`

La fiche de revue permet une saisie manuelle et affiche l’historique des snapshots, ainsi que les tags enregistrés. Les mesures sont append-only pour permettre des comparaisons futures entre instants de mesure.

Les tests couvrent la persistance, la normalisation de plateforme, l’ordre de lecture et le refus d’un Content Pack inexistant.
