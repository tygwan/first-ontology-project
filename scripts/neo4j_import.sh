#!/usr/bin/env bash
# Neo4j import script — reproducible Docker setup + data load
# Usage: bash scripts/neo4j_import.sh [start|load|stop|reset]
#
# Prerequisites: Docker running, data generated via Phase 1-4 pipeline
set -euo pipefail

CONTAINER="bimkg-neo4j"
NEO4J_USER="neo4j"
NEO4J_PASS="bimkg2026"
NEO4J_IMAGE="neo4j:5-community"
IMPORT_DIR="$(cd "$(dirname "$0")/.." && realpath data/ontology/2026-04-12/neo4j)"

cypher() {
    docker exec "$CONTAINER" cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASS" "$1"
}

cmd_start() {
    if docker ps -q -f name="$CONTAINER" | grep -q .; then
        echo "Container $CONTAINER is already running"
    elif docker ps -aq -f name="$CONTAINER" | grep -q .; then
        echo "Starting existing container..."
        docker start "$CONTAINER"
    else
        echo "Creating new container..."
        docker run -d \
            --name "$CONTAINER" \
            -p 7474:7474 -p 7687:7687 \
            -e NEO4J_AUTH="${NEO4J_USER}/${NEO4J_PASS}" \
            -e NEO4J_server_memory_heap_max__size=1G \
            -v "$IMPORT_DIR":/import \
            "$NEO4J_IMAGE"
    fi

    echo "Waiting for Neo4j..."
    for i in $(seq 1 30); do
        if docker logs "$CONTAINER" 2>&1 | grep -q "Started."; then
            echo "Neo4j ready at http://localhost:7474 ($NEO4J_USER/$NEO4J_PASS)"
            return 0
        fi
        sleep 2
    done
    echo "ERROR: Neo4j did not start in 60s"
    return 1
}

