#!/bin/bash
# AgriSecure - Ferma tutti i servizi

echo "Arresto servizi AgriSecure..."

sudo systemctl stop agrisecure-mqtt
sudo systemctl stop agrisecure-celery-beat
sudo systemctl stop agrisecure-celery
sudo systemctl stop agrisecure-web

echo "Tutti i servizi fermati!"
