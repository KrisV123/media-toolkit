FALLBACK_ABR_TOLERANCE = 6
ROUND_ABR_TOLERANCE = 1

YT_DLP_TUMBNAIL_SUPPORT = frozenset(
    (
        'mp3', 'mkv', 'mka', 'ogg', 'opus',
        'flac', 'm4a', 'mp4', 'm4v', 'mov'
    )
)

class ServiceError(Exception):
    pass

class StoppedService(Exception):
    pass
