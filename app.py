from flask import Flask, render_template, request

app = Flask(__name__)

import csv

import uuid
from azure.core.exceptions import AzureError
from azure.cosmos import CosmosClient, PartitionKey

# update the connection string to your own string
# the database in the tutorial has been deleted.
DB_CONN_STR = "AccountEndpoint=https://pengtaohe.documents.azure.com:443/;AccountKey=I593lvB3B2nRUiyxQaySwclTXoSksAatu8uzJvLW4GryuaKczUjEOh0CSqxScjKRRBRBrWRB6S5bACDbY9ek6A=="
db_client = CosmosClient.from_connection_string(conn_str = DB_CONN_STR)


def fetch_data(city_name = None, include_header = False, exact_match = False):
    database = db_client.get_database_client("dbpengtaohe")
    container = database.get_container_client("us-cities")
    QUERY = "SELECT * from us_cities"
    params = None
    if city_name is not None:
        QUERY = "SELECT * FROM us_cities p WHERE p.city = @city_name"
        params = [dict(name="@city_name", value=city_name)]
        if not exact_match:
            QUERY = "SELECT * FROM us_cities p WHERE p.city like @city_name"
    
    headers = ["city", "lat", "lng", "country", "state", "population"]
    result = []
    row_id = 0
    if include_header:
        line = [x for x in headers]
        line.insert(0, "")
        result.append(line)
    
    for item in container.query_items(
        query=QUERY, parameters=params, enable_cross_partition_query=True,
    ):
        row_id += 1
        line = [str(row_id)]
        for col in headers:
            line.append(item[col])
        result.append(line)
    return result

# def fetch_data(city_name = None, include_header = False, exact_match = False):
#     with open("us-cities.csv") as csvfile:
#         csvreader = csv.reader(csvfile, delimiter=',', quotechar='|')
#         row_id = -1
#         wanted_data = []
#         for row in csvreader:
#             row_id += 1
#             if row_id == 0 and not include_header:
#                 continue
#             line = []
#             col_id = -1
#             is_wanted_row = False
#             if city_name is None:
#                 is_wanted_row = True
#             for raw_col in row:
#                 col_id += 1
#                 col = raw_col.replace('"', '')
#                 line.append( col )
#                 if col_id == 0 and city_name is not None:
#                     if not exact_match and city_name.lower() in col.lower():
#                         is_wanted_row = True
#                     elif exact_match and city_name.lower() == col.lower():
#                         is_wanted_row = True
#             if is_wanted_row:
#                 if row_id > 0:
#                     line.insert(0, "{}".format(row_id))
#                 else:
#                     line.insert(0, "")
#                 wanted_data.append(line)
#     return wanted_data

def append_or_update_data(req):
    city_name = req['city_name']
    lat = req['lat']
    lng = req['lng']
    country = req['country']
    state = req['state']
    population = req['population']

    if city_name is None:
        return False

    input_line = '"{}","{}","{}","{}","{}","{}"'.format(
        city_name, lat, lng, country, state, population,
    )

    existing_records = fetch_data(city_name = city_name, exact_match=True)
    if len(existing_records) == 0:
        with open('us-cities.csv', 'a') as f:
            f.write(input_line)
            f.close()
    else:
        all_records = fetch_data(include_header=True)
        lines = []
        for row in all_records:
            line_to_write = ""
            if row[1].lower() != city_name.lower():
                line_to_write = ",".join(['"{}"'.format(col) for col in row[1:]])
            else:
                line_to_write = input_line
            lines.append(line_to_write + "\n")
        with open('us-cities.csv', 'w') as f:
            f.writelines(lines)
            f.close()
    return True

def delete_data(city_name):
    existing_records = fetch_data(city_name = city_name, exact_match=True)
    if len(existing_records) > 0:
        all_records = fetch_data(include_header=True)
        lines = []
        for row in all_records:
            if row[1].lower() != city_name.lower():
                line_to_write = ",".join(['"{}"'.format(col) for col in row[1:]])
                lines.append(line_to_write + "\n")
        with open('us-cities.csv', 'w') as f:
            f.writelines(lines)
            f.truncate()
            f.close()
        return True
    return False

@app.route('/data', methods=['GET'])
def query():
    city_name = request.args.get('city_name')
    if city_name is not None:
        city_name = city_name.replace('"', '')
    wanted_data = fetch_data(city_name = city_name, include_header = True)
    table_content = ""
    for row in wanted_data:
        line_str = ""
        for col in row:
            line_str += "<td>" + col + "</td>"
        table_content += "<tr>" + line_str + "</tr>"
    page = "<html><title>Tutorial of CSE6332 - Part2</title><body>"
    page += "<table>" + table_content + "</table>"
    page += "</body></html>"
    return page

@app.route('/data', methods=['PUT'])
def append_or_update():
    req = request.json
    if append_or_update_data(req):
        return "done"
    else:
        return "invalid input"
    
@app.route('/data', methods=['DELETE'])
def delete():
    city_name = request.args.get('city_name')
    if city_name is not None:
        city_name = city_name.replace('"', '')
    else:
        return "invalid input"

    if delete_data(city_name):
        return "done"
    else:
        return "city does not exist"
    
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', message='web')

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)