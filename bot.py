import json
import os
import time
import hashlib
import random
import requests
from datetime import datetime
from telebot import TeleBot
from telebot.types import InputMediaPhoto
from PIL import Image, ImageDraw
from io import BytesIO

# === CONFIGURAÇÕES ===
TOKEN = "7666728230:AAHx8x-dPipQGJaiAKxpJ03Ed5QhxIUHOqk"
APP_ID = "18382050001"
SECRET = "3T3NF243EY45MN4432D3ZBYQF3C5TFHR"
ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"
TEMPLATE_PATH = "template.png"
HISTORICO_JSON = "produtos_utilizados.json"

bot = TeleBot(TOKEN)

# === FUNÇÕES ===
def carregar_ids_usados():
    if os.path.exists(HISTORICO_JSON):
        with open(HISTORICO_JSON, "r") as f:
            return set(json.load(f))
    return set()

def salvar_ids_usados(ids):
    with open(HISTORICO_JSON, "w") as f:
        json.dump(list(ids), f)

def buscar_produtos_nao_usados(quantidade):
    query = {
        "query": """
        query {
          productOfferV2(page: 1, limit: 50, sortType: 5) {
            nodes {
              itemId
              productName
              offerLink
              imageUrl
            }
          }
        }
        """
    }

    payload = json.dumps(query)
    timestamp = str(int(time.time()))
    raw = APP_ID + timestamp + payload + SECRET
    signature = hashlib.sha256(raw.encode()).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={APP_ID}, Timestamp={timestamp}, Signature={signature}"
    }

    try:
        response = requests.post(ENDPOINT, headers=headers, data=payload)
        if response.status_code != 200:
            print("❌ ERRO HTTP:", response.text)
            return []

        data = response.json()
        todos = data.get("data", {}).get("productOfferV2", {}).get("nodes", [])
        usados = carregar_ids_usados()
        disponiveis = [p for p in todos if p["itemId"] not in usados]
        escolhidos = random.sample(disponiveis, min(quantidade, len(disponiveis)))
        return escolhidos

    except Exception as e:
        print("❌ ERRO AO BUSCAR PRODUTOS:", str(e))
        return []

def gerar_template(produtos):
    template = Image.open(TEMPLATE_PATH).convert("RGBA")
    posicoes = [(97, 550), (535, 551), (97, 884), (535, 884), (97, 1218), (535, 1218)]

    for i, produto in enumerate(produtos):
        url = produto["imageUrl"]
        response = requests.get(url)
        imagem = Image.open(BytesIO(response.content)).convert("RGBA")
        imagem = imagem.resize((390, 289))

        mask = Image.new("L", imagem.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([(0, 0), imagem.size], radius=37, fill=255)

        template.paste(imagem, posicoes[i], mask)

    os.makedirs("temp", exist_ok=True)
    saida = "temp/template_final.jpg"
    template.convert("RGB").save(saida, format="JPEG")
    return saida

@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    produtos = buscar_produtos_nao_usados(6)

    if not produtos:
        bot.send_message(chat_id, "❌ Não foi possível buscar ofertas agora. Tente novamente mais tarde.")
        return

    imagem_final = gerar_template(produtos)
    if not os.path.exists(imagem_final):
        bot.send_message(chat_id, "❌ Erro ao gerar imagem do template.")
        return

    bot.send_message(chat_id, "🌳 *Melhores ofertas para você hoje!*", parse_mode="Markdown")
    bot.send_photo(chat_id, open(imagem_final, "rb"))

    texto = "🧾 *Produtos do Dia:*"
    for i, p in enumerate(produtos, start=1):
        texto += f"\n🔹 PRODUTO {i} = {p['offerLink']}"

    bot.send_message(chat_id, texto, parse_mode="Markdown")

    usados = carregar_ids_usados()
    for p in produtos:
        usados.add(p["itemId"])
    salvar_ids_usados(usados)

bot.infinity_polling()
