import streamlit as st
import geopandas as gpd
from pyproj import CRS, Transformer
import plotly.graph_objects as go
import random
from shapely.geometry import Point, Polygon, MultiPolygon, LineString
import json
import numpy as np

def swap_xy(geometry):
    """
    Transform coordinates from EPSG:5186 to EPSG:4326
    """
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

def generate_random_hex_color():
    """
    랜덤하게 색상 hex코드 생성
    """
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))


def find_internal_centroid(multi_polygon):
    """
    폴리곤의 중심점 반환, 폴리곤 외부에 있을 시 폴리곤 내부점으로 이동한 좌표 반환
    """
    # 무게 중심 계산
    centroid = multi_polygon.centroid

    # 무게 중심이 MultiPolygon 내부에 있는지 확인
    if multi_polygon.contains(centroid):
        return centroid
    else:
        # MultiPolygon의 경계 내부의 점을 샘플링하여, 무게 중심과 가장 가까운 내부 점을 찾기
        min_distance = float('inf')
        best_point = None

        # 샘플링된 점 중 무게 중심과 가장 가까운 내부 점을 찾기
        num_samples = 2000
        min_x, min_y, max_x, max_y = multi_polygon.bounds
        for _ in range(num_samples):
            random_point = Point(np.random.uniform(min_x, max_x), np.random.uniform(min_y, max_y))
            if multi_polygon.contains(random_point):
                distance = random_point.distance(centroid)
                if distance < min_distance:
                    min_distance = distance
                    best_point = random_point

        if best_point:
            return best_point
        else:
            raise ValueError("Failed to find a suitable point inside the MultiPolygon.")

# Streamlit configuration
st.title("이지목현황")
st.write("(경기도 00시 00면 00리)")

# 지목별 색상 인덱스 지정, 지정색 이외의 현황은 로딩시 색상이 변함
color_discrete_map = {
        "제외지": 0,
        "도로": 1,
        "구거": 2,
        "대지": 3,
        "임야": 4,
        "답": 5,
        "전": 6    
    }
# 지목 인덱스 별 채움색 지정
colorscales = [((0.0, '#eeeeee'), (1.0, '#eeeeee')),    # 제외지
                ((0.0, '#999999'), (1.0, '#999999')),   # 도로
                ((0.0, '#222288'), (1.0, '#222288')),   # 구거
                ((0.0, '#882222'), (1.0, '#882222')),   # 대지
                ((0.0, '#222288'), (1.0, '#222288')),   # 임야
                ((0.0, '#445511'), (1.0, '#445511')),   # 답
                ((0.0, '#94C056'), (1.0, '#94C056'))    # 전
]


# GeoJSON file upload
# geojson_file = st.file_uploader("Upload GeoJSON file", type="geojson")

# geojson_file: 세계측지계 좌표(espg:5186), 이지목 현황 
geojson_file1 = "이지목현황.geojson"
geojson_file2 = "본필지.geojson"

