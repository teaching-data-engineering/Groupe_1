import argparse
import sys
from datetime import date

from google.api_core.exceptions import GoogleAPIError

from bandsintown_scraper import load_events_dataframe, scrap_all_events
from bandsintown_scraper.config import OUTPUT_CSV
from bandsintown_scraper.loader import load_events_to_bigquery
from bandsintown_scraper.model import print_report, save_model, train_model
from bandsintown_scraper.scraper import ScrapingError


def parse_args():
    parser = argparse.ArgumentParser(description="Scraper des concerts Bandsintown autour de Paris.")
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=date.today(),
        help="date de début de la collecte, au format AAAA-MM-JJ (par défaut : aujourd'hui). "
             "Permet de collecter par petits morceaux pour ne pas être bloqué par le site",
    )
    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        help="date de fin de la collecte, au format AAAA-MM-JJ (ex : 2026-11-30)",
    )
    parser.add_argument(
        "--skip-scraping",
        action="store_true",
        help="ne pas scraper, seulement reconstruire le CSV à partir des JSON déjà sauvegardés",
    )
    parser.add_argument(
        "--enrich-online",
        action="store_true",
        help="interroger Nominatim pour les coordonnées GPS des salles "
             "(résultats mis en cache dans data/cache/)",
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="entraîner le modèle de prédiction de popularité et le sauvegarder dans models/",
    )
    parser.add_argument(
        "--load-bigquery",
        action="store_true",
        help="charger les événements dans la table BigQuery (clé dans credentials/gcp_key.json)",
    )
    args = parser.parse_args()
    if not args.skip_scraping and args.end_date is None:
        parser.error("--end-date est obligatoire pour scraper")
    if args.end_date is not None and args.start_date > args.end_date:
        parser.error("--start-date doit être antérieure ou égale à --end-date")
    return args


def main():
    args = parse_args()

    if not args.skip_scraping:
        try:
            scrap_all_events(args.end_date, args.start_date)
        except ScrapingError as error:
            sys.exit(f"Collecte interrompue : {error}\n"
                     "data/ n'a pas été modifié. Réessayez plus tard ou depuis un autre réseau.")

    events_df = load_events_dataframe(enrich_online=args.enrich_online)
    events_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"{len(events_df)} événements exportés dans {OUTPUT_CSV}")

    if args.train:
        print("\nEntraînement du modèle de popularité...")
        model, report = train_model(events_df)
        print_report(report)
        print(f"\nModèle sauvegardé dans {save_model(model, report)}")

    if args.load_bigquery:
        print("\nChargement dans BigQuery...")
        try:
            table_id, nb_rows = load_events_to_bigquery(events_df)
        except (FileNotFoundError, GoogleAPIError) as error:
            sys.exit(f"Chargement BigQuery impossible : {error}")
        print(f"{nb_rows} événements chargés dans {table_id}")


if __name__ == "__main__":
    main()
