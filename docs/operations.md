# Exploitation V1

## Configuration et démarrage

Copier `.env.example` vers `.env`, puis définir au minimum `APP_SECRET_KEY` (32 caractères ou plus) et `ADMIN_PASSWORD`. Les jetons Sportmonks et OpenAI restent vides tant que les intégrations ne sont pas utilisées. Les clés ne sont jamais exposées au navigateur : Docker les fournit seulement à l’API et au worker.

La validation du démarrage de Compose nécessite Docker Desktop ou le Docker CLI. Si `docker compose version` n’est pas disponible, installer/démarrer Docker avant d’exécuter les commandes suivantes.

En production, `APP_ENV=production` (ou `staging`) refuse le secret et le mot de passe d’administration de démonstration au démarrage. Les valeurs de `.env.example` sont volontairement vides et ne constituent pas des secrets réutilisables.

```powershell
Copy-Item .env.example .env
docker compose up --build
```

## Déploiement VPS Hostinger

Le fichier `docker-compose.production.yml` isole PostgreSQL du réseau public et place le frontend ainsi que l’API derrière Caddy. Le navigateur communique avec l’API via `/api/v1`, sur le même domaine HTTPS ; les cookies de revue restent donc sécurisés.

1. Créer un enregistrement DNS `A` pour le sous-domaine retenu vers l’IPv4 du VPS.
2. Sur le VPS, copier `deploy/.env.production.example` vers `deploy/.env.production` et renseigner chaque secret. `APP_SECRET_KEY` et `POSTGRES_PASSWORD` doivent être générés avec `openssl rand -hex 32` ; ce format évite les problèmes d’encodage dans l’URL PostgreSQL.
3. Depuis la racine du dépôt sur le VPS, lancer :

```bash
docker compose --env-file deploy/.env.production -f docker-compose.production.yml up --build -d
```

Caddy obtient et renouvelle le certificat TLS automatiquement après propagation DNS. Ne pas exposer les ports 3000, 8000 ou 5432 : seuls 80 et 443 sont publiés.

### VPS déjà équipé de Nginx

Si le VPS héberge déjà un site sur 80/443, utiliser `docker-compose.hostinger-path.yml` au lieu de Caddy. Les conteneurs Football AI sont alors liés uniquement à `127.0.0.1:13000` et `127.0.0.1:18000`, leurs noms de volume sont spécifiques, et `deploy/nginx-football-ai.conf` publie l’application sous `/football-ai/` dans le serveur TLS Nginx existant. Cette option ne touche pas aux conteneurs existants ni à leurs ports.

Définir `VPS_HOSTNAME` dans `deploy/.env.production`, puis démarrer avec :

```bash
docker compose --env-file deploy/.env.production -f docker-compose.hostinger-path.yml up --build -d
```

Pour l'instance Hostinger `srv1610573.hstgr.cloud`, la valeur publique est `VPS_HOSTNAME=srv1610573.hstgr.cloud` et l'application est publiée sous `https://srv1610573.hstgr.cloud/football-ai/`. La configuration de production requiert également `BARCELONA_EXTERNAL_TEAM_ID` : il s'agit de l'identifiant d'équipe fourni par Sportmonks, utilisé uniquement comme seed du profil multi-équipe FC Barcelona. Il ne doit jamais être remplacé par une statistique ou un identifiant inventé.

Le déploiement sur ce VPS se fait sous le nom Compose `football-ai`, avec des ports exclusivement locaux :

```bash
docker compose --project-name football-ai \
  --env-file deploy/.env.production \
  -f docker-compose.hostinger-path.yml up --build -d
```

Conserver `deploy/nginx-football-ai.conf` dans `/etc/nginx/snippets/football-ai.conf`, puis l'inclure dans le bloc TLS existant de `srv1610573.hstgr.cloud`. Après chaque modification Nginx, exécuter `nginx -t` avant `systemctl reload nginx`. Le snippet ne doit pas modifier le proxy Meteorite existant sur `127.0.0.1:8000`.

Vérification sur le VPS :

```bash
docker compose --project-name football-ai \
  --env-file deploy/.env.production \
  -f docker-compose.hostinger-path.yml ps
curl --fail http://127.0.0.1:18000/api/v1/health
curl --fail https://srv1610573.hstgr.cloud/football-ai/api/v1/health
```

Retour arrière Football AI uniquement : retirer l'include Nginx, valider puis recharger Nginx, puis lancer `docker compose --project-name football-ai --env-file deploy/.env.production -f docker-compose.hostinger-path.yml down`. Ne pas ajouter `--volumes` : le volume PostgreSQL demeure disponible pour une reprise.

Les migrations et le seed idempotent sont exécutés par le conteneur API. Le seed crée le registre de métriques, l’administrateur et FC Barcelona uniquement lorsqu’ils sont absents ; Barcelona reste un `TeamProfile` configurable, pas une branche de code.

`GET /api/v1/health` est une sonde de vie sans dépendance externe. `GET /api/v1/health/providers` expose seulement la configuration et les capacités déclarées des providers, sans appeler Sportmonks ni OpenAI.

## Jobs, erreurs et logs

Les jobs automatiques sont persistés dans PostgreSQL et revendiqués avec verrouillage de ligne. Une erreur du provider ou du LLM reprogramme le même job avec un backoff exponentiel, limité par `max_attempts`; l’identifiant et la clé d’idempotence ne changent jamais. Après la dernière tentative, le job passe à `FAILED`; un administrateur peut le relancer, ce qui remet son compteur à zéro. Pour un POST_MATCH sans statistique d’équipe après le rafraîchissement, le worker replanifie exactement une fois à +10 minutes ; la seconde exécution conserve la dégradation contrôlée (pack avec avertissement) au lieu de bloquer le pipeline.

Les processus API et worker écrivent des événements JSON. Les fins de jobs comportent `job_id`, `team_profile_id`, `fixture_id`, `content_type`, `provider`, `duration_ms` et `status`. Les messages masquent les formes usuelles de jetons API. Aucun log ne doit être traité comme une source de vérité métier : PostgreSQL l’est.

## Sauvegarde PostgreSQL

Effectuer une sauvegarde régulière, hors du conteneur de base :

```powershell
docker compose exec -T postgres pg_dump -U football_ai -Fc football_ai > football_ai_2026-09-25.dump
```

Pour restaurer sur une base explicitement préparée et arrêtée côté API/worker :

```powershell
Get-Content football_ai_2026-09-25.dump -AsByteStream |
  docker compose exec -T postgres pg_restore -U football_ai -d football_ai --clean --if-exists
```

Tester périodiquement la restauration sur une instance non productive. La restauration remplace les données de la base cible : ne jamais l’exécuter contre une production sans sauvegarde vérifiée et fenêtre de maintenance.
