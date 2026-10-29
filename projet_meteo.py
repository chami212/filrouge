#Analyse des observations météo de Lille-Lesquin et régression linéaire

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(".cache/matplotlib").resolve()))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error


STATION_ID = "07015"
ANNEE = 2023
KELVIN_VERS_CELSIUS = 273.15
COLONNES_REQUISES = {"numer_sta", "date", "pmer", "ff", "t", "u", "rr3"}
VARIABLES_METEO = ["pression_hpa", "humidite_pct", "vent_ms"]
VARIABLES_PRINCIPALES = VARIABLES_METEO + [
    "mois_sin",
    "mois_cos",
    "heure_sin",
    "heure_cos",
]
NOMS_AFFICHAGE = {
    "temperature_c": "Température (°C)",
    "pression_hpa": "Pression (hPa)",
    "humidite_pct": "Humidité (%)",
    "vent_ms": "Vent (m/s)",
    "mois_sin": "Mois (sin)",
    "mois_cos": "Mois (cos)",
    "heure_sin": "Heure (sin)",
    "heure_cos": "Heure (cos)",
}
MOIS_FR = [
    "Jan",
    "Fév",
    "Mar",
    "Avr",
    "Mai",
    "Juin",
    "Juil",
    "Août",
    "Sep",
    "Oct",
    "Nov",
    "Déc",
]


def verifier_colonnes(df: pd.DataFrame, colonnes: set[str]) -> None:
    #erreur si une colonne nécessaire est absente
    manquantes = sorted(colonnes - set(df.columns))
    if manquantes:
        raise ValueError(f"Colonnes obligatoires absentes : {', '.join(manquantes)}")


def charger_donnees(chemin: Path) -> pd.DataFrame:
    """
    charge le CSV SYNOP
    chemin du fichier CSV séparé par des points-virgules et retourne un
    dataFrame brut dont les identifiants et les dates restent du texte
    """
    if not chemin.exists():
        raise FileNotFoundError(f"Fichier de données introuvable : {chemin}")

    df = pd.read_csv(
        chemin,
        sep=";",
        na_values=["mq"],
        dtype={"numer_sta": "string", "date": "string"},
    )
    if df.empty:
        raise ValueError("Le fichier de données est vide.")
    verifier_colonnes(df, COLONNES_REQUISES)
    return df


def rapport_valeurs_manquantes(df: pd.DataFrame) -> pd.DataFrame:
    #calcule le nombre et le pourcentage de valeur manquantes par colonne
    rapport = pd.DataFrame(
        {
            "nombre": df.isna().sum(),
            "pourcentage": df.isna().mean().mul(100),
        }
    )
    return rapport.loc[rapport["nombre"] > 0].sort_values("pourcentage", ascending=False)


def nettoyer_donnees(df_brut: pd.DataFrame) -> pd.DataFrame:
    verifier_colonnes(df_brut, COLONNES_REQUISES)
    df = df_brut.copy()

    for colonne in ["pmer", "ff", "t", "u", "rr3"]:
        df[colonne] = pd.to_numeric(df[colonne], errors="coerce")

    df["date"] = pd.to_datetime(
        df["date"], format="%Y%m%d%H%M%S", errors="coerce", utc=True
    )
    df = df.loc[
        (df["numer_sta"] == STATION_ID)
        & (df["date"].dt.year == ANNEE)
    ].copy()
    if df.empty:
        raise ValueError(
            f"Aucune observation pour la station {STATION_ID} en {ANNEE}."
        )

    df = df.sort_values("date").drop_duplicates(subset="date", keep="first")
    df["temperature_c"] = df["t"] - KELVIN_VERS_CELSIUS
    df["pression_hpa"] = df["pmer"] / 100
    df["humidite_pct"] = df["u"]
    df["vent_ms"] = df["ff"]
    df["precip_3h_mm"] = df["rr3"].replace(-0.1, 0)
    df.loc[df["precip_3h_mm"] < 0, "precip_3h_mm"] = np.nan
    df["mois"] = df["date"].dt.month
    df["heure"] = df["date"].dt.hour
    df["mois_sin"] = np.sin(2 * np.pi * (df["mois"] - 1) / 12)
    df["mois_cos"] = np.cos(2 * np.pi * (df["mois"] - 1) / 12)
    df["heure_sin"] = np.sin(2 * np.pi * df["heure"] / 24)
    df["heure_cos"] = np.cos(2 * np.pi * df["heure"] / 24)

    controles = {
        "temperature_c": (-40, 50),
        "pression_hpa": (870, 1085),
        "humidite_pct": (0, 100),
        "vent_ms": (0, 75),
    }
    for colonne, (minimum, maximum) in controles.items():
        invalides = df[colonne].notna() & ~df[colonne].between(minimum, maximum)
        if invalides.any():
            raise ValueError(
                f"{invalides.sum()} valeur(s) non plausible(s) dans {colonne}."
            )

    return df


