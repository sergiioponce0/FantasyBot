import discord
import json
import re
import os
import requests
from discord.ext import commands, tasks
from bs4 import BeautifulSoup

TOKEN = os.getenv("TOKEN")
INTENTS = discord.Intents.default()
INTENTS.message_content = True

bot = commands.Bot(command_prefix='/', intents=INTENTS)

JUGADORES_FILE = "jugadores.json"

# ---------------- UTILIDADES ----------------

def cargar_jugadores():
    try:
        with open(JUGADORES_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def guardar_jugadores(jugadores):
    with open(JUGADORES_FILE, "w") as f:
        json.dump(jugadores, f, indent=2)

def obtener_precio(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        elemento = soup.find(class_="valor-actual")
        if not elemento:
            return None

        precio_str = elemento.text
        precio_limpio = re.search(r'\d[\d.]*', precio_str).group(0)
        precio = int(precio_limpio.replace('.', ''))
        return precio
    except Exception as e:
        print(f"Error al obtener precio: {e}")
        return None

# ---------------- COMANDOS ----------------

@bot.command()
async def añadir(ctx, nombre: str, url: str):
    jugadores = cargar_jugadores()
    await ctx.send(f"Buscando precio para {nombre}...")

    precio = obtener_precio(url)
    if precio is None:
        await ctx.send("❌ No se pudo obtener el precio.")
        return

    jugadores[nombre] = {"url": url, "precio": precio}
    guardar_jugadores(jugadores)
    await ctx.send(f"✅ {nombre} añadido con precio {precio}€.")

@bot.command()
async def quitar(ctx, nombre: str):
    jugadores = cargar_jugadores()
    if nombre in jugadores:
        del jugadores[nombre]
        guardar_jugadores(jugadores)
        await ctx.send(f"🗑️ {nombre} eliminado.")
    else:
        await ctx.send("❌ Ese jugador no está en la lista.")

@bot.command()
async def listar(ctx):
    jugadores = cargar_jugadores()
    if not jugadores:
        await ctx.send("📭 Lista vacía.")
        return

    mensaje = "**Jugadores:**\n"
    for nombre, data in jugadores.items():
        mensaje += f"• {nombre} → {data['precio']}€\n"
    await ctx.send(mensaje)

@bot.command()
async def actualizar(ctx):
    jugadores = cargar_jugadores()
    mensaje = "**Actualización:**\n"
    cambios = False

    for nombre, data in jugadores.items():
        nuevo = obtener_precio(data["url"])
        if nuevo is None:
            continue
        anterior = data["precio"]
        if nuevo != anterior:
            cambio = "📈 Subió" if nuevo > anterior else "📉 Bajó"
            mensaje += f"{nombre}: {cambio} de {anterior}€ a {nuevo}€\n"
            jugadores[nombre]["precio"] = nuevo
            cambios = True

    guardar_jugadores(jugadores)
    await ctx.send(mensaje if cambios else "📊 Sin cambios de precio.")

# ---------------- TAREA AUTOMÁTICA ----------------

@tasks.loop(minutes=60)
async def comprobar_automatica():
    canal = bot.get_channel(int(os.getenv("DISCORD_CHANNEL_ID")))
    jugadores = cargar_jugadores()
    cambios = []

    for nombre, data in jugadores.items():
        nuevo = obtener_precio(data["url"])
        if nuevo is None:
            continue
        anterior = data["precio"]
        if nuevo != anterior:
            cambio = "📈 Subió" if nuevo > anterior else "📉 Bajó"
            cambios.append(f"{nombre}: {cambio} de {anterior}€ a {nuevo}€")
            jugadores[nombre]["precio"] = nuevo

    guardar_jugadores(jugadores)
    if cambios:
        await canal.send("**Cambios detectados:**\n" + "\n".join(cambios))

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    comprobar_automatica.start()

bot.run(TOKEN)
