"""OpenLineage emission helpers for the BIM pipeline.

Produces OpenLineage v2 events for each Phase, including:

- Schema facets   (column names + types of Bronze/Gold datasets)
- DataSource      (file://, sqlite://, palantir:// namespaces)
- Documentation   (per-dataset description)
- ColumnLineage   (Bronze column -> Gold column mapping)
- Statistics      (row count, byte size)
- JobType         (BATCH / PYTHON)
- SourceCode      (git revision, file path)

Events are written to ``data/lineage/{SNAPSHOT}/openlineage-events.jsonl``
and are inspectable without a Marquez/DataHub backend.
"""

from bimkg.lineage.openlineage_emitter import emit_pipeline_events

__all__ = ["emit_pipeline_events"]
