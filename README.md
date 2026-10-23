# Groupe_1 — Scraper Bandsintown

Scraping des concerts proposés par [Bandsintown](https://www.bandsintown.com) autour de Paris, puis transformation, prédiction et chargement dans BigQuery (GCP).

**écrire votre nom dans Membres**

**Membres :** Alexandre HAYOUN, Hoang

## Structure du repository

```
Groupe_1/
├── bandsintown_scraper/     module Python
│   ├── __init__.py
│   ├── config.py            constantes : URL de l'API, en-têtes HTTP, localisation, délais, dossiers
│   ├── scraper.py           collecte des événements et sauvegarde des JSON bruts
│   └── transform.py         agrégation des JSON en DataFrame pandas
├── main.py                  point d'entrée
└── data/                    généré à l'exécution (ignoré par git)
    ├── raw/<début>_<fin>/page_XXX.json
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

## Fonctionnement

1. **Une page** (`scrap_one_page`) : requête GET sur l'API interne `choose-dates/fetch-next/upcomingEvents` pour une période et un numéro de page.
2. **Sauvegarde** (`save_json`) : chaque page reçue est enregistrée telle quelle en JSON dans `data/raw/`. Les données brutes sont conservées, ce qui permet de refaire la transformation sans relancer le scraping.
3. **Plusieurs pages** (`scrap_multiple_pages`) : parcourt les pages d'une période et s'arrête dans l'un de ces cas :
   - une page vide : il n'y a plus de résultats ;
   - une page répétée : l'API renvoie en boucle une page déjà vue, sa limite est atteinte ;
   - la limite de 30 pages est atteinte.
4. **Toutes les périodes** (`scrap_all_events`) : l'API renvoie les événements triés par date, mais limite le nombre de pages par période. Quand une période est coupée par cette limite, une nouvelle période démarre au jour du dernier événement reçu. Le nombre de périodes s'adapte donc tout seul au volume de données, que la date de fin soit fin novembre ou fin 2030.
5. **Transformation** (`load_events_dataframe`) : lit tous les JSON, garde les champs utiles, supprime les doublons par `id` et trie par date.

### Colonnes du CSV

| Colonne | Description |
|---|---|
| `id` | identifiant Bandsintown de l'événement |
| `artiste` | nom de l'artiste |
| `lieu` | salle de concert |
| `debut` | date et heure de début |
| `fin` | date et heure de fin (souvent vide) |
| `url_evenement` | lien vers la page de l'événement |
| `streaming` | événement diffusé en ligne ou non |
| `watch_live_text` | texte affiché pour le direct |

## Éviter le ban

- Pause aléatoire de 2 à 5 secondes entre deux requêtes.
- En cas de réponse `429 Too Many Requests`, le scraper attend le délai indiqué par le serveur (60 s par défaut), puis redemande la même page.
- Pas de proxy : le réseau de l'université ne le permet pas.

## À venir

- Enrichissement des champs
- Algorithme de prédiction
- Chargement des événements dans une table BigQuery (GCP)
