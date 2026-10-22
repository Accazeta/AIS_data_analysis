import Constants as c
import pandas as p
import numpy as np

import plotly.graph_objects as go
import plotly.offline as po
from scipy.spatial import ConvexHull
import matplotlib.pyplot as plt

# Esri World Street Map: coloured, detailed, no token, no Referer policy issues.
# (CartoDB basemaps now require an API key.)
# NOTE: Esri tile URLs use the {z}/{y}/{x} order, not {z}/{x}/{y}.
# To change style, swap the service name in the URL below:
#   Street map (coloured):  World_Street_Map
#   Satellite:              World_Imagery
#   Light grey (minimal):   Canvas/World_Light_Gray_Base
_BASEMAP_STYLE = {
    "version": 8,
    "sources": {
        "esri-tiles": {
            "type": "raster",
            "tiles": ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"],
            "tileSize": 256,
            "attribution": "Tiles © Esri"
        }
    },
    "layers": [{"id": "esri-layer", "type": "raster", "source": "esri-tiles"}]
}

# Shared legend layout: placed top-left, scrollable, capped height to avoid overlap.
# bgcolor is light grey so that white markers (e.g. Noise) remain visible.
_LEGEND = dict(
    orientation='v',
    x=0.01,
    y=0.99,
    xanchor='left',
    yanchor='top',
    bgcolor='rgba(210,210,210,0.85)',
    bordercolor='grey',
    borderwidth=1,
    itemsizing='constant',
    tracegroupgap=2,
    maxheight=250          # px — scrollable beyond this
)

# Colorbar titles with unit of measure, indexed by column name.
# Can also be passed to plotly express as labels=f._COLORBAR_TITLES
# KDE densities are computed on (LON, LAT) in degrees, so each KDE is in deg^-2 and their product in deg^-4
_COLORBAR_TITLES = {
    'Avg_Speed': 'Avg_Speed [kn]',
    'SOG': 'SOG [kn]',
    'Weight': 'Weight [log<sub>2</sub>(count)]',
    'Density': 'Density [deg<sup>-4</sup>]',
    'Log_Density_prod': 'Log_Density_prod [-]',
    'Normalized_Log_Density': 'Normalized_Log_Density [-]',
    'log_prob': 'log_prob [-]'
}

def _colorbar_title(name) -> str:
    '''returns the colorbar title (with unit of measure) of the given column name, or the name itself if unknown'''
    if not isinstance(name, str):
        return ''
    return _COLORBAR_TITLES.get(name, name)

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

def predict_position(lat, lon, v_x, v_y, delta_t_seconds):
    '''Track Predictor (Pallotta et al., Algorithm 4): dead reckoning from a known position.\n
    :param lat, lon: starting position in decimal degrees
    :param v_x, v_y: east and north components of the speed in nautical knots
    :param delta_t_seconds: prediction horizon in seconds
    Returns the predicted (lat, lon) in decimal degrees.
    The travelled distance (nautical miles) is converted to degrees: 1 NM = 1/60 degree of latitude,
    while along the longitude it is further divided by cos(lat) (meridians converge towards the poles).
    '''
    north_nm = v_y * delta_t_seconds / 3600
    east_nm = v_x * delta_t_seconds / 3600
    pred_lat = lat + north_nm / 60
    pred_lon = lon + east_nm / (60 * np.cos(np.radians(lat)))
    return pred_lat, pred_lon

