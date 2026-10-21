---
name: editar-reel
description: Edita un vídeo de Daniel hablando a cámara y lo deja listo para Instagram Reels con su estilo (hook escrito con fotos, subtítulos, cortes de silencios, voz limpia, música suave). Úsala siempre que Daniel pase un vídeo para editar o pida "edita este vídeo".
---

# Editar un Reel de Daniel

Antes de nada, lee `my-rules.md` (reglas de Daniel) y `CLAUDE.md` (estilo acordado). Mandan sobre esta guía.
Si `modelos/` no existe, ejecuta `./instalar.sh` (descarga ~640 MB la primera vez).

## Lotes de vídeos desde una carpeta

Si Daniel dice "edita los vídeos de la carpeta X y guárdalos en Y" (en su ordenador suele ser
`~/Desktop/Mobile Devices` → `~/Desktop/videos insta`; si no existen con ese nombre exacto, búscalas en el
Escritorio y pregunta si hay dudas): procesa todos los vídeos de X (.mov, .mp4, .m4v), uno a uno, con los pasos
de abajo. Guarda en Y una carpeta por vídeo con sus 5 versiones y su `_publicaciones.md`. No borres ni muevas
los originales. Junta todas las dudas (palabras que no se entienden, hooks verbales flojos) en un solo mensaje
al final.

## Pasos

1. **Transcribir** y leer lo que dice, con tiempos por palabra:
   `python3 editar.py VIDEO --transcribir`
2. **Revisar la transcripción**:
   - Palabras mal entendidas → `--corregir 'mal=>bien'` (los nombres de my-rules.md ya se corrigen solos).
     Si no estás seguro de lo que dijo, pregúntale en vez de inventarlo.
   - Frases repetidas o tomas falladas → `--quitar INI-FIN` (segundos del original), quédate con la última toma buena.
   - Arranques flojos ("quiero decir con esto", "bueno…") antes del hook → quítalos.
   - Nunca cortes la última frase ni la llamada a la acción.
3. **Hook escrito** (`--hook-texto 'principal|secundaria'`): corto (4-7 palabras) para que quepa en una línea,
   complementa lo que dice sin repetirlo y crea curiosidad. La secundaria va entre paréntesis, opcional.
   Si el hook verbal no cumple my-rules.md (consejo genérico en vez de momento real), avísale.
4. **Fotos y GIFs del hook** (`--imagen`, 3 en fila encima del título mientras dura el hook): fotos de
   `fotos/<tema>/` o GIFs de `gifs/` que resuman la historia del vídeo (p. ej. agua → cortisol → dormir).
   En entrenamiento, prioriza tren superior / calistenia. Mejor sin imagen que con una que no pega.
4b. **GIFs sueltos** (`--gif RUTA@INI-FIN`, tiempos del vídeo ORIGINAL, los de `--transcribir`): cuando se
   quita el título, de uno en uno encima de la cabeza, cada uno mientras dice la palabra o frase que ilustra
   (p. ej. `gifs/sol-luz-brillante.gif@12.6-14.7` mientras dice "te expones a la luz"). Daniel los quiere largos: unos 3-4 s cada
   uno, encadenados uno detrás de otro (casi sin huecos) desde que se quita el título hasta el final.
   `--gif` acepta también fotos: combina GIFs de `gifs/` y fotos de `fotos/<tema>/` (Daniel lo pidió así),
   alternándolas para que no sean todo GIFs ni todo fotos. Las fotos y clips verticales se recortan solos a
   16:9 en el hueco de arriba (Daniel lo pidió así), así que también valen. Elige por el nombre del archivo; si un GIF nuevo tiene un
   nombre poco claro, míralo (saca un fotograma) y renómbralo con `git mv` a algo descriptivo.
4c. **Clips de Daniel / b-roll** (`--broll RUTA@INI-FIN`, tiempos del original): de `broll/`, a pantalla completa
   mientras sigue sonando su voz (los subtítulos siguen encima). 1,5-3 s, solo cuando ilustra lo que dice
   (entrenando, cocinando, la playa…). Por su rodilla: tren superior / calistenia antes que correr o saltar.
   No pongas GIF a la vez que un clip. Si un clip nuevo tiene nombre poco claro, míralo y renómbralo.
5. **Música** (`--musica`, opcional): una pista de `musica/<ambiente>/` según el tema
   (tranquila: descanso/salud · motivadora: entrenamiento/mentalidad · emotiva: historias). Volumen por defecto 0.10.
   Solo música sin derechos de autor; si Daniel prefiere ponerla en Instagram, no pongas ninguna.
6. **Montar**: `python3 editar.py VIDEO [opciones] --salida salidas/<nombre>.mp4`
7. **Revisar** antes de entregar: saca fotogramas (`ffmpeg -ss T -i salida.mp4 -frames:v 1 f.png`) y mira que
   el hook quepa en una línea, que los subtítulos no tapen la cara y que no se corte ninguna palabra.
   Si hace falta, ajusta `--y-subs` (0-1) o `--tam-subs`.
8. **Versiones para Reels de prueba** (Daniel quiere 5 por vídeo salvo que diga otra cosa): tienen que verse MUY
   distintas para que Instagram no las tome por el mismo vídeo. Cada versión usa un `--formato` distinto y
   además cambia el hook escrito y las imágenes del hook:
   v1 `normal` · v2 `bandas` (franja fina 16:9 con la cara en medio; negro arriba con título/fotos/GIFs y abajo con subtítulos) · v3 `recuadro`
   (mismo encuadre que bandas, pero en recuadro redondeado con negro a los lados) · v4 `lateral` (cara a la derecha, columna negra a la izquierda
   con todo; máx. 2 fotos en el hook) · v5 `velocidad` (normal acelerado ×1,15).
   Los hooks atacan ángulos distintos (beneficio, dato, acción, problema, concreto) sin prometer nada que no
   diga en el vídeo. Evita GIFs que empiecen en negro en la fila del hook. La transcripción va en caché, así
   que las versiones 2-5 van rápido. Nombres: `salidas/<nombre>_v1.mp4` … `_v5.mp4`.
   Escribe `salidas/<nombre>_publicaciones.md` con una tabla de versiones y, para cada una, texto para
   Instagram/TikTok (2-3 líneas, español de España, una llamada a la acción y 6-8 hashtags).
9. **Entregar** el MP4 con una línea de qué has cortado y qué has añadido, y los avisos que pide my-rules.md.

## Ejemplo

```
python3 editar.py video.mp4 --corregir 'despones a los=>te expones a la' --quitar 2.7-3.9 \
  --hook-texto 'Agua al despertar = mejor sueño|(te explico por qué)' \
  --imagen gifs/agua-beber-botella.gif --imagen gifs/cortisol-estres-medidor.gif --imagen gifs/dormir-pato-donald.gif \
  --gif gifs/cortisol-estres-medidor.gif@10.7-12.1 --gif gifs/sol-luz-brillante.gif@12.6-14.7 \
  --musica musica/tranquila/pista1.mp3 --salida salidas/agua.mp4
```
