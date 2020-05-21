from flask import Flask, jsonify
from flask import request, Response, make_response
from pymongo import MongoClient
from bson.json_util import dumps
# from flask_cors import CORS, cross_origin
from flask import g, abort
import json
import os
from splash.config import Config
from splash.data import MongoCollectionDao, ObjectNotFoundError, BadIdError
from splash.util import context_timer

import logging, sys
import pathlib
import jsonschema 


class Constants():
    API_URL_ROOT = "/api"
    COMPOUNDS_URL_ROOT = API_URL_ROOT + "/compounds"
    EXPERIMENTS_URL_ROOT = API_URL_ROOT + "/experiments"
    RUNS_URL_ROOT = API_URL_ROOT + "/runs"


app = Flask(__name__)

if app.config["ENV"] == "production":
    app.config.from_object("config.ProductionConfig")
else:
    app.config.from_object("config.DevelopmentConfig")
#define custom exceptions
class NoIdProvidedError(Exception):
    pass


def setup_logging():
    logger = logging.getLogger('splash-server')
    try:
        # flask_cors_logger = logging.getLogger('flask_cors')
        # flask_cors_logger.setLevel(logging.DEBUG)

        logging_level = os.environ.get("LOGLEVEL")
        print (f"Setting log level to {logging_level}")
        logger.setLevel(logging_level)

        # create console handler and set level to debug
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging_level)

        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to logger
        logger.addHandler(ch)

        logger.debug('testing debug')
        logger.info('testing info')
    except Exception as e:
        print("cannot setup logging: {}".format(str(e)))

setup_logging()


SPLASH_SERVER_DIR = os.environ.get("SPLASH_SERVER_DIR")
logger.info(f'Reading log file {SPLASH_SERVER_DIR}')
if SPLASH_SERVER_DIR == None:
    SPLASH_SERVER_DIR = str(pathlib.Path.home() / ".splash")


SPLASH_CONFIG_FILE = SPLASH_SERVER_DIR + "/config.cfg" if SPLASH_SERVER_DIR is not None else "/config.cfg"
config = Config(SPLASH_CONFIG_FILE)
 
MONGO_URL = config.get(CFG_APP_DB, 'mongo_url', fallback='localhost:27017')
MONGO_APP_USER = config.get(CFG_APP_DB, 'mongo_app_user', fallback='')
MONGO_APP_PW = config.get(CFG_APP_DB, 'mongo_app_pw', fallback='')
WEB_SERVER_HOST = config.get(CFG_WEB, 'server_host', fallback='0.0.0.0')
WEB_SERVER_HOST = config.get(CFG_WEB, 'server_port', fallback='80')
WEB_IMAGE_FOLDER_ROOT = config.get(CFG_WEB, 'image_root_folder', fallback='images')
SPLASH_DB_NAME = 'splash'

db = None

def get_app_db():
    #TODO: we need to cache the connections?
    db = MongoClient(MONGO_URL, 
        username=MONGO_APP_USER,        
        password=MONGO_APP_PW,
        authSource=SPLASH_DB_NAME,
        authMechanism='SCRAM-SHA-256')
    return db

def get_compound_dao():
    db = get_app_db()
    return MongoCollectionDao(db.SPLASH_DB_NAME.compounds)

def get_experiment_dao():
    db = get_app_db()
    return MongoCollectionDao(db.splash.experiments)

# @app.teardown_appcontext
# def teardown_db(exception):
#     db = g.pop('db')
#     if db is not None:
#         db.close()

@app.route(Constants.COMPOUNDS_URL_ROOT, methods=['GET'])
def retrieve_compounds():
    try:
        data_svc = get_compound_dao()
        logger.info("-----In retrieve_copounds")
        page = request.args.get('page')
        if page is None:
            page = 1
        else:
            page = int(page)
        if page <= 0:
            raise ValueError("Page parameter must be positive")
        results = data_svc.retrieve_many(page=page)
        data = {"total_results": results[0], "results": results[1]}
        logger.info("-----In retrieve_copounds find")
        json = dumps(data)
        logger.info("-----In retrieve_copounds dump")
        return json
    except ValueError as e:
        if str(e) == "Page parameter must be positive":
            raise e from None
        raise TypeError("page parameter must be a positive integer") from None




@app.route(Constants.COMPOUNDS_URL_ROOT + "/<compound_id>", methods=['GET'])
def retrieve_compound(compound_id):
    if compound_id:
        data_svc = get_compound_dao()
        compound = data_svc.retrieve(compound_id)
    else:
        raise NoIdProvidedError()
    if compound is None:
        raise ObjectNotFoundError()
    json = dumps(compound)
    return json


