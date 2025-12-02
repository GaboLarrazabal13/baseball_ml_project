import pandas as pd
import re
import os
import numpy as np 

# --- CONFIGURACIÓN DE RUTAS Y CONSTANTES ---

# Ajusta el nivel para encontrar la carpeta 'data' desde la ubicación del script
# Esto asume que el script está en src/data_extraction/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

RAW_FILE = os.path.join(BASE_DIR, 'data', 'raw', 'mlb_standings_historicos_scraped_selenium.csv')
PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed')
PROCESSED_FILE = os.path.join(PROCESSED_DIR, 'mlb_standings_clean.csv')

# Mapeo de Franquicias (Traído de la validación del Notebook)
FRANCHISE_MAP = {
    'Florida Marlins': 'Miami Marlins',
    'Montreal Expos': 'Washington Nationals',
    'Anaheim Angels': 'Los Angeles Angels',
    'Tampa Bay Devil Rays': 'Tampa Bay Rays',
    # ASEGÚRATE DE AGREGAR AQUÍ MÁS MAPEOS VALIDADOS
}

# --- FUNCIONES DE UTILIDAD ---

def clean_special_characters(text):
    """Limpia la cadena de texto de marcadores de playoff y otros símbolos."""
    if pd.isna(text):
        return text
    
    # 1. Eliminar marcadores de playoff y guiones residuales
    text = str(text).replace('x - ', '').replace('y - ', '').replace('* - ', '').replace(' - -', '').strip()
    
    # 2. Mantener solo alfanuméricos y espacios
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

# --- FUNCIÓN PRINCIPAL DE TRANSFORMACIÓN ---

def transform_standings_data():
    """Ejecuta la limpieza, estandarización, feature engineering y carga final."""
    
    print(f"Cargando datos raw desde: {RAW_FILE}")
    try:
        df = pd.read_csv(RAW_FILE)
    except FileNotFoundError:
        print("❌ Error: Archivo raw no encontrado. Ejecuta primero el scraper.")
        return

    # ------------------------------------------------------------------
    # FASE DE TRANSFORMACIÓN (T)
    # ------------------------------------------------------------------
    
    print("1. Limpieza de texto y estandarización...")
    
    # 1.1. Aplicar limpieza de caracteres
    df['Equipo'] = df['Equipo'].apply(clean_special_characters)
    df['Liga_Division'] = df['Liga_Division'].apply(clean_special_characters)
    
    # 1.2. Estandarización de Equipos (Mapeo de franquicias)
    df['Equipo'] = df['Equipo'].replace(FRANCHISE_MAP)
    
    # 1.3. Manejo de Nulos en el nombre del equipo
    df.dropna(subset=['Equipo'], inplace=True)
    df = df[df['Equipo'] != '']
    
    # ------------------------------------------------------------------
    
    print("2. Desglose de récords HOME/AWAY y conversión a int64...")
    
    # 2.1. Desglose de strings (Crea columnas V_Casa, D_Casa, etc. como strings)
    df[['V_Casa', 'D_Casa']] = df['Record_Casa'].str.split('-', expand=True)
    df[['V_Visitante', 'D_Visitante']] = df['Record_Visitante'].str.split('-', expand=True)
    
    # 2.2. CONVERSIÓN A int64 🎯 (Asegura enteros sin decimales)
    cols_to_convert_to_int = ['V_Casa', 'D_Casa', 'V_Visitante', 'D_Visitante']

    for col in cols_to_convert_to_int:
        # Convertir a numérico (strings -> float, strings no válidos -> NaN)
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Rellenar los NaNs con 0 (esencial antes de la conversión a entero)
        df[col].fillna(0, inplace=True) 
        
        # Conversión final a int64
        df[col] = df[col].astype('int64')

    # 2.3. Eliminar las columnas originales Record_Casa y Record_Visitante
    df.drop(columns=['Record_Casa', 'Record_Visitante'], inplace=True)
    
    # ------------------------------------------------------------------
    
    print("3. Ingeniería de Características (Feature Engineering)...")
    
    # 3.1. Calcular Porcentajes de Victoria (Resultado será float64)
    df['PCT_Casa'] = df['V_Casa'] / (df['V_Casa'] + df['D_Casa'])
    df['PCT_Visitante'] = df['V_Visitante'] / (df['V_Visitante'] + df['D_Visitante'])
    
    # 3.2. Balance Casa vs. Visitante
    df['Balance_Casa_Visitante'] = df['PCT_Casa'] - df['PCT_Visitante']
    
    # 3.3. Rellenar NaNs resultantes de divisiones por cero (0/0)
    df[['PCT_Casa', 'PCT_Visitante', 'Balance_Casa_Visitante']] = df[['PCT_Casa', 'PCT_Visitante', 'Balance_Casa_Visitante']].fillna(0)
    
    # ------------------------------------------------------------------
    # FASE DE CARGA (L)
    # ------------------------------------------------------------------
    
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    df.to_csv(PROCESSED_FILE, index=False, encoding='utf-8')
    
    print(f"\n✅ Transformación completada. Datos guardados en: {PROCESSED_FILE}")
    return df

# ------------------------------------------------------------------

if __name__ == '__main__':
    transform_standings_data()