def points_plotter(clustered : p.DataFrame, not_clustered : p.DataFrame, model) -> None:
    '''Function used to plot the results of dbscan and hdbscan\n
    Takes as input two dataframes: clusterd and not_clustered, both containing
    points that were successfully labelled or not, respectively.
    '''
    # each algorithm is saved to its own html file, otherwise the second plot overwrites the first one
    # (without a filename, plotly always writes to the same 'temp-plot.html')
    if 'eps' in model.get_params(): #it's DBSCAN
        my_title = 'DBSCAN. Eps: ' + str(model.get_params()['eps']) + ', min_size: ' + str(model.get_params()['min_samples'])
        filename = 'DBSCAN_waypoints.html'
    if "cluster_selection_epsilon" in model.get_params(): #it's HDBSCAN
        my_title = 'H-DBSCAN. Min Eps: ' + str(model.get_params()['cluster_selection_epsilon']) + \
            ', min_size: ' + str(model.get_params()['min_cluster_size']) + \
            ', max_size: ' + str(model.get_params()['max_cluster_size'])
        filename = 'HDBSCAN_waypoints.html'

    fig = go.Figure()

    # plot clustered points
    fig.add_trace(go.Scattermap(
        lat=clustered['LAT'],
        lon=clustered['LON'],
        mode='markers',
        marker=dict(
            size=6,
            color=clustered['Weight'],
            colorscale='portland',
            showscale=True,
            colorbar=dict(title=_colorbar_title('Weight'))
        ),
        name='Clustered'
    ))

    # add unclustered points
    fig.add_trace(go.Scattermap(
        lat=not_clustered['LAT'],
        lon=not_clustered['LON'],
        mode='markers',
        marker=dict(size=4, color='white'),
        name='Noise'
    ))

    # add domain border
    fig.add_trace(go.Scattermap(
        mode='lines',
        lon=[c.LON_MIN, c.LON_MIN, c.LON_MAX, c.LON_MAX, c.LON_MIN],
        lat=[c.LAT_MIN, c.LAT_MAX, c.LAT_MAX, c.LAT_MIN, c.LAT_MIN],
        line=dict(width=2, color='red'),
        name='Domain'
    ))

    # Add convex hull polygons
    for label in clustered['Label'].unique():
        groupLATLONDF = clustered[clustered['Label']==label][['LAT', 'LON']]
        hull = ConvexHull(groupLATLONDF)
        hull_lon = [groupLATLONDF['LON'].reset_index().iloc[vertex] for vertex in hull.vertices]
        hull_lat = [groupLATLONDF['LAT'].reset_index().iloc[vertex] for vertex in hull.vertices]
        hull_lon = [serie.tolist()[1] for serie in hull_lon]
        hull_lat = [serie.tolist()[1] for serie in hull_lat]
        fig.add_trace(go.Scattermap(
            lat=hull_lat + [hull_lat[0]],
            lon=hull_lon + [hull_lon[0]],
            mode='lines',
            line=dict(color='black', width=2),
            showlegend=False,
            name='WP_' + str(label)
        ))

    fig.update_layout(
        title=my_title,
        map=dict(
            style=_BASEMAP_STYLE,
            center=dict(lat=clustered['LAT'].mean(), lon=clustered['LON'].mean()),
            zoom=7
        ),
        margin={'r':0, 't':40, 'l':0, 'b':0},
        legend=_LEGEND
    )
    po.plot(fig, filename='../../plot/' + filename, auto_open=True)

