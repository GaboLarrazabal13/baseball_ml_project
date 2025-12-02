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
from selenium.common.exceptions import TimeoutException, WebDriverException

# --- Configuración de Rutas y Constantes ---
# Define la ruta donde se guardará el archivo CSV FINAL
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'raw', 'mlb_standings_historicos_scraped_selenium.csv')
# Ruta para guardar los archivos HTML (La variable queda, pero su uso está comentado)
HTML_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'html_cache_espn_selenium')

BASE_URL_FORMAT = "https://www.espn.com/mlb/standings/_/season/{}/group/overall"
START_YEAR = 2003
END_YEAR = 2025

# Selectores principales
MAIN_TABLE_CONTAINER_CLASS = 'ResponsiveTable--fixed-left'
MAIN_TABLE_CONTAINER_SELECTOR = f'div.{MAIN_TABLE_CONTAINER_CLASS}'


# --- Configuración del WebDriver (Global y Optimizado para Velocidad) ---
driver = None
try:
    # Inicialización del driver
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    
    # 🚀 OPTIMIZACIÓN 1: Modo Headless (Ejecución en segundo plano)
    options.add_argument('--headless') 
    
    # 🚀 OPTIMIZACIÓN 2: Deshabilitar recursos pesados (Imágenes/CSS/Popups)
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage') 
    options.add_argument('log-level=3') 
    options.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2, 
        "profile.managed_default_content_settings.stylesheets": 2, 
        "profile.default_content_settings.popups": 2, 
    })
    
    driver = webdriver.Chrome(service=service, options=options)
except WebDriverException as e:
    print(f"Error al inicializar el WebDriver: {e}")
    driver = None


