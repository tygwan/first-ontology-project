"""Phase 1d exporters: Power BI star schema + Foundry Object/Link Types.

The exporters read the Gold parquet files produced by Phase 1a
(``bim_objects_enriched.parquet`` and ``bim_adjacency_sym.parquet``)
and write them to two downstream formats:

- :mod:`bimkg.ingest.exporters.powerbi` — 12 CSV star schema files
- :mod:`bimkg.ingest.exporters.foundry` — 6 Object Type + 4 Link Type parquet
"""
