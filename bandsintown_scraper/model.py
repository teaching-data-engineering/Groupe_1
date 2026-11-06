"""Prédiction de la popularité d'un événement : est-ce qu'il atteindra POPULARITY_THRESHOLD RSVP ?"""
import json
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from scipy.stats import loguniform, randint
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from bandsintown_scraper.config import (
    CV_FOLDS,
    MIN_EVENTS_PER_CITY,
    MODELS_DIR,
    PARIS_LATITUDE,
    PARIS_LONGITUDE,
    POPULARITY_THRESHOLD,
    RANDOM_STATE,
    SEARCH_ITERATIONS,
    TEST_SIZE,
)

TARGET = "est_populaire"
CATEGORICAL_FEATURES = ["jour_semaine", "type_evenement", "ville"]
NUMERIC_FEATURES = [
    "heure",
    "mois",
    "jours_avant_evenement",
    "distance_centre_km",
    "nb_evenements_salle",
    "nb_evenements_artiste",
]
BOOLEAN_FEATURES = ["est_weekend", "streaming", "a_un_titre"]
FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES + BOOLEAN_FEATURES

EARTH_RADIUS_KM = 6371


def haversine_km(latitude, longitude, reference_latitude, reference_longitude):
    """Distance à vol d'oiseau entre des points GPS et un point de référence."""
    lat1, lon1 = np.radians(latitude), np.radians(longitude)
    lat2, lon2 = np.radians(reference_latitude), np.radians(reference_longitude)
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def build_features(events_df):
    """Construit la matrice des variables explicatives X et la cible y.

    nb_rsvp et popularite ne font pas partie de X : elles sont calculées à partir de la cible.
    Les comptages par salle et par artiste n'utilisent pas la cible : pas de fuite de données.
    """
    df = events_df.copy()
    df["distance_centre_km"] = haversine_km(
        df["latitude"], df["longitude"], float(PARIS_LATITUDE), float(PARIS_LONGITUDE)
    )
    df["nb_evenements_salle"] = df.groupby("lieu")["id"].transform("count")
    df["nb_evenements_artiste"] = df.groupby("artiste")["id"].transform("count")
    df["a_un_titre"] = df["titre"].notna()
    for column in BOOLEAN_FEATURES:
        df[column] = df[column].astype(int)

    X = df[FEATURES]
    y = (df["nb_rsvp"] >= POPULARITY_THRESHOLD).astype(int).rename(TARGET)
    return X, y


def build_preprocessor():
    return ColumnTransformer(
        [
            (
                "categories",
                OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=MIN_EVENTS_PER_CITY),
                CATEGORICAL_FEATURES,
            ),
            (
                "nombres",
                Pipeline([("imputation", SimpleImputer(strategy="median")), ("normalisation", StandardScaler())]),
                NUMERIC_FEATURES,
            ),
            ("booleens", "passthrough", BOOLEAN_FEATURES),
        ]
    )


