"""Geolocalização de painéis solares detectados.

Fornece leitura de metadados GeoTIFF (transform/crs), conversão pixel→lat/lon
e geocodificação reversa via Nominatim (OpenStreetMap), seguindo a lógica do
script de referência segmentacao_paineis_geo_v3_YOLO.py.

Todas as dependências pesadas (rasterio, geopy) são importadas de forma lazy
para não bloquear o boot da aplicação quando esses pacotes não estão instalados.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

# ─── Constantes de fallback ───────────────────────────────────────────────────

NOT_GEOREFERENCED   = "Não Georreferenciado"
GEOCODE_FAILED      = "Falha ao obter endereço"
GEOCODE_NOT_FOUND   = "Endereço não encontrado"
GEOCODE_NOT_REQUESTED = "Não solicitado"

# ─── Configurações do geocoder ────────────────────────────────────────────────

_GEOCODER_USER_AGENT  = "prevsolar_uema_brisas"
_GEOCODER_DELAY       = 1.1  # Nominatim exige mínimo 1 s entre requisições
_GEOCODER_TIMEOUT     = 10
_GEOCODER_RETRIES     = 3    # tentativas antes de desistir (igual ao script de referência)
_GEOCODER_RETRY_DELAY = 2.0  # segundos entre tentativas em caso de timeout/erro de serviço

_nominatim: Any = None


def _geolocator():
    """Retorna (e cacheia) a instância Nominatim."""
    global _nominatim
    if _nominatim is None:
        from geopy.geocoders import Nominatim
        _nominatim = Nominatim(user_agent=_GEOCODER_USER_AGENT)
    return _nominatim


# ─── Metadados GeoTIFF ────────────────────────────────────────────────────────

def read_geo_metadata(filepath: str) -> Tuple[Any, Any]:
    """Lê transform e crs do GeoTIFF via rasterio sem carregar os pixels.

    Retorna (None, None) se o arquivo não for GeoTIFF ou não tiver metadados
    geoespaciais válidos, sem lançar exceção.
    """
    path = Path(filepath)
    if path.suffix.lower() not in {".tif", ".tiff"}:
        return None, None
    try:
        import rasterio
        with rasterio.open(filepath) as src:
            return src.transform, src.crs
    except Exception as exc:
        logger.warning("⚠ Não foi possível ler metadados geo de %s: %s", path.name, exc)
        return None, None


def is_georeferenced(transform: Any, crs: Any) -> bool:
    """Retorna True apenas quando transform e crs são ambos não-None."""
    return transform is not None and crs is not None


# ─── Conversão pixel → lat/lon ────────────────────────────────────────────────

def pixel_to_latlon(
    transform: Any,
    crs: Any,
    cx: int,
    cy: int,
) -> Tuple[Optional[float], Optional[float]]:
    """Converte centroide em pixels (cx, cy) para coordenadas WGS84 (lat, lon).

    Reprojecta quando o CRS da imagem não for EPSG:4326 (mesmo comportamento
    que o script de referência).
    """
    if not is_georeferenced(transform, crs):
        return None, None
    try:
        from rasterio.transform import xy
        from rasterio.warp import transform as warp_transform

        x, y = xy(transform, cy, cx)

        if crs.to_epsg() == 4326:
            return y, x  # y=lat, x=lon no CRS geográfico

        lon_list, lat_list = warp_transform(crs, "EPSG:4326", [x], [y])
        return lat_list[0], lon_list[0]
    except Exception as exc:
        logger.warning("⚠ Falha na conversão pixel→lat/lon: %s", exc)
        return None, None


# ─── Geocodificação reversa ───────────────────────────────────────────────────

def reverse_geocode(lat: Optional[float], lon: Optional[float]) -> str:
    """Converte lat/lon em endereço legível via Nominatim (OpenStreetMap, pt-BR).

    Tenta até _GEOCODER_RETRIES vezes com backoff de _GEOCODER_RETRY_DELAY entre
    falhas recuperáveis (timeout / serviço indisponível), seguindo o mesmo padrão
    do script de referência unet_inferencia_geo.py.
    Nunca lança exceção — retorna string de fallback em caso de falha definitiva.
    """
    if lat is None or lon is None:
        return NOT_GEOREFERENCED

    from geopy.exc import GeocoderTimedOut, GeocoderServiceError

    for attempt in range(1, _GEOCODER_RETRIES + 1):
        try:
            location = _geolocator().reverse(
                (lat, lon), language="pt-BR", timeout=_GEOCODER_TIMEOUT
            )
            time.sleep(_GEOCODER_DELAY)
            return location.address if location else GEOCODE_NOT_FOUND
        except (GeocoderTimedOut, GeocoderServiceError) as exc:
            logger.warning("⚠ Tentativa %d/%d falhou: %s", attempt, _GEOCODER_RETRIES, exc)
            if attempt < _GEOCODER_RETRIES:
                time.sleep(_GEOCODER_RETRY_DELAY)
        except Exception as exc:
            logger.warning("⚠ Falha inesperada na geocodificação: %s", exc)
            return GEOCODE_FAILED

    logger.warning("⚠ Geocodificação falhou após %d tentativas", _GEOCODER_RETRIES)
    return GEOCODE_FAILED


def get_image_address(transform: Any, crs: Any, img_height: int, img_width: int) -> str:
    """Obtém o endereço do ponto central da imagem (estratégia one-call-per-image).

    Chamado uma única vez por imagem quando geocoding_per_panel=False.
    """
    if not is_georeferenced(transform, crs):
        return NOT_GEOREFERENCED
    lat, lon = pixel_to_latlon(transform, crs, img_width // 2, img_height // 2)
    return reverse_geocode(lat, lon)
