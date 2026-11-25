# Rilevamento di anomalie in rotte navali tramite dati AIS

Codice della tesi magistrale: re-implementazione in Python del framework TREAD
(Pallotta et al., 2013) applicata ai dati AIS del NOAA per le Hawaii (gennaio–marzo 2019).

## Dati

File giornalieri `AIS_2019_MM_DD` scaricati da
https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2019/index.html e salvati in
`dataset/Hawaii/2019/` (cartella non versionata).

## Ordine di esecuzione (`src/Hawaii`, con `.venv/bin/python`)

1. `Dataframe_import_cleaning.ipynb`: importazione, filtro sull'area di studio, rimozione dei
   duplicati e delle navi con pochi record (tesi, Sezione 3.3).
2. `TREAD.ipynb`: ottimizzazione dei tipi di dato, velocità media e stati delle navi
   (Sezione 3.3), waypoint con DBSCAN/H-DBSCAN, rotte e trip (Sezione 3.4).
   Salva il risultato in `out/TREAD_out.pkl`.
3. `Time_series_clustering.ipynb`: KDE, Weibull, punteggio di normalità (Sezione 3.5),
   etichettatura manuale e metriche (Capitolo 4). Legge `out/TREAD_out.pkl` e
   `out/trip_labels.csv`.

`Functions.py` e `Constants.py` contengono le funzioni e le costanti condivise.
Le mappe sono salvate in `plot/`, gli output intermedi in `out/`.

## Altre cartelle

- `thesis/`: sorgente LaTeX della tesi.
- `src/Denmark/`: esperimento preliminare, non usato nella tesi.
