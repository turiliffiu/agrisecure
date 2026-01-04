#!/bin/bash
# AgriSecure - Avvia tutti i servizi

echo "Avvio servizi AgriSecure..."

sudo systemctl start agrisecure-web
sudo systemctl start agrisecure-celery
sudo systemctl start agrisecure-celery-beat
sudo systemctl start agrisecure-mqtt

sleep 2

echo ""
echo "Stato servizi:"
sudo systemctl status agrisecure-web --no-pager -l | head -5
sudo systemctl status agrisecure-celery --no-pager -l | head -5
sudo systemctl status agrisecure-celery-beat --no-pager -l | head -5
sudo systemctl status agrisecure-mqtt --no-pager -l | head -5

echo ""
echo "Tutti i servizi avviati!"

# Ottieni IP
CONTAINER_IP=$(hostname -I | awk '{print $1}')
echo "Dashboard: http://$CONTAINER_IP/admin/"
echo "API Docs:  http://$CONTAINER_IP/api/v1/docs/"
