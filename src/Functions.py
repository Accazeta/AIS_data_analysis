import Constants as c
import pandas as p

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
                            color = clustered['Label'],
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


def route_clusters_plot(inputDF : p.DataFrame) -> None:
    fig = go.Figure(go.Scattermapbox(
                                    lat=inputDF['LAT'],
                                    lon=inputDF['LON'],
                                    mode='markers',
                                    marker=go.scattermapbox.Marker(
                                        size=12,
                                        color=inputDF['cluster'],
                                        colorscale='portland',
                                        showscale=True
                                    ),
                                    text='test',
                                    hoverinfo='text'
    ))

    fig.update_layout(
        mapbox=dict(
            style='open-street-map',
            zoom=12,
            center=dict(lat=inputDF['LAT'].mean(), lon=inputDF['LON'].mean())
        ),
        title='Clustering of route <insert route name>',
        margin={'r':0, 't':40, 'l':0, 'b':0}
    )

    po.plot(fig)