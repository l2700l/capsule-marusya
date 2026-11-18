
import asyncio

from yandex_music import Client

from classifier.base import SkillDefinition, BaseSkill
from protocol import Response
from protocol.music import Playlist, Track as CapsuleTrack
from skills.base import SkillRequest
from config.settings import YANDEX_MUSIC_TOKEN

from utils.music_streams import register_stream

class MusicSkill(BaseSkill):

    definition = SkillDefinition(
        name="music",

        rules=[
            r"\bвключи\b",
            r"\bпоставь музыку\b",
            r"\bнайди песню\b",
            r"\bнайди трек\b",
            r"\bвоспроизведи\b",
            r"\bпослушаем\b",
        ],

        examples=[
            "Включи музыку",
            "Включи песню Кукушка",
            "Поставь Спокойную ночь Виктора Цоя",
            "Найди трек Bohemian Rhapsody",
            "Включи альбом The Dark Side of the Moon",
            "Поставь музыку группы Кино",
            "Хочу послушать что-нибудь из рока",
        ],

        priority=10,
    )

    def __init__(self):
        self.client = None

    def get_client(self):
        if self.client is not None:
            return self.client

        if not YANDEX_MUSIC_TOKEN:
            raise RuntimeError("Не задан YANDEX_MUSIC_TOKEN")

        self.client = Client(YANDEX_MUSIC_TOKEN).init()

        return self.client

    @staticmethod
    def get_artist_name(track):
        artists = getattr(track, "artists", None) or []

        return ", ".join(
            artist.name
            for artist in artists
            if getattr(artist, "name", None)
        )

    @staticmethod
    def get_album_tracks(album):
        tracks = []

        for volume in getattr(album, "volumes", None) or []:
            tracks.extend(volume)

        return tracks

    def get_audio_url(self, track):
        print(f"[MusicSkill] Getting audio: {track.id} — {track.title}")

        file_info = track.get_file_info(
    quality="hq",
    codecs=["mp3"],
    transport="raw",
)

        print("[MusicSkill] FileInfo:", file_info)

        download_info = getattr(file_info, "download_info", None)
        print("[MusicSkill] DownloadInfo:", download_info)

        if not download_info:
            raise RuntimeError("FileInfo не содержит download_info")

        download_info = file_info.download_info

        print("Quality:", download_info.quality)
        print("Codec:", download_info.codec)
        print("Bitrate:", download_info.bitrate)
        print("Transport:", download_info.transport)
        print("Key:", bool(download_info.key))
        print("URL:", download_info.url)

        url = download_info.url

        print("[MusicSkill] URL received:", bool(url))

        if not url:
            raise RuntimeError("Пустая ссылка на аудио")

        return url

    
    def convert_track(self, track):
        source_url = self.get_audio_url(track)
        stream_id = register_stream(source_url)

        return CapsuleTrack(
            url=f"https://vc.go.mail.ru/music/stream/{stream_id}.mp3",
            title=track.title or "",
            artist=self.get_artist_name(track),
            duration=(
                track.duration_ms / 1000
                if getattr(track, "duration_ms", None)
                else None
            ),
            meta={
                "source": "yandex_music",
                "track_id": track.id,
                "album_id": (
                    track.albums[0].id
                    if getattr(track, "albums", None)
                    else None
                ),
            },
        )

    def play_track(self, track, query):
        capsule_track = self.convert_track(track)
        return (
            Response(
                skill="music",
                intent="music.play_track",
                asr_text=query,
            )
            .play_track(capsule_track, query=query)
        )

    def play_album(self, album, query):
        tracks = self.get_album_tracks(album)

        if not tracks:
            return (
                Response(
                    skill="music",
                    intent="music.empty_album",
                    asr_text=query,
                )
                .say("В этом альбоме не удалось найти треки")
            )

        capsule_tracks = [
            self.convert_track(track)
            for track in tracks
        ]

        playlist = Playlist(
            tracks=capsule_tracks,
            player_type="player",
            query=query,
        )
        return (
            Response(
                skill="music",
                intent="music.play_album",
                asr_text=query,
            )
            .play_playlist(playlist)
        )

    def search_and_play(self, text):
        client = self.get_client()

        search_result = client.search(text)
        best = search_result.best

        if not best or not best.result:
            return (
                Response(
                    skill="music",
                    intent="music.not_found",
                    asr_text=text,
                )
                .say("Не удалось ничего найти")
            )

        if best.type == "track":
            return self.play_track(best.result, text)

        if best.type == "album":
            album = client.albums_with_tracks(best.result.id)
            return self.play_album(album, text)

        return (
            Response(
                skill="music",
                intent="music.unsupported_result",
                asr_text=text,
            )
            .say("Не удалось подобрать музыку по этому запросу")
        )

    async def handle(self, request: SkillRequest):
        text = request.text.strip()

        if not text:
            return (
                Response(
                    skill="music",
                    intent="music.empty_query",
                    asr_text=text,
                )
                .say("Что включить?")
            )

        try:
            return await asyncio.to_thread(
                self.search_and_play,
                text,
            )

        except Exception as error:
            print(f"[MusicSkill] Error: {error}")

            return (
                Response(
                    skill="music",
                    intent="music.error",
                    asr_text=text,
                )
                .say("При поиске музыки произошла ошибка")
            )


SKILL = MusicSkill.definition
SKILL.handler = MusicSkill().handle
