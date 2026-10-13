# Données

`lille_lesquin_2023.csv` contient les observations SYNOP de la station
Lille-Lesquin (indicatif OMM `07015`) du 1er janvier au 31 décembre 2023.

Source : Météo-France, archives mensuelles SYNOP, Licence Ouverte / Open
Licence 2.0.

Le fichier est reproductible avec :

```bash
python scripts/preparer_donnees.py
```

Les colonnes conservées sont les données brutes nécessaires au projet : date,
pression au niveau de la mer, direction et vitesse du vent, température en
kelvins, humidité et précipitations sur trois heures. La valeur `mq` représente
une mesure manquante.
