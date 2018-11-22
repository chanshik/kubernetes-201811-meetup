import os
import glob

files = glob.glob("*.docker")
for filename in files:
    os.system("docker load -i {}".format(filename))