cmd_load() {
    echo "Wiping existing data..."
    cypher "MATCH (n) DETACH DELETE n;"

    echo "Loading nodes..."
    cypher "
    LOAD CSV WITH HEADERS FROM 'file:///nodes_objects.csv' AS row
    CREATE (:BIMObject {
        objectId: row.\`objectId:ID\`, displayName: row.displayName,
        refinedClass: row.refinedClass,
        centroidX: toFloat(row.\`centroidX:double\`),
        centroidY: toFloat(row.\`centroidY:double\`),
        centroidZ: toFloat(row.\`centroidZ:double\`),
        dryWeightKg: toFloat(row.\`dryWeightKg:double\`),
        confidence: row.confidence
    });"
    cypher "LOAD CSV WITH HEADERS FROM 'file:///nodes_pipelines.csv' AS row
    CREATE (:Pipeline {pipelineId: row.\`pipelineId:ID\`, name: row.name});"
    cypher "LOAD CSV WITH HEADERS FROM 'file:///nodes_zones.csv' AS row
    CREATE (:Zone {zoneId: row.\`zoneId:ID\`, zoneNumber: toInteger(row.\`zoneNumber:int\`)});"

    echo "Creating indexes..."
    cypher "CREATE INDEX obj_id IF NOT EXISTS FOR (o:BIMObject) ON (o.objectId);
    CREATE INDEX pipe_id IF NOT EXISTS FOR (p:Pipeline) ON (p.pipelineId);
    CREATE INDEX zone_id IF NOT EXISTS FOR (z:Zone) ON (z.zoneId);"

    echo "Loading edges (this takes ~2 min)..."
    for csv_file in edges_adjacent_to_enriched edges_has_parent edges_belongs_to_pipeline edges_in_zone edges_must_precede_sm edges_zone_precedes; do
        if [ ! -f "$IMPORT_DIR/${csv_file}.csv" ]; then
            echo "  SKIP: ${csv_file}.csv not found"
            continue
        fi
        local rel_type
        case "$csv_file" in
            edges_adjacent_to_enriched)
                cypher "LOAD CSV WITH HEADERS FROM 'file:///${csv_file}.csv' AS row
                CALL { WITH row
                    MATCH (s:BIMObject {objectId: row.\`:START_ID\`})
                    MATCH (t:BIMObject {objectId: row.\`:END_ID\`})
                    CREATE (s)-[:ADJACENT_TO {relationType: row.relationType,
                        distanceM: toFloat(row.\`distanceM:double\`),
                        overlapM3: toFloat(row.\`overlapM3:double\`)}]->(t)
                } IN TRANSACTIONS OF 10000 ROWS;" ;;
            edges_has_parent)
                cypher "LOAD CSV WITH HEADERS FROM 'file:///${csv_file}.csv' AS row
                CALL { WITH row
                    MATCH (c:BIMObject {objectId: row.\`:START_ID\`})
                    MATCH (p:BIMObject {objectId: row.\`:END_ID\`})
                    CREATE (c)-[:HAS_PARENT]->(p)
                } IN TRANSACTIONS OF 10000 ROWS;" ;;
            edges_belongs_to_pipeline)
                cypher "LOAD CSV WITH HEADERS FROM 'file:///${csv_file}.csv' AS row
                CALL { WITH row
                    MATCH (o:BIMObject {objectId: row.\`:START_ID\`})
                    MATCH (p:Pipeline {pipelineId: row.\`:END_ID\`})
                    CREATE (o)-[:BELONGS_TO_PIPELINE]->(p)
                } IN TRANSACTIONS OF 5000 ROWS;" ;;
            edges_in_zone)
                cypher "LOAD CSV WITH HEADERS FROM 'file:///${csv_file}.csv' AS row
                CALL { WITH row
                    MATCH (o:BIMObject {objectId: row.\`:START_ID\`})
                    MATCH (z:Zone {zoneId: row.\`:END_ID\`})
                    CREATE (o)-[:IN_ZONE]->(z)
                } IN TRANSACTIONS OF 5000 ROWS;" ;;
            edges_must_precede_sm)
                cypher "LOAD CSV WITH HEADERS FROM 'file:///${csv_file}.csv' AS row
                CALL { WITH row
                    MATCH (s:BIMObject {objectId: row.\`:START_ID\`})
                    MATCH (t:BIMObject {objectId: row.\`:END_ID\`})
                    CREATE (s)-[:MUST_PRECEDE {edgeType: row.edgeType,
                        onCriticalPath: row.onCriticalPath = 'True'}]->(t)
                } IN TRANSACTIONS OF 10000 ROWS;" ;;
            edges_zone_precedes)
                cypher "LOAD CSV WITH HEADERS FROM 'file:///${csv_file}.csv' AS row
                CALL { WITH row
                    MATCH (z1:Zone {zoneId: row.\`:START_ID\`})
                    MATCH (z2:Zone {zoneId: row.\`:END_ID\`})
                    CREATE (z1)-[:ZONE_PRECEDES {dependencies: toInteger(row.\`dependencies:int\`)}]->(z2)
                } IN TRANSACTIONS OF 500 ROWS;" ;;
        esac
        echo "  Loaded: ${csv_file}"
    done

    # Zone properties
    cypher "LOAD CSV WITH HEADERS FROM 'file:///zone_schedule.csv' AS row
    MATCH (z:Zone {zoneId: row.zoneId})
    SET z.installRank = toInteger(row.\`installRank:int\`),
        z.objectCount = toInteger(row.\`objectCount:int\`),
        z.equipmentCount = toInteger(row.\`equipmentCount:int\`),
        z.totalWeightKg = toFloat(row.\`totalWeightKg:double\`);"

    # Critical path
    cypher "LOAD CSV WITH HEADERS FROM 'file:///critical_path_steps.csv' AS row
    MATCH (o:BIMObject {objectId: row.objectId})
    SET o.criticalStep = toInteger(row.\`criticalStep:int\`), o.onCriticalPath = true;"

    echo ""
    echo "=== Import complete ==="
    cypher "MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS cnt ORDER BY cnt DESC;"
}

cmd_stop() {
    docker stop "$CONTAINER" 2>/dev/null && echo "Stopped $CONTAINER" || echo "Not running"
}

cmd_reset() {
    docker rm -f "$CONTAINER" 2>/dev/null && echo "Removed $CONTAINER" || echo "Not found"
}

case "${1:-help}" in
    start) cmd_start ;;
    load)  cmd_load ;;
    stop)  cmd_stop ;;
    reset) cmd_reset ;;
    *)
        echo "Usage: $0 {start|load|stop|reset}"
        echo "  start — create/start Neo4j container"
        echo "  load  — wipe + import all CSV data"
        echo "  stop  — stop container (data preserved)"
        echo "  reset — remove container entirely"
        ;;
esac
