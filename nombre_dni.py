import requests
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

TOKEN = "8676413735:AAG5pmijM6mgA49t7ngD1yVXPjFVvd9ohyE"

# 🔥 ANTISPAM
ultimo_uso = {}
TIEMPO_ESPERA = 20


# 🔥 Separar nombre completo
def separar_nombre(nombre_completo):
    partes = nombre_completo.split()

    if len(partes) < 3:
        return nombre_completo, "", ""

    apellido_materno = partes[-1]
    apellido_paterno = partes[-2]
    nombres = " ".join(partes[:-2])

    return nombres, apellido_paterno, apellido_materno


def buscar_dni(dni):
    driver = webdriver.Chrome()

    driver.get("https://eldni.com/pe/buscar-por-dni")
    time.sleep(3)

    input_dni = driver.find_element(By.NAME, "dni")
    input_dni.send_keys(dni)
    time.sleep(2)

    input_dni.send_keys(Keys.RETURN)
    time.sleep(5)

    texto = driver.find_element(By.TAG_NAME, "body").text
    lineas = texto.split("\n")

    nombre = "No encontrado"

    for linea in lineas:
        if linea.isupper() and len(linea) > 10 and "DNI" not in linea:
            nombre = linea
            break

    driver.quit()
    return nombre


def buscar_nombre(nombre_busqueda):
    driver = webdriver.Chrome()

    driver.get("https://dniperu.com/consultas/buscar-dni-por-nombre/")

    wait = WebDriverWait(driver, 10)

    inputs = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//input[@type='text']")))

    nombres, ap_paterno, ap_materno = separar_nombre(nombre_busqueda)

    try:
        inputs[0].clear()
        inputs[0].send_keys(nombres)

        inputs[1].clear()
        inputs[1].send_keys(ap_paterno)

        inputs[2].clear()
        inputs[2].send_keys(ap_materno)

    except Exception as e:
        print("❌ Error escribiendo:", e)

    time.sleep(2)

    try:
        boton = driver.find_element(By.XPATH, "//button")
        boton.click()
    except:
        inputs[2].send_keys(Keys.RETURN)

    time.sleep(6)

    texto = driver.find_element(By.TAG_NAME, "body").text

    # 🔥 EXTRAER DNIs
    dnis = re.findall(r"\b\d{8}\b", texto)

    driver.quit()

    if dnis:
        dnis_unicos = list(set(dnis))
        return "\n".join([f"🆔 {dni}" for dni in dnis_unicos[:5]])
    else:
        return "No encontrado"


def enviar_mensaje(chat_id, texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": texto
    })


# 🔥 INICIAR DESDE ÚLTIMO MENSAJE
url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
response = requests.get(url).json()

ultimo_update = None

if response.get("result"):
    ultimo_update = response["result"][-1]["update_id"]

print("✅ Bot iniciado correctamente")


# 🔁 LOOP PRINCIPAL
while True:
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={ultimo_update + 1 if ultimo_update else ''}"

    response = requests.get(url).json()

    if not response.get("ok"):
        print("❌ Error:", response)
        time.sleep(3)
        continue

    for update in response.get("result", []):
        update_id = update["update_id"]
        ultimo_update = update_id

        try:
            mensaje = update["message"]["text"]
            chat_id = update["message"]["chat"]["id"]

            print("📩 Nuevo mensaje:", mensaje)

            # 🔥 ANTISPAM
            ahora = time.time()

            if chat_id in ultimo_uso:
                tiempo_pasado = ahora - ultimo_uso[chat_id]

                if tiempo_pasado < TIEMPO_ESPERA:
                    restante = int(TIEMPO_ESPERA - tiempo_pasado)
                    enviar_mensaje(chat_id, f"⏳ Espera {restante}s antes de usar el bot otra vez")
                    continue

            ultimo_uso[chat_id] = ahora

            # 🔥 PARSEO CORRECTO
            mensaje_original = mensaje.strip()
            mensaje_lower = mensaje_original.lower()

            partes = mensaje_lower.split(maxsplit=1)
            comando = partes[0]
            argumento = partes[1] if len(partes) > 1 else ""

            # 👉 COMANDO /dni
            if comando == "/dni":
                if argumento.isdigit() and len(argumento) == 8:
                    enviar_mensaje(chat_id, "🔍 Buscando nombre...")
                    nombre = buscar_dni(argumento)
                    enviar_mensaje(chat_id, f"👤 {nombre}")
                else:
                    enviar_mensaje(chat_id, "⚠️ Usa: /dni 12345678")

            # 👉 COMANDO /nombre
            elif comando == "/nombre":
                if argumento:
                    enviar_mensaje(chat_id, "🔍 Buscando DNI...")
                    dni = buscar_nombre(argumento)
                    enviar_mensaje(chat_id, f"{dni}")
                else:
                    enviar_mensaje(chat_id, "⚠️ Usa: /nombre juan perez")

            # 👉 AYUDA
            else:
                enviar_mensaje(chat_id,
                    "📌 Comandos disponibles:\n"
                    "/dni 12345678\n"
                    "/nombre juan perez"
                )

        except Exception as e:
            print("Error:", e)

    time.sleep(3)