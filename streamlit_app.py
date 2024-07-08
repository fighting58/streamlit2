import streamlit as st
import geopandas as gpd
from pyproj import CRS, Transformer
import plotly.express as px
from shapely.geometry import Point, Polygon, MultiPolygon, LineString
import json
import plotly.io as pio
import tempfile

def swap_xy(geometry):
    # Transform coordinates from EPSG:5186 to EPSG:4326
    transformer = Transformer.from_crs(CRS.from_epsg(5186), CRS.from_epsg(4326), always_xy=True)

    if isinstance(geometry, Point):
        return Point(transformer.transform(geometry.x, geometry.y))
    elif isinstance(geometry, LineString):
        return LineString([transformer.transform(x, y) for x, y in geometry.coords])
    elif isinstance(geometry, Polygon):
        new_exterior = [transformer.transform(x, y) for x, y in geometry.exterior.coords]
        new_interiors = [[transformer.transform(x, y) for x, y in interior.coords] for interior in geometry.interiors]
        return Polygon(new_exterior, new_interiors)
    elif isinstance(geometry, MultiPolygon):
        new_polygons = []
        for polygon in geometry.geoms:
            new_exterior = [transformer.transform(x, y) for x, y in polygon.exterior.coords]
            new_interiors = [[transformer.transform(x, y) for x, y in interior.coords] for interior in polygon.interiors]
            new_polygons.append(Polygon(new_exterior, new_interiors))
        return MultiPolygon(new_polygons)
    else:
        raise TypeError("Unsupported geometry type")

# Streamlit configuration
st.title("이지목현황")
st.write("(경기도 00시 00면 00리)")

# GeoJSON file upload
# geojson_file = st.file_uploader("Upload GeoJSON file", type="geojson")
geojson_file1 = "이지목현황.geojson"
geojson_file2 = "본필지.geojson"

color_discrete_map = {
        "제외지": "#ffffff"    
    }

if geojson_file1:
    # Read GeoJSON data using GeoPandas
    gdf1 = gpd.read_file(geojson_file1)
    gdf2 = gpd.read_file(geojson_file2)
    
    # Swap x, y coordinates
    gdf1['geometry'] = gdf1['geometry'].apply(swap_xy)    
    gdf2['geometry'] = gdf2['geometry'].apply(swap_xy)

    # Convert to EPSG:4326 (WGS84)
    gdf1 = gdf1.to_crs(epsg=4326)
    gdf2 = gdf2.to_crs(epsg=4326)
    centroid = gdf1.geometry.centroid
    center_lat = centroid.y.mean()
    center_lon = centroid.x.mean()

    geojson_data1 = json.loads(gdf1.to_json())
    geojson_data2 = json.loads(gdf2.to_json())

    # Visualize using Plotly
    fig = px.choropleth(
        gdf1,
        geojson=geojson_data1,
        locations="SYMBOL",
        color="USAGE",
        labels="JIBUN",
        color_discrete_map=color_discrete_map,
        featureidkey="properties.SYMBOL",
        custom_data=[gdf1["JIBUN"], gdf1["SYMBOL"], gdf1['USAGE'], gdf1['AREA']],
        center={"lat": center_lat, "lon": center_lon},
    )
    fig.update_geos(fitbounds="locations",visible=False)

    hovertemp = '<b>%{customdata[0]} </b><i style="color:red">%{customdata[1]}</i><br>'
    hovertemp += '<i>%{customdata[2]}</i><br>'
    hovertemp += '<i>%{customdata[3]}㎡</i><br>'

    fig.update_traces(hovertemplate=hovertemp)

    # 본필지

    fig.update_layout(
        mapbox=dict(
            style="white-bg",
            center={"lat": center_lat, "lon": center_lon},
            zoom=15
        ),
        margin={"r":0,"t":0,"l":0,"b":0}
    )

    # Display the Plotly plot in Streamlit
    st.plotly_chart(fig, user_container_width=True )


