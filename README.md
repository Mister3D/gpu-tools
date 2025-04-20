apt-get install -y ffmpeg


Le serveur de développement recharge les models de multiple fois ce qui à pour effet de cracher le programme

gunicorn -c gunicorn_config.py main:app