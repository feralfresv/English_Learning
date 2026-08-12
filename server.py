#!/usr/bin/env python3
"""
Servidor para el juego de verbos.

Sirve los archivos de esta carpeta Y guarda el progreso en progreso.json,
aqui mismo, junto al HTML.

    python3 server.py

Luego abre:  http://localhost:8000/verbos-juego.html
Para detenerlo: Ctrl+C
"""

import http.server
import json
import os
import shutil
import socketserver
import sys
from datetime import datetime

PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
CARPETA = os.path.dirname(os.path.abspath(__file__))
ARCHIVO = os.path.join(CARPETA, "progreso.json")
RESPALDOS = os.path.join(CARPETA, "respaldos")


class Handler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=CARPETA, **kwargs)

    def do_POST(self):
        if self.path.rstrip("/") != "/progreso":
            self.send_error(404)
            return

        largo = int(self.headers.get("Content-Length", 0))
        if largo <= 0 or largo > 2_000_000:
            self._json(400, {"error": "tamano invalido"})
            return

        try:
            datos = json.loads(self.rfile.read(largo).decode("utf-8"))
            if not isinstance(datos, dict):
                raise ValueError("se esperaba un objeto")
        except Exception as e:
            self._json(400, {"error": f"json invalido: {e}"})
            return

        # respaldo diario, por si algo sale mal
        if os.path.exists(ARCHIVO):
            os.makedirs(RESPALDOS, exist_ok=True)
            hoy = datetime.now().strftime("%Y-%m-%d")
            copia = os.path.join(RESPALDOS, f"progreso-{hoy}.json")
            if not os.path.exists(copia):
                shutil.copy2(ARCHIVO, copia)

        # escritura atomica: primero temporal, luego reemplazo
        tmp = ARCHIVO + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
        os.replace(tmp, ARCHIVO)

        dom = sum(1 for v in datos.values()
                  if isinstance(v, dict) and v.get("box", 0) >= 5)
        print(f"  guardado -> progreso.json  ({len(datos)} verbos, {dom} dominados)")
        self._json(200, {"ok": True, "verbos": len(datos)})

    def _json(self, codigo, cuerpo):
        cuerpo = json.dumps(cuerpo).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def end_headers(self):
        # que el navegador no cachee el progreso viejo
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass  # sin ruido en la terminal


class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    print(f"\n  Carpeta:   {CARPETA}")
    print(f"  Progreso:  {ARCHIVO}")
    if os.path.exists(ARCHIVO):
        try:
            with open(ARCHIVO, encoding="utf-8") as f:
                n = len(json.load(f))
            print(f"             (ya existe, {n} verbos)")
        except Exception:
            print("             (existe pero no pude leerlo)")
    else:
        print("             (se crea al responder la primera pregunta)")

    print(f"\n  Abre:  http://localhost:{PUERTO}/verbos-juego.html")
    print("  Ctrl+C para detener\n")

    try:
        with Servidor(("", PUERTO), Handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Servidor detenido. Tu progreso quedo en progreso.json\n")
    except OSError as e:
        print(f"\n  No pude usar el puerto {PUERTO}: {e}")
        print(f"  Prueba con otro:  python3 server.py 8001\n")
