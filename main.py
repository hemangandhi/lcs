import sys
import importlib

import yaml

from flask import jsonify, Flask

class GenSym:
    def __init__(self):
        self.reg = dict()
    def __call__(self, fn):
        key = 'unlikely_to_collide_prefix_' + str(len(self.reg))
        self.reg[key] = fn
        fn.__name__ = key
        return getattr(self, key)
    def __getattr__(self, name):
        if name.startswith('unlikely_to_collide_prefix_'):
            return self.reg[name]
        return getattr(super(self), name)

def add_aws_lambda_to_flask(aws_lambda, yml_config, flask_app, sym):
    @flask_app.route('/' + yml_config['path'], methods=(yml_config['method'],))
    @sym
    def handler():
        event = request.get_json()
        aws_val = aws_lambda(event, None)
        return jsonify(aws_val.get('body', aws_val)), aws_val.get('statusCode', 200)
    

def read_serverless_yml(path, flask_app):
    g = GenSym()
    with open(path) as yml_config:
        parsed = yaml.load(yml_config, Loader=yaml.SafeLoader)
    for function in parsed['functions']:
        handler_path = parsed['functions'][function]['handler']
        import_path, fn_name = handler_path.split('.')
        import_path = import_path.replace('/', '.')
        print('from {} import {}'.format(import_path, fn_name))
        aws_lambda = getattr(importlib.import_module(import_path), fn_name)
        http_config = parsed['functions'][function]['events'][0]['http']
        add_aws_lambda_to_flask(aws_lambda, http_config, flask_app, g)


if __name__ == "__main__":
    app = Flask(__name__)
    read_serverless_yml('serverless.yml', app)
    app.run()
