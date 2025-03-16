#!/bin/bash
echo "🚀 Desplegando la app en ShinyApps.io..."
rsconnect deploy shiny /home/usuario/Documentos/TFG --name tfgcarmen --title app.py
echo "✅ ¡App actualizada con éxito!"
