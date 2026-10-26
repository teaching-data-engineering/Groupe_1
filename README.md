# Groupe_1 — Scraper Bandsintown

Collecte des concerts proposés par [Bandsintown](https://www.bandsintown.com) autour de Paris, transformation et enrichissement des données, prédiction de la popularité des événements, puis chargement dans BigQuery (GCP).

**écrire votre nom dans Membres**

**Membres :** Alexandre HAYOUN, Hoang , Soro , Mathis

## Sommaire

1. [Structure du repository](#structure-du-repository)
2. [Installation](#installation)
3. [Utilisation](#utilisation)
4. [Collecte des données](#collecte-des-données)
5. [Transformation et enrichissement](#transformation-et-enrichissement)
6. [Prédiction de la popularité](#prédiction-de-la-popularité)
7. [Tests](#tests)
8. [En cas d'erreur](#en-cas-derreur)

## Structure du repository

```
Groupe_1/
├── bandsintown_scraper/        module Python
│   ├── __init__.py
│   ├── config.py               toutes les constantes : API, en-têtes, délais, dossiers, réglages du modèle
│   ├── scraper.py              collecte des événements et sauvegarde des pages JSON brutes
│   ├── transform.py            nettoyage, enrichissement et géocodage → DataFrame pandas
│   └── model.py                prédiction de la popularité des événements
├── main.py                     point d'entrée en ligne de commande
├── tests/                      tests automatiques (pytest)
│   ├── test_model.py
│   └── test_transform.py
├── data/
│   ├── raw/                    pages brutes de l'API : page_001.json, page_002.json...
│   ├── cache/lieux.json        coordonnées GPS des salles déjà trouvées (Nominatim)
│   └── events_bandsintown.csv  résultat final : une ligne par événement
├── models/                     modèles entraînés (.joblib, ignorés par git) et leurs rapports (.json)
├── requirements.txt            dépendances du projet
└── requirements-dev.txt        dépendances pour les tests
```

Les pages brutes, le cache et le CSV sont versionnés : un membre du groupe qui fait `git pull` peut travailler sur les données sans refaire la collecte.

## Installation

Python 3.10 ou plus récent. Les dépendances s'installent dans un environnement virtuel `.venv`, propre au projet et ignoré par git. Toutes les commandes se lancent **depuis le dossier `Groupe_1`**.

```bash
python -m venv .venv                 # créer le .venv (une seule fois)
.venv\Scripts\activate               # l'activer : Windows (PowerShell), à chaque nouveau terminal
source .venv/bin/activate            #             Mac / Linux
pip install -r requirements.txt      # installer les dépendances (une seule fois)
pip install -r requirements-dev.txt  # en plus, pour lancer les tests
```

Quand le `.venv` est activé, `(.venv)` apparaît au début de la ligne du terminal. Dans VS Code : Ctrl+Shift+P → « Python: Select Interpreter » → choisir `.venv`. Les nouveaux terminaux l'activent alors automatiquement.

> Si PowerShell refuse l'activation (« l'exécution de scripts est désactivée »), lancer une fois `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, ou utiliser directement `.venv\Scripts\python.exe main.py ...`.

## Utilisation

| Commande | Ce qu'elle fait | Requêtes |
|---|---|---|
| `python main.py --end-date 2026-11-30` | collecte d'aujourd'hui au 30/11, puis reconstruit le CSV | Bandsintown |
| `python main.py --start-date 2026-11-01 --end-date 2026-11-15` | collecte une période précise | Bandsintown |
| `python main.py --skip-scraping` | reconstruit le CSV à partir des pages déjà collectées | aucune |
| `python main.py --skip-scraping --enrich-online` | ajoute les coordonnées GPS des salles manquantes | Nominatim |
| `python main.py --skip-scraping --train` | entraîne le modèle de popularité | aucune |
| `pytest` | lance les tests | aucune |
| `python main.py --help` | affiche toutes les options | aucune |

Le CSV `data/events_bandsintown.csv` est réécrit à chaque lancement de `main.py` : il faut le fermer s'il est ouvert dans Excel ou LibreOffice.

## Collecte des données

### La requête envoyée à Bandsintown

L'URL a été trouvée dans l'onglet *Network* des outils de développement du navigateur (F12), en faisant défiler la liste des concerts sur https://www.bandsintown.com/choose-dates/genre/all-genres : à chaque défilement, la page appelle cette API interne, qui renvoie du JSON.

```
GET https://www.bandsintown.com/choose-dates/fetch-next/upcomingEvents
```

| Paramètre | Exemple | Rôle |
|---|---|---|
| `date` | `2026-10-23T00:00:00,2026-11-30T23:00:00` | période : début et fin séparés par une virgule (`--start-date`, `--end-date`) |
| `page` | `1`, `2`, `3`… | numéro de la page (environ 36 événements par page), géré automatiquement |
| `latitude`, `longitude` | `48.85341`, `2.3488` | centre de la recherche : Paris (`PARIS_LATITUDE`, `PARIS_LONGITUDE`) |
| `genre_query` | `all-genres` | tous les genres musicaux (`GENRE_QUERY`) |

L'API renvoie les événements **autour** de ce point : on récupère donc aussi la banlieue (Montreuil, Pantin, Villepinte…).

Les en-têtes (`HEADERS` dans `config.py`) sont copiés depuis la requête du navigateur. `User-Agent`, `Accept`, `Accept-Encoding` et `Sec-Ch-Ua*` sont ajoutés par `curl_cffi` selon le navigateur imité :

```python
browser = random.choice(IMPERSONATE_BROWSERS)           # tiré au hasard une fois par collecte
with requests.Session(impersonate=browser) as session:  # garde les cookies d'une page à l'autre
    response = session.get(API_URL, headers=HEADERS, params=params)
```

### Fonctionnement

1. **Une page** (`scrap_one_page`) : une requête GET pour une période et un numéro de page.
2. **Plusieurs pages** (`scrap_multiple_pages`) : parcourt les pages d'une période et s'arrête sur :
   - une page vide : il n'y a plus de résultats ;
   - une page répétée : l'API renvoie en boucle une page déjà vue, sa limite est atteinte ;
   - la limite de 30 pages (`MAX_PAGE`).
3. **Toutes les périodes** (`scrap_all_events`) : l'API renvoie les événements triés par date, mais limite le nombre de pages par période. Quand une période est coupée, une nouvelle période démarre au jour du dernier événement reçu. Le nombre de périodes s'adapte donc tout seul au volume de données, que la date de fin soit fin novembre ou fin 2030.
4. **Sauvegarde** (`save_json`, `move_pages_to_raw_dir`) : chaque page est enregistrée dès sa réception, d'abord dans un dossier temporaire. Quand la collecte se termine sans erreur, les pages sont déplacées dans `data/raw/`, numérotées à la suite des pages existantes. **Si le site bloque en cours de route, `data/` n'est pas modifié.**

Chaque page garde la réponse brute de l'API, avec les informations de la collecte :

```json
{
  "collectedAt": "2026-10-23",
  "startDate": "2026-10-23",
  "endDate": "2026-11-30",
  "page": 1,
  "events": [
    {
      "id": 109045633,
      "artistName": "The Soul Rebels",
      "title": "NFL Experience Paris presented by Wilson",
      "venueName": "Champ de Mars",
      "locationText": "Paris, France",
      "startsAt": "2026-10-23T10:00:00",
      "endsAt": "2026-10-23T13:00:00",
      "rsvpCountInt": 4,
      "...": "..."
    }
  ]
}
```

`collectedAt` est stocké dans le fichier, car la date de modification d'un fichier change à chaque `git clone` ou `git pull`.

### Éviter le ban

- **curl_cffi** au lieu de `requests` : il imite l'empreinte TLS d'un vrai navigateur. `requests` est bloqué par Cloudflare (erreur 403).
- **User-Agent aléatoire** : une version de Chrome est tirée au hasard dans `IMPERSONATE_BROWSERS` à chaque collecte, puis gardée pendant toute la collecte, dans une session qui renvoie les cookies de Cloudflare. Changer de navigateur à chaque requête, sans cookies, était détecté comme un robot. Firefox n'est pas dans la liste : son imitation est bloquée par Cloudflare.
- **Pause aléatoire** entre deux pages (`MIN_DELAY_SECONDS` à `MAX_DELAY_SECONDS`).
- **Erreur 429** (trop de requêtes) : le scraper attend le délai indiqué par le serveur (`DEFAULT_RETRY_AFTER_SECONDS` par défaut), puis redemande la même page.
- **Pas de proxy** : le réseau de l'université ne le permet pas.
- **Une collecte, puis tout le travail hors ligne** : la transformation et le modèle utilisent les pages sauvegardées (`--skip-scraping`).

### Collecter par petits morceaux

Si le site bloque (erreurs `429` puis `416`), on découpe la collecte avec `--start-date` et on lance les morceaux à intervalle :

```bash
python main.py --start-date 2026-10-23 --end-date 2026-10-31
python main.py --start-date 2026-11-01 --end-date 2026-11-15
python main.py --start-date 2026-11-16 --end-date 2026-11-30
```

Chaque morceau ajoute ses pages à la suite des pages existantes, sans rien effacer. Les morceaux peuvent être partagés entre les membres du groupe : chacun en lance un depuis son PC, donc avec sa propre adresse IP, puis commite ses nouvelles pages. Si deux membres créent le même numéro de page, git signale un conflit sur ce fichier : il suffit de renommer l'une des deux pages avec le numéro suivant libre.

## Transformation et enrichissement

`load_events_dataframe` (dans `transform.py`) lit toutes les pages de `data/raw/` dans l'ordre de collecte, garde les champs utiles et supprime les doublons par `id`, en gardant la **version la plus récente** de chaque événement (nombre de RSVP à jour). Elle ajoute ensuite les colonnes d'enrichissement. Aucune requête n'est envoyée à Bandsintown.

### Colonnes du CSV

| Colonne | Origine |
|---|---|
| `id`, `artiste`, `titre`, `lieu`, `localisation`, `debut`, `fin`, `nb_rsvp`, `url_evenement`, `streaming`, `watch_live_text` | champs de l'API, renommés (`FIELDS`) |
| `date_collecte` | date de collecte de la page |
| `ville` | ville de la salle, tirée de `localisation` (« PARIS », « Paris 19 Buttes-Chaumont » → « Paris ») |
| `jour_semaine`, `est_weekend`, `numero_semaine`, `mois`, `heure` | calculés à partir de `debut` |
| `jours_avant_evenement` | nombre de jours entre `date_collecte` et `debut` |
| `duree_heures` | `fin` moins `debut` (vide quand `fin` est absente) |
| `type_evenement` | `festival`, `soirée` ou `concert`, selon les mots-clés du titre (`EVENT_TYPE_PATTERNS`) |
| `popularite` | `aucune` (0 RSVP), `faible` (1 à 9), `moyenne` (10 à 99), `forte` (100 et plus) |
| `longitude`, `latitude` | coordonnées de la salle selon Nominatim (OpenStreetMap), cherchées en Île-de-France |
| `source_geocodage` | `salle` si la salle a été trouvée, `ville` si ce sont les coordonnées de la ville |

### Coordonnées GPS des salles

```bash
python main.py --skip-scraping --enrich-online
```

Les coordonnées sont cherchées avec Nominatim (1 requête par seconde), puis gardées dans `data/cache/lieux.json`. Seules les salles absentes du cache sont cherchées : la première fois, il faut compter 15 à 30 minutes ; ensuite, c'est instantané. Le cache est sauvegardé au fur et à mesure. En cas d'interruption (Ctrl+C, réseau coupé), relancer la commande reprend là où elle s'était arrêtée. Sans `--enrich-online`, ces colonnes sont remplies avec ce qui est déjà en cache.

### Modifier le nettoyage

Le CSV étant reconstruit à partir des pages brutes, on peut changer le nettoyage ou ajouter des colonnes **sans refaire la collecte** :

1. modifier `bandsintown_scraper/transform.py` ;
2. lancer `python main.py --skip-scraping` ;
3. vérifier `data/events_bandsintown.csv`.

- **Ajouter un champ de l'API :** ajouter une ligne `"nomDansLeJSON": "nom_de_colonne"` dans `FIELDS`. Les champs disponibles sont visibles dans `data/raw/page_001.json`.
- **Ajouter une colonne calculée :** ajouter le code dans `load_events_dataframe`, avant le `return`.
- **Voir le résultat sans écrire le CSV :** `python -m bandsintown_scraper.transform` (le `-m` est obligatoire).

## Prédiction de la popularité

**Question :** un événement va-t-il atteindre au moins 10 RSVP (`POPULARITY_THRESHOLD`) ? C'est le cas d'environ 12 % des événements.

```bash
python main.py --skip-scraping --train
```

Le meilleur modèle est sauvegardé dans `models/popularite_<date>.joblib`, avec son rapport lisible `models/popularite_<date>.json` : métriques, hyperparamètres, variables et leur importance.

### Variables explicatives

| Variable | Construction |
|---|---|
| `jour_semaine`, `est_weekend`, `heure`, `mois` | date de l'événement |
| `jours_avant_evenement` | délai entre la collecte et l'événement |
| `type_evenement`, `streaming`, `a_un_titre` | nature de l'événement |
| `ville` | ville de la salle (villes de moins de 20 événements regroupées dans « autres ») |
| `distance_centre_km` | distance de la salle au centre de Paris, calculée à partir des coordonnées GPS |
| `nb_evenements_salle` | nombre d'événements de la salle dans les données |
| `nb_evenements_artiste` | nombre de concerts de l'artiste dans les données (indicateur de notoriété) |

`nb_rsvp` et `popularite` sont exclues : elles sont calculées à partir de la cible, et les utiliser reviendrait à donner la réponse au modèle (fuite de données).

### Méthode

1. 20 % des événements sont mis de côté (**jeu de test**), en gardant la même proportion d'événements populaires (découpage stratifié).
2. Pour chacun des trois modèles (régression logistique, random forest, gradient boosting), les **hyperparamètres sont choisis automatiquement** par `RandomizedSearchCV`. Il teste 20 combinaisons (`SEARCH_ITERATIONS`), chacune évaluée par **validation croisée** à 5 plis sur les 80 % restants. Les modèles sont pondérés (`class_weight="balanced"`) pour compenser le déséquilibre entre les classes.
3. Les trois modèles optimisés sont comparés sur leur ROC-AUC de validation croisée. Le meilleur est évalué **une seule fois** sur le jeu de test, face à une **référence naïve** qui tire au hasard en respectant les proportions.
4. L'**importance des variables** est mesurée par permutation : on mélange une variable et on regarde combien la performance baisse.

Encodage, imputation des valeurs manquantes et normalisation font partie d'un `Pipeline` scikit-learn : ils sont appris uniquement sur les données d'entraînement, et appliqués à l'identique aux nouvelles données. Le hasard est fixé (`RANDOM_STATE`), donc les résultats sont reproductibles.

### Résultats (3892 événements, collecte du 23/10/2026)

| Modèle | Meilleurs hyperparamètres | ROC-AUC (validation croisée) |
|---|---|---|
| Régression logistique | `C=0.075` | 0,710 |
| Random forest | `n_estimators=400, max_depth=10, min_samples_leaf=10, max_features=0.5` | 0,848 |
| **Gradient boosting** | `learning_rate=0.018, max_iter=100, max_leaf_nodes=31, min_samples_leaf=20, l2_regularization=0.215` | **0,849** |

| Métrique (jeu de test) | Gradient boosting | Référence naïve |
|---|---|---|
| ROC-AUC | **0,861** | 0,525 |
| F1 | **0,468** | 0,166 |
| Précision | 0,343 | 0,162 |
| Rappel | 0,734 | 0,170 |

- Le modèle retrouve environ 7 événements populaires sur 10 (rappel). Quand il prédit « populaire », il a raison environ 1 fois sur 3 (précision).
- Random forest et gradient boosting sont quasiment à égalité : l'écart (0,001) est bien plus petit que la variation d'un pli à l'autre (± 0,015).
- Variables les plus utiles : l'**heure** de l'événement, le **nombre de concerts de l'artiste**, la **distance au centre de Paris** et le **nombre d'événements de la salle**.
- **Limite :** la popularité dépend surtout de la notoriété de l'artiste, que les données ne mesurent qu'indirectement. Une vraie mesure (nombre de fans sur Bandsintown, écoutes…) devrait améliorer nettement les prédictions.

## Tests

```bash
pytest              # tous les tests
pytest -v           # avec le nom de chaque test
```

Les tests utilisent de petites données inventées et des dossiers temporaires : ils n'envoient aucune requête et n'écrivent rien dans `data/` ni dans `models/`. Ils vérifient notamment :

- l'absence de fuite de données : `nb_rsvp` ne fait pas partie des variables ;
- le calcul des distances et des comptages ;
- que le modèle fait mieux que la référence naïve ;
- que chaque modèle est optimisé et que le meilleur est bien retenu ;
- que le modèle et son rapport sont bien sauvegardés ;
- les règles de la transformation : type d'événement, ville, version la plus récente d'un événement.

## En cas d'erreur

| Message | Cause | Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'curl_cffi'` (ou `sklearn`) | le `.venv` n'est pas activé, ou les dépendances ne sont pas installées | `.venv\Scripts\activate` puis `pip install -r requirements.txt` |
| `ModuleNotFoundError: No module named 'bandsintown_scraper'` | la commande n'est pas lancée depuis `Groupe_1` | `cd` dans le dossier `Groupe_1` |
| `Collecte interrompue : ... échec (403) ... Just a moment...` | Cloudflare détecte un robot | attendre, ou changer de réseau. `data/` n'a pas été modifié |
| `Collecte interrompue : ... échec (416)` | Bandsintown bloque temporairement l'adresse IP | attendre (parfois plusieurs heures), changer de réseau (partage de connexion du téléphone) ou collecter par petits morceaux. En attendant, travailler avec `--skip-scraping` |
| `429 (trop de requêtes), pause de ... s` | trop de requêtes en peu de temps | rien à faire : le scraper attend puis réessaie |
| `nominatim.openstreetmap.org/search injoignable` | le réseau bloque Nominatim, ou le service est en panne | relancer `--enrich-online` plus tard ou depuis un autre réseau. Le CSV est quand même écrit |
| `PermissionError` sur `events_bandsintown.csv` | le CSV est ouvert dans Excel ou LibreOffice | fermer le fichier et relancer |

## À venir

- Chargement des événements dans une table BigQuery (GCP)
