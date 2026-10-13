# Analyse météorologique de Lille-Lesquin

Projet Python d'analyse des observations SYNOP de Météo-France et de prédiction
de la température par régression linéaire.

Le dépôt couvre tout le parcours demandé : chargement, contrôles de qualité,
nettoyage, agrégations, exploration graphique, structuration en fonctions,
gestion d'erreurs, modélisation, comparaison et interprétation critique.

## Résultats principaux

- 2 864 observations de la station Lille-Lesquin (`07015`) entre le 1er janvier
  et le 31 décembre 2023, au pas de trois heures. Les quelques créneaux absents
  proviennent des archives sources.
- Températures observées de **-5,0 °C à 33,9 °C**.
- Mois le plus chaud en moyenne : **juin (20,41 °C)**.
- Mois le plus pluvieux : **novembre (126,7 mm cumulés)**.
- 80,5 % des mesures de précipitations sont nulles.
- Parmi les variables météorologiques retenues, l'humidité présente la relation
  linéaire la plus forte avec la température (`r = -0,61`).

![Évolution de la température](figures/01_temperature.png)

![Relations entre variables](figures/03_relations.png)

## Modélisation

La cible est la température en degrés Celsius. Le modèle principal emploie :

- la pression au niveau de la mer ;
- l'humidité ;
- la vitesse du vent ;
- le mois et l'heure représentés par des couples sinus/cosinus, car ces
  variables sont cycliques.

Le point de rosée n'est pas utilisé : il est dérivé de la température et de
l'humidité et serait trop proche de la cible. Les données ne sont pas mélangées :
les premiers 80 % entraînent le modèle et les derniers 20 % le testent.

| Modèle | MAE test | RMSE test | R² test |
|---|---:|---:|---:|
| Météo + variables temporelles | 3,16 °C | 3,96 °C | -0,273 |
| Météo seule | 3,66 °C | 4,85 °C | -0,906 |
| Référence naïve (moyenne d'entraînement) | 5,12 °C | 6,15 °C | -2,067 |

Les variables temporelles améliorent nettement les erreurs par rapport à la
variante et à la référence naïve. Le R² de test demeure cependant négatif : la
régression linéaire prédit mieux que la moyenne d'entraînement en MAE et RMSE,
mais explique mal les variations de la période future du 21 octobre au 31
décembre. Le graphique met notamment en évidence une surestimation lors du
refroidissement de fin novembre et début décembre.

Ce résultat est une limite importante du modèle, pas une erreur de calcul. Une
relation linéaire ne capture ni les interactions météorologiques complexes, ni
la dépendance entre observations successives. Par ailleurs, les coefficients
bruts dépendent des unités et leurs amplitudes ne sont pas directement
comparables.

![Prédictions et erreurs](figures/04_predictions_erreurs.png)

## Installation et exécution

Python 3.10 ou une version plus récente est recommandé.

```bash
python -m venv .venv
```

Sous Windows :

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python projet_meteo.py
```

Sous Linux ou macOS :

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python projet_meteo.py
```

L'exécution régénère automatiquement :

- les quatre graphiques du dossier `figures/` ;
- l'agrégation mensuelle, les corrélations, les métriques et les coefficients
  dans `resultats/`.

Pour lancer les tests :

```bash
python -m pytest -q
```

## Données et reproductibilité

Le fichier prêt à l'emploi se trouve dans `data/lille_lesquin_2023.csv`. Il est
issu des [archives SYNOP officielles de Météo-France](https://donneespubliques.meteofrance.fr/?fond=produit&id_produit=90),
diffusées sous Licence Ouverte / Open Licence 2.0.

Pour le reconstruire à partir des douze archives mensuelles :

```bash
python scripts/preparer_donnees.py
```

Le script télécharge les archives `synop.202301.csv.gz` à
`synop.202312.csv.gz`, sélectionne la station `07015`, vérifie les doublons et
écrit le CSV utilisé par l'analyse.

## Choix de nettoyage

- `mq` est lu comme une valeur manquante.
- La température brute est conservée en kelvins et une nouvelle colonne en
  degrés Celsius est créée.
- La pression est convertie de pascals en hectopascals.
- Les dates sont converties en UTC avec un format strict.
- La valeur de précipitation `-0,1 mm`, qui code une trace, est ramenée à zéro.
- Les cinq précipitations manquantes restent manquantes : les remplacer par
  zéro confondrait absence de mesure et absence de pluie.
- Des bornes de plausibilité contrôlent température, pression, humidité et vent.

## Structure du dépôt

```text
.
├── data/                       # Données et provenance
├── figures/                    # Graphiques générés
├── resultats/                  # Tableaux CSV générés
├── scripts/preparer_donnees.py # Reconstruction du jeu de données
├── tests/                      # Tests automatisés
├── projet_meteo.py             # Programme principal
├── requirements.txt            # Dépendances Python
└── README.md                    # Présentation et interprétation
```