def calculer_agregation_mensuelle(df: pd.DataFrame) -> pd.DataFrame:
    #calculs moyenne minimum et maximum mensuels de la temp
    agregation = (
        df.groupby("mois", observed=True)["temperature_c"]
        .agg(moyenne="mean", minimum="min", maximum="max", observations="count")
        .reindex(range(1, 13))
    )
    agregation.index.name = "mois"
    return agregation


def calculer_correlations(df: pd.DataFrame) -> pd.DataFrame:
    #renvoi la matrice de correlation des variables meteorologiques
    colonnes = ["temperature_c", "pression_hpa", "humidite_pct", "vent_ms"]
    return df[colonnes].corr()


def enregistrer_figure(figure: plt.Figure, chemin: Path) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(chemin, dpi=160, bbox_inches="tight")
    plt.close(figure)


def tracer_temperature(df: pd.DataFrame, dossier: Path) -> None:
    #trace les observations et la synthèse mensuelle de température
    mensuelle = df.set_index("date")["temperature_c"].resample("MS").mean()
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), constrained_layout=True)

    axes[0].plot(df["date"], df["temperature_c"], color="#dd5f24", linewidth=0.7)
    axes[0].set_title("Température observée à Lille-Lesquin en 2023")
    axes[0].set_ylabel("Température (°C)")
    axes[0].grid(alpha=0.25)

    axes[1].plot(
        mensuelle.index,
        mensuelle.values,
        marker="o",
        color="#176b87",
        linewidth=2,
    )
    axes[1].set_title("Température moyenne mensuelle")
    axes[1].set_xlabel("Date")
    axes[1].set_ylabel("Température (°C)")
    axes[1].grid(alpha=0.25)
    enregistrer_figure(fig, dossier / "01_temperature.png")


def tracer_precipitations(df: pd.DataFrame, dossier: Path) -> None:
    pluie = df["precip_3h_mm"].dropna()
    pluie_positive = pluie.loc[pluie > 0]
    cumuls = df.groupby("mois", observed=True)["precip_3h_mm"].sum(min_count=1)
    proportion_zero = (pluie == 0).mean() * 100

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    axes[0].hist(pluie_positive, bins=30, color="#4a90a4", edgecolor="white")
    axes[0].set_title(
        "Précipitations positives sur 3 h\n"
        f"({proportion_zero:.1f} % des mesures sont nulles)"
    )
    axes[0].set_xlabel("Précipitations (mm/3 h)")
    axes[0].set_ylabel("Nombre d'observations")
    axes[0].grid(axis="y", alpha=0.25)

    axes[1].bar(MOIS_FR, cumuls.reindex(range(1, 13)), color="#176b87")
    axes[1].set_title("Cumul mensuel des précipitations")
    axes[1].set_xlabel("Mois")
    axes[1].set_ylabel("Précipitations (mm)")
    axes[1].tick_params(axis="x", rotation=35)
    axes[1].grid(axis="y", alpha=0.25)
    enregistrer_figure(fig, dossier / "02_precipitations.png")


def tracer_relations(df: pd.DataFrame, dossier: Path) -> str:
    """Trace la matrice de corrélation et le nuage le plus informatif."""
    correlations = calculer_correlations(df)
    candidates = correlations.loc["temperature_c", VARIABLES_METEO].abs()
    variable = candidates.idxmax()

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    image = axes[0].imshow(correlations, cmap="RdBu_r", vmin=-1, vmax=1)
    etiquettes = [NOMS_AFFICHAGE[col] for col in correlations.columns]
    axes[0].set_xticks(range(len(etiquettes)), etiquettes, rotation=40, ha="right")
    axes[0].set_yticks(range(len(etiquettes)), etiquettes)
    axes[0].set_title("Matrice de corrélation")
    for i in range(len(correlations)):
        for j in range(len(correlations.columns)):
            axes[0].text(
                j,
                i,
                f"{correlations.iloc[i, j]:.2f}",
                ha="center",
                va="center",
                color="white" if abs(correlations.iloc[i, j]) > 0.55 else "black",
            )
    fig.colorbar(image, ax=axes[0], fraction=0.046, pad=0.04)

    axes[1].scatter(
        df[variable],
        df["temperature_c"],
        s=10,
        alpha=0.35,
        color="#dd5f24",
    )
    coefficient = correlations.loc["temperature_c", variable]
    axes[1].set_title(
        f"Température et {NOMS_AFFICHAGE[variable].lower()} (r = {coefficient:.2f})"
    )
    axes[1].set_xlabel(NOMS_AFFICHAGE[variable])
    axes[1].set_ylabel("Température (°C)")
    axes[1].grid(alpha=0.25)
    enregistrer_figure(fig, dossier / "03_relations.png")
    return variable


