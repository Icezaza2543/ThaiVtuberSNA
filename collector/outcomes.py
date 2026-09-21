"""Public failures contain categories, never extractor payloads."""
class ExtractionFailure(RuntimeError):
    def __init__(self, status='EXTRACTION_FAILURE'):
        self.status = status
        super().__init__(status)


def classify_error(error):
    # Inspect in memory only. Never persist the original message or exception chain.
    message = str(error).lower()
    if 'commentsdisabled' in message or 'comments are turned off' in message:
        return 'COMMENTS_DISABLED'
    if '429' in message or 'ratelimit' in message or 'quotaexceeded' in message:
        return 'RATE_LIMITED'
    return 'EXTRACTION_FAILURE'


class QuietExtractorLogger:
    def debug(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
