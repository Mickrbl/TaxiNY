"""
################################################################################
# PROGETTO TAXI NYC
################################################################################

---
1. INFORMAZIONI GENERALI SUL VIAGGIO (YELLOW TAXI)
---

1. VendorID: Codice che indica il fornitore tecnologico TPEP (1=Creative Mobile Technologies, 2=Curb Mobility, 6=Myle Technologies Inc, 7=Helix).
   ❌ DA RIMUOVERE: Identificativo tecnico non utile per la previsione del prezzo o della domanda.

2. tpep_pickup_datetime: La data e l'ora in cui il tassametro è stato attivato (Meter Engaged).
   ✅ DA PRENDERE: Essenziale per estrarre ora del giorno, giorno della settimana e stagionalità.

3. tpep_dropoff_datetime: La data e l'ora in cui il viaggio è terminato e il tassametro è stato fermato.
   ✅ DA PRENDERE: Necessaria per calcolare la durata reale del viaggio (delta_time).

4. passenger_count: Il numero di passeggeri nel veicolo inserito manualmente dal conducente.
   ❌ DA RIMUOVERE: Un taxi è occupato indipendentemente dal numero di persone (1 taxi = 1 unità di domanda).

5. trip_distance: La distanza del viaggio percorsa in miglia riportata dal tassametro.
   ✅ DA PRENDERE: Variabile fondamentale per il calcolo e la stima del prezzo.

6. RatecodeID: Il codice della tariffa finale applicata alla fine del viaggio (1=Standard, 2=JFK, 3=Newark, 4=Nassau or Westchester, 5=Negotiated fare, 6=Group ride, 99=Null/unknown).
   ❌ DA RIMUOVERE: Il codice 99 indica un errore e va filtrato durante la pulizia.

7. store_and_fwd_flag: Indica se il record è stato memorizzato nel veicolo prima dell'invio al server (Y/N).
   ❌ DA RIMUOVERE: Dato tecnico non rilevante per i modelli di previsione.

8. PULocationID: ID della Zona TLC in cui il tassametro è stato attivato (Pickup).
   ✅ DA PRENDERE: Fondamentale per mappare la domanda geografica e le tariffe specifiche.

9. DOLocationID: ID della Zona TLC in cui il tassametro è stato disattivato (Dropoff).
   ✅ DA PRENDERE: Essenziale per calcolare il prezzo basato sulla destinazione (es. zone aeroportuali).

10. payment_type: Codice numerico che indica il metodo di pagamento (0=Flex Fare trip, 1=Credit card, 2=Cash, 3=No charge, 4=Dispute, 5=Unknown, 6=Voided trip).
    ⚠️ DA USARE PER LA PULIZIA: Essenziale per filtrare corse non valide (5, 6).

---
2. DEFINIZIONE DEI COSTI E TASSE (IN DOLLARI)
---

11. fare_amount: La tariffa calcolata dal tassametro in base puramente a tempo e distanza.
    ❌ DA RIMUOVERE: Informazione già catturata implicitamente dagli ID di Arrivo e Partenza.

12. extra: Supplementi vari (es. $2.50 per ore di punta o $1.00 per ore notturne).
    ❌ DA RIMUOVERE: Informazione catturata dall'orario di partenza e dagli ID zona.

13. mta_tax: Tassa MTA di $0.50 attivata automaticamente in base alla tariffa.
    ❌ DA RIMUOVERE: Costo fisso catturato implicitamente per i viaggi nell'area urbana.

14. tip_amount: Importo della mancia (popolato automaticamente solo per pagamenti elettronici).
    ⚠️ DA USARE PER LA PULIZIA: Essenziale per ricalcolare il "Totale Pulito" (Target).

15. tolls_amount: Importo totale di tutti i pedaggi pagati (ponti, tunnel, etc.).
    ❌ DA RIMUOVERE: Il costo dei pedaggi è già catturato dalla combinazione degli ID zona di partenza e arrivo.

16. improvement_surcharge: Supplemento di $1.00 introdotto nel 2015 per il miglioramento dell'accessibilità dei taxi.
    ❌ DA RIMUOVERE: Costo fisso già inglobato in total_amount, non utile per la previsione del prezzo.

17. total_amount: L'importo totale addebitato (non include le mance in contanti).
    ✅ TARGET: L'obiettivo principale del modello di previsione del prezzo.

    ⚠️ Nota: Deve essere pulita sottraendo la mancia (tip_amount) per ottenere 
    il costo reale del servizio.

18. congestion_surcharge: Supplemento congestione dello Stato di New York ($2.50 per taxi gialli).
    ❌ DA RIMUOVERE: Catturato dall'ID zona (Manhattan south of 96th St).

19. Airport_fee: Tariffa aeroportuale per i prelievi negli aeroporti LaGuardia e JFK ($1.75).
    ❌ DA RIMUOVERE: Il modello deduce questa tassa dagli ID zona aeroportuali (132, 138).

20. cbd_congestion_fee: Addebito per ogni viaggio nella zona "MTA's Congestion Relief Zone" attivo dal 5 Gennaio 2025.
    ❌ DA RIMUOVERE: Informazione geografica catturata interamente dagli ID di zona.


################################################################################
# SPECIFICHE TAXI VERDI (LPEP) - DIFFERENZE CHIAVE
################################################################################

1. TRIP_TYPE (Esclusivo LPEP)
   - 1 = Street-hail (Corsa presa in strada)
   - 2 = Dispatch (Corsa prenotata tramite centrale/app)
   ❌ DA RIMUOVERE: Incompatibile con il dataset dei taxi gialli; vogliamo un dataset unico e uniforme.

2. NOMENCLATURA COLONNE
   - ⚠️ Il prefisso cambia da `tpep_` a `lpep_` per le date di viaggio e altro ancora 
     (bisogna standardizzare i nomi).


################################################################################
# POSSIBILE ROADMAP DI IMPLEMENTAZIONE
################################################################################

1. DATA CLEANING & PRE-PROCESSING
   - Obiettivo: Ottenere un dataset di alta qualità (Yellow + Green).
   - Azioni: 
     - Rimuovere record con distanza = 0, durata nulla, Ratecode 99 o Payment 5/6.
     - Calcolare 'clean_total' e gestire i NaN.
     - Fare eventuali plot per capire meglio i dati.
     - Estrarre variabili temporali: `DayOfWeek`, `Hour`, `min`.
     - Creare indicatori binari: `is_weekend`, `is_holiday` etc... .
     - Calcolare la `Duration` (delta tempo tra dropoff e pickup).

2. PREVISIONE DELLA DOMANDA
   - Algoritmo: Random Forest Regressor.
   - Input (Features): PULocationID, DayOfWeek, Hour, min.
   - Logica di Aggregazione: Creare una variabile "Domanda" come conteggio delle 
     corse in una finestra mobile (esempio: 1h dal tempo di interesse).
   - Obiettivo: Fornire una stima del volume di taxi richiesti per ogni zona 
     e fascia oraria, filtrando i "viaggi finti" e le cancellazioni istantanee.

3. STIMATORE DEL DURATA E PREZZO
    DURATA:
    - Algoritmo: Random Forest Regressor.
    - Target: Durata del viaggio.
    - Input (Features): PULocationID, DOLocationID, trip_distance, DayOfWeek, (ore e min partenza).
    - NB: Quando andiamo a settare la 'trip_distance' una volta che abbiamo il modello, essa
        potrà essere fornita tramite API esterne (es. Google Maps) per ottenere il tempo stimato dall'utente.

   PREZZO:
    - Algoritmo: Random Forest Regressor.
    - Target: Prezzo del viaggio.
    - Input (Features): DURATA(stimata dal modello precedente), PULocationID, DOLocationID, trip_distance, DayOfWeek, (ore e min partenza).
    - NB: Quando andiamo a settare la 'trip_distance' una volta che abbiamo il modello, essa
        potrà essere fornita tramite API esterne (es. Google Maps) per ottenere il costo stimato dall'utente.

################################################################################
"""