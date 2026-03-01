import pandas as pd

from tbmeta.data.gene_mapping import map_probes_to_genes


def test_gene_mapping_collapses_probe_level_to_gene_level():
    expr = pd.DataFrame(
        {
            "probe_id": ["p1", "p2", "p3"],
            "S1": [1.0, 2.0, 3.0],
            "S2": [1.5, 2.5, 3.5],
        }
    )
    ann = pd.DataFrame({"probe_id": ["p1", "p2", "p3"], "gene_symbol": ["G1", "G1", "G2"]})
    gene_df, report = map_probes_to_genes(expr, ann)
    assert set(gene_df["gene_symbol"]) == {"G1", "G2"}
    assert report["n_unique_genes"].iloc[0] == 2
