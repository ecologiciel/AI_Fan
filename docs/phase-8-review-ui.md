# Phase 8 — Revue humaine et versions de contenu

La validation éditoriale est volontairement humaine par défaut. Les packs restent en `NEEDS_REVIEW` après génération, même quand les contrôles déterministes sont valides.

## Authentification administrateur

La migration `0007_review_and_auth` crée la table extensible `users`. Au seed, un compte administrateur est créé à partir de `ADMIN_EMAIL` et `ADMIN_PASSWORD`. Les mots de passe sont hachés avec `scrypt` et la connexion délivre un cookie signé HTTP-only (`football_ai_session` par défaut), à durée limitée. Les mutations et lectures de contenu exigent cette session ; les clés fournisseur ne passent jamais au navigateur.

## Cycle de revue

- `NEEDS_REVIEW` peut être approuvé ou rejeté par un administrateur.
- L’approbation conserve l’administrateur, l’horodatage et une note optionnelle.
- Le rejet exige un motif et conserve son auteur et son horodatage.
- Une édition manuelle crée un nouveau pack `NEEDS_REVIEW`, archive la version d’origine et conserve son payload LLM initial.
- Une régénération fait de même et laisse l’idempotence des jobs automatiques intacte.

Les éditions manuelles sont contrôlées contre le manifeste de preuves : un nombre absent de ce manifeste est refusé. Les versions archivées restent consultables par le filtre de statut.

## API et interface

Les endpoints suivants sont protégés par session :

- `GET /api/v1/contents`, `GET /api/v1/contents/{id}`
- `POST /api/v1/contents/{id}/approve`
- `POST /api/v1/contents/{id}/reject`
- `POST /api/v1/contents/{id}/regenerate`
- `PATCH /api/v1/contents/{id}`

L’écran d’administration propose la connexion, une queue filtrable, le détail du script, hooks, segments, contrôles qualité et preuves. Cliquer sur un insight isole ses preuves dans le manifeste. L’interface déclenche aussi les actions approuver, rejeter, régénérer et créer une révision éditée.

Les tests couvrent la session HTTP-only, les transitions de statut, l’audit de revue, l’immuabilité des révisions et le refus d’un chiffre non prouvé.
