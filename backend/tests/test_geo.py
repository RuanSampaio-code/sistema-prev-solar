"""Testes unitários para o módulo ai.geo.

Cenários cobertos:
  (a) Imagem georreferenciada com endereço obtido com sucesso
  (b) Imagem georreferenciada com falha no geocoder após as 3 tentativas
  (c) Imagem sem georreferenciamento (não-TIFF, ou TIFF sem metadados)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ── Fixture: reseta o singleton do Nominatim entre testes ─────────────────────

@pytest.fixture(autouse=True)
def reset_nominatim_cache():
    import ai.geo as geo_module
    geo_module._nominatim = None
    yield
    geo_module._nominatim = None


# ─────────────────────────────────────────────────────────────────────────────
# (c) Imagem SEM georreferenciamento
# ─────────────────────────────────────────────────────────────────────────────

class TestSemGeorreferenciamento:
    def test_read_geo_metadata_arquivo_nao_tiff(self, tmp_path):
        """read_geo_metadata devolve (None, None) para arquivos que não são TIFF."""
        from ai.geo import read_geo_metadata

        jpg = tmp_path / "imagem.jpg"
        jpg.write_bytes(b"fake")
        transform, crs = read_geo_metadata(str(jpg))

        assert transform is None
        assert crs is None

    def test_read_geo_metadata_tiff_sem_metadados(self, tmp_path):
        """read_geo_metadata devolve (None, None) quando rasterio falha ao abrir."""
        from ai.geo import read_geo_metadata

        tif = tmp_path / "imagem.tif"
        tif.write_bytes(b"not a real tiff")

        with patch("rasterio.open", side_effect=Exception("invalid tiff")):
            transform, crs = read_geo_metadata(str(tif))

        assert transform is None
        assert crs is None

    def test_is_georeferenced_false_para_none(self):
        from ai.geo import is_georeferenced
        assert not is_georeferenced(None, None)
        assert not is_georeferenced(MagicMock(), None)
        assert not is_georeferenced(None, MagicMock())

    def test_pixel_to_latlon_retorna_none_sem_transform(self):
        from ai.geo import pixel_to_latlon
        lat, lon = pixel_to_latlon(None, None, 100, 200)
        assert lat is None
        assert lon is None

    def test_reverse_geocode_retorna_nao_georeferenciado_para_none(self):
        from ai.geo import reverse_geocode, NOT_GEOREFERENCED
        result = reverse_geocode(None, None)
        assert result == NOT_GEOREFERENCED

    def test_get_image_address_sem_georef(self):
        from ai.geo import get_image_address, NOT_GEOREFERENCED
        result = get_image_address(None, None, 1000, 1000)
        assert result == NOT_GEOREFERENCED


# ─────────────────────────────────────────────────────────────────────────────
# (a) Imagem georreferenciada — endereço obtido com SUCESSO
# ─────────────────────────────────────────────────────────────────────────────

class TestGeocomSucesso:
    def _make_rasterio_src(self, transform, crs):
        src = MagicMock()
        src.transform = transform
        src.crs = crs
        src.__enter__ = lambda s: s
        src.__exit__ = MagicMock(return_value=False)
        return src

    def test_read_geo_metadata_tiff_valido(self, tmp_path):
        from ai.geo import read_geo_metadata

        tif = tmp_path / "imagem.tif"
        tif.write_bytes(b"fake tiff")

        mock_transform = MagicMock()
        mock_crs = MagicMock()
        mock_src = self._make_rasterio_src(mock_transform, mock_crs)

        with patch("rasterio.open", return_value=mock_src):
            transform, crs = read_geo_metadata(str(tif))

        assert transform is mock_transform
        assert crs is mock_crs

    def test_pixel_to_latlon_epsg4326(self):
        """Quando CRS já é EPSG:4326, coordenadas são devolvidas diretamente."""
        from ai.geo import pixel_to_latlon

        mock_transform = MagicMock()
        mock_crs = MagicMock()
        mock_crs.to_epsg.return_value = 4326

        with patch("rasterio.transform.xy", return_value=(-44.3, -2.5)):
            lat, lon = pixel_to_latlon(mock_transform, mock_crs, 100, 200)

        # xy retorna (x, y); para EPSG:4326 lat=y, lon=x
        assert lat == -2.5
        assert lon == -44.3

    def test_pixel_to_latlon_reprojecao(self):
        """Para CRS projetado (não 4326), reprojecta para WGS84."""
        from ai.geo import pixel_to_latlon

        mock_transform = MagicMock()
        mock_crs = MagicMock()
        mock_crs.to_epsg.return_value = 32724  # UTM zona 24S

        with patch("rasterio.transform.xy", return_value=(500000.0, 9700000.0)), \
             patch("rasterio.warp.transform", return_value=([-44.3], [-2.5])):
            lat, lon = pixel_to_latlon(mock_transform, mock_crs, 100, 200)

        assert lat == pytest.approx(-2.5)
        assert lon == pytest.approx(-44.3)

    def test_reverse_geocode_sucesso(self):
        """reverse_geocode devolve o endereço retornado pelo Nominatim."""
        from ai.geo import reverse_geocode

        mock_location = MagicMock()
        mock_location.address = "Av. Principal, São Luís, MA, Brasil"

        mock_nominatim_instance = MagicMock()
        mock_nominatim_instance.reverse.return_value = mock_location

        with patch("geopy.geocoders.Nominatim", return_value=mock_nominatim_instance), \
             patch("time.sleep"):
            result = reverse_geocode(-2.5297, -44.3028)

        assert result == "Av. Principal, São Luís, MA, Brasil"
        mock_nominatim_instance.reverse.assert_called_once_with(
            (-2.5297, -44.3028), language="pt-BR", timeout=10
        )

    def test_get_image_address_sucesso(self):
        """get_image_address obtém endereço do centro da imagem."""
        from ai.geo import get_image_address

        mock_transform = MagicMock()
        mock_crs = MagicMock()
        mock_crs.to_epsg.return_value = 4326

        mock_location = MagicMock()
        mock_location.address = "Centro, São Luís, MA"
        mock_nominatim_instance = MagicMock()
        mock_nominatim_instance.reverse.return_value = mock_location

        with patch("rasterio.transform.xy", return_value=(-44.3, -2.5)), \
             patch("geopy.geocoders.Nominatim", return_value=mock_nominatim_instance), \
             patch("time.sleep"):
            result = get_image_address(mock_transform, mock_crs, 1000, 1000)

        assert result == "Centro, São Luís, MA"


# ─────────────────────────────────────────────────────────────────────────────
# (b) Imagem georreferenciada — FALHA no geocoder
# ─────────────────────────────────────────────────────────────────────────────

class TestGeocoderFalha:
    def test_reverse_geocode_timeout_tenta_3_vezes(self):
        """GeocoderTimedOut dispara backoff e retry; após 3 tentativas retorna fallback."""
        from geopy.exc import GeocoderTimedOut
        from ai.geo import reverse_geocode, GEOCODE_FAILED, _GEOCODER_RETRIES

        mock_nominatim_instance = MagicMock()
        mock_nominatim_instance.reverse.side_effect = GeocoderTimedOut("timeout")

        with patch("geopy.geocoders.Nominatim", return_value=mock_nominatim_instance), \
             patch("time.sleep"):
            result = reverse_geocode(-2.5, -44.3)

        assert result == GEOCODE_FAILED
        assert mock_nominatim_instance.reverse.call_count == _GEOCODER_RETRIES

    def test_reverse_geocode_service_error_tenta_3_vezes(self):
        """GeocoderServiceError dispara backoff e retry; após 3 tentativas retorna fallback."""
        from geopy.exc import GeocoderServiceError
        from ai.geo import reverse_geocode, GEOCODE_FAILED, _GEOCODER_RETRIES

        mock_nominatim_instance = MagicMock()
        mock_nominatim_instance.reverse.side_effect = GeocoderServiceError("503")

        with patch("geopy.geocoders.Nominatim", return_value=mock_nominatim_instance), \
             patch("time.sleep"):
            result = reverse_geocode(-2.5, -44.3)

        assert result == GEOCODE_FAILED
        assert mock_nominatim_instance.reverse.call_count == _GEOCODER_RETRIES

    def test_reverse_geocode_excecao_generica_sem_retry(self):
        """Exceção inesperada (não timeout/serviço) aborta imediatamente sem retry."""
        from ai.geo import reverse_geocode, GEOCODE_FAILED

        mock_nominatim_instance = MagicMock()
        mock_nominatim_instance.reverse.side_effect = RuntimeError("unexpected")

        with patch("geopy.geocoders.Nominatim", return_value=mock_nominatim_instance), \
             patch("time.sleep"):
            result = reverse_geocode(-2.5, -44.3)

        assert result == GEOCODE_FAILED
        # Exceção genérica não faz retry — aborta na primeira tentativa
        assert mock_nominatim_instance.reverse.call_count == 1

    def test_reverse_geocode_sucesso_na_segunda_tentativa(self):
        """Se a primeira tentativa falha por timeout mas a segunda tem sucesso, retorna endereço."""
        from geopy.exc import GeocoderTimedOut
        from ai.geo import reverse_geocode

        mock_location = MagicMock()
        mock_location.address = "Rua das Palmeiras, São Luís, MA"
        mock_nominatim_instance = MagicMock()
        mock_nominatim_instance.reverse.side_effect = [
            GeocoderTimedOut("timeout"),  # 1ª tentativa falha
            mock_location,               # 2ª tentativa sucede
        ]

        with patch("geopy.geocoders.Nominatim", return_value=mock_nominatim_instance), \
             patch("time.sleep"):
            result = reverse_geocode(-2.5, -44.3)

        assert result == "Rua das Palmeiras, São Luís, MA"
        assert mock_nominatim_instance.reverse.call_count == 2

    def test_pixel_to_latlon_falha_na_reprojecao(self):
        """pixel_to_latlon captura erros de reprojeção e devolve (None, None)."""
        from ai.geo import pixel_to_latlon

        mock_crs = MagicMock()
        mock_crs.to_epsg.return_value = 32724

        with patch("rasterio.transform.xy", return_value=(500000.0, 9700000.0)), \
             patch("rasterio.warp.transform", side_effect=Exception("proj error")):
            lat, lon = pixel_to_latlon(MagicMock(), mock_crs, 100, 200)

        assert lat is None
        assert lon is None

    def test_inferencia_continua_mesmo_com_falha_geo(self):
        """Quando o geocoder esgota todas as tentativas, o pipeline não lança exceção."""
        from geopy.exc import GeocoderTimedOut
        from ai.geo import reverse_geocode, GEOCODE_FAILED

        mock_nominatim_instance = MagicMock()
        mock_nominatim_instance.reverse.side_effect = GeocoderTimedOut("network error")

        with patch("geopy.geocoders.Nominatim", return_value=mock_nominatim_instance), \
             patch("time.sleep"):
            result = reverse_geocode(-2.5, -44.3)

        # A inferência não é interrompida — apenas retorna o fallback após 3 tentativas
        assert result == GEOCODE_FAILED