def build_candidate_models(n_samples):
    """Modèles comparés, chacun avec son espace de recherche d'hyperparamètres.

    Les plages qui dépendent de la quantité de données (taille des feuilles, profondeur) sont calculées
    à partir de n_samples : elles restent adaptées si la collecte passe de 4 000 à 10 000 événements.
    Le nombre d'arbres du gradient boosting n'est pas cherché : l'arrêt précoce le choisit.
    class_weight="balanced" compense le déséquilibre (environ 12 % de populaires).
    Les noms d'hyperparamètres sont préfixés par "modele__", le nom de l'étape dans le Pipeline.
    """
    # Une feuille doit contenir entre 0,1 % et 2 % des événements (1 % au plus pour la random forest)
    min_leaf = max(5, n_samples // 1000)
    max_depths = list(range(4, int(np.log2(n_samples)) + 1, 2))
    # Complexité des arbres du boosting : de 7 feuilles à environ n_samples / 16 (doublée à chaque valeur)
    max_leaf_nodes = [2**k - 1 for k in range(3, int(np.log2(n_samples)) - 3)]
    candidates = {
        "regression_logistique": (
            LogisticRegression(class_weight="balanced", max_iter=2000),
            {"modele__C": loguniform(1e-3, 1e2)},
        ),
        "random_forest": (
            RandomForestClassifier(class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1),
            {
                "modele__n_estimators": randint(200, 600),
                "modele__max_depth": [None, *max_depths],
                "modele__min_samples_leaf": randint(1, max(2, n_samples // 100)),
                "modele__max_features": ["sqrt", 0.5, None],
            },
        ),
        "gradient_boosting": (
            # learning_rate fixé : plus petit, il gagne toujours un peu en ajoutant beaucoup d'arbres,
            # ce n'est donc pas un réglage à chercher (testé : 0.003 au lieu de 0.01, ROC-AUC +0.001, 3x plus d'arbres)
            HistGradientBoostingClassifier(
                class_weight="balanced",
                learning_rate=0.01,
                early_stopping=True,
                max_iter=1000,
                random_state=RANDOM_STATE,
            ),
            {
                "modele__max_leaf_nodes": max_leaf_nodes,
                "modele__min_samples_leaf": randint(min_leaf, max(min_leaf + 1, n_samples // 50)),
                "modele__l2_regularization": loguniform(1e-4, 1.0),
            },
        ),
    }
    return {
        name: (Pipeline([("preparation", build_preprocessor()), ("modele", classifier)]), search_space)
        for name, (classifier, search_space) in candidates.items()
    }


def evaluate(model, X, y):
    predictions = model.predict(X)
    return {
        "roc_auc": round(roc_auc_score(y, model.predict_proba(X)[:, 1]), 3),
        "f1": round(f1_score(y, predictions, zero_division=0), 3),
        "precision": round(precision_score(y, predictions, zero_division=0), 3),
        "rappel": round(recall_score(y, predictions, zero_division=0), 3),
    }


def tune_model(pipeline, search_space, X_train, y_train, n_iter):
    """Cherche les meilleurs hyperparamètres par validation croisée, sur les données d'entraînement seules.

    Renvoie la recherche terminée : best_estimator_ est déjà réentraîné sur tout X_train.
    """
    search = RandomizedSearchCV(
        pipeline,
        search_space,
        n_iter=n_iter,
        scoring="roc_auc",
        cv=StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE),
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    return search.fit(X_train, y_train)


def train_model(events_df, n_iter=SEARCH_ITERATIONS):
    """Optimise les hyperparamètres de chaque modèle, garde le meilleur et l'évalue sur un jeu de test.

    Le jeu de test (TEST_SIZE des événements) ne sert ni au choix des hyperparamètres ni au choix
    du modèle : il n'est utilisé qu'une seule fois, pour l'évaluation finale.
    Renvoie (meilleur_modele, rapport).
    """
    X, y = build_features(events_df)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )

    searches, cv_scores = {}, {}
    for name, (pipeline, search_space) in build_candidate_models(len(X_train)).items():
        search = tune_model(pipeline, search_space, X_train, y_train, n_iter)
        best_std = search.cv_results_["std_test_score"][search.best_index_]
        searches[name] = search
        cv_scores[name] = {
            "roc_auc_moyen": round(search.best_score_, 3),
            "ecart_type": round(best_std, 3),
            "hyperparametres": {
                param.removeprefix("modele__"): _to_json(value) for param, value in search.best_params_.items()
            },
        }
        print(f"  {name:22} meilleur ROC-AUC validation croisée : {search.best_score_:.3f} (± {best_std:.3f})")

    best_name = max(cv_scores, key=lambda name: cv_scores[name]["roc_auc_moyen"])
    best_model = searches[best_name].best_estimator_
    if isinstance(best_model.named_steps["modele"], HistGradientBoostingClassifier):
        cv_scores[best_name]["nb_arbres_arret_precoce"] = best_model.named_steps["modele"].n_iter_

    # Référence naïve : tout modèle utile doit faire mieux qu'un tirage respectant les proportions
    baseline = DummyClassifier(strategy="stratified", random_state=RANDOM_STATE).fit(X_train, y_train)

    importances = permutation_importance(
        best_model, X_test, y_test, scoring="roc_auc", n_repeats=10, random_state=RANDOM_STATE
    )
    feature_importances = (
        pd.Series(importances.importances_mean, index=FEATURES).sort_values(ascending=False).round(4)
    )

    report = {
        "date_entrainement": datetime.now().isoformat(timespec="seconds"),
        "cible": f"{TARGET} (nb_rsvp >= {POPULARITY_THRESHOLD})",
        "nb_evenements": len(X),
        "part_populaires": round(y.mean(), 3),
        "variables": FEATURES,
        "combinaisons_testees_par_modele": n_iter,
        "validation_croisee": cv_scores,
        "meilleur_modele": best_name,
        "test": evaluate(best_model, X_test, y_test),
        "test_reference_naive": evaluate(baseline, X_test, y_test),
        "importance_variables": feature_importances.to_dict(),
    }
    return best_model, report


def _to_json(value):
    """Convertit les valeurs numpy (np.float64...) en types Python, pour pouvoir les écrire en JSON."""
    if isinstance(value, np.generic):
        value = value.item()
    return round(value, 5) if isinstance(value, float) else value


def save_model(model, report, models_dir=MODELS_DIR):
    """Sauvegarde le modèle (joblib) et son rapport (JSON lisible), horodatés pour garder l'historique."""
    models_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = models_dir / f"popularite_{timestamp}.joblib"
    joblib.dump(model, model_path)
    with open(models_dir / f"popularite_{timestamp}.json", "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
    return model_path


def print_report(report):
    test, baseline = report["test"], report["test_reference_naive"]
    print(f"\nMeilleur modèle : {report['meilleur_modele']}")
    print(f"Hyperparamètres choisis : {report['validation_croisee'][report['meilleur_modele']]['hyperparametres']}")
    print(f"Cible : {report['cible']} ({report['part_populaires']:.0%} des {report['nb_evenements']} événements)")
    print(f"{'Jeu de test':22} {'modèle':>8} {'référence':>10}")
    for metric in test:
        print(f"  {metric:20} {test[metric]:>8.3f} {baseline[metric]:>10.3f}")
    print("Variables les plus utiles (perte de ROC-AUC si on les mélange) :")
    for feature, importance in list(report["importance_variables"].items())[:5]:
        print(f"  {feature:22} {importance:.4f}")
