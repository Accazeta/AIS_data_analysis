import Constants as c
import pandas as p
import numpy as np

import plotly.express as px
import plotly.graph_objects as go
import plotly.offline as po
from scipy.spatial import ConvexHull


if __name__ == "__main__":
    None

def points_plotter(clustered : p.DataFrame, not_clustered : p.DataFrame, model) -> None:
    '''Function used to plot the results of dbscan and hdbscan\n
    Takes as input two dataframes: clusterd and not_clustered, both containing
    points that were successfully labelled or not, respectively.
    '''
    
    
    if 'eps' in model.get_params(): #it's DBSCAN
        my_title = 'DBSCAN. Eps: ' + str(model.get_params()['eps']) + ', min_size: ' + str(model.get_params()['min_samples'])
    if "cluster_selection_epsilon" in model.get_params(): #it's HDBSCAN
        my_title = 'H-DBSCAN. Min Eps: ' + str(model.get_params()['cluster_selection_epsilon']) + \
            ', min_size: ' + str(model.get_params()['min_cluster_size']) + \
            ', max_size: ' + str(model.get_params()['max_cluster_size'])
    
    # plot clustered points on a map
    fig = px.scatter_mapbox(data_frame = clustered,
                            lon = clustered['LON'],
                            lat= clustered['LAT'],
                            zoom = 7,
                            color = clustered['Weight'],
                            title = my_title,
                            color_continuous_scale='portland'  #portland
                            )

    # add unclustered points
    fig.add_scattermapbox(
                          lat= not_clustered['LAT'],
                          lon= not_clustered['LON'],
                          marker={'color':'white'},
                          uid=1
                          )

    # add domain border
    fig.add_trace(go.Scattermapbox(
                                    mode = 'lines',
                                    lon = [c.LON_MIN, c.LON_MIN, c.LON_MAX, c.LON_MAX, c.LON_MIN],
                                    lat = [c.LAT_MIN, c.LAT_MAX, c.LAT_MAX, c.LAT_MIN, c.LAT_MIN],
                                    marker = {'size':10,
                                              'color': 'red'},
                                    uid=2,
                                    below=0
                                    ))
    
    # Add polygons on map
    for label in clustered['Label'].unique():
        groupLATLONDF = clustered[clustered['Label']==label][['LAT', 'LON']]
        hull = ConvexHull(groupLATLONDF)
        hull_lon = [groupLATLONDF['LON'].reset_index().iloc[vertex] for vertex in hull.vertices]
        hull_lat = [groupLATLONDF['LAT'].reset_index().iloc[vertex] for vertex in hull.vertices]
    
        hull_lon = [serie.tolist()[1] for serie in hull_lon]
        hull_lat = [serie.tolist()[1] for serie in hull_lat]
    
        fig.add_trace(go.Scattermapbox(
            lat=hull_lat + [hull_lat[0]],
            lon=hull_lon + [hull_lon[0]],
            mode='lines',
            line=dict(color='black', width=2),
            below=0,
            showlegend=False,
            name='WP_' + str(label)
            #fill='toself',
            #fillcolor='rgba(255,0,0,0.2)'
        ))

    fig.update_layout(mapbox_style = 'open-street-map',
                      margin={'r':0, 't':40, 'l':0, 'b':0},
                      )
    po.plot(fig)


def plot_routes(inputDF : p.DataFrame, clusteredPointsDF : p.DataFrame, mode) -> None:
    if inputDF.empty:
        print("No points to be plotted!")
    
    else:
        match mode:
            case "SingleVessel":
                output_title = "MMSI: " + str(inputDF.at[inputDF.index[0], 'MMSI'])
            case "SingleRoute":
                if type(inputDF.at[inputDF.index[0], 'Route']) == p.Series:
                    output_title = "Route: " + str(inputDF.at[inputDF.index[0], 'Route'].iloc[0])
                else:
                    output_title = "Route: " + str(inputDF.at[inputDF.index[0], 'Route'])
            case _: 
                print("Invalid plotting mode")

        # plot route points
        fig = px.scatter_mapbox(data_frame = inputDF,
                                    lon = inputDF['LON'],
                                    lat= inputDF['LAT'],
                                    zoom = 12,
                                    color = inputDF['Avg_Speed'],
                                    title = output_title,
                                    color_continuous_scale='portland',  #portland
                                    hover_data=inputDF[['BaseDateTime', 'Avg_Speed', 'Route', 'EstimatedStatus']]
                                    )

        # add domain border
        fig.add_trace(go.Scattermapbox(
                                        mode = 'lines',
                                        lon = [c.LON_MIN, c.LON_MIN, c.LON_MAX, c.LON_MAX, c.LON_MIN],
                                        lat = [c.LAT_MIN, c.LAT_MAX, c.LAT_MAX, c.LAT_MIN, c.LAT_MIN],
                                        marker = {'size':10,
                                                  'color': 'red'},
                                        uid=2,
                                        below=0
                                        ))
    
        # Add polygons on map
        for label in clusteredPointsDF['Label'].unique():
            groupLATLONDF = clusteredPointsDF[clusteredPointsDF['Label']==label][['LAT', 'LON']]
            hull = ConvexHull(groupLATLONDF)
            hull_lon = [groupLATLONDF['LON'].reset_index().iloc[vertex] for vertex in hull.vertices]
            hull_lat = [groupLATLONDF['LAT'].reset_index().iloc[vertex] for vertex in hull.vertices]

            hull_lon = [serie.tolist()[1] for serie in hull_lon]
            hull_lat = [serie.tolist()[1] for serie in hull_lat]

            fig.add_trace(go.Scattermapbox(
                lat=hull_lat + [hull_lat[0]],
                lon=hull_lon + [hull_lon[0]],
                mode='lines',
                line=dict(color='black', width=2),
                below=0,
                showlegend=False,
                name='WP_' + str(label)
                #fill='toself',
                #fillcolor='rgba(255,0,0,0.2)'
            ))

        fig.update_layout(mapbox_style = 'open-street-map',
                          margin={'r':0, 't':40, 'l':0, 'b':0},
                          )
        po.plot(fig)

