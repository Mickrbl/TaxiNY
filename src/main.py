import pandas as pd
from google import genai
import os

# 1. Configurazione Iniziale
client = genai.Client(api_key="AIzaSyBF3HOPW86YgaEh1ugUVmvw8dxv8kxnV7U")
df_previsioni = pd.read_csv("../data/comparison_df.csv")  # La tabella dello screenshot


def get_taxi_context(zone_id, hour, day):
    """
    Cerca nella tabella i dati predetto per i parametri indicati.
    """
    filtro = (df_previsioni['zone_id'] == zone_id) & \
             (df_previsioni['hour'] == hour) & \
             (df_previsioni['day_of_week'] == day)

    risultato = df_previsioni[filtro]

    if risultato.empty:
        return "Nessun dato disponibile per questa specifica richiesta."

    riga = risultato.iloc[0]
    context = (
        f"Dati per la Zona {zone_id} il {day} alle ore {hour}:00.\n"
        f"- Domanda Predetta: {riga['Pred_Demand']} passeggeri\n"
        f"- Offerta Predetta: {riga['Pred_Supply']} taxi\n"
        f"- Rapporto Offerta/Domanda: {round(riga['Pred_Supply'] / riga['Pred_Demand'], 2)}\n"
        f"Nota tecnica: Il sistema ha un errore medio (MAE) di 63 taxi/ora."
    )
    return context


def chiedi_a_gemini(domanda_utente, zone_id, hour, day):
    # Recuperiamo i dati dalla tabella (RAG "leggero")
    dati_tabella = get_taxi_context(zone_id, hour, day)

    prompt = f"""
    Sei un assistente virtuale per la mobilità di New York. 
    Usa i seguenti dati tecnici per rispondere alla domanda dell'utente in modo naturale.

    DATI PREVISIONARI:
    {dati_tabella}

    DOMANDA UTENTE: 
    {domanda_utente}
    """

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt
    )
    return response.text


# 2. Esempio di utilizzo
if __name__ == "__main__":
    # Simuliamo un'interazione
    user_query = "Com'è la situazione taxi? Mi conviene prenderlo adesso?"
    risposta = chiedi_a_gemini(user_query, zone_id=100, hour=20, day="Thursday")
    print(risposta)