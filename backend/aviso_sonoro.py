"""
aviso_sonoro.py — Som curto de "limite atingido" (ERS v6.0, 5.23).

O Flet 0.86.5 não oferece som no desktop Linux (sem `Audio` no cliente
desktop, e `HapticFeedback` só vibra no celular). Por isso o aviso usa um
programa de som do próprio sistema, sem nenhuma dependência pip:
`canberra-gtk-play` (tema de sons do desktop) ou, na falta dele, `paplay`
com o som padrão freedesktop.

É MELHOR ESFORÇO: depende do programa estar instalado, do tema de sons e
do servidor de áudio. Fora do desktop Linux de referência (ou sem esses
programas), o aviso simplesmente não toca -- nunca levanta erro nem trava a
interface. O aviso visual ("Limite atingido") não depende dele.
"""

import os
import shutil
import subprocess
import time

SOM_FREEDESKTOP = "/usr/share/sounds/freedesktop/stereo/dialog-warning.oga"

# Recusas separadas por menos que isto são a mesma sequência (ex.: tecla
# mantida pressionada, com repetição automática): só a primeira toca.
INTERVALO_SEM_REPETIR = 1.0


def _comandos_padrao(localizar=shutil.which, existe=os.path.exists):
    comandos = []
    if localizar("canberra-gtk-play"):
        comandos.append(["canberra-gtk-play", "--id=dialog-warning", "--description=Limite atingido"])
    if localizar("paplay") and existe(SOM_FREEDESKTOP):
        comandos.append(["paplay", SOM_FREEDESKTOP])
    return comandos


class AvisoSonoro:
    def __init__(self, comandos=None, iniciar=subprocess.Popen, relogio=time.monotonic):
        self._comandos = comandos
        self._iniciar = iniciar
        self._relogio = relogio
        self._ultima_tentativa = None
        self._processo = None

    def tocar(self):
        """
        Dispara o som sem esperar ele terminar. Retorna True se um processo
        de som foi iniciado; False quando foi suprimido (mesma sequência de
        recusas, ou um som ainda tocando) ou quando não há como tocar.
        """
        agora = self._relogio()
        anterior, self._ultima_tentativa = self._ultima_tentativa, agora
        if anterior is not None and agora - anterior < INTERVALO_SEM_REPETIR:
            return False
        if self._processo is not None and self._processo.poll() is None:
            return False  # nunca dois sons ao mesmo tempo

        if self._comandos is None:
            self._comandos = _comandos_padrao()
        for comando in self._comandos:
            try:
                self._processo = self._iniciar(
                    comando,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return True
            except (OSError, ValueError, subprocess.SubprocessError):
                continue  # programa sumiu ou falhou ao iniciar: tenta o próximo
        return False


aviso_limite = AvisoSonoro()
