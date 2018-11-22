import os
import glob

files = glob.glob("*.docker")
for filename in files:
    os.system("sudo docker load -i {}".format(filename))