def preparer_variables(
    df: pd.DataFrame, variables: list[str]
) -> tuple[pd.DataFrame, pd.Series, pd.Series, int]:
    """Prépare des lignes numériques complètes et alignées pour le modèle."""
    necessaires = set(variables) | {"temperature_c", "date"}
    verifier_colonnes(df, necessaires)
    complet = df[["date", "temperature_c", *variables]].dropna().sort_values("date")
    lignes_perdues = len(df) - len(complet)
    if len(complet) < 20:
        raise ValueError("Pas assez de lignes complètes pour entraîner le modèle.")
    return (
        complet[variables],
        complet["temperature_c"],
        complet["date"],
        lignes_perdues,
    )


def scinder_chronologiquement(
    X: pd.DataFrame,
    y: pd.Series,
    dates: pd.Series,
    proportion_test: float = 0.20,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series, pd.Series]:
    """Réserve les dernières observations au test, sans mélange temporel."""
    if not 0 < proportion_test < 1:
        raise ValueError("La proportion de test doit être comprise entre 0 et 1.")
    if not (len(X) == len(y) == len(dates)):
        raise ValueError("X, y et dates ne sont pas alignés.")

    coupure = int(len(X) * (1 - proportion_test))
    if coupure < 2 or len(X) - coupure < 2:
        raise ValueError("Jeu de données trop petit pour cette séparation.")
    return (
        X.iloc[:coupure],
        X.iloc[coupure:],
        y.iloc[:coupure],
        y.iloc[coupure:],
        dates.iloc[:coupure],
        dates.iloc[coupure:],
    )


def calculer_metriques(y_reel: pd.Series, y_predit: np.ndarray) -> dict[str, float]:
    return {
        "MAE_C": float(mean_absolute_error(y_reel, y_predit)),
        "RMSE_C": float(root_mean_squared_error(y_reel, y_predit)),
        "R2": float(r2_score(y_reel, y_predit)),
    }


def entrainer_modele(
    df: pd.DataFrame,
    variables: list[str],
    nom: str,
    proportion_test: float = 0.20,
) -> dict[str, object]:
    #entrainement pour une régression linéaire et evalue train test et ref
    X, y, dates, lignes_perdues = preparer_variables(df, variables)
    X_train, X_test, y_train, y_test, dates_train, dates_test = (
        scinder_chronologiquement(X, y, dates, proportion_test)
    )
    modele = LinearRegression()
    modele.fit(X_train, y_train)
    pred_train = modele.predict(X_train)
    pred_test = modele.predict(X_test)
    prediction_naive = np.full(len(y_test), y_train.mean())

    return {
        "nom": nom,
        "variables": variables,
        "modele": modele,
        "lignes_perdues": lignes_perdues,
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "dates_train": dates_train,
        "dates_test": dates_test,
        "pred_train": pred_train,
        "pred_test": pred_test,
        "metriques_train": calculer_metriques(y_train, pred_train),
        "metriques_test": calculer_metriques(y_test, pred_test),
        "metriques_reference": calculer_metriques(y_test, prediction_naive),
    }


def tracer_predictions(resultat: dict[str, object], dossier: Path) -> None:
    dates = resultat["dates_test"]
    y_test = resultat["y_test"]
    predictions = resultat["pred_test"]
    residus = np.asarray(y_test) - np.asarray(predictions)

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), constrained_layout=True)
    axes[0].plot(dates, y_test, label="Réel", color="#202124", linewidth=1.2)
    axes[0].plot(
        dates,
        predictions,
        label="Prédit",
        color="#dd5f24",
        linewidth=1.2,
        alpha=0.9,
    )
    axes[0].set_title("Températures réelles et prédites sur la période de test")
    axes[0].set_ylabel("Température (°C)")
    axes[0].legend()
    axes[0].grid(alpha=0.25)

    axes[1].scatter(dates, residus, s=13, alpha=0.55, color="#176b87")
    axes[1].axhline(0, color="#202124", linewidth=1)
    axes[1].set_title("Erreurs de prédiction dans le temps")
    axes[1].set_xlabel("Date")
    axes[1].set_ylabel("Erreur réel - prédit (°C)")
    axes[1].grid(alpha=0.25)
    enregistrer_figure(fig, dossier / "04_predictions_erreurs.png")


