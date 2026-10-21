# Editor de Reels de Daniel (@danigranellf)

Editor automático para vídeos hablando a cámara: corta silencios y muletillas, pone el hook escrito con fotos,
subtítulos en el estilo acordado, limpia la voz (-14 LUFS, volumen de Instagram) y añade música suave.

## Cómo se usa

Abre una sesión de Claude Code con este repositorio, sube el vídeo y di **"edita este vídeo"**.
Claude sigue la skill `.claude/skills/editar-reel` y tus reglas de `my-rules.md`.

## Qué hay aquí

| Carpeta / archivo | Qué es |
|---|---|
| `my-rules.md` | Tus reglas de edición. Cámbialas cuando quieras. |
| `CLAUDE.md` | Estilo acordado y notas para Claude. |
| `fotos/<tema>/` | Tus fotos para el hook. Claude las elige según de qué hables. |
| `musica/<ambiente>/` | Música sin derechos de autor para el fondo. |
| `gifs/` | GIFs y memes (.gif / .mp4). Nombre descriptivo: `cerebro-explota.gif`. |
| `stickers/` | PNG con fondo transparente (flechas, iconos…). |
| `broll/` | Clips cortos de vídeo (`muscle-up-barra.mp4`). |
| `sonidos/` | Efectos de sonido (`whoosh.mp3`, `pop.mp3`). |
| `fuentes/` | Inter Display (licencia libre SIL OFL). |
| `editar.py` | El editor (`python3 editar.py --help` para ver todas las opciones). |
| `instalar.sh` | Instala dependencias y descarga los modelos de transcripción (se ejecuta solo al abrir sesión). |
| `salidas/` | Vídeos editados (no se suben al repositorio). |

## Opciones principales de `editar.py`

- `--transcribir` solo transcribe y muestra cada palabra con su tiempo
- `--hook-texto 'principal|secundaria'` hook escrito (se ajusta a una línea del ancho de las fotos)
- `--imagen foto.jpg` foto o GIF encima del hook (repetible, hasta 3)
- `--broll broll/clip.mp4@15.4-17.6` clip a pantalla completa en ese tramo (se oye tu voz)
- `--gif gifs/sol.gif@12.6-14.7` GIF encima de la cabeza en ese tramo (segundos del vídeo original)
- `--corregir 'mal=>bien'` corrige palabras mal transcritas
- `--quitar 3.2-7.9` quita un tramo (segundos del vídeo original)
- `--musica pista.mp3` música de fondo (`--musica-vol 0.10`)
- `--zoom-cortes 0.10` salto de zoom alterno en cada corte · `--zoom-lento 0.03` acercamiento lento (0 = sin)
- `--clave palabra …` resalta esas palabras en amarillo
- `--y-subs 0.80` altura de los subtítulos · `--tam-subs 52` tamaño
- `--formato normal|bandas|recuadro|lateral|velocidad` diseño de la versión (`--velocidad 1.15` para acelerar)
- `--salida salidas/nombre.mp4`