def plot_routes(inputDF : p.DataFrame, clusteredPointsDF : p.DataFrame, mode, filename : str = None) -> None:
    '''
    :param str filename: name of the html file saved in plot/. Default: derived from the plotting mode
    '''
    if inputDF.empty:
        print("No points to be plotted!")
        return

    # each mode is saved to its own html file (without a filename, plotly always writes to 'temp-plot.html')
    match mode:
        case "SingleVessel":
            output_title = "MMSI: " + str(inputDF.at[inputDF.index[0], 'MMSI'])
            default_filename = 'single_vessel_routes.html'
        case "SingleRoute":
            default_filename = 'single_route.html'
            if type(inputDF.at[inputDF.index[0], 'Route']) == p.Series:
                output_title = "Route: " + str(inputDF.at[inputDF.index[0], 'Route'].iloc[0])
            else:
                output_title = "Route: " + str(inputDF.at[inputDF.index[0], 'Route'])
        case _:
            print("Invalid plotting mode")
            return

    fig = go.Figure()

    # plot route points
    fig.add_trace(go.Scattermap(
        lat=inputDF['LAT'],
        lon=inputDF['LON'],
        mode='markers',
        marker=dict(
            size=6,
            color=inputDF['Avg_Speed'],
            colorscale='portland',
            showscale=True,
            colorbar=dict(title=_colorbar_title('Avg_Speed'))
        ),
        customdata=inputDF[['MMSI', 'BaseDateTime', 'Avg_Speed', 'Route', 'EstimatedStatus']].to_numpy(),
        hovertemplate=(
            'MMSI: %{customdata[0]}<br>' +
            'Time: %{customdata[1]}<br>' +
            'Avg_Speed: %{customdata[2]:.2f} kn<br>' +
            'Route: %{customdata[3]}<br>' +
            'Status: %{customdata[4]}<extra></extra>'
        ),
        name='Route points'
    ))

    # add domain border
    fig.add_trace(go.Scattermap(
        mode='lines',
        lon=[c.LON_MIN, c.LON_MIN, c.LON_MAX, c.LON_MAX, c.LON_MIN],
        lat=[c.LAT_MIN, c.LAT_MAX, c.LAT_MAX, c.LAT_MIN, c.LAT_MIN],
        line=dict(width=2, color='red'),
        name='Domain'
    ))

    # Add convex hull polygons
    for label in clusteredPointsDF['Label'].unique():
        groupLATLONDF = clusteredPointsDF[clusteredPointsDF['Label']==label][['LAT', 'LON']]
        hull = ConvexHull(groupLATLONDF)
        hull_lon = [groupLATLONDF['LON'].reset_index().iloc[vertex] for vertex in hull.vertices]
        hull_lat = [groupLATLONDF['LAT'].reset_index().iloc[vertex] for vertex in hull.vertices]
        hull_lon = [serie.tolist()[1] for serie in hull_lon]
        hull_lat = [serie.tolist()[1] for serie in hull_lat]
        fig.add_trace(go.Scattermap(
            lat=hull_lat + [hull_lat[0]],
            lon=hull_lon + [hull_lon[0]],
            mode='lines',
            line=dict(color='black', width=2),
            showlegend=False,
            name='WP_' + str(label)
        ))

    fig.update_layout(
        title=output_title,
        map=dict(
            style=_BASEMAP_STYLE,
            center=dict(lat=inputDF['LAT'].mean(), lon=inputDF['LON'].mean()),
            zoom=12
        ),
        margin={'r':0, 't':40, 'l':0, 'b':0},
        legend=_LEGEND
    )
    po.plot(fig, filename='../../plot/' + (filename or default_filename), auto_open=True)

