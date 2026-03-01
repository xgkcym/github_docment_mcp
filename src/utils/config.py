import logging
import pathlib


root_dir = pathlib.Path(__file__).parent.parent

log_dir = root_dir / "logs"
log_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

