from db.neo4j_client import upsert_incident_graph, get_all_incidents_cytoscape
import json

upsert_incident_graph({
    'trace_id': 'test-123',
    'timestamp': '2026-05-10T10:00:00Z',
    'classification': 'Test',
    'blast_radius': 'HIGH',
    'root_cause': 'Test root cause',
    'status': 'active',
    'confidence_score': 0.8,
    'summary': 'Test summary',
    'service': 'test-service'
})

print(json.dumps(get_all_incidents_cytoscape(), indent=2))
