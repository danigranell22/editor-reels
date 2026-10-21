#!/usr/bin/env python3
"""Editor automático de Reels (hablar a cámara) según my-rules.md.

Resultado (vertical 1080x1920, MP4 listo para Instagram):
  - Silencios y muletillas cortados (y los tramos que indiques con --quitar)
  - Hook escrito (frase principal + secundaria) con hasta 3 fotos en fila encima
  - Título fijo arriba (opcional)
  - Subtítulos de 2-4 palabras, minúsculas, sin caja y con sombra suave
  - Voz limpia y normalizada a -14 LUFS, música suave por debajo (opcional)

Uso:
  python3 editar.py video.mp4 --transcribir            # ver transcripción con tiempos
  python3 editar.py video.mp4 --hook-texto "POV: lo primero que hago al despertar|(y no es café)" \
      --imagen a.jpg --imagen b.jpg --imagen c.jpg --musica fondo.mp3
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

W, H = 1080, 1920
SR = 16000
MODELOS = Path(__file__).resolve().parent / "modelos"

# Estilo (colores ASS en formato &HAABBGGRR)
FUENTE = "Inter Display"  # parecida a SF Pro; los .otf van en fuentes/
FUENTES = Path(__file__).resolve().parent / "fuentes"
BLANCO = "&H00FFFFFF"
AMARILLO = "&H0000E5FF"

MULETILLAS = {"eh", "ehh", "em", "emm", "mm", "mmm", "hmm", "ah", "uh", "um"}

# Nombres que la transcripción suele escribir mal (my-rules.md → Subtítulos)
DICCIONARIO = [
    ("veintidós athletic", "VNTDS Athletic"), ("veintidos athletic", "VNTDS Athletic"),
    ("22 athletic", "VNTDS Athletic"), ("vntds athletic", "VNTDS Athletic"),
    ("las cantera", "Las Canteras"), ("las canteras", "Las Canteras"),
    ("gran canaria", "Gran Canaria"), ("huberman", "Huberman"), ("hubermann", "Huberman"),
    ("hyrox", "Hyrox"), ("hirox", "Hyrox"), ("hyrocks", "Hyrox"), ("hai rox", "Hyrox"),
    ("muscle up", "muscle up"), ("masel ap", "muscle up"), ("muscle-up", "muscle up"),
    ("cmj", "CMJ"), ("c m j", "CMJ"), ("lca", "LCA"), ("l c a", "LCA"),
]

# Palabras que nunca se eligen como palabra clave
VACIAS = set("""
a al algo así como con cual cuando de del desde donde e el ella ellos en entre era es esa ese eso esta
este esto estoy fue ha hace hacia han has hasta hay la las le les lo los más me mi mis muy nada ni no
nos o os para pero poco por porque que qué se sea ser si sí sin sobre son su sus también tan te tener
tengo ti tu tú un una uno unos va vais vamos van voy y ya yo decir quiero todo todos cosa super súper
mucho mucha bien vale pues entonces tanto tiene
""".split())


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def ffprobe(path):
    out = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
              capture_output=True, text=True).stdout
    return json.loads(out)


def norm(t):
    return t.lower().strip(".,;:!?¿¡\"'…")


# ---------------------------------------------------------------- transcripción

def transcribir(video, hilos):
    """Transcribe con Parakeet (sherpa-onnx), con tiempos por palabra."""
    import numpy as np
    import sherpa_onnx

    print("[1/3] Transcribiendo…")
    pcm = run(["ffmpeg", "-v", "error", "-i", str(video), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
              capture_output=True).stdout
    audio = np.frombuffer(pcm, dtype=np.float32)

    d = MODELOS / "parakeet"
    rec = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=str(d / "encoder.int8.onnx"), decoder=str(d / "decoder.int8.onnx"),
        joiner=str(d / "joiner.int8.onnx"), tokens=str(d / "tokens.txt"),
        model_type="nemo_transducer", num_threads=hilos,
    )

    # Trocear por silencios (VAD)
    vcfg = sherpa_onnx.VadModelConfig()
    vcfg.silero_vad.model = str(MODELOS / "silero_vad.onnx")
    vcfg.silero_vad.min_silence_duration = 0.25
    vcfg.silero_vad.max_speech_duration = 25
    vcfg.sample_rate = SR
    vad = sherpa_onnx.VoiceActivityDetector(vcfg, buffer_size_in_seconds=60)
    trozos = []

    def vaciar():
        while not vad.empty():
            trozos.append((vad.front.start / SR, vad.front.samples))
            vad.pop()

    ventana = vcfg.silero_vad.window_size
    for i in range(0, len(audio), ventana):
        vad.accept_waveform(audio[i:i + ventana])
        vaciar()
    vad.flush()
    vaciar()

    palabras = []
    for inicio, muestras in trozos:
        st = rec.create_stream()
        st.accept_waveform(SR, muestras)
        rec.decode_stream(st)
        res = st.result
        fin_trozo = inicio + len(muestras) / SR
        nuevas = []
        for k, (tok, t) in enumerate(zip(res.tokens, res.timestamps)):
            t += inicio
            if k == 0 or tok.startswith(" "):
                nuevas.append({"t": tok.strip(), "ini": t, "ult": t})
            else:
                nuevas[-1]["t"] += tok
                if tok.strip(".,;:!?¿¡…"):  # la puntuación suele llegar tarde: no alarga la palabra
                    nuevas[-1]["ult"] = t
        for k, p in enumerate(nuevas):
            sig = nuevas[k + 1]["ini"] if k + 1 < len(nuevas) else fin_trozo
            p["fin"] = min(sig, p["ult"] + 0.4, fin_trozo)
        palabras += nuevas
    palabras = [p for p in palabras if p["t"]]
    print(f"      {len(palabras)} palabras")
    return palabras


def corregir(palabras, mal, bien, avisar=True):
    """Sustituye una secuencia de palabras repartiendo sus tiempos entre las nuevas."""
    n = len(mal)
    i = 0
    hecho = False
    while i <= len(palabras) - n:
        if [norm(x["t"]) for x in palabras[i:i + n]] == [norm(m) for m in mal]:
            ini, fin = palabras[i]["ini"], palabras[i + n - 1]["fin"]
            # Conservar la puntuación final de la última palabra sustituida
            punt = re.sub(r"^.*?([.,;:!?…]*)$", r"\1", palabras[i + n - 1]["t"])
            paso = (fin - ini) / len(bien)
            nuevas = [{"t": b, "ini": ini + k * paso, "fin": ini + (k + 1) * paso, "ult": ini + k * paso}
                      for k, b in enumerate(bien)]
            if punt and not nuevas[-1]["t"].endswith(punt):
                nuevas[-1]["t"] += punt
            palabras = palabras[:i] + nuevas + palabras[i + n:]
            i += len(bien)
            hecho = True
        else:
            i += 1
    if avisar and not hecho:
        print(f"      aviso: no encontré '{' '.join(mal)}' para corregir")
    return palabras


# ---------------------------------------------------------------- cortes

def silencios(video, umbral_db, minimo):
    """Intervalos de silencio medidos sobre el audio real."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-af",
                          f"highpass=f=80,silencedetect=n={umbral_db}dB:d={minimo}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    ini = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    fin = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return list(zip(ini, fin + [float("inf")] * (len(ini) - len(fin))))


