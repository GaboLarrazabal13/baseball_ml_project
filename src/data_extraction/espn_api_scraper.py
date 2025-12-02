import pandas as pd
from bs4 import BeautifulSoup
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Configuración del Proyecto ---
# Define la ruta donde se guardará el archivo CSV
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'raw', 'mlb_standings_historicos_scraped_selenium.csv')
BASE_URL_FORMAT = "https://www.espn.com/mlb/standings/_/season/{}/group/overall"

# --- Configuración del WebDriver (solo una vez) ---
# Instalar el driver de Chrome automáticamente y configurar el servicio
service = Service(ChromeDriverManager().install())
options = webdriver.ChromeOptions()
# Ejecutar en modo "headless" (sin interfaz gráfica) para mayor velocidad
options.add_argument('--headless') 
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
# Inicializar el driver globalmente
driver = webdriver.Chrome(service=service, options=options)


def extract_standings_from_html_selenium(season):
    """Extrae datos de standings de una sola temporada usando Selenium."""
    url = BASE_URL_FORMAT.format(season)
    print(f"Scraping temporada (Selenium): {season} de {url}")
    standings_data = []

    try:
        driver.get(url)
        
        # 1. Esperar a que el elemento clave de la tabla se cargue (Máximo 20 segundos)
        # Usamos el selector CSS que identifica el contenedor de la tabla de nombres:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.Table__Scroller-wrapper'))
        )
        
        # Obtener el HTML de la página después de que se ejecuta el JavaScript
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # --- LÓGICA DE EXTRACCIÓN (LA MISMA QUE ANTES) ---
        
        table_wrappers = soup.find_all('div', class_='Table__Scroller-wrapper')

        if not table_wrappers or len(table_wrappers) < 2:
            print(f"Advertencia: No se encontraron los dos contenedores principales (fijo/scroll) para {season}.")
            return []
            
        name_table_container = table_wrappers[0]
        stats_table_container = table_wrappers[1]
        
        # Buscar las filas dentro de tbody
        name_rows = name_table_container.find('tbody').find_all('tr', class_='Table__TR')
        stats_rows = stats_table_container.find('tbody').find_all('tr', class_='Table__TR')

        if len(name_rows) != len(stats_rows) or len(name_rows) < 1:
            print(f"Advertencia: Número de filas inconsistente o insuficiente para {season}. Filas encontradas: {len(name_rows)}")
            return []

        for i in range(len(name_rows)):
            team_row = name_rows[i]
            stats_row = stats_rows[i]
            
            # Extracción de Nombres
            team_name_tag = team_row.find('a', class_='AnchorLink')
            team_name = team_name_tag.text.strip() if team_name_tag else team_row.find('td').text.strip()
            
            league_division = "Overall" 
            
            # Extracción de Estadísticas
            stat_cells = stats_row.find_all('td')
            
            if len(stat_cells) >= 3:
                wins = stat_cells[0].text.strip()
                losses = stat_cells[1].text.strip()
                win_pct = stat_cells[2].text.strip() 
                
                standings_data.append({
                    'Temporada': season,
                    'Liga_Division': league_division,
                    'Equipo': team_name,
                    'Victorias': wins,
                    'Derrotas': losses,
                    'Porcentaje_Ganador': win_pct
                })
            else:
                print(f"Advertencia: Faltan celdas de estadísticas para {team_name} en {season}.")

        return standings_data

    except Exception as e:
        print(f"Error durante el scraping con Selenium para {season}: {e}")
        return []

def main_scraper():
    """Bucle principal para iterar sobre todas las temporadas y cerrar el driver."""
    all_standings = []
    
    # Intentaremos de 2015 a 2025 (periodo más probable de éxito)
    for season in range(2003, 2026):
        # NOTA: Ya no necesitamos time.sleep(2) porque Selenium maneja la latencia
        data = extract_standings_from_html_selenium(season)
        all_standings.extend(data)
        
    # CERRAR EL DRIVER ES CRUCIAL
    driver.quit() 

    # Convertir y guardar
    if all_standings:
        df = pd.DataFrame(all_standings)
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        df.to_csv(OUTPUT_PATH, index=False, encoding='utf-8')
        print(f"\nDatos de Standings Guardados exitosamente en: {OUTPUT_PATH}")
    else:
        print("\nNo se pudieron extraer datos de ninguna temporada.")


if __name__ == '__main__':
    main_scraper()