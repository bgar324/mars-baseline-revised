import inspect
import logging
import sys
from http import HTTPStatus
from urllib.parse import parse_qs, urlsplit

from loguru import logger

from mars.llm.providers.base import TokenUsage

LOG_FORMAT = (
    "<dim>{time:YYYY-MM-DD HH:mm:ss}</dim> | "
    "<level>{level:<8}</level> | "
    "<cyan>{extra[source]:<20}</cyan> - <blue>{extra[stage]:<9}</blue> | "
    "{message}"
)

LEVEL_COLORS = {
    "DEBUG": "<blue>",
    "INFO": "<green>",
    "WARNING": "<yellow>",
    "ERROR": "<red>",
    "CRITICAL": "<red><bold>",
}

NOISY_LOGGERS = {
    "absl": "WARNING",
    "httpcore": "WARNING",
    "google_genai": "WARNING",
    "urllib3": "WARNING",
}

SUPPRESS_SUBSTRINGS = ("Prompt alignment: non-exact match",)


def http_status_text(code: int) -> str:
    try:
        return f"{code} {HTTPStatus(code).phrase}"
    except ValueError:
        return f"{code} Unknown"


def http_status_family(code: int) -> str:
    match code // 100:
        case 1:
            return "1xx informational"
        case 2:
            return "2xx success"
        case 3:
            return "3xx redirection"
        case 4:
            return "4xx client_error"
        case 5:
            return "5xx server_error"
        case _:
            return "unknown"


def format_http_log(method: str, route: str, status_code: int, query: str) -> str:
    head = (
        f"{method.upper()} {route} | "
        f"{http_status_text(status_code)} | {http_status_family(status_code)}"
    )
    return f'{head} | "{query}"' if query else head


def _shorten_httpx(record: logging.LogRecord) -> None:
    args = record.args
    if not isinstance(args, tuple) or len(args) < 4:
        return
    method, url, status = args[0], str(args[1]), args[3]
    split = urlsplit(url)
    parts = [p for p in split.path.split("/") if p]
    endpoint = "/".join(parts[-2:]) if parts else split.path
    query = parse_qs(split.query).get("query", [None])[0] or ""
    code = int(status)
    record.msg = format_http_log(method, endpoint, code, query)
    record.args = ()
    if code == 429:
        record.levelno = logging.DEBUG
        record.levelname = "DEBUG"


class _ExternalFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if (
            record.name == "httpx"
            and isinstance(record.msg, str)
            and record.msg.startswith("HTTP Request:")
        ):
            _shorten_httpx(record)
        return not any(s in record.getMessage() for s in SUPPRESS_SUBSTRINGS)


def configure_logging(
    *,
    level: str = "INFO",
    jsonl_path: str | None = None,
    enqueue: bool = True,
) -> None:
    logger.remove()
    logger.configure(extra={"source": "mars", "stage": "pipeline"})
    for name, color in LEVEL_COLORS.items():
        logger.level(name, color=color)
    logger.add(
        sys.stderr,
        format=LOG_FORMAT,
        level=level,
        colorize=True,
        enqueue=enqueue,
    )
    if jsonl_path:
        logger.add(jsonl_path, level="DEBUG", serialize=True, enqueue=enqueue)
    _intercept_stdlib(level)
    for name, lvl in NOISY_LOGGERS.items():
        logging.getLogger(name).setLevel(lvl)


def _intercept_stdlib(level: str) -> None:
    class Intercept(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                lvl: str | int = logger.level(record.levelname).name
            except ValueError:
                lvl = record.levelno
            frame, depth = inspect.currentframe(), 0
            while frame:
                filename = frame.f_code.co_filename
                is_logging = filename == logging.__file__
                is_frozen = "importlib" in filename and "_bootstrap" in filename
                if depth > 0 and not (is_logging or is_frozen):
                    break
                frame = frame.f_back
                depth += 1
            label = (
                "diagnostic.warning"
                if record.levelno >= logging.WARNING
                else "diagnostic"
            )
            logger.bind(source=record.name, stage="external").opt(
                depth=depth, exception=record.exc_info
            ).log(lvl, "{} | {}", label, record.getMessage())

    handler = Intercept()
    handler.addFilter(_ExternalFilter())
    logging.basicConfig(handlers=[handler], level=level, force=True)


def format_token_usage(usage: TokenUsage | None) -> str:
    if usage is None or usage.total_tokens == 0:
        return ""
    return (
        "token usage: "
        f"total={usage.total_tokens}, input={usage.input_tokens}, "
        f"output={usage.output_tokens}, thinking={usage.thinking_tokens}, "
        f"cache={usage.cached_tokens}"
    )


def format_model(provider: str | None, model: str | None) -> str:
    if not provider or not model:
        return ""
    return f"model: {provider}/{model}"


def format_duration(seconds: float) -> str:
    return f"completed in {seconds:.1f}s"


def format_failure_duration(seconds: float) -> str:
    return f"failed after {seconds:.1f}s"


def join_meta(*parts: str) -> str:
    return " | ".join(p for p in parts if p)