def extract_standings_from_html_selenium(season):
    """
    Extrae datos de standings de una sola temporada usando Selenium.
    Usa la navegación precisa para nombres y extrae HOME/AWAY.
    """
    if driver is None:
        return []

    url = BASE_URL_FORMAT.format(season)
    print(f"Scraping temporada (Selenium): {season} de {url}")
    standings_data = []

    try:
        driver.get(url)
        
        # --- 1. LÓGICA PARA CERRAR EL POP-UP DE PRIVACIDAD ---
        try:
            accept_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[text()="Accept All"]'))
            )
            accept_button.click()
            print("   -> Pop-up de consentimiento 'Accept All' cerrado.")
            
        except TimeoutException:
            print("   -> No se detectó el pop-up de consentimiento. Continuando...")
            pass
        except Exception:
             pass
        # ----------------------------------------------------
        
        # 🚀 OPTIMIZACIÓN 3: Reducir la espera bruta
        time.sleep(1.5) 
        
        # 3. ESPERA CLAVE: Esperar a que el CONTENEDOR PRINCIPAL sea VISIBLE (Espera dinámica)
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, MAIN_TABLE_CONTAINER_SELECTOR))
        )
        
        # 4. OBTENER EL HTML GENERADO LOCALMENTE
        page_source = driver.page_source
        
        # 5. PARSEO Y EXTRACCIÓN CON BEAUTIFULSOUP
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # 5a. Buscamos el contenedor principal
        main_container = soup.find('div', class_=lambda c: c and MAIN_TABLE_CONTAINER_CLASS in c.split())
        
        if not main_container:
            print(f"❌ Error crítico: No se encontró el contenedor {MAIN_TABLE_CONTAINER_CLASS} en el HTML para {season}.")
            return []

        # 5b. Navegación para la TABLA DE NOMBRES (Fija)
        flex_container = main_container.find('div', class_='flex')
        if flex_container:
            name_table = flex_container.find('table', class_=lambda c: c and 'Table--fixed-left' in c)
        else:
            name_table = None
        
        # 5c. Navegación para la TABLA DE ESTADÍSTICAS (Scroll)
        scroller_wrapper = main_container.find('div', class_='Table__ScrollerWrapper')
        
        stats_table = None
        if scroller_wrapper:
            scroller = scroller_wrapper.find('div', class_='Table__Scroller')
            if scroller:
                stats_table = scroller.find('table', class_=lambda c: c and 'Table--align-right' in c)

        if not name_table or not stats_table:
            print(f"❌ Fallo de extracción: No se pudieron encontrar las tablas de nombres o estadísticas usando la ruta de selectores para {season}.")
            return []
            
        # 6. EXTRACCIÓN DE FILAS
        name_rows = name_table.find('tbody').find_all('tr', class_='Table__TR')
        stats_rows = stats_table.find('tbody').find_all('tr', class_='Table__TR')

        if len(name_rows) != len(stats_rows) or len(name_rows) < 1:
            print(f"Advertencia: Número de filas inconsistente o insuficiente para {season}. Filas encontradas: {len(name_rows)}")
            return []

        for i in range(len(name_rows)):
            team_row = name_rows[i]
            stats_row = stats_rows[i]
            
            # ⚾ EXTRACCIÓN DE NOMBRES (RUTA PRECISA)
            first_cell = team_row.find('td')
            team_name = 'N/A'

            if first_cell:
                # Intento de navegación precisa (td -> div.team-link -> span.hide-mobile -> a.AnchorLink)
                team_link_div = first_cell.find('div', class_='team-link')
                
                if team_link_div:
                    hide_mobile_span = team_link_div.find('span', class_='hide-mobile')
                    
                    if hide_mobile_span:
                        anchor = hide_mobile_span.find('a', class_='AnchorLink')
                        
                        if anchor:
                            team_name = anchor.get_text(strip=True)
                        else:
                            team_name = hide_mobile_span.get_text(strip=True)
                    else:
                        anchor = team_link_div.find('a', class_='AnchorLink')
                        if anchor:
                            team_name = anchor.get_text(strip=True)
                        
                # Último recurso (Fallback general)
                if team_name == 'N/A' or team_name == '':
                    team_name = first_cell.get_text(strip=True)
            
            league_division = "Overall" 
            
            # 📊 Extracción de Estadísticas (W, L, PCT, HOME, AWAY)
            stat_cells = stats_row.find_all('td')
            
            # Necesitamos al menos 6 columnas (0 a 5)
            if len(stat_cells) >= 6:
                wins = stat_cells[0].text.strip()
                losses = stat_cells[1].text.strip()
                win_pct = stat_cells[2].text.strip()
                # Columna 3 es GB, la saltamos
                
                # HOME (índice 4)
                home_record = stat_cells[4].text.strip()
                # AWAY (índice 5)
                away_record = stat_cells[5].text.strip()
                
                standings_data.append({
                    'Temporada': season,
                    'Liga_Division': league_division,
                    'Equipo': team_name,
                    'Victorias': wins,
                    'Derrotas': losses,
                    'Porcentaje_Ganador': win_pct,
                    'Record_Casa': home_record,
                    'Record_Visitante': away_record
                })
            else:
                print(f"Advertencia: Faltan celdas de estadísticas (Mínimo 6) para {team_name} en {season}. Celdas encontradas: {len(stat_cells)}")

        print(f"   -> Extracción exitosa para {season}.")
        return standings_data

    except Exception as e:
        print(f"Error general durante el scraping con Selenium para {season}: {e}")
        return []

def main_scraper():
    """Bucle principal para iterar sobre todas las temporadas y cerrar el driver."""
    
    if driver is None:
        print("El scraper no se puede ejecutar debido a un error de inicialización del WebDriver.")
        return
        
    all_standings = []
    
    for season in range(START_YEAR, END_YEAR + 1):
        data = extract_standings_from_html_selenium(season)
        all_standings.extend(data)
        
    # CERRAR EL DRIVER ES CRUCIAL
    driver.quit() 

    # Convertir y guardar
    if all_standings:
        df = pd.DataFrame(all_standings)
        
        # Conversión de tipos
        df['Victorias'] = pd.to_numeric(df['Victorias'], errors='coerce')
        df['Derrotas'] = pd.to_numeric(df['Derrotas'], errors='coerce')
        df['Porcentaje_Ganador'] = pd.to_numeric(df['Porcentaje_Ganador'], errors='coerce')
        
        # Los records de casa/visitante se limpian en la etapa de transformación (T)
        
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        df.to_csv(OUTPUT_PATH, index=False, encoding='utf-8')
        print(f"\n✅ Datos de Standings Guardados exitosamente en: {OUTPUT_PATH}")
        print(f"Total de filas extraídas: {len(df)}")
    else:
        print("\n❌ No se pudieron extraer datos de ninguna temporada.")


if __name__ == '__main__':
    main_scraper()