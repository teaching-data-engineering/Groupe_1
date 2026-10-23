import argparse
from datetime import date

from bandsintown_scraper import load_events_dataframe, scrap_all_events
from bandsintown_scraper.config import OUTPUT_CSV


def parse_args():
    parser = argparse.ArgumentParser(description="Scraper des concerts Bandsintown autour de Paris.")
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
    args = parser.parse_args()
    if not args.skip_scraping and args.end_date is None:
        parser.error("--end-date est obligatoire pour scraper")
    return args


def main():
    args = parse_args()

    if not args.skip_scraping:
        scrap_all_events(args.end_date)

    events_df = load_events_dataframe()
    events_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"{len(events_df)} événements exportés dans {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
