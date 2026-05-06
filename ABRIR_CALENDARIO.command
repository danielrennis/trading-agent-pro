#!/bin/bash

# Intentar abrir en Google Chrome (Modo App) si está instalado
if [ -d "/Applications/Google Chrome.app" ]; then
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --app=http://localhost:3000/calendar &
else
    # Si no, abrir en Safari o navegador por defecto
    open http://localhost:3000/calendar
fi

# Mantener la ventana al frente (vía AppleScript)
osascript -e 'tell application "Google Chrome" to activate'
osascript -e 'tell application "Safari" to activate'

exit
