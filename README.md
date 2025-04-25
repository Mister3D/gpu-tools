apt-get install -y ffmpeg


Le serveur de développement recharge les models de multiple fois ce qui à pour effet de cracher le programme

gunicorn -c gunicorn_config.py main:app

poetry run gunicorn -c gunicorn_config.py main:app

nano /etc/systemd/system/gpu-tools.service


```
[Unit]
Description=Service Gunicorn avec Poetry pour GPU Tools
After=network.target

[Service]
User=root
WorkingDirectory=/root/gpu-tools
ExecStart=/root/.local/bin/poetry run gunicorn -c gunicorn_config.py main:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Tester le service : `systemctl start gpu-tools.service`
Activer le service au boot : `systemctl enable gpu-tools.service`
Voir le status : `systemctl status gpu-tools.service`
Voir les log en live : `journalctl -u gpu-tools.service -f`