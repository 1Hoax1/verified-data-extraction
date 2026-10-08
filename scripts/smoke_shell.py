"""Reproduce ready/rerun/degraded/blocked shell checks without external services."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from streamlit.testing.v1 import AppTest
from vde.bootstrap import bootstrap
from vde.config import Config
from vde.persistence.database import connect


def main():
    previous = os.environ.get("VDE_WORKSPACE")
    try:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            os.environ["VDE_WORKSPACE"] = str(root)
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "src/vde/app.py")).run()
            assert not app.exception and app.success[0].value == "Local persistence is ready."
            app.run()
            assert not app.exception and app.success[0].value == "Local persistence is ready."
            (root / ".staging/leftover").write_bytes(b"interrupted")
            app.run()
            assert not app.exception and app.warning
            result = bootstrap(Config(root))
            connection = connect(result.database)
            try:
                connection.execute("UPDATE schema_migrations SET checksum=?", ("0" * 64,))
            finally:
                connection.close()
            app.run()
            assert not app.exception and app.error and "STORAGE_ERROR" in app.json[0].value
            print("PASS: Streamlit ready, rerun, degraded and blocked rendering")
    finally:
        if previous is None:
            os.environ.pop("VDE_WORKSPACE", None)
        else:
            os.environ["VDE_WORKSPACE"] = previous


if __name__ == "__main__":
    main()