def route_plot(inputDF : p.DataFrame(), 
               color_criteria : str, 
               title : str = 'Route',
               hover_data : list = ['BaseDateTime', 'Avg_Speed', 'Route', 'EstimatedStatus']
               ):
    '''
    plots points and colors them according to the parsed criteria
    :param str color_criteria: The name of the column used for coloring the points
    :param str title: The title of the resulting plot, shown at the top
    :param list hover_data: list of strings specifying the names of the columns to show when the mouse overs on a point
    '''
    
    if inputDF.empty:
        print("No points to be plotted!")
        return
    
    if not color_criteria:
        print("Empty color criteria")
        return
    
    # plot route points
    fig = px.scatter_mapbox(data_frame = inputDF,
                                lon = inputDF['LON'],
                                lat= inputDF['LAT'],
                                zoom = 12,
                                color = inputDF[color_criteria],
                                title = title,
                                color_continuous_scale='portland',  #portland
                                hover_data=inputDF[hover_data]
                                )
    
    # add domain border
    fig.add_trace(go.Scattermapbox(
                                    mode = 'lines',
                                    lon = [c.LON_MIN, c.LON_MIN, c.LON_MAX, c.LON_MAX, c.LON_MIN],
                                    lat = [c.LAT_MIN, c.LAT_MAX, c.LAT_MAX, c.LAT_MIN, c.LAT_MIN],
                                    marker = {'size':10,
                                              'color': 'red'},
                                    uid=2,
                                    below=0
                                    ))
    
    fig.update_layout(mapbox_style = 'open-street-map',
                       margin={'r':0, 't':40, 'l':0, 'b':0},
                       )
    po.plot(fig)



# Vectorized function to compute the endpoint of the arrow based on lat, lon, angle (cog), and speed (modulus)
def compute_endpoint(lat, lon, cog, sog): #haversine is back!
    # Convert cog angle to radians for trigonometry
    cog_rad = np.deg2rad(cog)
    
    # this is used to make the arrows look more proportional (it's necessary because the earth is round while the map I'm plotting on is flat)
    scaling_factor = 0.005

    delta = sog * scaling_factor /c.EARTH_RADIUS_KM
    # calculate latitude/logitude change
    delta_lat = delta * np.cos(cog_rad)
    delta_lon = delta * np.sin(cog_rad) / np.cos(np.deg2rad(lat))

    end_lat = lat + np.rad2deg(delta_lat)
    end_lon = lon + np.rad2deg(delta_lon)
    return end_lat, end_lon

def route_arrows_plot(inputDF : p.DataFrame) -> None:
    text_description = inputDF[['MMSI', 'VesselName', 'COG', 'Avg_Speed', 'Heading', 'IsClassA', 'SOG']].values.tolist()
    text_description = [f"MMSI: {x[0]}\nName: {x[1]}\nCOG: {x[2]}\nAvg_Speed: {x[3]}\nSOG: {x[6]}\nHeading: {x[4]}\nClassA: {x[5]}" for x in text_description]
    
    # Compute all start and end points at once
    # applying 'zip' here is like doing pd.concat([whatever], axis=1). 'endpoints' is a list of (lat,lon) tuples
    endpoints = [compute_endpoint(lat, lon, cog, speed) for lat, lon, cog, speed in zip(inputDF['LAT'], inputDF['LON'], inputDF['COG'], inputDF['Avg_Speed'])]
    # the '*' operator inside the zip function unzips the elements of the list into two separate lists
    lat_end, lon_end = zip(*endpoints, strict=True)

    # Vectorized approach to create interleaved lat and lon lists (start, end, None for line break)
    lat_all = np.array([[start, end, None] for start, end in zip(inputDF['LAT'], lat_end)]).flatten()
    lon_all = np.array([[start, end, None] for start, end in zip(inputDF['LON'], lon_end)]).flatten()
    marker_sizes = np.array([[10, 0, 0] for _ in inputDF['LAT']]).flatten().tolist()

    fig = go.Figure(go.Scattermapbox(
                                    lat=lat_all,
                                    lon=lon_all,
                                    mode='markers+lines',
                                    marker=go.scattermapbox.Marker(
                                        size=marker_sizes,
                                        color=inputDF['cluster'],
                                        colorscale='portland',
                                        showscale=True
                                    ),
                                    line=dict(width=2, color='black'),
                                    hovertext=text_description,
                                    hoverinfo='text'
    ))

    fig.update_layout(
        mapbox=dict(
            style='open-street-map',
            zoom=10,
            center=dict(lat=inputDF['LAT'].mean(), lon=inputDF['LON'].mean())
        ),
        title=f"Clustering of route {inputDF['Route'].iloc[1]}",
        margin={'r':0, 't':40, 'l':0, 'b':0}
    )

    po.plot(fig)