@app.route(Constants.COMPOUNDS_URL_ROOT, methods=['POST'])
def create_compound():
    data = json.loads(request.data)
    get_compound_dao().create(data)
    return dumps({'message': 'CREATE SUCCESS', 'uid': str(data['uid'])})


@app.route(Constants.COMPOUNDS_URL_ROOT + "/<compound_id>", methods=['PATCH'])
def update_compound(compound_id):
    data = json.loads(request.data)
    if compound_id:
        get_compound_dao().update(compound_id, data)
    else:
        raise NoIdProvidedError()
    return dumps({'message': 'SUCCESS'})

@app.route(Constants.COMPOUNDS_URL_ROOT + "/<compound_id>", methods=['DELETE'])
def delete_compound(compound_id):
    if compound_id:
        get_compound_dao().delete(compound_id)
    else:
        raise NoIdProvidedError()
    return dumps({'message': 'SUCCESS'})


@app.route(Constants.EXPERIMENTS_URL_ROOT, methods=['POST'])
def create_experiment():
    data = json.loads(request.data)
    jsonschema.validate(data, EXPERIMENTS_SCHEMA)
    get_experiment_dao().create(data)
    return dumps({'message': 'CREATE SUCCESS', 'uid': str(data['uid'])})


@app.route(Constants.EXPERIMENTS_URL_ROOT + "/<experiment_id>", methods=['GET'])
def retrieve_experiment(experiment_id):
    if experiment_id:
        data_svc = get_experiment_dao()
        experiment = data_svc.retrieve(experiment_id)
    else:
        raise NoIdProvidedError()
    if experiment is None:
        raise ObjectNotFoundError()
    json = dumps(experiment)
    return json
        


@app.route(Constants.EXPERIMENTS_URL_ROOT, methods=['GET'])
def retrieve_experiments():
    try:
        data_svc = get_experiment_dao()
        page = request.args.get('page')
        if page is None:
            page = 1
        else:
            page = int(page)
        if page <= 0:
            raise ValueError("Page parameter must be positive")
        results = data_svc.retrieve_many(page=page)
        data = {"total_results": results[0], "results": results[1]}
        json = dumps(data)
        return json
    except ValueError as e:
        if str(e) == "Page parameter must be positive":
            raise e from None
        raise TypeError("page parameter must be a positive integer") from None


@app.route(Constants.EXPERIMENTS_URL_ROOT + "/<experiment_id>", methods=['DELETE'])
def delete_experiment(experiment_id):
    if experiment_id:
        get_experiment_dao().delete(experiment_id)
    else:
        raise NoIdProvidedError()
    return dumps({'message': 'SUCCESS'})
    


@app.route(Constants.EXPERIMENTS_URL_ROOT + "/<experiment_id>", methods=['PUT'])
def update_experiment(experiment_id):
    data = json.loads(request.data)
    jsonschema.validate(data, EXPERIMENTS_SCHEMA)

    if experiment_id:
        get_experiment_dao().update(experiment_id, data)
    else:
        raise NoIdProvidedError()
    return dumps({'message': 'SUCCESS'})







@app.errorhandler(404)
def resource_not_found(error):
    logger.info("Resource not found: ", exc_info=1)
    return make_response(str({'error': 'resource not found'}), 404)


@app.errorhandler(jsonschema.exceptions.ValidationError)
def validation_error(error):
    logger.info(" Validation Error: ", exc_info=1 )
    return make_response(str(error), 400)

@app.errorhandler(TypeError)
def type_error(error):
    logger.info(" TypeError ", exc_info=1)
    return make_response(str(error), 400)

#This actually might never get called because trailing slashes with
#no parameters won't get routed to the route that would raise a
#NoIdProvidedError, they would get routed to a route that just 
#has the trailing slash
@app.errorhandler(NoIdProvidedError)
def no_id_provided_error(error):
    logger.info("No Id Provided Error: ", exc_info=1)
    return make_response(str({'error': 'no id provided'}), 400)

@app.errorhandler(ObjectNotFoundError)
def object_not_found_error(error):
     logger.info(" Object Not Found Error: ", exc_info=1 )
     return make_response(str({'error': 'object not found'}), 404)


@app.errorhandler(BadIdError)
def bad_id_error(error):
    logger.info(" Bad ID error: ", exc_info=1)
    return make_response(str(error), 400)

@app.errorhandler(ValueError)
def value_error(error):
    logger.info(" ValueError ", exc_info=1)
    return make_response(str(error), 400)

@app.errorhandler(Exception)
def general_error(error):
    logger.critical(" Houston we have a problem: ", exc_info=1)
    return make_response(str(error), 500)


def main(args=None):
    logger.info("-----In Main")
    app.run()

if __name__ == '__main__':
    main()