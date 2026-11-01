import Constants as c
import pandas as p
import numpy as np

import plotly.graph_objects as go
import plotly.offline as po
import plotly.io as pio
from plotly.colors import sample_colorscale
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
    'Weight': 'Peso',
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

# Scale bar drawn over the map (bottom right), recomputed at every zoom/pan. A graphical bar is used instead of a
# ratio ("1 cm = X km") because the screenshots are resized in the thesis: the bar is resized with them and stays correct.
# The length is measured horizontally at the centre of the view (in Mercator the scale changes slightly with latitude).
# plotly keeps the MapLibre map of the subplot in gd._fullLayout.map._subplot.map
_SCALE_BAR_JS = """
(function () {
    var gd = document.getElementById('{plot_id}');
    function haversineKm(a, b) {
        var r = Math.PI / 180, dLat = (b.lat - a.lat) * r, dLon = (b.lng - a.lng) * r;
        var h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dLon / 2) ** 2;
        return 2 * 6371.0088 * Math.asin(Math.sqrt(h));
    }
    function attach() {
        var sub = gd._fullLayout && gd._fullLayout.map && gd._fullLayout.map._subplot;
        if (!sub || !sub.map) { setTimeout(attach, 200); return; }
        var map = sub.map, container = map.getContainer();
        var box = document.createElement('div');
        box.style.cssText = 'position:absolute; right:10px; bottom:10px; z-index:10; padding:2px 6px 4px;' +
            'background:rgba(255,255,255,0.85); border:1px solid grey; font:13px sans-serif; color:black; pointer-events:none;';
        var label = document.createElement('div');
        label.style.cssText = 'text-align:center; margin-bottom:2px;';
        var bar = document.createElement('div');
        bar.style.cssText = 'height:7px; border:2px solid black; border-top:none; box-sizing:border-box;';
        box.appendChild(label); box.appendChild(bar);
        container.appendChild(box);
        function update() {
            var x = container.clientWidth / 2, y = container.clientHeight / 2;
            var kmPerPx = haversineKm(map.unproject([x - 50, y]), map.unproject([x + 50, y])) / 100;
            var maxKm = kmPerPx * 150;  // the bar is at most 150 px long
            var pow = Math.pow(10, Math.floor(Math.log10(maxKm)));
            var km = [5, 2, 1].map(function (m) { return m * pow; }).find(function (v) { return v <= maxKm; });
            bar.style.width = (km / kmPerPx) + 'px';
            label.textContent = km >= 1 ? km + ' km' : Math.round(km * 1000) + ' m';
        }
        map.on('move', update);
        map.on('resize', update);
        update();
    }
    attach();
})();
"""