def restar(tramos, a, b):
    salida = []
    for x, y in tramos:
        if b <= x or a >= y:
            salida.append((x, y))
            continue
        if a > x:
            salida.append((x, a))
        if b < y:
            salida.append((b, y))
    return [(x, y) for x, y in salida if y - x > 0.04]


def calcular_cortes(palabras, duracion, quitar, pausa_max, sil):
    """Devuelve (tramos a conservar, palabras con tiempos en el vídeo final)."""
    def quitada(p):
        if norm(p["t"]) in MULETILLAS:
            return True
        centro = (p["ini"] + p["ult"]) / 2
        return any(a <= centro <= b for a, b in quitar)

    vivas = [p for p in palabras if not quitada(p)]
    if not vivas:
        return [(0, duracion)], []

    # Desde justo antes de la primera palabra hasta un respiro después de la última
    # (nunca se corta la última frase ni la llamada a la acción)
    tramos = [(max(vivas[0]["ini"] - 0.1, 0), min(vivas[-1]["fin"] + 0.5, duracion))]
    for a, b in quitar:
        tramos = restar(tramos, a, b)
    for p in palabras:
        if norm(p["t"]) in MULETILLAS:
            tramos = restar(tramos, p["ini"] - 0.03, p["fin"])
    # Silencios: se deja como mucho pausa_max (mitad a cada lado)
    margen = pausa_max / 2
    for a, b in sil:
        if b - a > pausa_max:
            tramos = restar(tramos, a + margen, b - margen)

    salida, off = [], 0.0
    for a, b in tramos:
        for p in vivas:
            if a - 0.15 <= p["ini"] < b and not any(p is q["p"] for q in salida):
                ini = max(p["ini"], a)
                salida.append({"p": p, **p, "ini": off + ini - a, "fin": off + min(max(p["fin"], ini + 0.1), b) - a})
        off += b - a
    for q in salida:
        del q["p"]
    return tramos, salida