def route_plot(inputDF : p.DataFrame,
               color_criteria : str,
               title : str = 'Route',
               hover_data : list = ['BaseDateTime', 'Avg_Speed', 'Route', 'EstimatedStatus'],
               filename : str = 'route_plot.html',
               colorbar_title : str = None
               ):
    '''
    plots points and colors them according to the parsed criteria
    :param p.Dataframe inputDF: Dataframe with all the info about points. Required columns: 'BaseDateTime','LON','LAT','Avg_Speed','EstimatedStatus','Route'
    :param str|Dataframe color_criteria: The name of the column used for coloring the points or the dataframe column itself
    :param str title: The title of the resulting plot, shown at the top
    :param list hover_data: list of strings specifying the names of the columns to show when the mouse overs on a point
    :param str colorbar_title: title of the colorbar. Default: derived from the column name (with unit of measure, if known)
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

    fig = go.Figure()

    fig.add_trace(go.Scattermap(
        lat=inputDF['LAT'],
        lon=inputDF['LON'],
        mode='markers',
        marker=dict(
            size=6,
            color=final_criteria,
            colorscale='portland',
            showscale=True,
            colorbar=dict(title=colorbar_title if colorbar_title is not None
                          else _colorbar_title(color_criteria if isinstance(color_criteria, str)
                                               else getattr(color_criteria, 'name', None)))
        ),
        customdata=inputDF[hover_data].to_numpy(),
        hovertemplate='<br>'.join(
            [f'{col}: %{{customdata[{i}]}}' for i, col in enumerate(hover_data)]
        ) + '<extra></extra>',
        name='Route points'
    ))

    # add domain border
    fig.add_trace(go.Scattermap(
        mode='lines',
        lon=[c.LON_MIN, c.LON_MIN, c.LON_MAX, c.LON_MAX, c.LON_MIN],
        lat=[c.LAT_MIN, c.LAT_MAX, c.LAT_MAX, c.LAT_MIN, c.LAT_MIN],
        line=dict(width=2, color='red'),
        name='Domain'
    ))

    fig.update_layout(
        title=title,
        map=dict(
            style=_BASEMAP_STYLE,
            center=dict(lat=inputDF['LAT'].mean(), lon=inputDF['LON'].mean()),
            zoom=12
        ),
        margin={'r':0, 't':40, 'l':0, 'b':0},
        legend=_LEGEND
    )
    po.plot(fig, filename='../../plot/' + filename, auto_open=True)

def route_arrows_plot(inputDF : p.DataFrame,
                      color_criteria : str = 'Avg_Speed',
                      scale_factor : float = 0.001,
                      title : str = 'Plot with arrows',
                      max_points : int = 5000
                      ) -> go.Figure:
    """
    Plotly plot that plots vessels positions, their instantaneous speed and direction.
    Uses the modern Scattermap API (no Mapbox token required) with fully vectorized
    numpy operations to handle large datasets efficiently.

    Parameters:
    :param Dataframe inputDF: the pandas dataframe containing all the points that are going to be plotted. Required columns: "MMSI, LAT, LON, COG, SOG, Avg_Speed"
    :param str color_criteria: the criteria used to assign a color to the different points. Must be a valid dataframe column name. Default: 'Avg_Speed'
    :param float scale_factor: the multiplying constant to adjust arrows length. Default: 0.001
    :param int max_points: maximum number of points to render. If the dataframe exceeds this, it is uniformly sampled. Default: 5000
    Returns:
    Plotly Graph Objects Figure
    """
    if color_criteria not in inputDF.columns:
        raise KeyError(f"Column {color_criteria} not found in the provided Dataframe")

    inputDF = inputDF.copy()

    # Uniform sampling if dataset is too large for the browser to render
    if len(inputDF) > max_points:
        print(f"[route_arrows_plot] Dataset has {len(inputDF)} points, sampling down to {max_points} for rendering.")
        inputDF = inputDF.sample(n=max_points, random_state=42).sort_index()

    # Vectorized computation of arrow endpoints
    cog_rad = np.radians(inputDF["COG"].to_numpy())
    magnitude = scale_factor * inputDF[color_criteria].to_numpy()
    lat0 = inputDF["LAT"].to_numpy().round(5)
    lon0 = inputDF["LON"].to_numpy().round(5)
    lat1 = (lat0 + magnitude * np.cos(cog_rad)).round(5)
    lon1 = (lon0 + magnitude * np.sin(cog_rad)).round(5)

    # Build interleaved [start, end, NaN, ...] arrays with numpy (much faster than extend in a loop)
    nan_col = np.full(len(inputDF), np.nan)
    arrow_lat = np.column_stack([lat0, lat1, nan_col]).ravel()
    arrow_lon = np.column_stack([lon0, lon1, nan_col]).ravel()

    fig = go.Figure()

    # Add arrows first so they don't cover the scatter points on hover
    fig.add_trace(go.Scattermap(
        lat=arrow_lat,
        lon=arrow_lon,
        mode='lines',
        line=dict(width=1, color='grey'),
        hoverinfo='skip',
        showlegend=False,
        name='Arrows'
    ))

    # Add scatter points for vessel positions
    fig.add_trace(go.Scattermap(
        lat=inputDF["LAT"],
        lon=inputDF["LON"],
        mode="markers",
        marker=dict(size=8, color=inputDF[color_criteria], colorscale='portland', showscale=True,
                    colorbar=dict(title=_colorbar_title(color_criteria))),
        text=inputDF["MMSI"],
        hovertemplate=(
            'MMSI: %{text}<br>' +
            'COG: %{customdata[0]:.1f} deg<br>' +
            'SOG: %{customdata[1]:.1f} kn<br>' +
            'Avg_Speed: %{customdata[2]:.1f} kn<extra></extra>'
        ),
        customdata=inputDF[['COG', 'SOG', 'Avg_Speed']].to_numpy(),
        name="Vessels"
    ))

    fig.update_layout(
        title=title,
        map=dict(
            style=_BASEMAP_STYLE,
            center=dict(lat=inputDF["LAT"].mean(), lon=inputDF["LON"].mean()),
            zoom=10
        ),
        margin={'r':40, 't':40, 'l':40, 'b':40},
        showlegend=True,
        legend=_LEGEND
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
    ax1 = fig.add_subplot(111)
    im1 = ax1.pcolormesh(xx, yy, zz, shading='auto', cmap='turbo')
    ax1.set_title('KDE')
    ax1.set_xlabel('Longitude')
    ax1.set_ylabel('Latitude')
    ax1.set_aspect('equal')
    plt.colorbar(im1, ax=ax1, label=r'Density [deg$^{-2}$]')
    plt.tight_layout()
    return fig
