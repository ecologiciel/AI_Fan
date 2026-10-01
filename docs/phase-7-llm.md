# Phase 7 — LLM, Script Engine et Content Packs

La Phase 7 transforme exclusivement un `EditorialPackage` déterministe en contenu court. Elle ne donne jamais au modèle la base brute de statistiques.

## Frontière fournisseur

`LLMProvider` est le contrat utilisé par le reste de l’application. L’unique intégration OpenAI est `app/providers/llm/openai/provider.py`, qui utilise la réponse structurée Pydantic du SDK officiel. `OPENAI_API_KEY` et `LLM_MODEL` sont lus côté serveur ; le nom de modèle n’est pas codé en dur. Une configuration absente renvoie une erreur contrôlée à la génération, sans exposer de secret.

## Génération vérifiable

`ContentPackService` fabrique un manifeste de preuves à partir des insights sélectionnés et le transmet avec le contexte match, personnage, émotion, angle, durée et résumé anti-répétition des dix derniers contenus. Les templates immuables sont versionnés : `prematch_script_v1`, `postmatch_script_v1`, `hook_v1` et `fact_repair_v1`. Le `prompt_version` effectif, le provider, le modèle, la réponse originale, les hooks, segments, preuves et contrôles qualité sont enregistrés dans PostgreSQL (`content_packs`, migration `0006_content_packs`).

Le validateur déterministe vérifie langue, longueur à ±8 %, trois hooks de catégories différentes, références de preuve, entités déclarées et chaque nombre utilisé. Un seul appel de réparation est permis. Si la seconde version reste invalide, le pack est tout de même conservé en `NEEDS_REVIEW` avec `quality_warning=true`; aucune publication automatique n’est possible. En cas d’insights absents, un pack avec avertissement est créé sans appeler le LLM afin que des données manquantes ne fassent pas échouer le pipeline.

## Utilisation

- `POST /api/v1/fixtures/{fixture_id}/generate/pre-match?team_id=...`
- `POST /api/v1/fixtures/{fixture_id}/generate/post-match?team_id=...`
- `GET /api/v1/contents` et `GET /api/v1/contents/{id}`

Le worker exécute désormais les jobs persistés via le même service ; l’unicité de `generation_job_id` garantit qu’un job automatique ne crée pas deux packs. La console affiche également les actions de génération et le résultat factuel minimal. La Phase 8 complète ce flux avec l’approbation, l’édition, la régénération et la queue de revue.

Les tests utilisent un faux fournisseur structuré : aucune clé ni appel OpenAI réel n’est nécessaire. Ils couvrent notamment le rejet d’un chiffre inventé, l’unique tentative de correction, un pack espagnol avec preuves et l’idempotence d’un job.
