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
│   └── transform.py         agrégation des JSON en DataFrame pandas
├── main.py                  point d'entrée
├── Test/                    essais et tests (voir section « Dossier Test »)
└── data/                    généré à l'exécution (ignoré par git)
    ├── raw/<début>_<fin>/page_XXX.json
    ├── cache/               résultats de MusicBrainz et Nominatim (artistes.json, lieux.json)
    └── events_bandsintown.csv
```

## Installation

Python 3.10 ou plus récent.

```bash
pip install -r requirements.txt
```

## Lancer le scraper

Collecter tous les événements d'aujourd'hui jusqu'à une date de fin :

```bash
python main.py --end-date 2026-11-30
```

Reconstruire le CSV à partir des JSON déjà sauvegardés, sans envoyer de requête :

```bash
python main.py --skip-scraping
```

Le résultat est écrit dans `data/events_bandsintown.csv`, avec une ligne par événement.

Ajouter la nationalité des artistes et les coordonnées GPS des salles (requêtes vers MusicBrainz et Nominatim) :

```bash
python main.py --skip-scraping --enrich-online
```

La première fois, il faut compter environ 20 à 40 minutes (1 requête par seconde, environ 1000 artistes et 300 salles). Les résultats sont gardés dans `data/cache/`, donc les lancements suivants sont instantanés. Le cache est sauvegardé au fur et à mesure : en cas d'interruption (Ctrl+C), relancer la commande reprend là où elle s'était arrêtée. Sans `--enrich-online`, ces colonnes sont remplies avec ce qui est déjà en cache, sans aucune requête.

> Toutes les commandes se lancent **depuis le dossier `Groupe_1`**. Sinon : `ModuleNotFoundError: No module named 'bandsintown_scraper'`.

## Dossier Test

Ce dossier contient des essais. Le projet ne les utilise pas : le code officiel est dans `bandsintown_scraper/` et `main.py`.

| Fichier | Rôle |
|---|---|
| `Test.py` | teste uniquement la transformation (`load_events_dataframe`) sur les JSON de `data/raw/`, sans aucune requête, et affiche les 10 premiers événements |
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

Le CSV est toujours **reconstruit à partir des JSON bruts** de `data/raw/`. Ces JSON contiennent tous les champs renvoyés par l'API. On peut donc changer le nettoyage ou ajouter des colonnes **sans re-scraper**, et sans risque de se faire bloquer par le site.

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

Pour connaître les champs disponibles, ouvrir un fichier `data/raw/.../page_001.json`.

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
2. **Sauvegarde** (`save_json`) : chaque page reçue est enregistrée telle quelle en JSON dans `data/raw/`. Les données brutes sont conservées, ce qui permet de refaire la transformation sans relancer le scraping.
3. **Plusieurs pages** (`scrap_multiple_pages`) : parcourt les pages d'une période et s'arrête dans l'un de ces cas :
   - une page vide : il n'y a plus de résultats ;
   - une page répétée : l'API renvoie en boucle une page déjà vue, sa limite est atteinte ;
   - la limite de 30 pages est atteinte.
4. **Toutes les périodes** (`scrap_all_events`) : l'API renvoie les événements triés par date, mais limite le nombre de pages par période. Quand une période est coupée par cette limite, une nouvelle période démarre au jour du dernier événement reçu. Le nombre de périodes s'adapte donc tout seul au volume de données, que la date de fin soit fin novembre ou fin 2030.
5. **Transformation** (`load_events_dataframe`) : lit tous les JSON, garde les champs utiles, supprime les doublons par `id`, ajoute les colonnes d'enrichissement et trie par date.

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
| `pays_artiste` | pays de l'artiste, en code ISO (`FR`, `US`…), selon MusicBrainz, si la correspondance du nom est jugée fiable (score de 90 ou plus) |
| `artiste_local` | `True` si `pays_artiste` vaut `FR` |
| `longitude`, `latitude` | coordonnées de la salle selon Nominatim (OpenStreetMap), cherchées en Île-de-France |
| `source_geocodage` | `salle` si la salle a été trouvée, `ville` si ce sont les coordonnées de la ville |

Limite : la nationalité est trouvée à partir du nom seul. Un artiste peu connu peut être confondu avec un homonyme.

## Éviter le ban

- Requêtes envoyées avec `curl_cffi`, qui imite l'empreinte d'un vrai navigateur Chrome. La librairie `requests` est bloquée par Cloudflare (erreur 403).
- Pause aléatoire de 2 à 5 secondes entre deux requêtes.
- Une seule collecte complète, puis tout le travail se fait sur les JSON sauvegardés (`--skip-scraping`).
- En cas de réponse `429 Too Many Requests`, le scraper attend le délai indiqué par le serveur (60 s par défaut), puis redemande la même page.


## À venir

- Algorithme de prédiction
- Chargement des événements dans une table BigQuery (GCP)