def _save_map(fig : go.Figure, filename : str):
    '''saves a map plot to plot/filename (and opens it), with the scale bar'''
    pio.write_html(fig, file='../../plot/' + filename, include_plotlyjs=True, post_script=_SCALE_BAR_JS, auto_open=True)


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
        name='In un cluster'
    ))

    # add unclustered points
    fig.add_trace(go.Scattermap(
        lat=not_clustered['LAT'],
        lon=not_clustered['LON'],
        mode='markers',
        marker=dict(size=4, color='white'),
        name='Rumore'
    ))

    # add domain border
    fig.add_trace(go.Scattermap(
        mode='lines',
        lon=[c.LON_MIN, c.LON_MIN, c.LON_MAX, c.LON_MAX, c.LON_MIN],
        lat=[c.LAT_MIN, c.LAT_MAX, c.LAT_MAX, c.LAT_MIN, c.LAT_MIN],
        line=dict(width=2, color='red'),
        name='Dominio di analisi'
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

    # no title: the plot is used in the thesis, where the caption describes it (parameters included)
    print(f'[points_plotter] {my_title}')
    fig.update_layout(
        map=dict(
            style=_BASEMAP_STYLE,
            center=dict(lat=clustered['LAT'].mean(), lon=clustered['LON'].mean()),
            zoom=7
        ),
        margin={'r':0, 't':0, 'l':0, 'b':0},
        legend=_LEGEND
    )
    _save_map(fig, filename)

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
                output_title = "Rotta: " + str(inputDF.at[inputDF.index[0], 'Route'].iloc[0])
            else:
                output_title = "Rotta: " + str(inputDF.at[inputDF.index[0], 'Route'])
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
        name='Punti della rotta'
    ))

    # add domain border
    fig.add_trace(go.Scattermap(
        mode='lines',
        lon=[c.LON_MIN, c.LON_MIN, c.LON_MAX, c.LON_MAX, c.LON_MIN],
        lat=[c.LAT_MIN, c.LAT_MAX, c.LAT_MAX, c.LAT_MIN, c.LAT_MIN],
        line=dict(width=2, color='red'),
        name='Dominio di analisi'
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
               title : str = 'Rotta',
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
        name='Punti della rotta'
    ))

    # add domain border
    fig.add_trace(go.Scattermap(
        mode='lines',
        lon=[c.LON_MIN, c.LON_MIN, c.LON_MAX, c.LON_MAX, c.LON_MIN],
        lat=[c.LAT_MIN, c.LAT_MAX, c.LAT_MAX, c.LAT_MIN, c.LAT_MIN],
        line=dict(width=2, color='red'),
        name='Dominio di analisi'
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
                      title : str = 'Grafico con frecce',
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
        name='Frecce'
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
        name="Navi"
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

# Same basemap, plus a glyphs source: MapLibre cannot render text labels (mode='text') without it.
# Plotly's built-in styles use this same font server.
_BASEMAP_STYLE_WITH_TEXT = dict(_BASEMAP_STYLE, glyphs="https://fonts.openmaptiles.org/{fontstack}/{range}.pbf")

def route_trips(inputDF : p.DataFrame) -> p.DataFrame:
    '''
    Splits the points labelled with a route ('A - B') into trips: a trip is a run of consecutive points
    of the same vessel with the same 'Route' value (same logic used to count the routes in TREAD).
    :param Dataframe inputDF: points ordered by vessel and time. Required columns: "MMSI, LAT, LON, IsInWP, Route"
    Returns a Dataframe with one row per trip and columns:
    MMSI, Route, Origin, Destination, NumPoints, FirstIndex, LastIndex (positional indexes in inputDF),
    LeavesWP (only meaningful for self-loops 'A - A': True if at least one point lies outside waypoint A)
    '''
    df = inputDF[['MMSI', 'Route', 'IsInWP']].reset_index(drop=True)
    # a new run starts every time the route or the vessel changes
    run_id = ((df['Route'] != df['Route'].shift()) | (df['MMSI'] != df['MMSI'].shift())).cumsum()
    df['run'] = run_id.to_numpy()
    df['pos'] = np.arange(len(df))
    df = df[df['Route'].astype(str).str.contains(' - ', regex=False)]
    origin_dest = df['Route'].astype(str).str.split(' - ', expand=True)
    df['Origin'], df['Destination'] = origin_dest[0], origin_dest[1]
    # a point is outside the origin WP if it is in no WP (None) or in a different one
    df['OutsideOrigin'] = df['IsInWP'].astype(str) != df['Origin']

    trips = df.groupby('run').agg(MMSI=('MMSI', 'first'),
                                  Route=('Route', 'first'),
                                  Origin=('Origin', 'first'),
                                  Destination=('Destination', 'first'),
                                  NumPoints=('pos', 'size'),
                                  FirstIndex=('pos', 'min'),
                                  LastIndex=('pos', 'max'),
                                  LeavesWP=('OutsideOrigin', 'any'))
    return trips.reset_index(drop=True)

def _waypoint_centroids(waypointsDF : p.DataFrame) -> dict:
    '''returns {WP name: (lon, lat)} using the centroid of each waypoint polygon'''
    valid = waypointsDF.dropna(subset=['PolygonObj'])
    return {name: (poly.centroid.x, poly.centroid.y) for name, poly in valid[['Name', 'PolygonObj']].values}

def _domain_trace() -> go.Scattermap:
    '''red rectangle of the study area (same as the clustering plots)'''
    return go.Scattermap(
        mode='lines',
        lon=[c.LON_MIN, c.LON_MIN, c.LON_MAX, c.LON_MAX, c.LON_MIN],
        lat=[c.LAT_MIN, c.LAT_MAX, c.LAT_MAX, c.LAT_MIN, c.LAT_MIN],
        line=dict(width=2, color='red'),
        hoverinfo='skip',
        name='Dominio di analisi'
    )

def _resample_path(lon : np.ndarray, lat : np.ndarray, n_points : int) -> np.ndarray:
    '''resamples a trajectory to n_points equally spaced along its length (local equirectangular distance). Returns an (n_points, 2) array of (lon, lat)'''
    k = np.cos(np.radians(lat.mean()))
    step = np.hypot(np.diff(lon) * k, np.diff(lat))
    dist = np.concatenate([[0], np.cumsum(step)])
    if dist[-1] == 0:
        return np.column_stack([np.full(n_points, lon[0]), np.full(n_points, lat[0])])
    target = np.linspace(0, dist[-1], n_points)
    return np.column_stack([np.interp(target, dist, lon), np.interp(target, dist, lat)])

def _medoid_path(paths : np.ndarray, max_paths : int = 300) -> np.ndarray:
    '''
    returns the medoid of a set of resampled paths (shape: n_paths x n_points x 2), i.e. the actual path with the
    smallest mean point-to-point distance from all the others. Unlike an average, it is always a real trajectory
    (it never cuts across an island when trips go around it on different sides)
    '''
    if len(paths) > max_paths:
        paths = paths[np.random.default_rng(42).choice(len(paths), max_paths, replace=False)]
    diff = paths[:, None, :, :] - paths[None, :, :, :]
    mean_dist = np.hypot(diff[..., 0], diff[..., 1]).mean(axis=2)  # n_paths x n_paths
    return paths[mean_dist.sum(axis=1).argmin()]

def _waypoint_shapes_trace(waypointsDF : p.DataFrame, names : list) -> go.Scattermap:
    '''shapes (convex hulls) of the given waypoints, as a single filled trace'''
    polygons = dict(waypointsDF.dropna(subset=['PolygonObj'])[['Name', 'PolygonObj']].values)
    hull_lon, hull_lat = [], []
    for wp in names:
        x, y = polygons[wp].exterior.xy
        hull_lon.extend(list(x) + [None]); hull_lat.extend(list(y) + [None])
    return go.Scattermap(
        lon=hull_lon, lat=hull_lat, mode='lines', fill='toself',
        fillcolor='rgba(0,0,0,0.15)', line=dict(width=1.5, color='black'),
        hoverinfo='skip', name='Waypoint'
    )

def _waypoint_names_trace(waypointsDF : p.DataFrame, names : list, labels : list = None) -> go.Scattermap:
    '''names of the given waypoints, written next to their centroid (labels, if given, replace the names as text)'''
    centroids = _waypoint_centroids(waypointsDF)
    labels = names if labels is None else labels
    # invisible marker: Scattermap computes the textposition offset from the marker size, and with mode='text'
    # alone the offset is NaN and the names are not drawn at all
    return go.Scattermap(
        lon=[centroids[wp][0] for wp in names], lat=[centroids[wp][1] for wp in names],
        mode='markers+text', text=labels, textposition='top right', textfont=dict(size=12, color='black'),
        marker=dict(size=1, opacity=0),
        hovertext=labels, hoverinfo='text', showlegend=False, name='Waypoint names'
    )

def _trips_colorbar(min_trips : int, max_trips : int) -> dict:
    '''colorbar for a number of trips drawn on a log scale (tick labels in trips, not in log10)'''
    ticks = [t for t in (10, 20, 50, 100, 200, 500, 1000) if min_trips <= t <= max_trips]
    return dict(title='Trip [scala log.]', tickvals=np.log10(ticks), ticktext=[str(t) for t in ticks])

def route_graph_plot(inputDF : p.DataFrame,
                     waypointsDF : p.DataFrame,
                     min_trips : int = 10,
                     self_loops : bool = False,
                     self_loops_must_leave : bool = True,
                     line_width : float = 4,
                     n_points : int = 60,
                     title : str = None,
                     filename : str = None
                     ) -> p.DataFrame:
    '''
    Plots the extracted routes as a directed graph on the map. Waypoints are drawn with their convex hull;
    each route A -> B is an arrow that follows the medoid trip of the route (the most representative actual trajectory),
    so it also shows the path followed by the vessels. Routes that start and end in the same waypoint (A - A) are
    drawn in a separate plot (self_loops=True): there no single path is representative of the trips, so only the
    waypoints involved are drawn, coloured by their number of A - A trips.
    The colour of each arrow (or waypoint) shows the number of trips, on a logarithmic 'portland' scale (same colours as the other plots).
    Routes with an unknown origin or destination ('<NA>') are excluded (see na_routes_plot).
    :param Dataframe inputDF: points ordered by vessel and time. Required columns: "MMSI, LAT, LON, IsInWP, Route"
    :param Dataframe waypointsDF: waypoints. Required columns: "Name, PolygonObj"
    :param int min_trips: only routes with at least this many trips are drawn. Default: 10
    :param bool self_loops: if False, plots the routes between different waypoints (A - B); if True, only the routes
        that come back to the same waypoint (A - A). Default: False
    :param bool self_loops_must_leave: if True, a trip A - A is counted only if it actually leaves waypoint A
        (otherwise most of them are manoeuvres inside the waypoint). Default: True
    :param float line_width: width (px) of the arrows. Default: 4
    :param int n_points: number of points used to resample each trip (and to draw each arrow). Default: 60
    :param str title: Default: None (no title, the plot is used in the thesis where the caption describes it)
    :param str filename: name of the html file saved in plot/. Default: 'route_graph.html' or 'route_graph_self_loops.html'
    Returns a Dataframe with the routes drawn (Origin, Destination, Trips)
    '''
    trips = route_trips(inputDF)
    known = trips[(trips['Origin'] != '<NA>') & (trips['Destination'] != '<NA>')]
    is_loop = known['Origin'] == known['Destination']
    print(f"[route_graph_plot] trips between waypoints: {(~is_loop).sum()}, self-loop trips: {is_loop.sum()} "
          f"(of which leaving the waypoint: {(is_loop & known['LeavesWP']).sum()})")
    if self_loops_must_leave:
        known = known[~is_loop | known['LeavesWP']]
    # keep only one of the two kinds of routes (A - B or A - A)
    known = known[(known['Origin'] == known['Destination']) == self_loops]
    if filename is None:
        filename = 'route_graph_self_loops.html' if self_loops else 'route_graph.html'

    edges = known.groupby(['Origin', 'Destination']).size().reset_index(name='Trips')
    tot_routes = len(edges)
    edges = edges[edges['Trips'] >= min_trips].reset_index(drop=True)
    print(f"[route_graph_plot] routes drawn: {len(edges)} of {tot_routes} (min_trips = {min_trips}), "
          f"covering {edges['Trips'].sum()} of {len(known)} trips")
    if edges.empty:
        print("No routes to be plotted!")
        return edges

    # colour of each route: number of trips on a log scale (the counts span more than an order of magnitude)
    log_min, log_max = np.log10(edges['Trips'].min()), np.log10(edges['Trips'].max())
    normalized = (np.log10(edges['Trips']) - log_min) / ((log_max - log_min) or 1)
    edges['Color'] = sample_colorscale('Portland', normalized.tolist())
    # busiest routes drawn last, so that they stay on top
    edges = edges.sort_values('Trips', ascending=True, ignore_index=True)

    fig = go.Figure()
    fig.add_trace(_domain_trace())
    used = sorted(set(edges['Origin']) | set(edges['Destination']), key=lambda wp: int(wp.split('_')[1]))

    if self_loops:
        _self_loop_waypoints(fig, edges, waypointsDF, log_min, log_max)
        trips_per_wp = dict(edges[['Origin', 'Trips']].values)
        fig.add_trace(_waypoint_names_trace(waypointsDF, used, [f'{wp}: {trips_per_wp[wp]}' for wp in used]))
    else:
        _route_arrows(fig, edges, known, inputDF, waypointsDF, used, n_points, line_width, log_min, log_max)

    fig.update_layout(
        title=title,
        map=dict(
            style=_BASEMAP_STYLE_WITH_TEXT,
            center=dict(lat=(c.LAT_MIN + c.LAT_MAX) / 2, lon=(c.LON_MIN + c.LON_MAX) / 2),
            zoom=6.5
        ),
        margin={'r':0, 't':40 if title else 0, 'l':0, 'b':0},
        legend=_LEGEND
    )
    _save_map(fig, filename)
    return edges.drop(columns='Color').sort_values('Trips', ascending=False, ignore_index=True)

def _self_loop_waypoints(fig : go.Figure, edges : p.DataFrame, waypointsDF : p.DataFrame, log_min : float, log_max : float):
    '''
    draws the waypoints with A - A trips, filled with the colour of their number of trips. A single path cannot
    represent these trips (each one is a loop of a different shape and length), so only the waypoints are shown.
    '''
    polygons = dict(waypointsDF.dropna(subset=['PolygonObj'])[['Name', 'PolygonObj']].values)
    for i, (wp, color) in enumerate(edges[['Origin', 'Color']].values):
        x, y = polygons[wp].exterior.xy
        fig.add_trace(go.Scattermap(
            lon=list(x), lat=list(y), mode='lines', fill='toself',
            fillcolor=color.replace('rgb(', 'rgba(').replace(')', ', 0.6)'), line=dict(width=1.5, color='black'),
            hoverinfo='skip', legendgroup='wp', showlegend=(i == 0), name='Waypoint'
        ))
    # colorbar: Scattermap lines cannot have one, so it is attached to an invisible marker
    fig.add_trace(go.Scattermap(
        lon=[None], lat=[None], mode='markers', hoverinfo='skip', showlegend=False,
        marker=dict(color=[log_min], cmin=log_min, cmax=log_max, colorscale='Portland', showscale=True,
                    colorbar=_trips_colorbar(edges['Trips'].min(), edges['Trips'].max()))
    ))

# textposition for a label placed in the direction 0, 45, ..., 315 degrees (counter-clockwise from east)
_TEXT_POSITIONS = ['middle right', 'top right', 'top center', 'top left',
                   'middle left', 'bottom left', 'bottom center', 'bottom right']

def _nearest_on_segments(points : np.ndarray, seg_start : np.ndarray, seg_end : np.ndarray) -> np.ndarray:
    '''for each point (n x 2), the nearest point of each segment seg_start -> seg_end (m x 2 each). Returns n x m x 2'''
    seg = seg_end - seg_start
    rel = points[:, None, :] - seg_start[None, :, :]
    t = np.clip((rel * seg).sum(axis=2) / np.maximum((seg ** 2).sum(axis=1), 1e-12), 0, 1)
    return seg_start[None, :, :] + t[..., None] * seg[None, :, :]

def _label_positions(routes : list, n_points : int, start : float = 0.25, end : float = 0.75,
                     enough_clearance : float = 0.1, label_shift : float = 0.01) -> list:
    '''
    chooses where to put the number of trips of each route (routes: list of (origin, destination, n_trips, path)).
    The label can go on any point of the arrow between start and end (fractions of the path), on either side of it.
    For each option, the clearance is the distance from the obstacles that lie on the side where the label is shown:
    the other arrows (except the reverse route, which follows the same path) and the labels already placed.
    The option with the largest clearance wins, so that the label is not mistaken for the one of a nearby route.
    Clearances above enough_clearance (degrees, ~11 km) count as equal: then the point closest to the middle and the
    left side of the direction of travel are preferred. Labels are placed from the busiest route to the least busy one.
    label_shift (degrees) approximates how far a placed label is from its anchor, when it is used as an obstacle.
    Returns a list of (lon, lat, text, textposition), in the same order as routes
    '''
    k = np.cos(np.radians(np.mean([path[:, 1].mean() for *_, path in routes])))
    xys = [np.column_stack([path[:, 0] * k, path[:, 1]]) for *_, path in routes]
    candidates = np.arange(int(start * (n_points - 1)), int(end * (n_points - 1)) + 1)
    mid = (n_points - 1) / 2
    placed = []  # approximate positions (scaled x, y) of the labels already placed
    result = [None] * len(routes)
    for i in sorted(range(len(routes)), key=lambda r: -routes[r][2]):
        origin, dest, n_trips, path = routes[i]
        xy = xys[i]
        direction = xy[candidates + 1] - xy[candidates - 1]
        left = np.column_stack([-direction[:, 1], direction[:, 0]])
        left = left / np.maximum(np.linalg.norm(left, axis=1, keepdims=True), 1e-12)
        points = xy[candidates]

        # obstacles: nearest point of every segment of the other arrows, and the labels already placed
        others = [xys[j] for j, (o, d, *_) in enumerate(routes) if j != i and (o, d) != (dest, origin)]
        obstacles = np.zeros((len(candidates), 0, 2))
        if others:
            obstacles = _nearest_on_segments(points, np.concatenate([o[:-1] for o in others]),
                                             np.concatenate([o[1:] for o in others]))
        if placed:
            obstacles = np.concatenate([obstacles, np.broadcast_to(np.array(placed), (len(candidates), len(placed), 2))], axis=1)

        options = []  # (score, distance from the middle, 0 = left / 1 = right, candidate index, side vector)
        for side_id, side in enumerate((left, -left)):
            rel = obstacles - points[:, None, :]
            on_side = (rel * side[:, None, :]).sum(axis=2) > 0
            dist = np.where(on_side, np.hypot(rel[..., 0], rel[..., 1]), np.inf)
            score = np.minimum(dist.min(axis=1) if dist.shape[1] else np.full(len(candidates), np.inf), enough_clearance)
            options += [(-score[c], abs(candidates[c] - mid), side_id, c, side[c]) for c in range(len(candidates))]
        _, _, _, c, side = min(options, key=lambda o: o[:3])
        best = candidates[c]
        placed.append(xy[best] + label_shift * side)
        side_angle = np.degrees(np.arctan2(side[1], side[0]))  # counter-clockwise from east
        # anchored on the path and shifted by textposition (a fixed number of pixels): it stays next to its arrow at any zoom
        result[i] = (path[best, 0], path[best, 1], str(n_trips), _TEXT_POSITIONS[int(np.round(side_angle / 45)) % 8])
    return result

def _route_arrows(fig : go.Figure, edges : p.DataFrame, known : p.DataFrame, inputDF : p.DataFrame, waypointsDF : p.DataFrame,
                  used : list, n_points : int, line_width : float, log_min : float, log_max : float):
    '''draws the routes A -> B as arrows following the medoid trip of each route, with the number of trips next to them'''
    lat_all, lon_all = inputDF['LAT'].to_numpy(), inputDF['LON'].to_numpy()
    # waypoint shapes (convex hulls) of the waypoints involved
    fig.add_trace(_waypoint_shapes_trace(waypointsDF, used))

    routes = []  # (origin, destination, n_trips, medoid path) of each route, used afterwards to place the labels
    for origin, dest, n_trips, color in edges[['Origin', 'Destination', 'Trips', 'Color']].values:
        # single-point trips are counted but have no path to draw
        route_sel = known[(known['Origin'] == origin) & (known['Destination'] == dest) & (known['NumPoints'] >= 2)]
        paths = np.array([_resample_path(lon_all[first:last + 1], lat_all[first:last + 1], n_points)
                          for first, last in route_sel[['FirstIndex', 'LastIndex']].values])
        path = _medoid_path(paths)

        # arrowhead at the end of the path, oriented along its last stretch
        # (the direction is taken over the last ~5% of the path, the very last points can wiggle inside the waypoint)
        k = np.cos(np.radians(path[:, 1].mean()))
        xy = np.column_stack([path[:, 0] * k, path[:, 1]])
        tangent = xy[-1] - xy[-max(2, n_points // 20)]
        tangent = tangent / (np.linalg.norm(tangent) or 1)
        side = np.array([-tangent[1], tangent[0]])
        # arrowhead size stays small on short paths (e.g. inside the harbours)
        path_length = np.hypot(*np.diff(xy, axis=0).T).sum()
        head = min(0.035, 0.08 * path_length)
        arrow = np.array([xy[-1] - head * tangent + 0.6 * head * side, xy[-1], xy[-1] - head * tangent - 0.6 * head * side])
        arrow[:, 0] /= k

        fig.add_trace(go.Scattermap(
            lon=np.concatenate([path[:, 0], [np.nan], arrow[:, 0]]),
            lat=np.concatenate([path[:, 1], [np.nan], arrow[:, 1]]),
            mode='lines', line=dict(width=line_width, color=color),
            showlegend=False, name=f'{origin} → {dest}',
            hovertext=f'{origin} → {dest}: {n_trips} trip', hoverinfo='text'
        ))
        routes.append((origin, dest, n_trips, path))

    # colorbar: Scattermap lines cannot have one, so it is attached to an invisible marker
    fig.add_trace(go.Scattermap(
        lon=[None], lat=[None], mode='markers', hoverinfo='skip', showlegend=False,
        marker=dict(color=[log_min], cmin=log_min, cmax=log_max, colorscale='Portland', showscale=True,
                    colorbar=_trips_colorbar(edges['Trips'].min(), edges['Trips'].max()))
    ))

    labels = {}  # textposition -> (lon, lat, text) of the labels placed on that side of their arrow
    for lon_l, lat_l, text_l, position in _label_positions(routes, n_points):
        group = labels.setdefault(position, ([], [], []))
        group[0].append(lon_l); group[1].append(lat_l); group[2].append(text_l)

    # number of trips next to each arrow (one trace per side: textposition cannot be set point by point in Scattermap).
    # An invisible marker is needed: Scattermap computes the text offset from the marker size, and with mode='text'
    # alone the offset is NaN and the labels are not drawn at all
    for position, (lon_l, lat_l, text_l) in labels.items():
        fig.add_trace(go.Scattermap(
            lon=lon_l, lat=lat_l, mode='markers+text', text=text_l, textposition=position,
            marker=dict(size=1, opacity=0), textfont=dict(size=13, color='black'),
            hoverinfo='skip', showlegend=False, name='Trips'
        ))
    fig.add_trace(_waypoint_names_trace(waypointsDF, used))

def na_routes_plot(inputDF : p.DataFrame,
                   waypointsDF : p.DataFrame,
                   max_points_per_trip : int = 50,
                   title : str = None,
                   filename : str = 'na_routes.html'
                   ) -> p.DataFrame:
    '''
    Plots all the trips whose origin or destination is unknown ('<NA>', i.e. the trip starts or ends
    with an entry/exit point outside any waypoint). Trips with both ends unknown ('<NA> - <NA>') are only counted. '<NA>' has no position, so the actual trajectories are drawn,
    coloured by type, with a white marker on the first point and a black marker on the last point of each trip.
    :param Dataframe inputDF: points ordered by vessel and time. Required columns: "MMSI, LAT, LON, IsInWP, Route"
    :param Dataframe waypointsDF: waypoints. Required columns: "Name, PolygonObj"
    :param int max_points_per_trip: each trajectory is evenly downsampled to at most this many points (first and last always kept). Default: 50
    Returns a Dataframe with the number of trips for each '<NA>' route (Route, Trips)
    '''
    trips = route_trips(inputDF)
    na_trips = trips[(trips['Origin'] == '<NA>') | (trips['Destination'] == '<NA>')].copy()
    # trips with both ends unknown are not linked to any waypoint: they are only counted
    both_unknown = (na_trips['Origin'] == '<NA>') & (na_trips['Destination'] == '<NA>')
    print(f"[na_routes_plot] trips with both ends unknown (<NA> → <NA>), not plotted: {both_unknown.sum()}")
    na_trips = na_trips[~both_unknown]
    if na_trips.empty:
        print("No points to be plotted!")
        return p.DataFrame(columns=['Route', 'Trips'])
    categories = {
        'Origine ignota (<NA> → WP)': (na_trips['Origin'] == '<NA>') & (na_trips['Destination'] != '<NA>'),
        'Destinazione ignota (WP → <NA>)': (na_trips['Origin'] != '<NA>') & (na_trips['Destination'] == '<NA>')
    }
    colors = ['royalblue', 'darkorange']
    lat_all, lon_all = inputDF['LAT'].to_numpy(), inputDF['LON'].to_numpy()

    # waypoints involved in at least one of these trips
    used = sorted((set(na_trips['Origin']) | set(na_trips['Destination'])) - {'<NA>'}, key=lambda wp: int(wp.split('_')[1]))

    fig = go.Figure()
    fig.add_trace(_domain_trace())
    fig.add_trace(_waypoint_shapes_trace(waypointsDF, used))
    start_lat, start_lon, end_lat, end_lon, hover = [], [], [], [], []
    for (name, mask), color in zip(categories.items(), colors):
        selected = na_trips[mask]
        print(f"[na_routes_plot] {name}: {len(selected)} trips")
        lat, lon = [], []
        for first, last, origin, dest, mmsi, route in selected[['FirstIndex', 'LastIndex', 'Origin', 'Destination', 'MMSI', 'Route']].values:
            idx = np.unique(np.linspace(first, last, min(max_points_per_trip, last - first + 1)).round().astype(int))
            lat.extend(lat_all[idx]); lat.append(np.nan)
            lon.extend(lon_all[idx]); lon.append(np.nan)
            start_lat.append(lat_all[first]); start_lon.append(lon_all[first])
            end_lat.append(lat_all[last]); end_lon.append(lon_all[last])
            hover.append(f'MMSI: {mmsi}<br>Rotta: {route}')
        fig.add_trace(go.Scattermap(
            lat=lat, lon=lon, mode='lines',
            line=dict(width=1.5, color=color), opacity=0.6,
            hoverinfo='skip', name=f'{name}: {len(selected)} trip'
        ))

    # first point: white marker with a black border (Scattermap markers have no border, so a larger black marker is drawn below)
    fig.add_trace(go.Scattermap(
        lat=start_lat, lon=start_lon, mode='markers', marker=dict(size=9, color='black'),
        hoverinfo='skip', legendgroup='start', showlegend=False, name='Inizio del trip'
    ))
    fig.add_trace(go.Scattermap(
        lat=start_lat, lon=start_lon, mode='markers', marker=dict(size=6, color='white'),
        hovertext=[h + '<br>(inizio)' for h in hover], hoverinfo='text', legendgroup='start', name='Inizio del trip'
    ))
    fig.add_trace(go.Scattermap(
        lat=end_lat, lon=end_lon, mode='markers', marker=dict(size=7, color='black'),
        hovertext=[h + '<br>(fine)' for h in hover], hoverinfo='text', name='Fine del trip'
    ))
    fig.add_trace(_waypoint_names_trace(waypointsDF, used))

    fig.update_layout(
        title=title,
        map=dict(
            style=_BASEMAP_STYLE_WITH_TEXT,
            center=dict(lat=(c.LAT_MIN + c.LAT_MAX) / 2, lon=(c.LON_MIN + c.LON_MAX) / 2),
            zoom=6.5
        ),
        margin={'r':0, 't':40 if title else 0, 'l':0, 'b':0},
        legend=_LEGEND
    )
    _save_map(fig, filename)
    return na_trips.groupby('Route').size().reset_index(name='Trips').sort_values('Trips', ascending=False, ignore_index=True)

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
