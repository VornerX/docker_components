Usage for Ubuntu:
-----
1. Install Docker CE like it described here: https://docs.docker.com/engine/installation/linux/docker-ce/ubuntu/#install-docker-ce-1
2. Add current user to docker's group:
```
sudo usermod -aG docker $USER
```
3. Make sure that you have python3 installed. Execute at root directory of a project:
```
pip3 install -r requirements.txt
```
4. Create config from config_default.py
```
cp config_default.py config.py
```
5. Execute run.py
```
python3 run.py
```