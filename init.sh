# See dev.nix for the NixOS way to have the system dependencies for this.
# TL;DR: have mongo and python3.6 (but cffi in py depends on libffi and gcc, so those too)

python -m venv venv
source venv/bin/activate

[ -d db ] || mkdir db/

pip install -r requirements.txt
mongod --dbpath db/&
MONGO_PID = $!

echo "db.createUser({user: 'les-user', pwd: 'ludicrous-event-system', roles = ['readWrite']})" | mongo

cd tests
pytest || echo "Py tests failed, something didn't work";

kill $MONGO_PID;

echo "Everything looks OK."
echo "Run 'mongod' and 'python main.py' in separate shells to start a flask server."
echo $MONGO_PID
# or fork, if you roll that way.
