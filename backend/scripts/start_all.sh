#!/bin/bash
# AgriSecure - Avvia tutti i servizi

echo "Avvio servizi AgriSecure..."

sudo systemctl start agrisecure-web
sudo systemctl start agrisecure-celery
sudo systemctl start agrisecure-celery-beat
sudo systemctl start agrisecure-mqtt

echo ""
echo "Stato servizi:"
sudo systemctl status agrisecure-web --no-pager -l | head -5
sudo systemctl status agrisecure-celery --no-pager -l | head -5
sudo systemctl status agrisecure-celery-beat --no-pager -l | head -5
sudo systemctl status agrisecure-mqtt --no-pager -l | head -5

echo ""
echo "Tutti i servizi avviati!"
echo "Dashboard: http://localhost/admin/"
echo "API Docs:  http://localhost/api/v1/docs/"
