import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent   # Test/Test.py -> Groupe_1
sys.path.insert(0, str(PROJECT_ROOT))   # pour que Python trouve bandsintown_scraper
os.chdir(PROJECT_ROOT)                  # l'équivalent de setwd(), pour que "data/raw" soit trouvé

from bandsintown_scraper.transform import load_events_dataframe

events_df = load_events_dataframe()
print(events_df.head(10))
print(f"{len(events_df)} événements")

