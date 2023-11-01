from rest_framework.response import Response
from rest_framework.views import APIView

import requests
import geopy.distance
import sys
from datetime import datetime
import pprint
class GetStationData(APIView):
    def get(self, request):
        # Retrieving parameters to get the right data
        location = request.query_params.get("location", "")
        # Default distance is 5km
        distance = request.query_params.get("distance","5")
        # Default sort by distance
        criteria = request.query_params.get("criteria","dist")
        if location == "":
            return Response(status=400, data={"Geo position was not provided"})
        location = location.split(",")

        # Forced to split the string like this due to format issues 
        where_string = "within_distance(geom,GEOM'"
        where_string = where_string + '{"type":"Point","coordinates":['+str(location[0])+","+str(location[1])+"]}',"+str(distance)+"km)"

        data = requests.get(
            "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/prix-des-carburants-en-france-flux-instantane-v2/records", {"where":where_string,"limit":100}
        )
        formated = self.format_data(data.json(),location)
        order = self.sort_data(formated,criteria)
        
        return Response(order, status=data.status_code)


    def format_data(self,data,location):
        """Function adding missing informations (Distance/Brand)"""

        names = requests.get("https://eddybess.github.io/nomStationsJson/formattedNames.json").json()
        # Prices key to convert to float numbers
        prices_keys = ["gazole_prix","sp95_prix","e10_prix","sp98_prix","e85_prix","gplc_prix"]
        prices_maj = ["gazole_maj","sp95_maj","e10_maj","sp98_maj","e85_maj","gplc_maj"]
        new_data = []
        for station in data["results"]:
            # In case all fuels are out of stock, we delete the station from the results
            if station["prix"] is None:
                data["results"].remove(station)
                continue
            # Adding the brand
            try:
                station["marque"] = names[str(station["id"])]["marque"]
            except KeyError:
                station["marque"] = "Marque non spécifiée"
            # Adding distance between user and station
            dist = geopy.distance.distance((station["geom"]["lat"],station["geom"]["lon"]),(location[1],location[0])).km
            
            station["dist"] = dist
            # Converting prices to float to faciliate the sort
            for key in prices_keys:
                if station[key] is not None:
                    station[key] = float(station[key])
            # Getting the last update
            price_maj = datetime.strptime("1920-10-10 10:00:00",'%Y-%m-%d %H:%M:%S')
            
            for key in prices_maj:
                if station[key] is not None:
                    current_maj = datetime.strptime(station[key],'%Y-%m-%d %H:%M:%S')
                    if current_maj>price_maj:
                        price_maj = current_maj

            station["price_maj"] = price_maj
            new_data.append(station)
        return new_data

    def sort_data(self, data, criteria):
        """Function to sort the data based on the criteria"""

        return sorted(data,key=lambda x:sys.maxsize if x[criteria] is None else x[criteria])


