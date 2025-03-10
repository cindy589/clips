import os
import yt_dlp
import whisper
import srt
import datetime
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from scenedetect import SceneManager, open_video, ContentDetector
from django.shortcuts import render
from .forms import VideoURLForm
from django.conf import settings

os.environ['IMAGEMAGICK_BINARY'] = '/usr/bin/convert'

OUTPUT_FOLDER = os.path.join(settings.BASE_DIR, "output_videos")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def descargar_video(url):
    print("Descargando video...")
    output_path = os.path.join(OUTPUT_FOLDER, "video.mp4")
    ydl_opts = {
        'format': 'best',
        'outtmpl': output_path,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_path

def transcribir_audio(video_path):
    print("Transcribiendo audio...")
    model = whisper.load_model("small")
    result = model.transcribe(video_path)
    return result["text"], result["segments"]

def detectar_escenas(video_path, min_duration=2.0):
    print("Detectando escenas...")
    video = open_video(video_path)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video)
    scene_list = scene_manager.get_scene_list()
    # Filtrar escenas con una duración mínima
    filtered_scenes = [(scene[0].get_seconds(), scene[1].get_seconds()) for scene in scene_list if (scene[1].get_seconds() - scene[0].get_seconds()) >= min_duration]
    return filtered_scenes

def generar_subtitulos(segments, output_srt):
    print("Generando subtitulos...")
    subs = []
    for i, seg in enumerate(segments):
        start = datetime.timedelta(seconds=seg['start'])
        end = datetime.timedelta(seconds=seg['end'])
        text = seg['text']
        subs.append(srt.Subtitle(index=i, start=start, end=end, content=text))
    with open(output_srt, "w") as f:
        f.write(srt.compose(subs))

def agregar_subtitulos(video_path, srt_path, output_video):
    print("Agregando subtitulos al video...")
    video = VideoFileClip(video_path)
    subs = []
    font_path = "/path/to/your/font.ttf"  # Cambia esta ruta a la ubicación de tu fuente

    with open(srt_path, "r") as f:
        subtitles = list(srt.parse(f.read()))
        for subtitle in subtitles:
            words = subtitle.content.split()
            word_clips = []
            for i, word in enumerate(words):
                txt_clip = TextClip(word, fontsize=24, font=font_path, color='white', bg_color='green', method='caption')
                txt_clip = txt_clip.set_start(subtitle.start.total_seconds() + i * (subtitle.end.total_seconds() - subtitle.start.total_seconds()) / len(words))
                txt_clip = txt_clip.set_end(subtitle.start.total_seconds() + (i + 1) * (subtitle.end.total_seconds() - subtitle.start.total_seconds()) / len(words))
                txt_clip = txt_clip.set_pos(('center', 'bottom'))
                word_clips.append(txt_clip)
            subs.extend(word_clips)

    final_video = CompositeVideoClip([video] + subs)
    final_video.write_videofile(output_video, codec="libx264", fps=30)

def procesar_video(request):
    print("Procesando video...")
    if request.method == 'POST':
        form = VideoURLForm(request.POST)
        if form.is_valid():
            url = form.cleaned_data['url']
            video_path = descargar_video(url)

            transcripcion, segments = transcribir_audio(video_path)
            escenas = detectar_escenas(video_path)

            srt_path = os.path.join(OUTPUT_FOLDER, "subtitles.srt")
            generar_subtitulos(segments, srt_path)

            # Crear la carpeta media si no existe
            if not os.path.exists(settings.MEDIA_ROOT):
                os.makedirs(settings.MEDIA_ROOT)

            final_clip_path = os.path.join(settings.MEDIA_ROOT, "video_subtitled.mp4")
            agregar_subtitulos(video_path, srt_path, final_clip_path)
            os.remove(video_path)

            # Convertir las rutas absolutas a rutas relativas a MEDIA_URL
            clip_path = os.path.join(settings.MEDIA_URL, os.path.relpath(final_clip_path, settings.MEDIA_ROOT))
            subtitles = os.path.join(settings.MEDIA_URL, os.path.relpath(srt_path, settings.MEDIA_ROOT))

            return render(request, 'videoapp/procesado.html', {'clip_path': clip_path, 'subtitles': subtitles})

    else:
        form = VideoURLForm()
    return render(request, 'videoapp/index.html', {'form': form})