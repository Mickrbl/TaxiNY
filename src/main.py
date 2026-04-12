import pandas as pd
import joblib
import datetime
import json
import re
import warnings
import numpy as np
from google import genai

warnings.filterwarnings("ignore", category=UserWarning)

# --- 1. CONFIGURAZIONE ---
API_KEY = "AIzaSyCOMSrr7I0Oo0_Oyups94Ezp_y3E9MFMus"
client = genai.Client(api_key=API_KEY)
MODEL_NAME = "gemini-2.5-flash"

MODELS_DIR = "../models/"
ZONES_PATH = "../data/taxi_zone_lookup.csv"

try:
    MODELS = {
        "manhattan_demand": joblib.load(f"{MODELS_DIR}xgb_demand_manhattan.joblib"),
        "manhattan_supply": joblib.load(f"{MODELS_DIR}xgb_supply_manhattan.joblib"),
        "outer_demand": joblib.load(f"{MODELS_DIR}xgb_demand_outer.joblib"),
        "outer_supply": joblib.load(f"{MODELS_DIR}xgb_supply_outer.joblib")
    }
    zones_df = pd.read_csv(ZONES_PATH)
    print("Modelli e Zone CSV caricati correttamente.")

except Exception as e:
    print(f"Errore caricamento file: {e}")
    exit()


# --- 2. LOGICA DI PREDIZIONE ---

def get_prediction(params, t_type, z_info):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    try:
        dt = datetime.datetime(params['year'], params['month'], params['day'], params['hour'])

        # FIX: Usiamo 'zone_id' come richiesto dal modello, non 'Zone'
        df_input = pd.DataFrame([{
            'taxi_type': t_type.lower(),
            'zone_id': int(z_info['LocationID']),  # <--- PASSAGGIO CHIAVE
            'hour': int(params['hour']),
            'month': int(params['month']),
            'week_of_year': int(dt.isocalendar().week),
            'day_of_week': days[dt.weekday()],
            'is_weekend': 1 if dt.weekday() >= 5 else 0,
            'is_holiday': 0,
            'day_of_month': int(params['day'])
        }])

        # Setup Categorie (devono corrispondere a feature_names mismatch)
        df_input['taxi_type'] = pd.Categorical(df_input['taxi_type'], categories=['yellow', 'hvfhv', 'green', 'fhv'])
        df_input['day_of_week'] = pd.Categorical(df_input['day_of_week'], categories=days)

        prefix = params['prefix']

        # Predizione
        d_log = MODELS[f"{prefix}_demand"].predict(df_input)[0]
        s_raw = MODELS[f"{prefix}_supply"].predict(df_input)[0]

        return {
            "demand": round(float(np.exp(d_log)), 1),
            "supply": round(float(s_raw), 1),
            "ratio": round(float(s_raw / (np.exp(d_log) + 0.1)), 2)
        }
    except Exception as e:
        print(f"⚠️ Errore predizione {t_type}: {e}")
        return None


# --- 3. INTERFACCIA ASSISTENTE ---
def chiedi_a_gemini(user_query):
    now = datetime.datetime.now()
    prompt_params = f"""
    Oggi è {now.strftime('%A %d/%m/%Y %H:%M')}. 
    Analizza la richiesta: "{user_query}"

    REGOLE:
    1. Estrai la zona e traducila in inglese (es. 'aeroporto' -> 'Airport').
    2. Se l'utente cerca un aeroporto (JFK, LaGuardia, Newark), usa il nome proprio.
    3. Cerca di correggere errori di battitura. (es se uno sbaglia a scrivere Manhattan e scrive Manattan)

    Restituisci SOLO il JSON:
    {{ "zone_keyword": "string", "hour": int, "day": int, "month": int, "year": int }}
    """

    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt_params)
        if not response or not response.text:
            return "L'AI non ha risposto. Riprova tra un momento."

        json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group(0)
        params = json.loads(json_str)
    except Exception as e:
        return f"Errore nell'estrazione dati dall'AI: {e}"

    # --- LOGICA DI MATCHING POTENZIATA ---
    # 1. Gestione abbreviazioni e pulizia (es. Square -> Sq come ID 186) [cite: 12]
    keyword = params['zone_keyword'].replace("Square", "Sq").strip()
    keyword = re.sub(r'\baeroporto\b|\bdi\b', '', keyword, flags=re.IGNORECASE).strip()
    keyword = keyword.replace("/", " ")

    # 2. Filtro zone non valide (ID 1, 264, 265 come Newark o Outside NYC)
    filtro_validi = ~zones_df['Borough'].isin(['EWR', 'Unknown', 'N/A'])
    df_filtrato = zones_df[filtro_validi].copy()

    # 3. Ricerca Match
    match = df_filtrato[df_filtrato['Zone'].str.contains(keyword, case=False, na=False)]

    if match.empty:
        keyword_short = keyword.split()[0] if keyword.split() else keyword
        match = df_filtrato[df_filtrato['Zone'].str.contains(keyword_short, case=False, na=False)]

    if match.empty:
        return f"Spiacente, non ho trovato la zona '{keyword}' tra quelle gestite a New York."

    # 4. Risoluzione Ambiguità e Duplicati (es. Manhattan vs Manhattan Beach o ID duplicati) [cite: 10, 15]
    # Ordiniamo per lunghezza nome (priorità ai match brevi) e poi per LocationID
    match = match.assign(name_len=match['Zone'].str.len()).sort_values(['name_len', 'LocationID'])
    z_info = match.iloc[0]

    # 5. Determinazione Prefix Modello
    borough = str(z_info['Borough']).lower()
    params['prefix'] = 'manhattan' if borough == 'manhattan' else 'outer'

    print(
        f"🧠 [AI] Keyword: '{params['zone_keyword']}' | 📍 Match: '{z_info['Zone']}' ({z_info['Borough']}) - ID: {z_info['LocationID']}")

    # --- PREDIZIONI ---
    results = {}
    for t in ['yellow', 'hvfhv', 'green', 'fhv']:
        res = get_prediction(params, t, z_info)
        if res: results[t] = res

    if not results:
        return f"I modelli non hanno dati disponibili per {z_info['Zone']} in questa fascia oraria."

    # --- RISPOSTA FINALE ---
    context = f"Dati reali per {z_info['Zone']}: {results}"
    try:
        final_prompt = f"Rispondi a '{user_query}' in italiano. Dati tecnici che tieni per te che servono per farti rispondere in modo adeguato senza però rivelarli all'utente: {context}. Ratio > 1.2 è OK, < 0.8 è difficile trovare auto. Se nella query richiede un aeroporto non prendere in considerazione i taxi verdi che non possono andarci e in generale valuta in che zona ci sono taxi verdi (es. manhattan). Rispondi per ogni tipo di taxi e cerca di argomentare."
        risposta = client.models.generate_content(model=MODEL_NAME, contents=final_prompt)
        return risposta.text if risposta.text else "Errore nella generazione del testo finale."
    except Exception as e:
        return f"Dati calcolati ma errore nella risposta testuale: {e}\n{context}"

if __name__ == "__main__":
    print("--- 👋 NYC TAXI AI ASSISTANT ---")
    query = input("Ciao! Come posso aiutarti? ")
    print(chiedi_a_gemini(query))