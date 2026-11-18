import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.treinar_modelos import treinar  # noqa: E402
from tests.fixtures import dados_sinteticos  # noqa: E402


@pytest.fixture(scope="session")
def modelos_sinteticos(tmp_path_factory):
    """Treina com dados SINTÉTICOS numa pasta temporária (nunca em models/)."""
    base = tmp_path_factory.mktemp("modelos")
    csv = base / "dados.csv"
    dados_sinteticos(4000).to_csv(csv, index=False)
    treinar(str(csv), str(base))
    return base


@pytest.fixture()
def cliente_flask(modelos_sinteticos, monkeypatch):
    import predictor
    monkeypatch.setattr(predictor, "CAMINHO_PRAZO", str(modelos_sinteticos / "modelo_prazo.joblib"))
    monkeypatch.setattr(predictor, "CAMINHO_ATRASO", str(modelos_sinteticos / "modelo_atraso.joblib"))
    predictor.limpar_cache()
    from app import criar_app
    app = criar_app()
    app.testing = True
    yield app.test_client()
    predictor.limpar_cache()
