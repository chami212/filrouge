"""Télécharge et extrait les observations SYNOP de Lille-Lesquin pour 2023.

Le script utilise les douze archives mensuelles officielles de Météo-France.
Il peut aussi travailler hors ligne avec ``--source-dir`` si les archives
``synop.2023MM.csv.gz`` sont déjà présentes localement.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import urllib.request
from pathlib import Path


STATION_ID = "07015"
YEAR = 2023
BASE_URL = (
    "https://donneespubliques.meteofrance.fr/donnees_libres/"
    "Txt/Synop/Archive"
)
COLONNES_CONSERVEES = [
    "numer_sta",
    "date",
    "pmer",
    "dd",
    "ff",
    "t",
    "u",
    "rr3",
]


def lire_archive(source: Path | str) -> list[dict[str, str]]:
    """Lit une archive locale ou distante et renvoie ses lignes SYNOP."""
    if isinstance(source, Path):
        flux = gzip.open(source, mode="rt", encoding="utf-8", newline="")
    else:
        reponse = urllib.request.urlopen(source, timeout=60)
        flux = io.TextIOWrapper(gzip.GzipFile(fileobj=reponse), encoding="utf-8")

    with flux:
        return list(csv.DictReader(flux, delimiter=";"))


def extraire_station(
    source_dir: Path | None,
    station_id: str = STATION_ID,
    year: int = YEAR,
) -> list[dict[str, str]]:
    """Assemble les douze mois et conserve uniquement une station."""
    observations: list[dict[str, str]] = []

    for mois in range(1, 13):
        nom = f"synop.{year}{mois:02d}.csv.gz"
        source: Path | str = source_dir / nom if source_dir else f"{BASE_URL}/{nom}"
        if isinstance(source, Path) and not source.exists():
            raise FileNotFoundError(f"Archive mensuelle absente : {source}")

        for ligne in lire_archive(source):
            if ligne.get("numer_sta") == station_id:
                observations.append(
                    {colonne: ligne.get(colonne, "mq") for colonne in COLONNES_CONSERVEES}
                )

    observations.sort(key=lambda ligne: ligne["date"])
    if not observations:
        raise ValueError(f"Aucune observation trouvée pour la station {station_id}.")

    dates = [ligne["date"] for ligne in observations]
    if len(dates) != len(set(dates)):
        raise ValueError("Les archives contiennent des dates en double.")
    if not all(date.startswith(str(year)) for date in dates):
        raise ValueError("Une observation se trouve hors de l'année demandée.")

    return observations


def ecrire_csv(observations: list[dict[str, str]], destination: Path) -> None:
    """Écrit l'extrait avec le format brut SYNOP (séparateur point-virgule)."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as fichier:
        writer = csv.DictWriter(
            fichier,
            fieldnames=COLONNES_CONSERVEES,
            delimiter=";",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(observations)


def analyser_arguments() -> argparse.Namespace:
    """Construit l'interface en ligne de commande."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir",
        type=Path,
        help="Dossier contenant les douze archives .csv.gz (sinon téléchargement).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/lille_lesquin_2023.csv"),
        help="Chemin du CSV produit.",
    )
    return parser.parse_args()


def main() -> None:
    """Prépare le fichier de données utilisé par le projet."""
    args = analyser_arguments()
    observations = extraire_station(args.source_dir)
    ecrire_csv(observations, args.output)
    print(
        f"{len(observations)} observations écrites dans {args.output} "
        f"({observations[0]['date']} -> {observations[-1]['date']})."
    )


if __name__ == "__main__":
    main()

