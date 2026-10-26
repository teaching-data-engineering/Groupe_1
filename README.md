# Groupe_1 — Scraper Bandsintown

Scraping des concerts proposés par [Bandsintown](https://www.bandsintown.com) autour de Paris, puis transformation, prédiction et chargement dans BigQuery (GCP).

**écrire votre nom dans Membres**

**Membres :** Alexandre HAYOUN, Hoang , Soro , Mathis

## Structure du repository

```
Groupe_1/
├── bandsintown_scraper/     module Python
│   ├── __init__.py
│   ├── config.py            constantes : URL de l'API, en-têtes HTTP, localisation, délais, dossiers
│   ├── scraper.py           collecte des événements et sauvegarde des JSON bruts
│   ├── transform.py         agrégation des JSON en DataFrame pandas
│   └── model.py             prédiction de la popularité des événements
├── main.py                  point d'entrée
├── tests/                   tests automatiques (pytest)
├── models/                  modèles entraînés (.joblib, ignorés par git) et leurs rapports (.json)
├── Test/                    essais (voir section « Dossier Test »)
└── data/                    généré à l'exécution (ignoré par git)
    ├── raw/                 toutes les pages brutes de l'API, dans un seul dossier
    │   ├── page_001.json
    │   ├── page_002.json
    │   └── ...
    ├── cache/               résultats de Nominatim (lieux.json)
    └── events_bandsintown.csv
```

## Installation

Python 3.10 ou plus récent. On installe les dépendances dans un environnement virtuel `.venv`, propre au projet (ignoré par git).

**Créer le `.venv`** (une seule fois, depuis le dossier `Groupe_1`) :

```bash
python -m venv .venv
```

**L'activer** (à chaque nouveau terminal) :

```bash
.venv\Scripts\activate          # Windows (PowerShell)
source .venv/bin/activate       # Mac / Linux
```

`(.venv)` apparaît alors au début de la ligne du terminal.

**Installer les dépendances** (une seule fois, `.venv` activé) :

```bash
pip install -r requirements.txt
```

Pour lancer aussi les tests, installer en plus les dépendances de développement : `pip install -r requirements-dev.txt`.

Ensuite, toutes les commandes `python main.py ...` utilisent le Python du `.venv`. Dans VS Code : Ctrl+Shift+P → « Python: Select Interpreter » → choisir `.venv`. Les nouveaux terminaux l'activent alors automatiquement.

> Si PowerShell refuse l'activation (« l'exécution de scripts est désactivée »), lancer une fois `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, ou utiliser directement `.venv\Scripts\python.exe main.py ...`.

## Lancer le scraper

Collecter tous les événements d'aujourd'hui jusqu'à une date de fin :

```bash
python main.py --end-date 2026-11-30
```

### Collecter par petits morceaux

Le site bloque l'adresse IP après une vingtaine de pages d'affilée (erreurs `429` puis `416`). Pour rester sous ce seuil, on découpe la collecte avec `--start-date` et on lance les morceaux à environ une heure d'intervalle :

```bash
python main.py --start-date 2026-10-23 --end-date 2026-10-31
python main.py --start-date 2026-11-01 --end-date 2026-11-15
python main.py --start-date 2026-11-16 --end-date 2026-11-30
```

Chaque morceau ajoute ses pages dans `data/raw/` à la suite des pages existantes (par exemple `page_067.json`, `page_068.json`…), sans effacer celles des autres morceaux. Le CSV est ensuite reconstruit avec toutes les pages, sans doublon. Si un morceau est bloqué, il s'arrête sans rien modifier dans `data/` : il suffit de le relancer plus tard. Les morceaux peuvent aussi être partagés entre les membres du groupe : chacun en lance un depuis son PC, puis commite ses nouvelles pages. Si deux membres créent le même numéro de page, git signale un conflit sur ce fichier : il suffit alors de renommer l'une des deux pages avec le numéro suivant libre.

Reconstruire le CSV à partir des JSON déjà sauvegardés, sans envoyer de requête :

```bash
python main.py --skip-scraping
```

Le résultat est écrit dans `data/events_bandsintown.csv`, avec une ligne par événement.

Ajouter les coordonnées GPS des salles (requêtes vers Nominatim, OpenStreetMap) :

```bash
python main.py --skip-scraping --enrich-online
```

La première fois, il faut compter environ 15 à 30 minutes (1 requête par seconde, environ 750 salles). Les résultats sont gardés dans `data/cache/`, donc les lancements suivants sont instantanés. Le cache est sauvegardé au fur et à mesure : en cas d'interruption (Ctrl+C), relancer la commande reprend là où elle s'était arrêtée. Sans `--enrich-online`, ces colonnes sont remplies avec ce qui est déjà en cache, sans aucune requête.

> Toutes les commandes se lancent **depuis le dossier `Groupe_1`**. Sinon : `ModuleNotFoundError: No module named 'bandsintown_scraper'`.

## Dossier Test

Ce dossier contient des essais. Le projet ne les utilise pas : le code officiel est dans `bandsintown_scraper/` et `main.py`.

| Fichier | Rôle |
|---|---|
| `Test.py` | teste uniquement la transformation (`load_events_dataframe`) sur les pages de `data/raw/`, sans aucune requête, et affiche les 10 premiers événements |
| `version_2.py` | ancienne version du scraper, en un seul fichier, avant le découpage en module. Gardée comme référence |
| `events_bandsintown_v2.csv` | résultat d'une collecte complète faite avec `version_2.py` (3702 événements, du 23/10/2026 au 30/11/2026) |

### Lancer Test.py

```bash
python Test/Test.py
```

ou le bouton ▶ de VS Code.

Le module `bandsintown_scraper` est dans `Groupe_1/`, pas dans `Test/`. Le début de `Test.py` règle donc deux choses :

```python
PROJECT_ROOT = Path(__file__).resolve().parent.parent   # Test/Test.py -> Groupe_1
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)
```

- `sys.path.insert` : permet à Python de trouver `bandsintown_scraper`. Sans cette ligne : `ModuleNotFoundError`.
- `os.chdir` : se place dans `Groupe_1` (l'équivalent de `setwd()` en R). Sans cette ligne, le chemin relatif `data/raw` n'est pas trouvé et le DataFrame est vide, sans message d'erreur.

Ce bloc sert uniquement aux fichiers de test. Il ne doit pas être ajouté dans le module.

## Modifier le nettoyage sans refaire de requêtes

Le CSV est toujours **reconstruit à partir des pages JSON brutes** de `data/raw/`. Ces pages contiennent tous les champs renvoyés par l'API. On peut donc changer le nettoyage ou ajouter des colonnes **sans re-scraper**, et sans risque de se faire bloquer par le site.

Cycle de travail :

1. modifier `bandsintown_scraper/transform.py` ;
2. lancer `python main.py --skip-scraping` (sur terminal)
3. vérifier `data/events_bandsintown.csv`.

On ne relance le scraping que pour récupérer des événements **plus récents**.

### Ajouter un champ présent dans le JSON

Ajouter une ligne dans `FIELDS`, au format `"nomDansLeJSON": "nom_de_colonne"` :

```python
FIELDS = {
    "id": "id",
    ...
    "venueCity": "ville",   # nouvelle colonne
}
```

Pour connaître les champs disponibles, ouvrir `data/raw/page_001.json`.

### Créer une colonne calculée ou nettoyer

Ajouter le code dans `load_events_dataframe`, avant le `return` :

```python
df["jour_semaine"] = df["debut"].dt.day_name()
df["artiste"] = df["artiste"].str.strip()
df = df.dropna(subset=["lieu"])
```

### Tester uniquement la transformation

Pour afficher le DataFrame sans écrire le CSV :

```bash
python -m bandsintown_scraper.transform
```

Le `-m` est obligatoire. `python bandsintown_scraper/transform.py` provoque l'erreur `ModuleNotFoundError`. Cette commande demande d'avoir à la fin de `transform.py` un bloc `if __name__ == "__main__":` qui affiche le DataFrame.

## En cas d'erreur

| Message | Cause | Solution |
|---|---|---|
| `échec (403) : ... Just a moment...` | Cloudflare détecte un robot | vérifier que `curl_cffi` est installé (`pip install -r requirements.txt`) |
| `429 (trop de requêtes)` | trop de requêtes en peu de temps | le scraper attend tout seul, puis réessaie |
| `échec (416)` | le site bloque temporairement l'adresse IP | attendre (parfois plusieurs heures) ou changer de réseau (partage de connexion du téléphone). En attendant, travailler avec `--skip-scraping` |
| `0 événements collectés` | la première page a échoué | lire la ligne `page 1 : ...` juste au-dessus pour connaître le code d'erreur |

## Fonctionnement

1. **Une page** (`scrap_one_page`) : requête GET sur l'API interne `choose-dates/fetch-next/upcomingEvents` pour une période et un numéro de page.
2. **Sauvegarde** (`save_json`, `move_pages_to_raw_dir`) : chaque page reçue est enregistrée dès son arrivée dans un fichier JSON, d'abord dans un dossier temporaire. Une fois la collecte terminée sans erreur, les pages sont déplacées dans le dossier unique `data/raw/`, numérotées à la suite des pages existantes. Si le site bloque en cours de route, `data/` n'est pas modifié. Les données brutes sont conservées, ce qui permet de refaire la transformation sans relancer le scraping.
3. **Plusieurs pages** (`scrap_multiple_pages`) : parcourt les pages d'une période et s'arrête dans l'un de ces cas :
   - une page vide : il n'y a plus de résultats ;
   - une page répétée : l'API renvoie en boucle une page déjà vue, sa limite est atteinte ;
   - la limite de 30 pages est atteinte.
4. **Toutes les périodes** (`scrap_all_events`) : l'API renvoie les événements triés par date, mais limite le nombre de pages par période. Quand une période est coupée par cette limite, une nouvelle période démarre au jour du dernier événement reçu. Le nombre de périodes s'adapte donc tout seul au volume de données, que la date de fin soit fin novembre ou fin 2030.
5. **Transformation** (`load_events_dataframe`) : lit toutes les pages de `data/raw/` dans l'ordre de collecte, garde les champs utiles et supprime les doublons par `id`, en gardant la version la plus récente de chaque événement (nombre de RSVP à jour). Elle ajoute ensuite les colonnes d'enrichissement et trie par date.

### La requête envoyée à Bandsintown

L'URL a été trouvée dans l'onglet *Network* des outils de développement du navigateur (F12), en faisant défiler la liste des concerts sur https://www.bandsintown.com/choose-dates/genre/all-genres : à chaque défilement, la page appelle cette API interne, qui renvoie du JSON.

**Méthode et URL :**

```
GET https://www.bandsintown.com/choose-dates/fetch-next/upcomingEvents
```

**Paramètres** (construits dans `scrap_one_page`, valeurs dans `config.py`) :

| Paramètre | Exemple | Rôle |
|---|---|---|
| `date` | `2026-10-23T00:00:00,2026-11-30T23:00:00` | période : début et fin séparés par une virgule |
| `page` | `1`, `2`, `3`… | numéro de la page (environ 36 événements par page, 30 pages au maximum par période) |
| `latitude` | `48.85341` | centre de la recherche : Paris (`PARIS_LATITUDE`) |
| `longitude` | `2.3488` | centre de la recherche : Paris (`PARIS_LONGITUDE`) |
| `genre_query` | `all-genres` | tous les genres musicaux (`GENRE_QUERY`) |

Ce qui donne par exemple :

```
https://www.bandsintown.com/choose-dates/fetch-next/upcomingEvents?date=2026-10-23T00%3A00%3A00%2C2026-11-30T23%3A00%3A00&page=1&longitude=2.3488&latitude=48.85341&genre_query=all-genres
```

**En-têtes** (`HEADERS` dans `config.py`) : `Accept-language`, `Referer` (la page de la liste des concerts), `Sec-Fetch-*` et `Upgrade-Insecure-Requests`, copiés depuis la requête du navigateur. Aucun cookie n'est envoyé. `User-Agent`, `Accept`, `Accept-Encoding` et `Sec-Ch-Ua*` sont ajoutés par `curl_cffi`, selon le navigateur imité.

**Envoi** :

```python
from curl_cffi import requests