# ---------------------------------------------------------------- subtítulos

def agrupar(palabras, max_palabras, max_chars, pausa=0.5):
    bloques, actual = [], []
    for p in palabras:
        if actual:
            largo = len(" ".join(x["t"] for x in actual + [p]))
            if (len(actual) >= max_palabras or largo > max_chars
                    or p["ini"] - actual[-1]["fin"] > pausa or actual[-1]["t"][-1] in ".?!,"):
                bloques.append(actual)
                actual = []
        actual.append(p)
    if actual:
        bloques.append(actual)
    return bloques


def ts(seg):
    seg = max(seg, 0)
    h, r = divmod(seg, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def ts_srt(seg):
    ms = int(round(max(seg, 0) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def escapar(t):
    return t.replace("\\", "\\\\").replace("{", "(").replace("}", ")")


def limpiar(t):
    """Subtítulo estilo referencia: minúsculas y sin puntuación (se respetan siglas y nombres)."""
    t = t.strip(".,;:!?¿¡\"'…")
    nombres = {n for _, n in DICCIONARIO} | {w for _, n in DICCIONARIO for w in n.split()}
    return t if t in nombres or (t.isupper() and len(t) > 1) else t.lower()


def filtro_zoom(tramos, args):
    """Zoom que alterna en cada corte (salto) + acercamiento lento dentro de cada tramo.

    El punto fijo del zoom está a la altura de la cara (42 % de la pantalla), así nunca se sale de plano.
    Se trabaja a doble resolución para que el acercamiento lento no tiemble.
    """
    partes, ini = [], 0.0
    for k, (a, b) in enumerate(tramos):
        dur = b - a
        base = 1 + (args.zoom_cortes if k % 2 else 0)
        partes.append((ini + dur, f"{base:.4f}+{args.zoom_lento:.4f}*(it-{ini:.3f})/{dur:.3f}"))
        ini += dur
    expr = partes[-1][1]
    for fin, e in reversed(partes[:-1]):
        expr = f"if(lt(it,{fin:.3f}),{e},{expr})"
    return (f"scale={W * 2}:{H * 2},zoompan=z='{expr}':d=1:fps=30:s={W}x{H}:"
            f"x='iw/2-iw/zoom/2':y='ih*0.42-ih/zoom*0.42'")


def ajustar_tam(texto, ancho, espaciado=-2, maximo=110):
    """Tamaño de letra para que el hook ocupe una sola línea del ancho de la fila de fotos."""
    from PIL import ImageFont

    if not texto:
        return 76
    ruta = str(FUENTES / "InterDisplay-Black.otf")
    f = ImageFont.truetype(ruta, 100)
    asc, desc = f.getmetrics()
    # libass escala la fuente por su altura (ascendente + descendente), no por el em
    em_por_tam = 100 / (asc + desc)
    ancho_100 = f.getlength(texto)
    tam = (ancho - espaciado * (len(texto) - 1)) / (ancho_100 / 100) / em_por_tam
    return int(min(tam, maximo))


def crear_ass(palabras, duracion, lay, args):
    # Sombra suave sin caja (como el vídeo de referencia): borde negro semitransparente difuminado
    sombra = "&H70000000"
    ass = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {W}\nPlayResY: {H}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Hook,{FUENTE} Black,{lay['tam_hook']},{BLANCO},{BLANCO},{sombra},{sombra},"
        f"0,0,0,0,100,100,-2,0,1,3,1,2,50,50,{H - lay['y_hook']},1\n"
        f"Style: Hook2,{FUENTE},{args.tam_hook2},{BLANCO},{BLANCO},{sombra},{sombra},"
        f"0,0,0,0,100,100,0,0,1,3,1,8,60,60,{lay["y_hook"] + 14},1\n"
        f"Style: Titulo,{FUENTE},{args.tam_titulo},{BLANCO},{BLANCO},{sombra},{sombra},"
        f"-1,0,0,0,100,100,-1,0,1,3,1,8,70,70,170,1\n"
        f"Style: Subs,{FUENTE} SemiBold,{args.tam_subs},{BLANCO},{BLANCO},{sombra},{sombra},"
        f"0,0,0,0,100,100,-0.5,0,1,3,1,2,80,80,{H - lay['y_subs']},1\n"
        "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    suave = r"{\blur5}"
    fade = r"{\fad(120,150)\blur5}"

    if args.hook_texto:
        principal, _, secundaria = args.hook_texto.partition("|")
        ass += f"Dialogue: 2,{ts(0)},{ts(args.hook_texto_seg)},Hook,,0,0,0,,{fade}{escapar(principal.strip())}\n"
        if secundaria.strip():
            ass += f"Dialogue: 2,{ts(0)},{ts(args.hook_texto_seg)},Hook2,,0,0,0,,{fade}{escapar(secundaria.strip())}\n"

    if args.titulo:
        ini_t = args.hook_texto_seg if args.hook_texto else 0
        fin_t = duracion if args.titulo_seg <= 0 else ini_t + args.titulo_seg
        ass += f"Dialogue: 1,{ts(ini_t)},{ts(fin_t)},Titulo,,0,0,0,,{fade}{escapar(args.titulo)}\n"

    claves = {norm(c) for c in args.clave}
    bloques = agrupar(palabras, args.palabras, args.max_chars)
    for i, bloque in enumerate(bloques):
        ini = bloque[0]["ini"]
        fin = bloque[-1]["fin"]
        if i + 1 < len(bloques) and bloques[i + 1][0]["ini"] - fin < 0.6:
            fin = bloques[i + 1][0]["ini"]
        partes = []
        for x in bloque:
            t = escapar(limpiar(x["t"]))
            if claves and norm(x["t"]) in claves:  # resaltado solo si se pide con --clave
                t = r"{\c" + AMARILLO + "&}" + t + r"{\c" + BLANCO + "&}"
            partes.append(t)
        ass += f"Dialogue: 0,{ts(ini)},{ts(fin)},Subs,,0,0,0,,{suave}{' '.join(partes)}\n"
    return ass


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Editor automático de Reels")
    ap.add_argument("video")
    ap.add_argument("--transcribir", action="store_true",
                    help="Solo transcribir y mostrar las palabras con tiempos (para revisar)")
    ap.add_argument("--salida", help="Archivo de salida (def. <video>_editado.mp4)")
    # Textos
    ap.add_argument("--hook-texto", default="",
                    help="Hook escrito: 'frase principal|frase secundaria (opcional)'")
    ap.add_argument("--hook-texto-seg", type=float, default=4.5)
    ap.add_argument("--titulo", default="", help="Título fijo arriba (opcional)")
    ap.add_argument("--titulo-seg", type=float, default=0, help="Duración del título (0 = todo el vídeo)")
    ap.add_argument("--imagen", action="append", default=[],
                    help="Foto encima del hook (repetible, hasta 3 en fila)")
    ap.add_argument("--clave", nargs="*", default=[], help="Palabras a resaltar en amarillo (def. ninguna)")
    # Cortes
    ap.add_argument("--corregir", action="append", default=[], metavar="'MAL=>BIEN'",
                    help="Corrige palabras mal transcritas, p.ej. 'despones a los=>te expones a la luz'")
    ap.add_argument("--quitar", action="append", default=[], metavar="INI-FIN",
                    help="Quitar un tramo (segundos del original), p.ej. 3.2-7.9 para una toma repetida")
    ap.add_argument("--pausa-max", type=float, default=0.25, help="Silencio máximo que se deja (s)")
    ap.add_argument("--umbral", type=float, default=-35, help="Nivel (dB) por debajo del cual es silencio")
    ap.add_argument("--zoom-cortes", type=float, default=0.10,
                    help="Salto de zoom alterno en cada corte (0.10 = 10 %%, 0 = sin)")
    ap.add_argument("--zoom-lento", type=float, default=0.03,
                    help="Acercamiento lento dentro de cada tramo (0.03 = 3 %%, 0 = sin)")
    ap.add_argument("--sin-cortes", action="store_true", help="No cortar silencios ni muletillas")
    # Audio
    ap.add_argument("--musica", help="Música de fondo (se repite si es corta)")
    ap.add_argument("--musica-vol", type=float, default=0.10)
    ap.add_argument("--hook", help="Efecto de sonido al principio")
    ap.add_argument("--hook-vol", type=float, default=0.35)
    # Estilo
    ap.add_argument("--palabras", type=int, default=3, help="Máx. palabras por subtítulo (2-4)")
    ap.add_argument("--max-chars", type=int, default=18)
    ap.add_argument("--tam-subs", type=int, default=52)
    ap.add_argument("--tam-titulo", type=int, default=46)
    ap.add_argument("--tam-hook", type=int, default=0, help="0 = ajustar a una línea del ancho de las fotos")
    ap.add_argument("--tam-hook2", type=int, default=42)
    ap.add_argument("--y-subs", type=float, default=0.80, help="Altura de los subtítulos (0-1)")
    ap.add_argument("--hilos", type=int, default=4)
    args = ap.parse_args()

    video = Path(args.video)
    salida = Path(args.salida) if args.salida else video.with_name(video.stem + "_editado.mp4")
    info = ffprobe(video)
    dur_orig = float(info["format"]["duration"])

    palabras = transcribir(video, args.hilos)
    for mal, bien in DICCIONARIO:
        palabras = corregir(palabras, mal.split(), bien.split(), avisar=False)
    for c in args.corregir:
        mal, bien = c.split("=>")
        palabras = corregir(palabras, mal.split(), bien.split())

    if args.transcribir:
        for p in palabras:
            print(f"{p['ini']:7.2f} {p['fin']:7.2f}  {p['t']}")
        return

    quitar = [tuple(float(x) for x in q.split("-")) for q in args.quitar]
    if args.sin_cortes:
        tramos = [(0, dur_orig)]
        palabras = [p for p in palabras if not any(a <= p["ini"] <= b for a, b in quitar)]
    else:
        sil = silencios(video, args.umbral, 0.2)
        tramos, palabras = calcular_cortes(palabras, dur_orig, quitar, args.pausa_max, sil)
    duracion = sum(b - a for a, b in tramos)
    print(f"      {dur_orig:.1f}s → {duracion:.1f}s ({len(tramos)} tramos)")

    # Layout: fila de fotos arriba, hook pegado a su borde inferior, subtítulos bajo la cara
    imagenes = args.imagen[:3]
    lado = 316 if len(imagenes) == 3 else 380
    y_img = 250
    y_hook = y_img + lado + 10 if imagenes else 430
    ancho_fila = len(imagenes) * lado + (len(imagenes) - 1) * 4 if imagenes else W - 140
    principal = args.hook_texto.partition("|")[0].strip()
    tam_hook = args.tam_hook or ajustar_tam(principal, ancho_fila)
    lay = {"y_hook": y_hook, "y_subs": int(H * args.y_subs), "tam_hook": tam_hook}

    ass_path = salida.with_suffix(".ass")
    ass_path.write_text(crear_ass(palabras, duracion, lay, args), encoding="utf-8")

    srt = []
    for n, b in enumerate(agrupar(palabras, 8, 42), 1):
        srt.append(f"{n}\n{ts_srt(b[0]['ini'])} --> {ts_srt(b[-1]['fin'])}\n{' '.join(x['t'] for x in b)}\n")
    salida.with_suffix(".srt").write_text("\n".join(srt), encoding="utf-8")

    print("[2/3] Montando vídeo…")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(video)]
    idx = 1
    i_hook = i_mus = None
    i_imgs = []
    for im in imagenes:
        cmd += ["-loop", "1", "-t", f"{args.hook_texto_seg}", "-i", im]
        i_imgs.append(idx)
        idx += 1
    if args.hook:
        cmd += ["-i", args.hook]
        i_hook, idx = idx, idx + 1
    if args.musica:
        cmd += ["-stream_loop", "-1", "-i", args.musica]
        i_mus, idx = idx, idx + 1

    tiene_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    fc = []
    # Cortes: trocear y concatenar
    for k, (a, b) in enumerate(tramos):
        fc.append(f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS[v{k}]")
        if tiene_audio:
            fc.append(f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,"
                      f"afade=t=in:d=0.02,afade=t=out:st={max(b - a - 0.02, 0):.3f}:d=0.02[a{k}]")
    pares = "".join(f"[v{k}]" + (f"[a{k}]" if tiene_audio else "") for k in range(len(tramos)))
    fc.append(f"{pares}concat=n={len(tramos)}:v=1:a={1 if tiene_audio else 0}[vc]" + ("[ac]" if tiene_audio else ""))

    fc.append(f"[vc]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps=30[base]")
    v = "base"
    if args.zoom_cortes > 0 or args.zoom_lento > 0:
        fc.append(f"[{v}]{filtro_zoom(tramos, args)}[zoom]")
        v = "zoom"
    hueco = 4
    x0 = (W - len(i_imgs) * lado - (len(i_imgs) - 1) * hueco) // 2
    for k, ii in enumerate(i_imgs):
        fin_h = args.hook_texto_seg
        fc.append(f"[{ii}:v]scale={lado}:{lado}:force_original_aspect_ratio=increase,crop={lado}:{lado},"
                  f"setsar=1,format=rgba,fade=t=in:d=0.12:alpha=1,fade=t=out:st={fin_h - 0.15}:d=0.15:alpha=1[im{k}]")
        fc.append(f"[{v}][im{k}]overlay={x0 + k * (lado + hueco)}:{y_img}:eof_action=pass[vi{k}]")
        v = f"vi{k}"
    ass_esc = str(ass_path.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    fdir = str(FUENTES).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    fc.append(f"[{v}]ass='{ass_esc}':fontsdir='{fdir}'[vout]")

    # Audio: voz limpia (sin zumbidos ni ruido) + música/efecto por debajo
    mezcla = []
    if tiene_audio:
        fc.append("[ac]highpass=f=80,afftdn=nr=12:nf=-40,loudnorm=I=-14:TP=-1.5:LRA=11,"
                  "aresample=48000[voz]")
        mezcla.append("[voz]")
    if i_hook is not None:
        fc.append(f"[{i_hook}:a]volume={args.hook_vol},aresample=48000,apad[hk]")
        mezcla.append("[hk]")
    if i_mus is not None:
        fc.append(f"[{i_mus}:a]atrim=0:{duracion:.3f},volume={args.musica_vol},aresample=48000,"
                  f"afade=t=in:d=0.5,afade=t=out:st={max(duracion - 1.5, 0):.3f}:d=1.5[mus]")
        mezcla.append("[mus]")
    if len(mezcla) > 1:
        fc.append(f"{''.join(mezcla)}amix=inputs={len(mezcla)}:duration=first:normalize=0[aout]")
    elif mezcla:
        fc.append(f"{mezcla[0]}anull[aout]")

    cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]"]
    if mezcla:
        cmd += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
            "-r", "30", "-movflags", "+faststart", "-t", f"{duracion:.3f}", str(salida)]
    run(cmd)
    print(f"[3/3] Listo → {salida}")


if __name__ == "__main__":
    sys.exit(main())
