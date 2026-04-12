import pandas as pd
import joblib
import numpy as np

# --- 1. CARICAMENTO MODELLI ---
MODELS_DIR = "../models/"
MODELS = {
    "manhattan_demand": joblib.load(f"{MODELS_DIR}xgb_demand_manhattan.joblib"),
    "manhattan_supply": joblib.load(f"{MODELS_DIR}xgb_supply_manhattan.joblib"),
    "outer_demand": joblib.load(f"{MODELS_DIR}xgb_demand_outer.joblib"),
    "outer_supply": joblib.load(f"{MODELS_DIR}xgb_supply_outer.joblib")
}

def genera_tabella_interpretata():
    scenari_zone = [
        {"id": 230, "nome": "Times Sq (Manhattan)", "prefix": "manhattan"},
        {"id": 138, "nome": "laguardia airport", "prefix": "outer"}
    ]

    # Testiamo la serata di sabato: ore 21, 23 e mezzanotte
    ore = [21, 23, 0]
    tipi_taxi = ['yellow', 'hvfhv', 'green','fhv']

    risultati = []

    for sz in scenari_zone:
        for ora in ore:
            for t in tipi_taxi:
                # 1. Preparazione Input
                df_i = pd.DataFrame([{
                    'taxi_type': t,
                    'zone_id': sz['id'],
                    'hour': ora,
                    'month': 4,
                    'week_of_year': 15,
                    'day_of_week': 'Saturday',
                    'is_weekend': 1,
                    'is_holiday': 0,
                    'day_of_month': 11
                }])

                # Allineamento colonne e categorie
                cols = ['taxi_type', 'zone_id', 'hour', 'month', 'week_of_year', 'day_of_week', 'is_weekend', 'is_holiday', 'day_of_month']
                df_i = df_i[cols]
                df_i['taxi_type'] = pd.Categorical(df_i['taxi_type'], categories=['yellow', 'hvfhv', 'green', 'fhv'])
                df_i['day_of_week'] = pd.Categorical(df_i['day_of_week'], categories=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])

                # 2. Predizione Raw dal Modello
                d_log = MODELS[f"{sz['prefix']}_demand"].predict(df_i)[0]
                s_raw = MODELS[f"{sz['prefix']}_supply"].predict(df_i)[0]

                # 3. Trasformazione: Da logaritmo a valore reale (es. da 5.9 a ~385)
                # Usiamo np.exp per riportare la domanda sulla scala dell'offerta
                d_reale = np.exp(d_log)
                s_reale = max(0, s_raw) # L'offerta sembra già lineare nei tuoi test

                # 4. Calcolo Indice di Reperibilità (Auto / Richieste)
                # Se l'indice è > 1, ci sono più auto che clienti (buona reperibilità)
                indice = s_reale / (d_reale + 0.1)

                risultati.append({
                    'Zona': sz['nome'],
                    'Ora': f"{ora}:00",
                    'Tipo': t.upper(),
                    'Domanda (Log)': round(float(d_log), 2),
                    'Domanda (Reale)': round(float(d_reale), 1),
                    'Offerta (Reale)': round(float(s_reale), 1),
                    'Reperibilità': round(float(indice), 2)
                })

    return pd.DataFrame(risultati)

# Esecuzione
df_final = genera_tabella_interpretata()
print("\n--- 📊 ANALISI REPERIBILITÀ (DOMANDA CONVERTITA DA LOG) ---")
print(df_final.to_string(index=False))