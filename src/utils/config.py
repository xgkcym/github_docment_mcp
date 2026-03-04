import logging
import os.path
import pathlib


root_dir = pathlib.Path(__file__).parent.parent.parent

log_dir = root_dir / "logs"
log_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")


chroma_data_dir = root_dir / 'chroma_data'

