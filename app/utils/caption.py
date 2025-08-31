from datetime import date

CAPTION = 'Source: MusicBrainz (CC BY-NC-SA 4.0). Pulled {pulled}. "Music metadata provided by MusicBrainz."'


def caption_today() -> str:
    return CAPTION.format(pulled=date.today().isoformat())
