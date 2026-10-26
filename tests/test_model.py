import numpy as np
import pandas as pd
import pytest

from bandsintown_scraper.model import (
    FEATURES,
    TARGET,
    build_features,
    haversine_km,
    save_model,
    train_model,
)


@pytest.fixture
def events_df():
    """Faux événements : les concerts du soir dans Paris sont plus souvent populaires."""
    rng = np.random.default_rng(0)
    n = 400
    evening = rng.random(n) < 0.5
    return pd.DataFrame(
        {
            "id": range(n),
            "artiste": rng.choice([f"artiste_{i}" for i in range(80)], n),
            "titre": np.where(rng.random(n) < 0.1, "Release Party", None),
            "lieu": rng.choice([f"salle_{i}" for i in range(30)], n),
            "ville": rng.choice(["Paris", "Montreuil", "Pantin"], n, p=[0.8, 0.1, 0.1]),
            "latitude": 48.85 + rng.normal(0, 0.05, n),
            "longitude": 2.35 + rng.normal(0, 0.05, n),
            "jour_semaine": rng.choice(["Friday", "Saturday", "Monday"], n),
            "est_weekend": rng.random(n) < 0.3,
            "streaming": False,
            "type_evenement": "concert",
            "heure": np.where(evening, 21, 15),
            "mois": 11,
            "jours_avant_evenement": rng.integers(0, 40, n),
            "nb_rsvp": np.where(evening & (rng.random(n) < 0.6), 50, 1),
        }
    )


def test_haversine_km_paris_to_versailles():
    assert haversine_km(48.8049, 2.1204, 48.8534, 2.3488) == pytest.approx(17.5, abs=0.5)


def test_build_features_excludes_target_derived_columns(events_df):
    X, y = build_features(events_df)
    assert list(X.columns) == FEATURES
    assert "nb_rsvp" not in X.columns and "popularite" not in X.columns
    assert y.name == TARGET
    assert set(y.unique()) <= {0, 1}


def test_build_features_does_not_modify_input(events_df):
    columns_before = list(events_df.columns)
    build_features(events_df)
    assert list(events_df.columns) == columns_before


def test_build_features_counts_events_per_artist(events_df):
    X, _ = build_features(events_df)
    expected = events_df.groupby("artiste")["id"].transform("count")
    assert (X["nb_evenements_artiste"] == expected).all()


@pytest.fixture
def trained(events_df):
    # 2 combinaisons par modèle suffisent pour tester le fonctionnement, sans ralentir les tests
    return train_model(events_df, n_iter=2)


def test_train_model_beats_naive_baseline(events_df, trained):
    model, report = trained
    assert report["test"]["roc_auc"] > report["test_reference_naive"]["roc_auc"]
    X, _ = build_features(events_df)
    assert model.predict_proba(X).shape == (len(X), 2)


def test_train_model_tunes_every_candidate(trained):
    _, report = trained
    assert set(report["validation_croisee"]) == {"regression_logistique", "random_forest", "gradient_boosting"}
    for scores in report["validation_croisee"].values():
        assert scores["hyperparametres"]
        assert all(not name.startswith("modele__") for name in scores["hyperparametres"])
    best = report["meilleur_modele"]
    assert report["validation_croisee"][best]["roc_auc_moyen"] == max(
        scores["roc_auc_moyen"] for scores in report["validation_croisee"].values()
    )


def test_save_model_writes_model_and_report(trained, tmp_path):
    model, report = trained
    model_path = save_model(model, report, tmp_path)
    assert model_path.exists()
    assert model_path.with_suffix(".json").exists()
