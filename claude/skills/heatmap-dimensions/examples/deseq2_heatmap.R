#!/usr/bin/env Rscript
#############################################
## Example: DESeq2 Results Heatmap
## Author: Samuel Ahuno
## Date: 2026-01-30
##
## Creates a publication-ready heatmap from DESeq2 differential
## expression results using ComplexHeatmap
#############################################

# --- Load packages ------------------------------------------------------------
library(DESeq2)
library(ComplexHeatmap)
library(viridis)
library(dplyr)

# --- Source dimension calculation functions -----------------------------------
source("/data1/greenbab/users/ahunos/apps/llm_configs/claude/skills/heatmap-dimensions/calc_heatmap_dimensions.R")

# --- Example with airway dataset ----------------------------------------------
library(airway)
data("airway")

# Create DESeq2 object
dds <- DESeqDataSet(airway, design = ~ dex)
dds <- DESeq(dds)

# Get results
res <- results(dds, contrast = c("dex", "trt", "untrt"))

# Select top 30 DE genes by adjusted p-value
top_genes <- res %>%
  as.data.frame() %>%
  filter(!is.na(padj)) %>%
  arrange(padj) %>%
  head(30) %>%
  rownames()

# Get normalized counts and subset
vsd <- vst(dds, blind = FALSE)
expr_matrix <- assay(vsd)[top_genes, ]

# --- Calculate dimensions -----------------------------------------------------
dims <- calc_heatmap_dimensions(
  n_genes = nrow(expr_matrix),
  n_samples = ncol(expr_matrix),
  n_annotation_tracks = 1
)

# --- Prepare data -------------------------------------------------------------
# Scale by row (z-score)
expr_scaled <- scale_matrix_by_row(expr_matrix)

# Sample metadata
sample_metadata <- data.frame(
  Treatment = colData(dds)$dex,
  row.names = colnames(expr_matrix)
)

# --- Create heatmap -----------------------------------------------------------
ht <- create_publication_heatmap(
  matrix = expr_scaled,
  dims = dims,
  column_annotation = sample_metadata,
  title = "Top 30 Differentially Expressed Genes",
  name = "Z-score",
  annotation_colors = list(
    Treatment = c("untrt" = "#0072B2", "trt" = "#D55E00")
  )
)

# --- Save ---------------------------------------------------------------------
output_dir <- "figures"
save_heatmap(ht, "deseq2_top30_heatmap", dims, output_dir)

message("\n=== Complete ===")
message("Heatmap saved to: ", output_dir)
message("Dimensions: ", dims$width_mm, "mm x ", dims$height_mm, "mm")
