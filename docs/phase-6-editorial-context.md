# Phase 6 — Character, Narrative & Duration

## Livré

- `CharacterEngine` construit un `CharacterContext` depuis le `TeamProfile` : langue, locale, identité, contexte culturel, règles éditoriales et niveaux de ton. Aucune identité d’équipe n’est codée dans le moteur.
- Le profil Barça existant fournit donc naturellement `es` / `es-ES` et l’identité de supporter catalan natif ; le script restera en espagnol, conformément à sa configuration.
- `EmotionEngine` applique des règles explicites à partir du résultat, des insights sélectionnés, de la rivalité et du niveau émotionnel du profil. Une victoire flatteuse devient ainsi `relieved / critical`, sans aléa ni donnée inventée.
- `NarrativeAngleEngine` sélectionne un angle transparent : Scoreline Truth Check, spotlight joueur, avertissement tactique, rivalité, positif/négatif inattendu ou `STRAIGHT_ANALYSIS` quand aucun twist n’est justifié.
- `DurationEngine` supporte les modes `AUTO`, `30`, `45`, `60`, `90` et un forçage profil. Il calcule les mots avec un arrondi demi-supérieur (45 s à 150 mots/minute = 113 mots) et une tolérance de ±8 %.
- `EditorialContextService` assemble un package interne prêt pour le futur scénariste : match, insights sélectionnés et leurs preuves, personnage, émotion, angle, durée et état de préparation.
- Endpoint `POST /fixtures/{id}/editorial-context?team_id=...` et aperçu dans l’admin.

## Décisions

Ce package n’est pas un `ContentPack` et ne persiste pas de texte généré. La Phase 7 l’utilise comme unique contexte d’entrée du Script Engine : seuls les insights sélectionnés et leurs preuves sont transmis au LLM.

Les moteurs éditoriaux ne modifient aucune statistique et ne formulent aucune affirmation sportive. Ils déterminent uniquement la présentation, le ton et la longueur à partir de données déjà vérifiées.

## Vérifications exécutées

- Tests de localisation/personnage, boost de rivalité, émotion victoire flatteuse, angle sans twist, modes de durée, arrondi à 113 mots, tolérance ±8 % et endpoint de package.
- Lint/type-check API et tests du projet complet.

Le test Docker Compose reste différé : Docker CLI n’est pas disponible dans l’environnement courant.
