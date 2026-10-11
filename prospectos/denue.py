"""Cliente DENUE (INEGI) con validación estricta de esquema. El token nunca se loguea."""
import time
from typing import Iterator

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

BASE = "https://www.inegi.org.mx/app/api/denue/v1/consulta"
PAGE = 200


class Establecimiento(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = Field(alias="Id")
    nombre: str = Field(alias="Nombre")
    razon_social: str = Field(default="", alias="Razon_social")
    clase_actividad: str = Field(default="", alias="Clase_actividad")
    estrato: str = Field(default="", alias="Estrato")
    tipo_vialidad: str = Field(default="", alias="Tipo_vialidad")
    calle: str = Field(default="", alias="Calle")
    num_exterior: str = Field(default="", alias="Num_Exterior")
    colonia: str = Field(default="", alias="Colonia")
    cp: str = Field(default="", alias="CP")
    ubicacion: str = Field(default="", alias="Ubicacion")
    telefono: str = Field(default="", alias="Telefono")
    correo: str = Field(default="", alias="Correo_e")
    sitio: str = Field(default="", alias="Sitio_internet")
    latitud: str = Field(default="", alias="Latitud")
    longitud: str = Field(default="", alias="Longitud")
    num_interior: str = Field(default="", alias="Num_Interior")
    edificio: str = Field(default="", alias="EDIFICIO")
    numero_local: str = Field(default="", alias="numero_local")
    tipo_establecimiento: str = Field(default="", alias="Tipo")
    corredor_nombre: str = Field(default="", alias="nom_corredor_industrial")
    corredor_tipo: str = Field(default="", alias="tipo_corredor_industrial")
    subrama_id: str = Field(default="", alias="SUBRAMA_ACTIVIDAD_ID")
    sector_id: str = Field(default="", alias="SECTOR_ACTIVIDAD_ID")
    subsector_id: str = Field(default="", alias="SUBSECTOR_ACTIVIDAD_ID")
    rama_id: str = Field(default="", alias="RAMA_ACTIVIDAD_ID")
    clase_id: str = Field(default="", alias="CLASE_ACTIVIDAD_ID")
    fecha_alta: str = Field(default="", alias="Fecha_Alta")


class DenueError(RuntimeError):
    pass


def _redact(msg: str, token: str) -> str:
    return msg.replace(token, "***")


class DenueClient:
    def __init__(self, token: str, pause: float = 0.4):
        self._token = token
        self._pause = pause
        self._http = httpx.Client(timeout=45, headers={"User-Agent": "prospectos/0.1"})

    def close(self) -> None:
        self._http.close()

    def _get(self, path: str):
        url = f"{BASE}/{path}/{self._token}"
        for intento in range(3):
            try:
                r = self._http.get(url)
                if r.status_code == 200:
                    return r.json()
                if r.status_code in (404, 204):
                    return []
                if r.status_code >= 500 or r.status_code == 429:
                    time.sleep(2 * (intento + 1))
                    continue
                raise DenueError(f"HTTP {r.status_code}")
            except httpx.HTTPError as e:
                if intento == 2:
                    raise DenueError(_redact(str(e), self._token)) from None
                time.sleep(2 * (intento + 1))
        raise DenueError("reintentos agotados")

    def cuantificar(self, sector: str, entidad: str, estrato: str) -> int:
        data = self._get(f"Cuantificar/{sector}/{entidad}/{estrato}")
        return sum(int(x.get("Total", 0)) for x in data) if isinstance(data, list) else 0

    def buscar(self, entidad: str, sector: str, subsector: str, estrato: str, limite: int | None = None) -> Iterator[Establecimiento]:
        """Pagina BuscarAreaActEstr. Registros malformados se omiten, no rompen la corrida."""
        inicio, emitidos = 1, 0
        while True:
            fin = inicio + PAGE - 1
            ruta = f"BuscarAreaActEstr/{entidad}/0/0/0/0/{sector}/{subsector}/0/0/0/{inicio}/{fin}/0/{estrato}"
            data = self._get(ruta)
            if not isinstance(data, list) or not data:
                return
            for raw in data:
                try:
                    yield Establecimiento.model_validate(raw)
                except ValidationError:
                    continue
                emitidos += 1
                if limite and emitidos >= limite:
                    return
            if len(data) < PAGE:
                return
            inicio += PAGE
            time.sleep(self._pause)