def exporter_resultats(
    agregation: pd.DataFrame,
    correlations: pd.DataFrame,
    resultats_modeles: list[dict[str, object]],
    dossier: Path,
) -> None:
    dossier.mkdir(parents=True, exist_ok=True)
    agregation.round(2).to_csv(dossier / "agregation_mensuelle.csv")
    correlations.round(3).to_csv(dossier / "correlations.csv")

    lignes_metriques: list[dict[str, object]] = []
    lignes_coefficients: list[dict[str, object]] = []
    for resultat in resultats_modeles:
        for jeu in ["train", "test", "reference"]:
            for metrique, valeur in resultat[f"metriques_{jeu}"].items():
                lignes_metriques.append(
                    {
                        "modele": resultat["nom"],
                        "jeu": jeu,
                        "metrique": metrique,
                        "valeur": valeur,
                    }
                )
        modele = resultat["modele"]
        for variable, coefficient in zip(resultat["variables"], modele.coef_):
            lignes_coefficients.append(
                {
                    "modele": resultat["nom"],
                    "variable": variable,
                    "coefficient": coefficient,
                }
            )

    pd.DataFrame(lignes_metriques).round(4).to_csv(
        dossier / "metriques_modeles.csv", index=False
    )
    pd.DataFrame(lignes_coefficients).round(4).to_csv(
        dossier / "coefficients_modeles.csv", index=False
    )


def afficher_synthese(
    df_brut: pd.DataFrame,
    df: pd.DataFrame,
    agregation: pd.DataFrame,
    variable_liee: str,
    principal: dict[str, object],
    variante: dict[str, object],
) -> None:
    print(f"Observations chargées : {len(df_brut)}")
    print(f"Période : {df['date'].min()} -> {df['date'].max()}")
    print(
        "Température : "
        f"{df['temperature_c'].min():.1f} à {df['temperature_c'].max():.1f} °C"
    )
    rapport = rapport_valeurs_manquantes(df)
    print("\nValeurs manquantes après nettoyage :")
    print(rapport.round(2).to_string() if not rapport.empty else "Aucune")
    print("\nAgrégation mensuelle (°C) :")
    print(agregation.round(2).to_string())
    print(
        "\nVariable météo la plus corrélée à la température : "
        f"{NOMS_AFFICHAGE[variable_liee]}"
    )

    for resultat in [principal, variante]:
        test = resultat["metriques_test"]
        print(
            f"\n{resultat['nom']} - test : "
            f"MAE={test['MAE_C']:.2f} °C, RMSE={test['RMSE_C']:.2f} °C, "
            f"R²={test['R2']:.3f}"
        )
    reference = principal["metriques_reference"]
    print(
        "Référence naïve (moyenne d'entraînement) : "
        f"MAE={reference['MAE_C']:.2f} °C, RMSE={reference['RMSE_C']:.2f} °C, "
        f"R²={reference['R2']:.3f}"
    )
    print(
        "\nInterprétation : les variables temporelles cycliques décrivent les "
        "cycles saisonnier et journalier. Une régression linéaire reste limitée : "
        "elle ne modélise ni les interactions complexes ni la dépendance entre "
        "observations successives. Les coefficients bruts dépendent des unités "
        "des variables et leurs amplitudes ne sont donc pas directement comparables."
    )


def analyser_arguments() -> argparse.Namespace:
    """Construit les options de lancement du projet."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/lille_lesquin_2023.csv"),
        help="Fichier CSV SYNOP à analyser.",
    )
    parser.add_argument(
        "--figures",
        type=Path,
        default=Path("figures"),
        help="Dossier de sortie des graphiques.",
    )
    parser.add_argument(
        "--resultats",
        type=Path,
        default=Path("resultats"),
        help="Dossier de sortie des tableaux.",
    )
    return parser.parse_args()


def main() -> None:
    """Exécute l'analyse complète, du chargement aux résultats du modèle."""
    args = analyser_arguments()
    try:
        df_brut = charger_donnees(args.data)
        df = nettoyer_donnees(df_brut)
        agregation = calculer_agregation_mensuelle(df)
        correlations = calculer_correlations(df)

        tracer_temperature(df, args.figures)
        tracer_precipitations(df, args.figures)
        variable_liee = tracer_relations(df, args.figures)

        principal = entrainer_modele(
            df, VARIABLES_PRINCIPALES, "meteo_et_temps", proportion_test=0.20
        )
        variante = entrainer_modele(
            df, VARIABLES_METEO, "meteo_seule", proportion_test=0.20
        )
        tracer_predictions(principal, args.figures)
        exporter_resultats(
            agregation, correlations, [principal, variante], args.resultats
        )
        afficher_synthese(
            df_brut, df, agregation, variable_liee, principal, variante
        )
    except (FileNotFoundError, ValueError, pd.errors.ParserError) as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        raise SystemExit(1) from erreur


if __name__ == "__main__":
    main()