browser = random.choice(IMPERSONATE_BROWSERS)  # tiré au hasard une fois par collecte
with requests.Session(impersonate=browser) as session:  # garde les cookies d'une page à l'autre
    response = session.get(API_URL, headers=HEADERS, params=params)  # pour chaque page
```

**Réponse** : une liste JSON d'événements (codes de retour possibles : voir « En cas d'erreur »). Extrait d'un événement :

```json
{
  "id": 109045633,
  "artistName": "The Soul Rebels",
  "title": "NFL Experience Paris presented by Wilson",
  "venueName": "Champ de Mars",
  "locationText": "Paris, France",
  "startsAt": "2026-10-23T10:00:00",
  "endsAt": "2026-10-23T13:00:00",
  "rsvpCountInt": 4,
  "streamingEvent": false,
  "eventUrl": "https://www.bandsintown.com/e/109045633-the-soul-rebels-at-champ-de-mars?...",
  "artistUrl": "https://www.bandsintown.com/a/149826-the-soul-rebels?...",
  "watchLiveText": "Watch Live"
}
```

Chaque réponse est enregistrée dans `data/raw/page_XXX.json`. La liste brute des événements, telle que renvoyée par l'API, est accompagnée des informations de la collecte :

```json
{
  "collectedAt": "2026-10-23",
  "startDate": "2026-10-23",
  "endDate": "2026-11-30",
  "page": 1,
  "events": [ { "id": 109045633, "artistName": "The Soul Rebels", "...": "..." } ]
}
```

`collectedAt` sert à calculer `jours_avant_evenement`. La date du fichier ne peut pas servir à ça : elle change à chaque `git clone` ou `git pull`.

**Exécuter les requêtes** : c'est `main.py` qui envoie les requêtes, page après page, pour la période demandée. Depuis le dossier `Groupe_1` :

```bash
python main.py --start-date 2026-10-23 --end-date 2026-10-31
```

- `--start-date` correspond au début du paramètre `date`. Sans cette option, la collecte commence aujourd'hui.
- `--end-date` correspond à la fin du paramètre `date`.
- `page` est géré automatiquement : 1, 2, 3… jusqu'à la fin des résultats.

Dans le terminal, on voit chaque requête :

```
=== Période 1 : du 23/10/2026 au 31/10/2026 ===
page 1 : 36 nouveaux événements.
page 2 : 36 nouveaux événements.
...
page 14 : vide, fin des résultats.
```

Le `.venv` doit être activé (voir « Installation »). Sinon : `ModuleNotFoundError: No module named 'curl_cffi'`.

### Colonnes du CSV

Champs de l'API :

| Colonne | Description |
|---|---|
| `id` | identifiant Bandsintown de l'événement |
| `artiste` | nom de l'artiste |
| `titre` | titre de l'événement (souvent vide) |
| `lieu` | salle de concert |
| `localisation` | texte brut de l'API, par exemple « Paris, France » |
| `debut` | date et heure de début |
| `fin` | date et heure de fin (souvent vide) |
| `nb_rsvp` | nombre de personnes ayant signalé leur intérêt |
| `url_evenement` | lien vers la page de l'événement |
| `streaming` | événement diffusé en ligne ou non |
| `watch_live_text` | texte affiché pour le direct |

Enrichissement calculé, sans requête :

| Colonne | Calcul |
|---|---|
| `date_collecte` | date à laquelle la page JSON a été collectée |
| `ville` | ville de la salle, tirée de `localisation`. « PARIS » et « Paris 19 Buttes-Chaumont » donnent « Paris » |
| `jour_semaine`, `est_weekend` | jour de la semaine ; `True` le samedi et le dimanche |
| `numero_semaine`, `mois`, `heure` | à partir de `debut` |
| `jours_avant_evenement` | nombre de jours entre `date_collecte` et `debut` |
| `duree_heures` | `fin` moins `debut` (vide quand `fin` est absente) |
| `type_evenement` | `festival`, `soirée` ou `concert`, selon les mots-clés du titre (`EVENT_TYPE_PATTERNS`) |
| `popularite` | `aucune` (0 RSVP), `faible` (1 à 9), `moyenne` (10 à 99) ou `forte` (100 et plus) |

Enrichissement externe, rempli par `--enrich-online` puis lu depuis le cache :

| Colonne | Source |
|---|---|
| `longitude`, `latitude` | coordonnées de la salle selon Nominatim (OpenStreetMap), cherchées en Île-de-France |
| `source_geocodage` | `salle` si la salle a été trouvée, `ville` si ce sont les coordonnées de la ville |

## Éviter le ban

- Requêtes envoyées avec `curl_cffi`, qui imite l'empreinte d'un vrai navigateur. La librairie `requests` est bloquée par Cloudflare (erreur 403).
- User-Agent aléatoire : à chaque collecte, le navigateur imité est tiré au hasard dans `IMPERSONATE_BROWSERS` (plusieurs versions de Chrome, de 131 à 150). Il est ensuite gardé pendant toute la collecte, dans une session qui renvoie les cookies de Cloudflare d'une page à l'autre, comme un vrai navigateur. Changer de navigateur à chaque requête depuis la même IP, sans renvoyer les cookies, était détecté comme un robot (403 après quelques pages). `curl_cffi` envoie le User-Agent **et** l'empreinte TLS du navigateur choisi, ce qui les garde cohérents. Un User-Agent Firefox avec une empreinte Chrome serait repéré par Cloudflare. Firefox n'est pas dans la liste : testée, son imitation est bloquée par Cloudflare (403), alors que celle de Chrome passe.
- Pause aléatoire de 2 à 5 secondes entre deux requêtes.
- Une seule collecte complète, puis tout le travail se fait sur les JSON sauvegardés (`--skip-scraping`).
- En cas de réponse `429 Too Many Requests`, le scraper attend le délai indiqué par le serveur (60 s par défaut), puis redemande la même page.


## Prédiction de la popularité

**Question :** un événement va-t-il être **populaire**, c'est-à-dire atteindre au moins 10 RSVP (`POPULARITY_THRESHOLD`) ? C'est le cas d'environ 12 % des événements.

**Lancer l'entraînement** (sans aucune requête au site) :

```bash
python main.py --skip-scraping --train
```

Le modèle est sauvegardé dans `models/popularite_<date>.joblib`, avec son rapport lisible dans `models/popularite_<date>.json` : métriques, variables utilisées, importance des variables.

### Variables explicatives

| Variable | Construction |
|---|---|
| `jour_semaine`, `est_weekend`, `heure`, `mois` | date de l'événement |
| `jours_avant_evenement` | délai entre la collecte et l'événement |
| `type_evenement`, `streaming`, `a_un_titre` | nature de l'événement |
| `ville` | ville de la salle (villes de moins de 20 événements regroupées) |
| `distance_centre_km` | distance de la salle au centre de Paris, calculée à partir des coordonnées GPS |
| `nb_evenements_salle` | nombre d'événements de la salle dans les données (taille, activité de la salle) |
| `nb_evenements_artiste` | nombre de concerts de l'artiste dans les données (indicateur de notoriété) |

`nb_rsvp` et `popularite` sont exclues des variables : elles sont calculées à partir de la cible, et les utiliser reviendrait à tricher (fuite de données).

### Méthode

1. 20 % des événements sont mis de côté (**jeu de test**), en gardant la même proportion d'événements populaires (découpage stratifié).
2. Pour chacun des trois modèles (régression logistique, random forest, gradient boosting), les **hyperparamètres sont choisis automatiquement** par `RandomizedSearchCV`. Il tire 20 combinaisons (`SEARCH_ITERATIONS`) dans l'espace de recherche défini dans `build_candidate_models`, et évalue chacune par **validation croisée** à 5 plis sur les 80 % restants. Tous les modèles sont pondérés (`class_weight="balanced"`) pour compenser le déséquilibre entre les classes.
3. Les trois modèles, chacun avec ses meilleurs hyperparamètres, sont comparés sur leur ROC-AUC de validation croisée. Le meilleur est réentraîné sur les 80 %, puis évalué **une seule fois** sur le jeu de test. On le compare à une **référence naïve** qui tire au hasard en respectant les proportions.
4. L'**importance des variables** est mesurée par permutation : on mélange une variable et on regarde combien la performance baisse.

Toutes les transformations (encodage, imputation des valeurs manquantes, normalisation) font partie d'un `Pipeline` scikit-learn. Elles sont donc apprises uniquement sur les données d'entraînement, et appliquées à l'identique aux nouvelles données.

### Résultats (3892 événements, collecte du 23/10/2026)

| Modèle | Meilleurs hyperparamètres trouvés | ROC-AUC (validation croisée) |
|---|---|---|
| Régression logistique | `C=0.075` | 0,710 |
| Random forest | `n_estimators=400, max_depth=10, min_samples_leaf=10, max_features=0.5` | 0,848 |
| **Gradient boosting** | `learning_rate=0.018, max_iter=100, max_leaf_nodes=31, min_samples_leaf=20, l2_regularization=0.215` | **0,849** |

Random forest et gradient boosting sont quasiment à égalité : l'écart (0,001) est bien plus petit que la variation d'un pli à l'autre (± 0,015). Sans optimisation, le gradient boosting obtenait 0,842 en validation croisée.

Sur le jeu de test, comparé à la référence naïve :

| Métrique | Gradient boosting | Référence naïve |
|---|---|---|
| ROC-AUC | **0,861** | 0,525 |
| F1 | **0,468** | 0,166 |
| Précision | 0,343 | 0,162 |
| Rappel | 0,734 | 0,170 |

Le modèle détecte environ 7 événements populaires sur 10 (rappel). Quand il prédit « populaire », il a raison environ 1 fois sur 3 (précision). Les modèles sont choisis sur le ROC-AUC, qui mesure la capacité à **classer** les événements du moins au plus populaire. Précision et rappel dépendent en plus du seuil de décision (0,5 par défaut), qu'on peut déplacer selon l'usage : plus haut pour se tromper moins souvent, plus bas pour rater moins d'événements populaires.

Variables les plus utiles : l'**heure** de l'événement, le **nombre de concerts de l'artiste**, la **distance au centre de Paris** et le **nombre d'événements de la salle**.

L'optimisation complète prend environ 1 minute (3 modèles × 20 combinaisons × 5 plis).

**Limite :** la popularité dépend surtout de la notoriété de l'artiste, que les données ne contiennent qu'indirectement (`nb_evenements_artiste`). Ajouter une vraie mesure de notoriété (nombre de fans de l'artiste sur Bandsintown, écoutes…) devrait améliorer nettement les prédictions.

### Tests

```bash
pytest
```

Les tests vérifient notamment :
- l'absence de fuite de données : `nb_rsvp` ne fait pas partie des variables ;
- le calcul des distances et des comptages ;
- que le modèle fait mieux que la référence naïve ;
- que les hyperparamètres de chaque modèle sont optimisés, et que le modèle retenu est bien le meilleur en validation croisée ;
- que le modèle et son rapport sont bien sauvegardés ;
- les règles de la transformation (type d'événement, ville, version la plus récente d'un événement).

## À venir

- Chargement des événements dans une table BigQuery (GCP)
