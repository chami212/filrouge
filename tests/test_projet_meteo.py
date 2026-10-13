from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from projet_meteo import (
    charger_donnees,
    nettoyer_donnees,
    preparer_variables,
    scinder_chronologiquement,
)


def jeu_brut_minimal() -> pd.DataFrame:
    """Construit quelques observations valides au format SYNOP brut."""
    return pd.DataFrame(
        {
            "numer_sta": pd.Series(["07015"] * 3, dtype="string"),
            "date": pd.Series(
                ["20230101000000", "20230101030000", "20230101060000"],
                dtype="string",
            ),
            "pmer": [101300, 101250, 101200],
            "ff": [3.0, 3.5, 4.0],
            "t": [273.15, 274.15, 275.15],
            "u": [90, 88, 85],
            "rr3": [-0.1, 0.0, np.nan],
        }
    )


def test_charger_donnees_signale_un_fichier_absent(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="introuvable"):
        charger_donnees(tmp_path / "absent.csv")


def test_nettoyage_convertit_unites_et_trace_de_pluie() -> None:
    nettoye = nettoyer_donnees(jeu_brut_minimal())

    assert nettoye["temperature_c"].tolist() == pytest.approx([0, 1, 2])
    assert nettoye["pression_hpa"].tolist() == pytest.approx(
        [1013, 1012.5, 1012]
    )
    assert nettoye["precip_3h_mm"].iloc[0] == 0
    assert pd.isna(nettoye["precip_3h_mm"].iloc[2])
    assert nettoye["mois"].tolist() == [1, 1, 1]


def test_nettoyage_signale_une_colonne_absente() -> None:
    brut = jeu_brut_minimal().drop(columns="u")
    with pytest.raises(ValueError, match="u"):
        nettoyer_donnees(brut)


def test_preparer_variables_signale_une_variable_absente() -> None:
    nettoye = nettoyer_donnees(jeu_brut_minimal())
    with pytest.raises(ValueError, match="variable_inconnue"):
        preparer_variables(nettoye, ["variable_inconnue"])


def test_scission_est_chronologique() -> None:
    dates = pd.Series(pd.date_range("2023-01-01", periods=10, freq="3h"))
    X = pd.DataFrame({"x": range(10)})
    y = pd.Series(range(10))

    _, _, _, _, dates_train, dates_test = scinder_chronologiquement(
        X, y, dates, proportion_test=0.2
    )

    assert len(dates_train) == 8
    assert len(dates_test) == 2
    assert dates_train.max() < dates_test.min()