if geojson_file1:
    # Read GeoJSON data using GeoPandas
    gdf1 = gpd.read_file(geojson_file1)
    gdf2 = gpd.read_file(geojson_file2)
    
    # Swap x, y coordinates
    # 세계좌표(espg:5186) -> WGS84 경위도좌표(espg:4326)으로 좌표 변환
    gdf1['geometry'] = gdf1['geometry'].apply(swap_xy)    
    gdf2['geometry'] = gdf2['geometry'].apply(swap_xy)

    # 지도 중심좌표
    centroid = gdf1.geometry.centroid
    center_lat = centroid.y.mean()
    center_lon = centroid.x.mean()

    geojson_data1 = json.loads(gdf1.to_json())
    geojson_data2 = json.loads(gdf2.to_json())

    # Visualize using Plotly
    fig = go.Figure()

    # 이지목 종류만큼 색상표 추가(실제 색상목록수는 이지목수량보다 클 수 있음)
    for i in range(len(gdf1['USAGE'].unique())):
        color_hex = generate_random_hex_color()
        colorscales.append(((0.0, color_hex), (1.0, color_hex)))

    # 지목별 현황도 생성
    for i, usage in enumerate(gdf1['USAGE'].unique()):  # 이용현황별 생성
        dfp = gdf1[gdf1['USAGE'] == usage]
        if usage in color_discrete_map.keys():          # 이지목 인덱스 적용
            idx = color_discrete_map[usage]
        else:
            idx = i + len(color_discrete_map)

        fig.add_trace(go.Choroplethmapbox(geojson=geojson_data1, 
                                            locations=dfp['SYMBOL'],  # 고유값(여기서는 부호)
                                            z=[idx,] * len(dfp),  # z값이 색상과 연계, z에 해당 이지목 수량만큼 인덱스 생성
                                            featureidkey="properties.SYMBOL",  # 고유값 키(여기서는 부호)
                                            showlegend=True,  # 범례표시(이용현황)
                                            name=usage,  # trace명 => 이용현황
                                            marker=dict(opacity=0.8, line=dict(color='red', width=1)), # 마커 스타일(투명도 80%, 선색: 빨강, 선두께: 1)
                                            colorscale=colorscales[idx],   # 색상표에 의한 색상(z값에 의함)
                                            customdata = list(zip(dfp['JIBUN'],dfp["USAGE"], dfp['AREA'])),  # 추가 데이터
                                            hoverlabel=dict(bgcolor="whitesmoke", namelength=0),  # 레이블 서식(배경색: 옅은회색, 고유값표시 X)
                                            showscale=False))
        # 마우스를 올릴 때 표현 
        hovertemp = '<b>%{customdata[0]} <i style="color:red;">%{location}</i></b><br><br>'
        hovertemp += '<b>이용현황: <i>%{customdata[1]}</i></b><br>'
        hovertemp += '<b>점유면적: <i>%{customdata[2]}㎡</i></b><br>'
        fig.update_traces(hovertemplate=hovertemp)

    # 원필지 도형 생성
    for row in geojson_data2['features']:
        fig.add_trace(go.Scattermapbox(
            lon=[lon for lon, lat in row['geometry']['coordinates'][0][0]],  # x 좌표들
            lat=[lat for lon, lat in row['geometry']['coordinates'][0][0]],  # y 좌표들
            mode='lines',  # 타입설정(marker, lines, text)
            line=dict(color='black', width=1.5),  # 선 스타일
            name=row['properties']['JIBUN'],  # trace명 => 지번 
            showlegend=False,  # 범례 X
            hoverinfo='skip'  # hoverinfo 설정을 통해 hover시 정보 제외, 마우스 올려도 정보 표시 X
            )
    )

    # 지번 생성
    fig.add_trace(go.Scattermapbox(
        lon=[find_internal_centroid(geom).x for geom in gdf2["geometry"]],
        lat=[find_internal_centroid(geom).y for geom in gdf2["geometry"]],
        mode='text',  # 타입 설정
        text=gdf2["JIBUN"],  # 삽입할 문자는 지번
        textposition="middle center",  # 텍스트 삽입점("(top|middle|bottom) (left|center|right)")
        textfont=dict(size=12, color="black"),  # 텍스트 크기/색상
        name="지번",  #trace명 => "지번"
        hoverinfo='skip'  # hoverinfo 설정을 통해 hover시 정보 제외
        )
    )
    ######################

    # 지도 설정(배경없음, 지도중심점 및 줌레벨 지정)
    fig.update_layout(
        mapbox=dict(
            style= 'white-bg',  # ,"carto-positron"
            center={"lat": center_lat, "lon": center_lon},
            zoom=15
        ),
        margin={"r":0,"t":0,"l":0,"b":0}
    )

    # Display the Plotly plot in Streamlit
    st.plotly_chart(fig, user_container_width=True)

        
