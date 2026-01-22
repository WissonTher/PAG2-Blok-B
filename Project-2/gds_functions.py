from neo4j import GraphDatabase, basic_auth
import shapely
import geopandas
import pandas
from pyproj.datadir import set_data_dir

set_data_dir(r'C:\Users\razu\AppData\Local\miniconda3\envs\conda\Library\share\proj')

driver = GraphDatabase.driver(
    "bolt://3.239.108.52:7687",
    auth=basic_auth("neo4j", "fireballs-enemies-print")
)

BINS = [0, 300, 600, 900, 1200, 1500, 1800, 2100, 2400, 2700, 3000, 3300, 3600, 3900, 4200, 4500, 4800, 5100, 5400, 5700, 6000, 6300, 6600, 6900, 7200]


def nearest_node(typ="s", ext=None):
    ext_s = f"{', '.join(ext)}, " if ext else ""
    return f"""
        MATCH ({typ}:Point)
        WITH {ext_s}{typ}, ({typ}.x - ${typ}x)^2 + ({typ}.y - ${typ}y)^2 AS dist
        ORDER BY dist ASC LIMIT 1
        """


def dijkstratarget(start_y, start_x, target_y, target_x):
    request = f"""
            {nearest_node("s")}
            {nearest_node("t", ext=["s"])}
            CALL gds.shortestPath.dijkstra.stream('mapaDrogowa', {{
                sourceNode: s,
                targetNode: t,
                relationshipWeightProperty: 'time'
            }})
            YIELD nodeIds, costs
            RETURN 
                costs[-1] AS total_cost,
                [id IN nodeIds | [gds.util.asNode(id).x, gds.util.asNode(id).y]] AS trace
        """

    with driver.session() as session:
        result = session.run(request, sx=float(start_x), sy=float(start_y), tx=float(target_x),
                             ty=float(target_y)).single()

    if not result or result["trace"] is None:
        return None

    geom = shapely.LineString(result["trace"])
    gdf = geopandas.GeoDataFrame(
        {"cost": [result["total_cost"]], "distance": [geom.length]},
        geometry=[geom],
        crs="EPSG:2180"
    )
    return gdf.to_json()


def astar(start_y, start_x, target_y, target_x):
    request = f"""
        {nearest_node("s")}
        {nearest_node("t", ext=["s"])}
        CALL gds.shortestPath.astar.stream('mapaDrogowa', {{
            sourceNode: s,
            targetNode: t,
            latitudeProperty: 'y', 
            longitudeProperty: 'x',
            relationshipWeightProperty: 'time'
        }})
        YIELD nodeIds, costs
        RETURN 
            costs[-1] AS total_cost,
            [id IN nodeIds | [gds.util.asNode(id).x, gds.util.asNode(id).y]] AS trace
        """

    with driver.session() as session:
        result = session.run(request, sx=float(start_x), sy=float(start_y), tx=float(target_x),
                             ty=float(target_y)).single()

    if not result or result["trace"] is None:
        return None

    geom = shapely.LineString(result["trace"])
    gdf = geopandas.GeoDataFrame(
        {"cost": [result["total_cost"]], "distance": [geom.length]},
        geometry=[geom],
        crs="EPSG:2180"
    )
    return gdf.to_json()


def dijkstraranges(start_y, start_x, max_cost, max_buffer, step, simplified=False):
    request = f"""
    {nearest_node("s")}
    CALL gds.allShortestPaths.dijkstra.stream('mapaDrogowa', {{
        sourceNode: s,
        relationshipWeightProperty: 'time'
    }})
    YIELD targetNode, totalCost, nodeIds
    WHERE totalCost <= $max_cost
    RETURN 
        totalCost as cost,
        [id IN nodeIds | [gds.util.asNode(id).x, gds.util.asNode(id).y]] AS trace
    """

    geom = []
    with driver.session() as session:
        ret = session.run(request, sx=float(start_x), sy=float(start_y), max_cost=float(max_cost))

        for r in ret:
            trace = r["trace"]
            if len(trace) > 1:
                cost = r["cost"]
                buff = max(1, int(max_buffer) - (int(step) * (cost // 300)))

                line = shapely.LineString(trace)
                if simplified:
                    line = line.simplify(tolerance=5)

                geom.append({'cost': cost, 'geometry': line.buffer(buff)})

    if not geom:
        return None

    gdf = geopandas.GeoDataFrame(geom, crs="EPSG:2180")
    gdf['grupy'] = pandas.cut(gdf['cost'], bins=BINS).astype(str)

    dis = gdf.dissolve(by='grupy', aggfunc={'cost': 'max'})
    dis = dis.sort_values('cost', ascending=False).reset_index(drop=True)

    sort = dis.copy()
    for i in range(0, len(dis) - 1):
        sort.at[i, 'geometry'] = dis.at[i, 'geometry'].difference(dis.at[i + 1, 'geometry'])

    return sort.to_json()

# geojson = dijkstratarget(186940.80, 502461.75, 207331.00, 528063.05)
# geojson = astar(186940.80, 502461.75, 207331.00, 528063.05)
# geojson = dijkstraranges(186940.80, 502461.75, 600, 20, 300, simplified=True)
print(geojson)