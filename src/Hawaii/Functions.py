import Constants as c
import pandas as p
import numpy as np

import plotly.express as px
import plotly.graph_objects as go
import plotly.offline as po
from scipy.spatial import ConvexHull
import matplotlib.pyplot as plt


if __name__ == "__main__":
    None

def great_circle_distance_vectorized(lat_left, lon_left, lat_right, lon_right):
    '''Vectorized function used to calculate the Great-Circle distance between two GPS coordinates'''    
    lon_left, lat_left, lon_right, lat_right = map(np.radians, [lon_left, lat_left, lon_right, lat_right])
    deg_lon = lon_right - lon_left
    deg_lat = lat_right - lat_left
    a = np.sin(deg_lat/2.0)**2 + np.cos(lat_left) * np.cos(lat_right) * np.sin(deg_lon/2.0)**2
    cx = 2 * np.arcsin(np.sqrt(a))
    meters = c.EARTH_RADIUS_M * cx
    return meters

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
                                    hover_data=inputDF[['MMSI', 'BaseDateTime', 'Avg_Speed', 'Route', 'EstimatedStatus']]
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

def route_plot(inputDF : p.DataFrame, 
               color_criteria : str, 
               title : str = 'Route',
               hover_data : list = ['BaseDateTime', 'Avg_Speed', 'Route', 'EstimatedStatus'],
               filename : str = 'route_plot.html'
               ):
    '''
    plots points and colors them according to the parsed criteria
    :param p.Dataframe inputDF: Dataframe with all the info about points. Required columns: 'BaseDateTime','LON','LAT','Avg_Speed','EstimatedStatus','Route'
    :param str|Dataframe color_criteria: The name of the column used for coloring the points or the dataframe column itself
    :param str title: The title of the resulting plot, shown at the top
    :param list hover_data: list of strings specifying the names of the columns to show when the mouse overs on a point
    '''
    
    if inputDF.empty:
        print("No points to be plotted!")
        return
    
    if type(color_criteria) == p.Series or type(color_criteria) == np.ndarray:
        final_criteria = color_criteria
    else:
        if not color_criteria:
            print("Empty color criteria")
            return
        if type(color_criteria) == str:
            final_criteria = inputDF[color_criteria]
        else:
            print('Wrong color_criteria type')
            return

    
    # plot route points
    fig = px.scatter_mapbox(data_frame = inputDF,
                                lon = inputDF['LON'],
                                lat= inputDF['LAT'],
                                zoom = 12,
                                color = final_criteria,
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
    po.plot(fig, filename='../../plot/' + filename, auto_open=True)

def route_arrows_plot(inputDF : p.DataFrame,
                      color_criteria : str = 'Avg_Speed',
                      scale_factor : float = 0.001,
                      title : str = 'Plot with arrows'
                      ) -> go.Figure:
    """
    Plotly plot that plots vessels positions, their instantaneous speed and direction 
    
    Parameters:
    :param Dataframe inputDF: the pandas dataframe containing all the points that are going to be plotted. Required columns: "MMSI, LAT, LON, COG, SOG, Avg_Speed, "
    :param str color_criteria: the criteria used to assign a color to the different points. Must be a valid dataframe column name. Default set to 'MMSI' 
    :param float scale_factor: the multiplying constant to adjust arrows length
    Returns:
    Plotly Graph Objects plot
    """
    if color_criteria not in inputDF.columns:
        raise KeyError(f"Column {color_criteria} not found in the provided Dataframe")
    
    inputDF = inputDF.copy() # This is necessary so that the code below doesn't raise a warning
    # Compute arrow endpoints from SOG and COG
    inputDF.loc[:,"delta_lon"] = scale_factor * inputDF.loc[:,color_criteria] * np.sin(np.radians(inputDF.loc[:,"COG"]))
    inputDF.loc[:,"delta_lat"] = scale_factor * inputDF.loc[:,color_criteria] * np.cos(np.radians(inputDF.loc[:,"COG"]))
    
    fig = go.Figure()

    # add arrow traces before points so that they do not cover the points when overing with the mouse
    # Add arrows for vessel movement
    arrow_lat = []
    arrow_lon = []
    for _, row in inputDF.iterrows():
        arrow_lat.extend([round(row['LAT'], 5), round(row['LAT'] + row['delta_lat'], 5), None])
        arrow_lon.extend([round(row['LON'], 5), round(row['LON'] + row['delta_lon'], 5), None])
    
    fig.add_trace(
        go.Scattermapbox(
            lat=arrow_lat,
            lon=arrow_lon,
            mode='lines',
            line=dict(width=1, color='grey')
        )
    )

    # Add scatter points for the vessel positions
    fig.add_trace(
        go.Scattermapbox(
            lat=inputDF["LAT"],
            lon=inputDF["LON"],
            mode="markers",
            marker=dict(size=8, color=inputDF[color_criteria], colorscale='portland', showscale=True),
            text=inputDF["MMSI"],
            hovertemplate=(
                'MMSI: %{text}<br>' +
                'COG: %{customdata[0]:.1f} deg<br>' +
                'SOG: %{customdata[1]:.1f} kn<br>' +
                'Avg_Speed: %{customdata[2]:.1f} kn<extra></extra>'
            ),
            customdata=inputDF[['COG', 'SOG', 'Avg_Speed']].to_numpy(),
            name="Arrows plot"
        )
    )

    fig.update_layout(
        title=title,
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=inputDF["LAT"].mean(), lon=inputDF["LON"].mean()),
            zoom=10
        ),
        margin={'r':40, 't':40, 'l':40, 'b':40},
        showlegend=True
    )
    return fig

def plot_kde(xx : np.ndarray, yy : np.ndarray, zz : np.ndarray, fig_width : float, fig_height : float):
    '''
    plots the result of the KDE
    :param np.ndarray xx: the array of x coordinates resulting from numpy.meshgrid()
    :param np.ndarray yy: the array of y coordinates resulting from numpy.meshgrid()
    :param np.ndarray zz: the density values resulting from the KDE
    :param float fig_width: the width of the figure
    :param float fig_heigth: the height of the figure
    '''
    
    fig = plt.figure(figsize=(fig_width, fig_height))
    ax1 = fig.add_subplot(111) #111 -> 1 row, 1 column, index of the current subplot
    im1 = ax1.pcolormesh(xx, yy, zz, shading='auto', cmap='turbo') # pseudocolor plot with non-regular grid (makes the plt rectangular instead of squared)
    ax1.set_title('KDE')
    ax1.set_xlabel('Longitude')
    ax1.set_ylabel('Latitude')
    ax1.set_aspect('equal')  # Sets the correct aspect ratio
    plt.colorbar(im1, ax=ax1, label='Density')
    plt.tight_layout() # automatically adjust subplot size so that it fits its area

    return fig
