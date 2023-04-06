from flask import Flask, request, render_template, make_response
from flask_restful import reqparse, abort, Api, Resource
from functools import wraps
import re
import json
import snsql
from snsql import Privacy
import pandas as pd
from helper import StringProcessor

# Loading the query configurations and rules
f = open('config/query_config.json')
query_config = json.load(f)

csv_path = 'datasets/iris-new.csv'
meta_path = 'datasets/iris-new.yaml'

app = Flask(__name__)
api = Api(app)

string_processor = StringProcessor()
parser = reqparse.RequestParser()
parser.add_argument('query', type=str, help="query to be executed")

data = pd.read_csv(csv_path)
privacy = Privacy(epsilon=1.0, delta=0.01)

"""  Wrappers """
# Wrapper layer for API authentication
def authenticate(function=None):
 
    @wraps(function)
    def wrapper(*args, **kwargs):
        print("Validating the API token")
        header_info = request.headers
        """
        We will get the "token" string from the request header. So add here the code to validate that token.
        """
        isValid = True # Assuming that the token is valid
        if not isValid:
            abort(401, message="Not authorized to use this API")
        else:
            _ = function(*args, **kwargs)
            return _
    return wrapper


# Wrapper - Request validation layer for checking the payload
def validatePayload(function=None):
 
    @wraps(function)
    def wrapper(*args, **kwargs):
        print("Validating the request payload")
        params = request.args
        err_msg = ""
        """ if we have more than one request parameters, recommending to define them in a separate config file """
        if "query" not in params:
            err_msg = "query parameter is missing in the request"
            abort(400, message=err_msg)
        else:
            _ = function(*args, **kwargs)
            return _
    return wrapper

""" Wrappers ends here """

class Home(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('index.html'), 200, headers)
    


class DataStore(Resource):
    @authenticate
    @validatePayload
    def get(self):
        params = request.args
        query = params.get('query')
        if query != "":
            decoded_select_query = decodeSelectQuery(query)
            isValid = validateQuery(decoded_select_query, operation="select")
            if isValid:
                try:
                    # execute the query on DB and use the results as data. Here we are using the iris csv information as data
                    reader = snsql.from_connection(data, privacy=privacy, metadata=meta_path)
                    result = reader.execute(query)
                    return result
                except Exception as e:
                    abort(400, message=str(e))
            else:
                abort(400, message="Invalid query")
            
        else:
            abort(400, message="Query should not be empty")


        
""" Decoding the query string into an object"""
def decodeSelectQuery(query):
    qry_obj = query_config["select"]["query_object_format"]
    query = query.strip()
    operation = ""
    if query != "":
        operation_info = query.split(maxsplit=1)
        if len(operation_info) > 0:
            operation = operation_info[0].lower()
            if operation == "select":
                qry_obj["operation"] = operation
                target_group = re.search('select (.*) FROM ', query, re.IGNORECASE)
                if target_group:
                    targets = target_group.group(1)
                    qry_obj["targets"] = list(map(str.strip, targets.split(",")))
                    grp_by = re.split(" GROUP BY ", query, flags=re.IGNORECASE)
                    if len(grp_by) > 1:
                        qry_obj["group_by"] = grp_by[1].strip()
                        conditions = re.search(' where (.*) group by', query, re.IGNORECASE)
                    else:
                        conditions = re.search(' where (.*)', query, re.IGNORECASE)
                    qry_obj["from"] = re.split(" from ", query, flags=re.IGNORECASE)[1].split(" ")[0].strip()
                    
                    if conditions:
                        qry_obj["conditon"] = conditions.group(1)
                        
                    return qry_obj
                    
                else:
                    abort(400, message="Invalid query")
                return qry_obj
            else:
                abort(400, message="Invalid or non-supported query. Please pass a proper SELECT query.")

    if operation == "":
        abort(400, message="Invalid operation. Please check your query string")
    else:
        return qry_obj



""" Validating the query string with the pre-defined rules from the config"""
def validateQuery(query_obj, operation):
    if operation in query_config:
        select_config = query_config[operation]

        #validating targets
        for target in query_obj["targets"]:
            name_split = re.split(" as ", target, flags=re.IGNORECASE)
            if len(name_split) > 1:
                target = name_split[0]
            target_frm_aggregate_func = string_processor.getSubstringBetweenTwoChars("(",")",target)
            if target_frm_aggregate_func != target:
                target = target_frm_aggregate_func
            if target not in select_config["allowed_targets"]:
                abort(400, message=f"'{target}' filed is not allowed to fetch")

        #validating database & table
        if query_obj["from"] not in select_config["allowed_tables"]:
            abort(400, message=f"Not allowed to fetch from this table")
        else:
            return True
    else:
        abort(400, message=f"'{operation}' operation is not supported")


api.add_resource(Home, "/")
api.add_resource(DataStore, "/data", endpoint="data")


if __name__ == "__main__":
    app.run(debug=False, port=8000)